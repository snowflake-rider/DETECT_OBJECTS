"""Convert OpenCV-style image arrays into Qt images."""

from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage


def frame_to_qimage(frame: np.ndarray) -> QImage:
    """Return an owned Qt image from an unsigned 8-bit BGR frame."""
    if not isinstance(frame, np.ndarray):
        raise TypeError("frame must be a NumPy array")
    if frame.dtype != np.uint8:
        raise ValueError("frame must use the uint8 data type")
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("frame must have shape (height, width, 3)")

    height, width, _channels = frame.shape
    if height == 0 or width == 0:
        raise ValueError("frame width and height must be greater than zero")

    contiguous_frame = np.ascontiguousarray(frame)
    image = QImage(
        contiguous_frame.data,
        width,
        height,
        contiguous_frame.strides[0],
        QImage.Format.Format_BGR888,
    )

    # QImage initially points at the NumPy buffer. copy() gives Qt its own
    # pixels, so the image remains valid after OpenCV reuses the frame memory.
    return image.copy()
