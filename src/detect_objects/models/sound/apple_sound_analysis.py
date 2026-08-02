"""Apple SoundAnalysis backend for timestamped audio-file classification."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from ..model_config import AppleSoundAnalysisConfig
from .base import SoundPrediction, SoundWindow

try:
    import CoreMedia
    import objc
    import SoundAnalysis
    from Foundation import NSObject, NSURL
except ImportError:
    CoreMedia = None
    objc = None
    SoundAnalysis = None
    NSObject = object
    NSURL = None


class SoundAnalysisUnavailableError(RuntimeError):
    """Raised when Apple's native SoundAnalysis framework cannot be used."""


class SoundAnalysisError(RuntimeError):
    """Raised when the native analyzer rejects or fails an analysis request."""


class _ResultsObserver(NSObject):
    """Collect callbacks from ``SNResultsObserving`` during file analysis."""

    if objc is not None:
        __pyobjc_protocols__ = (objc.protocolNamed("SNResultsObserving"),)

    def request_didProduceResult_(self, request: Any, result: Any) -> None:
        """Convert one native classification result into project values."""
        del request
        time_range = result.timeRange()
        start_seconds = float(CoreMedia.CMTimeGetSeconds(time_range.start))
        duration_seconds = float(CoreMedia.CMTimeGetSeconds(time_range.duration))

        predictions = []
        for classification in result.classifications():
            label = str(classification.identifier())
            threshold = self.config.thresholds.get(label)
            confidence = float(classification.confidence())
            if threshold is None or confidence < threshold:
                continue
            predictions.append(SoundPrediction(label=label, confidence=confidence))

        predictions.sort(key=lambda prediction: prediction.confidence, reverse=True)
        self.windows.append(
            SoundWindow(
                start_seconds=start_seconds,
                duration_seconds=duration_seconds,
                predictions=tuple(predictions[: self.config.top_k]),
            )
        )

    def request_didFailWithError_(self, request: Any, error: Any) -> None:
        """Store an analyzer failure for the synchronous caller to raise."""
        del request
        self.failure = error

    def requestDidComplete_(self, request: Any) -> None:
        """Record normal completion of the native analysis request."""
        del request
        self.completed = True


class AppleSoundAnalysisClassifier:
    """Classify complete audio files with the macOS built-in model."""

    def __init__(self, config: AppleSoundAnalysisConfig) -> None:
        """Keep validated runtime policy for subsequent file analyses."""
        self._config = config

    @property
    def known_labels(self) -> tuple[str, ...]:
        """Return every label exposed by Apple's version-one classifier."""
        request = self._make_request()
        return tuple(str(label) for label in request.knownClassifications())

    def classify_file(self, audio_path: str | Path) -> list[SoundWindow]:
        """Analyze an audio file synchronously and return chronological windows."""
        self._ensure_available()
        resolved_audio_path = Path(audio_path).expanduser().resolve()
        if not resolved_audio_path.is_file():
            raise FileNotFoundError(f"Audio file was not found: {resolved_audio_path}")

        url = NSURL.fileURLWithPath_(str(resolved_audio_path))
        (
            analyzer,
            analyzer_error,
        ) = SoundAnalysis.SNAudioFileAnalyzer.alloc().initWithURL_error_(
            url,
            None,
        )
        if analyzer is None:
            raise SoundAnalysisError(
                f"Could not open audio file: {_describe_error(analyzer_error)}"
            )

        request = self._make_request()
        observer = _create_results_observer(self._config)
        added, request_error = analyzer.addRequest_withObserver_error_(
            request,
            observer,
            None,
        )
        if not added:
            raise SoundAnalysisError(
                f"Could not add sound-classification request: "
                f"{_describe_error(request_error)}"
            )

        analyzer.analyze()
        if observer.failure is not None:
            raise SoundAnalysisError(
                f"Sound classification failed: {_describe_error(observer.failure)}"
            )
        if not observer.completed:
            raise SoundAnalysisError("Sound classification ended without completion")

        return sorted(observer.windows, key=lambda window: window.start_seconds)

    def _make_request(self) -> Any:
        """Create a configured request for Apple's built-in classifier."""
        self._ensure_available()
        identifier = SoundAnalysis.SNClassifierIdentifierVersion1
        (
            request,
            error,
        ) = SoundAnalysis.SNClassifySoundRequest.alloc().initWithClassifierIdentifier_error_(
            identifier, None
        )
        if request is None:
            raise SoundAnalysisError(
                f"Could not create sound-classification request: "
                f"{_describe_error(error)}"
            )

        duration = CoreMedia.CMTimeMakeWithSeconds(
            self._config.window_seconds,
            600,
        )
        request.setWindowDuration_(duration)
        request.setOverlapFactor_(self._config.overlap)
        return request

    @staticmethod
    def _ensure_available() -> None:
        """Reject unsupported systems with an actionable error message."""
        if sys.platform != "darwin":
            raise SoundAnalysisUnavailableError(
                "Apple SoundAnalysis is available only on macOS"
            )
        if SoundAnalysis is None or CoreMedia is None or NSURL is None:
            raise SoundAnalysisUnavailableError(
                "Install the macOS dependency with `uv sync` before using "
                "Apple SoundAnalysis"
            )


def _create_results_observer(
    config: AppleSoundAnalysisConfig,
) -> _ResultsObserver:
    """Allocate an Objective-C observer and attach Python result state."""
    observer = _ResultsObserver.alloc().init()
    observer.config = config
    observer.windows = []
    observer.failure = None
    observer.completed = False
    return observer


def _describe_error(error: Any) -> str:
    """Return an NSError description without leaking Objective-C details."""
    if error is None:
        return "unknown native error"
    localized_description = getattr(error, "localizedDescription", None)
    if callable(localized_description):
        return str(localized_description())
    return str(error)
