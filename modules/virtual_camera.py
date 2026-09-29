# --- START OF FILE virtual_camera.py ---
"""Virtual camera output for Deep-Live-Cam.

Streams the processed (face-swapped) live frames to a system *virtual* webcam
so the result can be picked as a camera inside Google Meet, Zoom, Teams,
Discord, OBS, browsers, etc. — exactly like a physical camera.

Backed by ``pyvirtualcam``, which targets:
  * Windows -> OBS Virtual Camera  (install OBS Studio once to register it)
  * macOS   -> OBS Virtual Camera
  * Linux   -> v4l2loopback

The module degrades gracefully: if ``pyvirtualcam`` is not installed, or no
virtual-camera backend is registered on the system, sending simply fails with
a helpful message and the live preview keeps working regardless.
"""

import sys
from typing import Optional

import cv2
import numpy as np

try:
    import pyvirtualcam
    from pyvirtualcam import PixelFormat

    _AVAILABLE = True
    _IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # pragma: no cover - depends on the install
    pyvirtualcam = None  # type: ignore[assignment]
    PixelFormat = None  # type: ignore[assignment]
    _AVAILABLE = False
    _IMPORT_ERROR = str(exc)


def is_available() -> bool:
    """True if the ``pyvirtualcam`` package imported successfully."""
    return _AVAILABLE


def unavailable_reason() -> str:
    """Human-readable explanation for why the package could not be used."""
    if _IMPORT_ERROR is None:
        return "pyvirtualcam is not installed. Run: pip install pyvirtualcam"
    return f"pyvirtualcam import failed: {_IMPORT_ERROR}"


def _to_bgr_uint8(frame: np.ndarray) -> np.ndarray:
    """Coerce any OpenCV frame to a contiguous H×W×3 uint8 BGR array.

    The swapper/enhancer pipeline normally emits exactly that, but we stay
    defensive so a virtual-camera consumer never receives a malformed buffer
    (which would tear the stream or crash the backend).
    """
    if frame.dtype != np.uint8:
        frame = np.clip(frame, 0, 255).astype(np.uint8)
    if frame.ndim == 2:  # grayscale -> BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.ndim == 3 and frame.shape[2] == 4:  # BGRA -> BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    if not frame.flags["C_CONTIGUOUS"]:
        frame = np.ascontiguousarray(frame)
    return frame


class VirtualCameraOutput:
    """Lazily-opened virtual-camera sink.

    Owned and driven by a single thread (the live processing worker).  The
    first frame fixes the output resolution; later frames of a different size
    are resized to match so the consumer always sees a stable, fixed-format
    stream — just like a real webcam.
    """

    def __init__(self, fps: float = 30.0):
        # pyvirtualcam needs a sane, positive frame rate advertised to clients.
        self._fps = float(min(max(fps, 1.0), 1000.0))
        self._cam = None
        self._width = 0
        self._height = 0
        self._failed = False
        self.last_error: Optional[str] = None

    # ── lifecycle ────────────────────────────────────────────────────────
    def _open(self, width: int, height: int) -> bool:
        if not _AVAILABLE:
            self.last_error = unavailable_reason()
            self._failed = True
            return False
        try:
            # fmt=BGR lets us hand OpenCV frames straight through; pyvirtualcam
            # converts to whatever the OS backend needs.
            self._cam = pyvirtualcam.Camera(
                width=width,
                height=height,
                fps=self._fps,
                fmt=PixelFormat.BGR,
                print_fps=False,
            )
            self._width = width
            self._height = height
            self.last_error = None
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self._failed = True
            self._cam = None
            return False

    def is_active(self) -> bool:
        return self._cam is not None

    @property
    def device(self) -> str:
        return getattr(self._cam, "device", "virtual camera") if self._cam else ""

    def reset(self) -> None:
        """Clear a previous failure so the next ``send`` retries opening.

        Called when the user re-enables the toggle after fixing the backend
        (e.g. installing OBS), so we don't stay latched in the failed state.
        """
        self._failed = False
        self.last_error = None

    # ── frame I/O ────────────────────────────────────────────────────────
    def send(self, bgr_frame: np.ndarray) -> bool:
        """Push one BGR frame to the virtual camera. Returns False on failure."""
        if self._failed and self._cam is None:
            return False
        frame = _to_bgr_uint8(bgr_frame)
        h, w = frame.shape[:2]
        if self._cam is None:
            if not self._open(w, h):
                return False
        if w != self._width or h != self._height:
            frame = cv2.resize(
                frame, (self._width, self._height), interpolation=cv2.INTER_LINEAR
            )
        try:
            self._cam.send(frame)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self._failed = True
            self.close()
            return False

    def close(self) -> None:
        if self._cam is not None:
            try:
                self._cam.close()
            except Exception:
                pass
        self._cam = None
        self._width = 0
        self._height = 0


# --- END OF FILE virtual_camera.py ---
