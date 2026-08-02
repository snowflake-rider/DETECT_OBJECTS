"""PySide window for the isolated ODIA desktop runtime."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..device_setup.context import Context
from ..models.catalog import get_model_option
from .camera_video import CameraVideoStream
from .fake_video import FakeVideoStream
from .yolo_detection import YoloDetector

VideoStream = FakeVideoStream | CameraVideoStream


class RuntimeWindow(QMainWindow):
    """Present the first hardware-free desktop dashboard shell."""

    command_submitted = Signal(str)
    quit_requested = Signal()

    def __init__(
        self,
        context: Context | None = None,
        video_stream: VideoStream | None = None,
    ) -> None:
        super().__init__()
        self._context = context
        self._current_frame: QImage | None = None
        if video_stream is not None:
            self._video_stream = video_stream
        elif context is not None:
            camera = context.camera.info
            self._video_stream = CameraVideoStream(
                index=camera.index,
                backend=camera.backend,
                name=camera.name,
                detector=YoloDetector(context.models.vision_id),
                parent=self,
            )
        else:
            self._video_stream = FakeVideoStream(parent=self)
        self.setWindowTitle("ODIA Live")
        self.resize(1280, 800)
        self.setMinimumSize(900, 620)
        self.setCentralWidget(self._build_content())
        self.setStyleSheet(self._stylesheet())
        self._video_stream.frame_ready.connect(self.display_frame)
        self._video_stream.error.connect(self.show_video_error)
        self._video_stream.model_status.connect(self.show_model_status)
        self._video_stream.detections_ready.connect(self.show_detections)
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
        page.addWidget(self._build_video_panel(), stretch=1)
        page.addWidget(self._build_command_dock())

        return content

    def _build_top_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("top-rail")
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        primary_row = QHBoxLayout()
        primary_row.setSpacing(12)

        brand = QLabel("ODIA")
        brand.setObjectName("brand")
        primary_row.addWidget(brand)

        live_status = QLabel("● LIVE")
        live_status.setObjectName("live-status")
        primary_row.addWidget(live_status)
        primary_row.addStretch()

        preview_button = QPushButton("Pause")
        preview_button.setObjectName("toggle-preview")
        preview_button.clicked.connect(self._toggle_preview)
        primary_row.addWidget(preview_button)

        quit_button = QPushButton("Quit")
        quit_button.setObjectName("quit-runtime")
        quit_button.clicked.connect(self._request_quit)
        primary_row.addWidget(quit_button)
        layout.addLayout(primary_row)

        device_row = QHBoxLayout()
        device_row.setSpacing(18)
        if self._context is not None:
            camera = self._context.camera.info
            camera_selection = QLabel(f"Camera: {camera.name} (index {camera.index})")
            audio_input_selection = QLabel(
                f"Audio input: {self._context.audio_input.info.name}"
            )
            audio_output_selection = QLabel(
                f"Audio output: {self._context.audio_output.info.name}"
            )
        else:
            camera_selection = QLabel("Camera: Synthetic preview")
            audio_input_selection = QLabel("Audio input: Not connected")
            audio_output_selection = QLabel("Audio output: Not connected")

        for label, object_name in (
            (camera_selection, "camera-selection"),
            (audio_input_selection, "audio-input-selection"),
            (audio_output_selection, "audio-output-selection"),
        ):
            label.setObjectName(object_name)
            label.setToolTip(label.text())
            device_row.addWidget(label)
        device_row.addStretch()
        layout.addLayout(device_row)

        status_row = QHBoxLayout()
        status_row.setSpacing(18)
        yolo_name = ""
        whisper_name = ""
        if self._context is not None:
            yolo_name = (
                get_model_option(self._context.models.vision_id, kind="vision").name
                + " · "
            )
            whisper_name = (
                get_model_option(self._context.models.voice_id, kind="voice").name
                + " · "
            )

        yolo_status = QLabel(f"YOLO: {yolo_name}Not started")
        yolo_status.setObjectName("yolo-status")
        status_row.addWidget(yolo_status)

        whisper_status = QLabel(f"Whisper: {whisper_name}Not started")
        whisper_status.setObjectName("whisper-status")
        status_row.addWidget(whisper_status)
        status_row.addStretch()
        layout.addLayout(status_row)

        return rail

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

        transcript_row = QHBoxLayout()
        transcript_heading = QLabel("HEARD")
        transcript_heading.setObjectName("rail-label")
        transcript_row.addWidget(transcript_heading)
        transcript = QLabel("No transcript yet")
        transcript.setObjectName("transcript")
        transcript.setWordWrap(True)
        transcript_row.addWidget(transcript, stretch=1)
        layout.addLayout(transcript_row)

        command_row = QHBoxLayout()
        command_input = QLineEdit()
        command_input.setObjectName("command-input")
        command_input.setPlaceholderText("Type a detection command…")
        command_input.returnPressed.connect(self._submit_command)
        command_row.addWidget(command_input, stretch=1)

        send_button = QPushButton("Send")
        send_button.setObjectName("send-command")
        send_button.clicked.connect(self._submit_command)
        command_row.addWidget(send_button)
        layout.addLayout(command_row)

        return panel

    def _submit_command(self) -> None:
        command_input = self.findChild(QLineEdit, "command-input")
        command = command_input.text().strip()
        if not command:
            return

        self.findChild(QLabel, "transcript").setText(f"Typed command: {command}")
        command_input.clear()
        self.command_submitted.emit(command)

    def _toggle_preview(self) -> None:
        preview_button = self.findChild(QPushButton, "toggle-preview")
        if self._video_stream.is_running:
            self._video_stream.stop()
            preview_button.setText("Resume")
            self.findChild(QLabel, "live-status").setText("● PAUSED")
            return

        self._video_stream.start()
        preview_button.setText("Pause")
        self.findChild(QLabel, "live-status").setText("● LIVE")

    @Slot(QImage)
    def display_frame(self, image: QImage) -> None:
        """Replace the video panel with the latest available image."""
        self._current_frame = image
        self._refresh_video_panel()

    @Slot(str)
    def show_video_error(self, message: str) -> None:
        """Keep the dashboard open and explain why previewing stopped."""
        self._video_stream.stop()
        self._current_frame = None

        video_panel = self.findChild(QLabel, "video-panel")
        video_panel.setPixmap(QPixmap())
        video_panel.setText(f"Camera preview unavailable\n{message}")
        self.findChild(QPushButton, "toggle-preview").setText("Resume")
        self.findChild(QLabel, "live-status").setText("● ERROR")

    @Slot(str)
    def show_model_status(self, status: str) -> None:
        """Present YOLO loading and accelerator status."""
        model_name = ""
        if self._context is not None:
            model_name = (
                get_model_option(self._context.models.vision_id, kind="vision").name
                + " · "
            )
        self.findChild(QLabel, "yolo-status").setText(f"YOLO: {model_name}{status}")

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
        """Stop the preview timer before the window closes."""
        self._video_stream.stop()
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
        QLabel#camera-selection,
        QLabel#audio-input-selection,
        QLabel#audio-output-selection,
        QLabel#yolo-status,
        QLabel#whisper-status {
            color: #8e97a6;
            font-size: 12px;
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
        QLabel#detection-summary {
            color: #f2a33a;
            font-weight: 700;
        }
        QLabel#transcript {
            color: #c9cfda;
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
