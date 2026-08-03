"""PySide window for the isolated ODIA desktop runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QSize, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent, QIcon, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..device_setup.context import Context
from ..models.catalog import get_model_option
from ..paths import PROJECT_ROOT
from ..story.generator import StoryGenerator, StoryResult, create_story_generator
from ..story.session import CropEvent, SessionRecorder
from ..story.worker import StoryWorker
from ..voice_text_convert.parse_and_match_module import Text_Manager
from .camera_video import CameraVideoStream
from .fake_video import FakeVideoStream
from .whisper_stream import WhisperStream
from .yolo_detection import YoloDetector

VideoStream = FakeVideoStream | CameraVideoStream


class RuntimeWindow(QMainWindow):
    """Present live vision, voice control, and typed object instructions."""

    command_submitted = Signal(str)
    quit_requested = Signal()

    def __init__(
        self,
        context: Context | None = None,
        video_stream: VideoStream | None = None,
        session_recorder: SessionRecorder | None = None,
        story_generator: StoryGenerator | None = None,
    ) -> None:
        super().__init__()
        self._context = context
        self._current_frame: QImage | None = None
        self._last_queued_classes: tuple[str, ...] = ()
        self._session_recorder = session_recorder or SessionRecorder(
            PROJECT_ROOT / "outputs" / "story_sessions"
        )
        self._story_generator = story_generator or create_story_generator()
        self._story_worker: StoryWorker | None = None
        self._text_manager_context = Text_Manager()
        self._text_manager = self._text_manager_context.__enter__()
        supported_classes = self._text_manager.get_supported_yolo_classes()
        if video_stream is not None:
            self._video_stream = video_stream
        elif context is not None:
            camera = context.camera.info
            self._video_stream = CameraVideoStream(
                index=camera.index,
                backend=camera.backend,
                name=camera.name,
                detector=YoloDetector(
                    context.models.vision_id,
                    supported_classes=supported_classes,
                ),
                parent=self,
            )
        else:
            self._video_stream = FakeVideoStream(parent=self)
        self._whisper_stream = (
            WhisperStream(
                model_id=context.models.voice_id,
                device_id=context.audio_input.info.index,
                parent=self,
            )
            if context is not None
            else None
        )
        self.setWindowTitle("ODIA Live")
        self.resize(1280, 800)
        self.setMinimumSize(900, 620)
        self.setCentralWidget(self._build_content())
        self.setStyleSheet(self._stylesheet())
        self._video_stream.frame_ready.connect(self.display_frame)
        self._video_stream.error.connect(self.show_video_error)
        self._video_stream.model_status.connect(self.show_model_status)
        self._video_stream.detections_ready.connect(self.show_detections)
        self._video_stream.keyword_queue_changed.connect(
            self.show_keyword_queue,
        )
        self._video_stream.active_classes_changed.connect(
            self.show_active_classes,
        )
        self._video_stream.detection_frame_ready.connect(self.record_story_frame)
        if self._whisper_stream is not None:
            self._whisper_stream.status_changed.connect(self.show_whisper_status)
            self._whisper_stream.transcript_ready.connect(self.receive_transcript)
            self._whisper_stream.error.connect(self.show_whisper_error)
            self._whisper_stream.finished.connect(self._whisper_finished)
        self._video_stream.start()
        QTimer.singleShot(0, self._refresh_video_panel)

    @property
    def video_stream(self) -> VideoStream:
        """Return the preview source so its lifecycle can be inspected."""
        return self._video_stream

    def _build_content(self) -> QWidget:
        content = QWidget()
        page = QVBoxLayout(content)
        page.setContentsMargins(16, 14, 16, 14)
        page.setSpacing(12)
        page.addWidget(self._build_top_rail())

        body = QHBoxLayout()
        body.setSpacing(12)
        main_column = QVBoxLayout()
        main_column.setSpacing(12)
        main_column.addWidget(self._build_video_panel(), stretch=1)
        main_column.addWidget(self._build_command_dock())
        body.addLayout(main_column, stretch=1)
        body.addWidget(self._build_crop_sidebar())
        page.addLayout(body, stretch=1)

        return content

    def _build_crop_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("object-crop-sidebar")
        sidebar.setMinimumWidth(260)
        sidebar.setMaximumWidth(320)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        heading = QLabel("STORY OBJECT CROPS")
        heading.setObjectName("status-heading")
        layout.addWidget(heading)

        queue_status = QLabel("0 crops queued for Codex")
        queue_status.setObjectName("crop-queue-status")
        layout.addWidget(queue_status)

        preview = QLabel("Click an object crop to inspect it")
        preview.setObjectName("crop-preview")
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumHeight(170)
        preview.setWordWrap(True)
        layout.addWidget(preview)

        details = QLabel("No object crop selected")
        details.setObjectName("crop-details")
        details.setWordWrap(True)
        layout.addWidget(details)

        gallery = QListWidget()
        gallery.setObjectName("crop-gallery")
        gallery.setViewMode(QListView.ViewMode.IconMode)
        gallery.setResizeMode(QListView.ResizeMode.Adjust)
        gallery.setMovement(QListView.Movement.Static)
        gallery.setIconSize(QSize(104, 64))
        gallery.setSpacing(6)
        gallery.setWordWrap(True)
        gallery.itemClicked.connect(self._show_crop)
        gallery.itemChanged.connect(self._crop_selection_changed)
        layout.addWidget(gallery, stretch=1)

        remove_button = QPushButton("Remove crop")
        remove_button.setObjectName("remove-crop")
        remove_button.setEnabled(False)
        remove_button.clicked.connect(self._remove_selected_crop)
        layout.addWidget(remove_button)
        return sidebar

    def _build_top_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("top-rail")
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        primary_row = QHBoxLayout()
        primary_row.setSpacing(12)

        brand = QLabel("ODIA")
        brand.setObjectName("brand")
        primary_row.addWidget(brand)

        live_status = QLabel("● LIVE")
        live_status.setObjectName("live-status")
        primary_row.addWidget(live_status)
        primary_row.addStretch()

        preview_button = QPushButton("Camera Pause")
        preview_button.setObjectName("toggle-preview")
        preview_button.clicked.connect(self._toggle_preview)
        primary_row.addWidget(preview_button)

        listen_button = QPushButton("Mic Resume")
        listen_button.setObjectName("toggle-whisper")
        listen_button.setToolTip(
            "Resume or pause microphone listening. Text input remains available."
        )
        listen_button.clicked.connect(self._toggle_whisper)
        listen_button.setEnabled(self._whisper_stream is not None)
        primary_row.addWidget(listen_button)

        quit_button = QPushButton("Quit")
        quit_button.setObjectName("quit-runtime")
        quit_button.clicked.connect(self._request_quit)
        primary_row.addWidget(quit_button)
        layout.addLayout(primary_row)

        if self._context is not None:
            camera = self._context.camera.info
            camera_name = f"{camera.name} · index {camera.index}"
            yolo_name = get_model_option(
                self._context.models.vision_id,
                kind="vision",
            ).name
            whisper_name = get_model_option(
                self._context.models.voice_id,
                kind="voice",
            ).name
            yolo_status = "Not started"
        else:
            camera_name = "Synthetic preview"
            yolo_name = "Simulation"
            whisper_name = "No setup context"
            yolo_status = "Simulation ready"

        dashboard = QHBoxLayout()
        dashboard.setSpacing(10)
        dashboard.addWidget(
            self._build_status_card(
                title="CAMERA",
                value=camera_name,
                value_name="camera-selection",
                status="Opening selected device…",
                status_name="camera-runtime-status",
            ),
            stretch=1,
        )
        dashboard.addWidget(
            self._build_status_card(
                title="YOLO VISION",
                value=yolo_name,
                value_name="yolo-model",
                status=yolo_status,
                status_name="yolo-status",
            ),
            stretch=1,
        )
        dashboard.addWidget(self._build_whisper_card(whisper_name), stretch=1)
        layout.addLayout(dashboard)

        if self._context is not None:
            devices = QLabel(
                f"MIC  {self._context.audio_input.info.name}"
                f"     •     OUTPUT  {self._context.audio_output.info.name}"
            )
        else:
            devices = QLabel("MIC  Not connected     •     OUTPUT  Not connected")
        devices.setObjectName("audio-device-summary")
        devices.setToolTip(devices.text())
        layout.addWidget(devices)

        return rail

    @staticmethod
    def _build_status_card(
        *,
        title: str,
        value: str,
        value_name: str,
        status: str,
        status_name: str,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("status-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        heading = QLabel(title)
        heading.setObjectName("status-heading")
        layout.addWidget(heading)

        value_label = QLabel(value)
        value_label.setObjectName(value_name)
        value_label.setToolTip(value)
        layout.addWidget(value_label)

        status_label = QLabel(status)
        status_label.setObjectName(status_name)
        layout.addWidget(status_label)
        return card

    def _build_whisper_card(self, model_name: str) -> QFrame:
        card = QFrame()
        card.setObjectName("status-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(3)

        heading = QLabel("WHISPER VOICE")
        heading.setObjectName("status-heading")
        layout.addWidget(heading)

        model = QLabel(model_name)
        model.setObjectName("whisper-model")
        model.setToolTip(model_name)
        layout.addWidget(model)

        status = QLabel("Off" if self._whisper_stream is not None else "Unavailable")
        status.setObjectName("whisper-status")
        layout.addWidget(status)
        return card

    def _build_video_panel(self) -> QLabel:
        video_panel = QLabel("Camera preview will appear here")
        video_panel.setObjectName("video-panel")
        video_panel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_panel.setMinimumSize(640, 360)
        video_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        return video_panel

    def _build_command_dock(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("command-dock")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(9)

        detection_row = QHBoxLayout()
        detection_heading = QLabel("DETECTIONS")
        detection_heading.setObjectName("rail-label")
        detection_row.addWidget(detection_heading)
        detection_count = QLabel("0 objects")
        detection_count.setObjectName("detection-count")
        detection_row.addWidget(detection_count)

        detection_summary = QLabel("No objects")
        detection_summary.setObjectName("detection-summary")
        detection_row.addWidget(detection_summary, stretch=1)
        layout.addLayout(detection_row)

        target_row = QHBoxLayout()
        target_heading = QLabel("TARGETS")
        target_heading.setObjectName("rail-label")
        target_row.addWidget(target_heading)
        targets = QLabel("cell phone · clock · keyboard · person")
        targets.setObjectName("target-summary")
        targets.setWordWrap(True)
        target_row.addWidget(targets, stretch=1)
        layout.addLayout(target_row)

        queue_row = QHBoxLayout()
        queue_heading = QLabel("QUEUE")
        queue_heading.setObjectName("rail-label")
        queue_row.addWidget(queue_heading)

        queue_count = QLabel("0 keywords")
        queue_count.setObjectName("keyword-queue-count")
        queue_row.addWidget(queue_count)

        queue_summary = QLabel("Empty — waiting for an instruction")
        queue_summary.setObjectName("keyword-queue-summary")
        queue_summary.setWordWrap(True)
        queue_row.addWidget(queue_summary, stretch=1)
        layout.addLayout(queue_row)

        transcript_row = QHBoxLayout()
        transcript_heading = QLabel("INSTRUCTION")
        transcript_heading.setObjectName("rail-label")
        transcript_row.addWidget(transcript_heading)
        transcript = QLabel("Speak with Whisper or type below")
        transcript.setObjectName("transcript")
        transcript.setWordWrap(True)
        transcript_row.addWidget(transcript, stretch=1)
        layout.addLayout(transcript_row)

        text_input_hint = QLabel(
            "TEXT INPUT  Always available — uses the same keyword path as Whisper"
        )
        text_input_hint.setObjectName("text-input-hint")
        layout.addWidget(text_input_hint)

        command_row = QHBoxLayout()
        command_input = QLineEdit()
        command_input.setObjectName("command-input")
        command_input.setPlaceholderText(
            "Type keywords or an instruction: person, bicycle / 사람, 자전거"
        )
        command_input.setToolTip(
            "Text works while the microphone is off and follows the same "
            "keyword parsing path as Whisper."
        )
        command_input.returnPressed.connect(self._submit_command)
        command_row.addWidget(command_input, stretch=1)

        send_button = QPushButton("Queue")
        send_button.setObjectName("send-command")
        send_button.clicked.connect(self._submit_command)
        command_row.addWidget(send_button)

        story_button = QPushButton("Story")
        story_button.setObjectName("generate-story")
        story_button.clicked.connect(self._generate_story)
        command_row.addWidget(story_button)
        layout.addLayout(command_row)

        story_row = QHBoxLayout()
        story_image = QLabel("No story image")
        story_image.setObjectName("story-image")
        story_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        story_image.setFixedSize(180, 102)
        story_row.addWidget(story_image)

        story_output = QLabel(
            "Selected object crops will become a short story for this session."
        )
        story_output.setObjectName("story-output")
        story_output.setWordWrap(True)
        story_row.addWidget(story_output, stretch=1)
        layout.addLayout(story_row)

        return panel

    def _submit_command(self) -> None:
        command_input = self.findChild(QLineEdit, "command-input")
        command = command_input.text().strip()
        if not command:
            return

        self._apply_instruction(command, source="Typed")
        command_input.clear()
        self.command_submitted.emit(command)

    def _apply_instruction(self, text: str, *, source: str) -> None:
        """Parse typed or spoken text and switch YOLO to matching classes."""
        self.findChild(QLabel, "transcript").setText(f"{source}: {text}")
        try:
            detected_classes = self._text_manager.extract(text)
        except (RuntimeError, ValueError) as error:
            self._show_queue_message(
                f"Could not parse instruction: {error}",
            )
            return

        classes = tuple(
            dict.fromkeys(detected.yolo_class for detected in detected_classes)
        )
        if not classes:
            self._show_queue_message("No supported keywords found")
            return

        self._session_recorder.record_instruction(text, classes)
        self._video_stream.set_classes(classes)

    def _show_queue_message(self, message: str) -> None:
        """Show instruction feedback without replacing active targets."""
        self.findChild(QLabel, "keyword-queue-count").setText("0 keywords")
        self.findChild(QLabel, "keyword-queue-summary").setText(message)

    @Slot(object)
    def show_keyword_queue(self, _classes: object) -> None:
        """Show the keyword batch currently waiting for the camera worker."""
        event_classes = tuple(_classes) if _classes else ()
        if event_classes:
            self._last_queued_classes = event_classes

        pending_classes = self._video_stream.pending_classes
        queued_classes = tuple(pending_classes) if pending_classes else ()
        count = len(queued_classes)
        noun = "keyword" if count == 1 else "keywords"
        self.findChild(QLabel, "keyword-queue-count").setText(f"{count} {noun}")
        if queued_classes:
            summary = " · ".join(queued_classes)
        elif self._last_queued_classes:
            summary = "Empty — sent to targets: " + " · ".join(
                self._last_queued_classes
            )
        else:
            summary = "Empty — waiting for an instruction"
        self.findChild(QLabel, "keyword-queue-summary").setText(summary)

    @Slot(object)
    def show_active_classes(self, classes: object) -> None:
        """Show the keyword classes currently active in YOLO."""
        active_classes = tuple(classes) if classes else ()
        if active_classes:
            self.findChild(QLabel, "target-summary").setText(" · ".join(active_classes))

    @Slot(str)
    def receive_transcript(self, transcript: str) -> None:
        """Route recognized speech through the same path as typed input."""
        self._apply_instruction(transcript, source="Heard")

    def _toggle_whisper(self) -> None:
        if self._whisper_stream is None:
            return

        button = self.findChild(QPushButton, "toggle-whisper")
        if self._whisper_stream.is_running:
            button.setEnabled(False)
            self._whisper_stream.stop()
            return

        button.setText("Mic Pause")
        self._whisper_stream.start()

    def _toggle_preview(self) -> None:
        preview_button = self.findChild(QPushButton, "toggle-preview")
        if self._video_stream.is_running:
            self._video_stream.stop()
            preview_button.setText("Camera Resume")
            self.findChild(QLabel, "live-status").setText("● PAUSED")
            self.findChild(QLabel, "camera-runtime-status").setText("Paused")
            self.findChild(QLabel, "yolo-status").setText("Stopped")
            return

        self._video_stream.start()
        preview_button.setText("Camera Pause")
        self.findChild(QLabel, "live-status").setText("● LIVE")
        self.findChild(QLabel, "camera-runtime-status").setText("Opening…")

    @Slot(QImage)
    def display_frame(self, image: QImage) -> None:
        """Replace the video panel with the latest available image."""
        self._current_frame = image
        self.findChild(QLabel, "camera-runtime-status").setText("Streaming")
        self._refresh_video_panel()

    @Slot(QImage, object)
    def record_story_frame(self, image: QImage, detections: object) -> None:
        """Save matching YOLO box crops from the unannotated camera frame."""
        try:
            events = self._session_recorder.record_detection(image, detections)
        except (OSError, TypeError, ValueError) as error:
            self.findChild(QLabel, "story-output").setText(
                f"Could not save object crop: {error}"
            )
            return

        for event in events:
            self._add_crop(event)

    def _add_crop(self, event: CropEvent) -> None:
        crop_path = self._session_recorder.session_dir / event.crop
        object_summary = " · ".join(
            f"{found.class_name.upper()} {found.confidence:.0%}"
            for found in event.objects
        )
        captured_at = datetime.fromisoformat(event.timestamp).astimezone(timezone.utc)
        details = f"{object_summary}\n{captured_at:%Y-%m-%d %H:%M:%S UTC}"

        thumbnail = QPixmap(str(crop_path)).scaled(
            QSize(104, 64),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        item = QListWidgetItem(QIcon(thumbnail), object_summary)
        item.setData(Qt.ItemDataRole.UserRole, str(crop_path))
        item.setData(Qt.ItemDataRole.UserRole + 1, details)
        item.setCheckState(Qt.CheckState.Checked)
        item.setToolTip(details)
        gallery = self.findChild(QListWidget, "crop-gallery")
        blocker = QSignalBlocker(gallery)
        gallery.addItem(item)
        del blocker
        self._refresh_crop_queue_status()

    @Slot(object)
    def _show_crop(self, item: QListWidgetItem) -> None:
        crop_path = item.data(Qt.ItemDataRole.UserRole)
        preview = self.findChild(QLabel, "crop-preview")
        pixmap = QPixmap(crop_path)
        preview.setText("")
        preview.setPixmap(
            pixmap.scaled(
                preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.findChild(QLabel, "crop-details").setText(
            item.data(Qt.ItemDataRole.UserRole + 1)
        )
        self.findChild(QPushButton, "remove-crop").setEnabled(True)

    @Slot(object)
    def _crop_selection_changed(self, item: QListWidgetItem) -> None:
        crop_path = Path(item.data(Qt.ItemDataRole.UserRole))
        try:
            self._session_recorder.set_crop_selected(
                crop_path,
                item.checkState() == Qt.CheckState.Checked,
            )
        except ValueError as error:
            self.findChild(QLabel, "story-output").setText(
                f"Could not update Story crop queue: {error}"
            )
        self._refresh_crop_queue_status()

    def _remove_selected_crop(self) -> None:
        gallery = self.findChild(QListWidget, "crop-gallery")
        item = gallery.currentItem()
        if item is None:
            return
        crop_path = Path(item.data(Qt.ItemDataRole.UserRole))
        try:
            self._session_recorder.remove_crop(crop_path)
        except (OSError, ValueError) as error:
            self.findChild(QLabel, "story-output").setText(
                f"Could not remove object crop: {error}"
            )
            return

        row = gallery.row(item)
        gallery.takeItem(row)
        self.findChild(QLabel, "crop-preview").setPixmap(QPixmap())
        self.findChild(QLabel, "crop-preview").setText("No object crop selected")
        self.findChild(QLabel, "crop-details").setText("No object crop selected")
        self.findChild(QPushButton, "remove-crop").setEnabled(False)
        self._refresh_crop_queue_status()

    def _refresh_crop_queue_status(self) -> None:
        gallery = self.findChild(QListWidget, "crop-gallery")
        selected = sum(
            gallery.item(index).checkState() == Qt.CheckState.Checked
            for index in range(gallery.count())
        )
        self.findChild(QLabel, "crop-queue-status").setText(
            f"{selected} of {gallery.count()} crops queued for Codex"
        )

    def _generate_story(self) -> None:
        story_output = self.findChild(QLabel, "story-output")
        story_button = self.findChild(QPushButton, "generate-story")
        if not self._session_recorder.selected_crop_paths:
            story_output.setText(
                "Select at least one object crop before generating a Story."
            )
            return
        if self._story_worker is not None and self._story_worker.isRunning():
            return

        story_button.setEnabled(False)
        story_output.setText("Writing a story with Codex…")
        self.findChild(QListWidget, "crop-gallery").setEnabled(False)
        self.findChild(QPushButton, "remove-crop").setEnabled(False)
        worker = StoryWorker(
            self._story_generator,
            self._session_recorder.session_dir,
            parent=self,
        )
        self._story_worker = worker
        worker.completed.connect(self._show_story)
        worker.failed.connect(self._show_story_error)
        worker.finished.connect(self._story_worker_finished)
        worker.start()

    @Slot(object)
    def _show_story(self, result: StoryResult) -> None:
        self.findChild(QLabel, "story-output").setText(
            f"{result.title}\n{result.story}"
        )
        story_image = self.findChild(QLabel, "story-image")
        pixmap = QPixmap(str(result.representative_image))
        story_image.setText("")
        story_image.setPixmap(
            pixmap.scaled(
                story_image.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.findChild(QPushButton, "generate-story").setEnabled(True)

    @Slot(str)
    def _show_story_error(self, message: str) -> None:
        self.findChild(QLabel, "story-output").setText(
            f"Story generation failed: {message}"
        )
        self.findChild(QPushButton, "generate-story").setEnabled(True)

    @Slot()
    def _story_worker_finished(self) -> None:
        gallery = self.findChild(QListWidget, "crop-gallery")
        gallery.setEnabled(True)
        self.findChild(QPushButton, "remove-crop").setEnabled(
            gallery.currentItem() is not None
        )
        if self._story_worker is not None:
            self._story_worker.deleteLater()
        self._story_worker = None

    @Slot(str)
    def show_video_error(self, message: str) -> None:
        """Keep the dashboard open and explain why previewing stopped."""
        self._video_stream.stop()
        self._current_frame = None

        video_panel = self.findChild(QLabel, "video-panel")
        video_panel.setPixmap(QPixmap())
        video_panel.setText(f"Camera preview unavailable\n{message}")
        self.findChild(QPushButton, "toggle-preview").setText("Camera Resume")
        self.findChild(QLabel, "live-status").setText("● ERROR")
        self.findChild(QLabel, "camera-runtime-status").setText("Error")
        self.findChild(QLabel, "camera-runtime-status").setToolTip(message)
        self.findChild(QLabel, "yolo-status").setText("Stopped")

    @Slot(str)
    def show_model_status(self, status: str) -> None:
        """Present YOLO loading and accelerator status."""
        self.findChild(QLabel, "yolo-status").setText(status)

    @Slot(str)
    def show_whisper_status(self, status: str) -> None:
        """Show whether Whisper is loading, listening, stopping, or off."""
        self.findChild(QLabel, "whisper-status").setText(status)
        button = self.findChild(QPushButton, "toggle-whisper")
        if status == "Listening":
            button.setText("Mic Pause")
        elif status in {"Off", "Error"}:
            button.setText("Mic Resume")
            button.setEnabled(False)

    @Slot(str)
    def show_whisper_error(self, message: str) -> None:
        """Keep the desktop open and retain Whisper failure details."""
        status = self.findChild(QLabel, "whisper-status")
        status.setText("Error")
        status.setToolTip(message)
        self.findChild(QLabel, "transcript").setText(message)

    @Slot()
    def _whisper_finished(self) -> None:
        button = self.findChild(QPushButton, "toggle-whisper")
        button.setText("Mic Resume")
        button.setEnabled(True)

    @Slot(int, str)
    def show_detections(self, count: int, summary: str) -> None:
        """Present the latest detection count and percentage labels."""
        noun = "object" if count == 1 else "objects"
        self.findChild(QLabel, "detection-count").setText(f"{count} {noun}")
        self.findChild(QLabel, "detection-summary").setText(summary)

    def _refresh_video_panel(self) -> None:
        if self._current_frame is None:
            return

        video_panel = self.findChild(QLabel, "video-panel")
        if video_panel is None:
            return

        pixmap = QPixmap.fromImage(self._current_frame)
        scaled_pixmap = pixmap.scaled(
            video_panel.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        video_panel.setText("")
        video_panel.setPixmap(scaled_pixmap)

    def _request_quit(self) -> None:
        self.quit_requested.emit()
        self.close()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Rescale the latest frame when the window changes size."""
        super().resizeEvent(event)
        QTimer.singleShot(0, self._refresh_video_panel)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Release camera, Whisper, and parser resources before closing."""
        self._video_stream.stop()
        if self._whisper_stream is not None:
            self._whisper_stream.stop()
            self._whisper_stream.wait()
        if self._story_worker is not None and self._story_worker.isRunning():
            self._story_worker.wait()
        self._text_manager_context.__exit__(None, None, None)
        super().closeEvent(event)

    @staticmethod
    def _stylesheet() -> str:
        return """
        QMainWindow, QWidget {
            background: #0b0d10;
            color: #e8ecf2;
            font-size: 14px;
        }
        QFrame#top-rail, QFrame#command-dock {
            background: #111419;
            border: 1px solid #272c34;
            border-radius: 8px;
        }
        QFrame#object-crop-sidebar {
            background: #111419;
            border: 1px solid #272c34;
            border-radius: 8px;
        }
        QFrame#status-card {
            background: #171b21;
            border: 1px solid #2c323b;
            border-radius: 7px;
        }
        QLabel#brand {
            color: #f2a33a;
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 2px;
        }
        QLabel#live-status {
            color: #49c98b;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#status-heading {
            color: #8e97a6;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
        }
        QLabel#camera-selection,
        QLabel#yolo-model,
        QLabel#whisper-model {
            color: #e8ecf2;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#camera-runtime-status,
        QLabel#yolo-status,
        QLabel#whisper-status {
            color: #49c98b;
            font-size: 11px;
            font-weight: 700;
        }
        QLabel#audio-device-summary {
            color: #747e8d;
            font-size: 11px;
        }
        QLabel#video-panel {
            background: #050608;
            border: 1px solid #272c34;
            border-radius: 8px;
            color: #8e97a6;
            font-size: 16px;
        }
        QLabel#rail-label {
            color: #8e97a6;
            font-size: 11px;
            font-weight: 700;
            min-width: 82px;
        }
        QLabel#detection-count {
            color: #e8ecf2;
            font-weight: 700;
            min-width: 72px;
        }
        QLabel#keyword-queue-count {
            background: #242a32;
            border: 1px solid #3a424e;
            border-radius: 9px;
            color: #aeb7c5;
            font-size: 10px;
            font-weight: 700;
            min-width: 72px;
            padding: 2px 7px;
        }
        QLabel#detection-summary {
            color: #f2a33a;
            font-weight: 700;
        }
        QLabel#target-summary {
            color: #67c7d4;
            font-weight: 700;
        }
        QLabel#keyword-queue-summary {
            color: #d9a85f;
            font-weight: 700;
        }
        QLabel#transcript {
            color: #c9cfda;
        }
        QLabel#text-input-hint {
            color: #747e8d;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.3px;
        }
        QLabel#story-image {
            background: #090b0e;
            border: 1px solid #343a44;
            border-radius: 6px;
            color: #68717d;
        }
        QLabel#story-output {
            color: #c9cfda;
            font-style: italic;
        }
        QLabel#crop-preview {
            background: #050608;
            border: 1px solid #343a44;
            border-radius: 6px;
            color: #747e8d;
            padding: 6px;
        }
        QLabel#crop-details {
            color: #c9cfda;
            font-size: 12px;
            font-weight: 700;
        }
        QLabel#crop-queue-status {
            color: #8265d6;
            font-size: 11px;
            font-weight: 700;
        }
        QListWidget#crop-gallery {
            background: #090b0e;
            border: 1px solid #343a44;
            border-radius: 6px;
            color: #c9cfda;
            outline: none;
        }
        QListWidget#crop-gallery::item {
            border: 1px solid transparent;
            border-radius: 5px;
            padding: 5px;
        }
        QListWidget#crop-gallery::item:selected {
            background: #302653;
            border-color: #8265d6;
            color: #ffffff;
        }
        QLineEdit {
            background: #090b0e;
            border: 1px solid #343a44;
            border-radius: 6px;
            color: #e8ecf2;
            padding: 9px 11px;
            selection-background-color: #f2a33a;
        }
        QLineEdit:focus {
            border-color: #f2a33a;
        }
        QPushButton {
            background: #20252d;
            border: 1px solid #343a44;
            border-radius: 6px;
            color: #e8ecf2;
            padding: 9px 15px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #2a3039;
            border-color: #555e6c;
        }
        QPushButton#send-command {
            background: #c77e25;
            border-color: #f2a33a;
            color: #111419;
        }
        QPushButton#generate-story {
            background: #6046a8;
            border-color: #8265d6;
            color: #ffffff;
        }
        QPushButton#toggle-whisper {
            background: #167f8c;
            border: 2px solid #5de4f2;
            color: #ffffff;
            font-weight: 800;
        }
        QPushButton#toggle-whisper:hover {
            background: #1b9dac;
            border-color: #8af2fc;
        }
        QPushButton#toggle-whisper:disabled {
            background: #20242a;
            border-color: #30353d;
            color: #68717d;
        }
        QPushButton#quit-runtime {
            background: #d64550;
            border-color: #e86069;
            color: #ffffff;
            font-weight: 800;
        }
        QPushButton#quit-runtime:hover {
            background: #ea5661;
        }
        """
