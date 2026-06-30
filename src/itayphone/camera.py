"""Camera backend (Raspberry Pi Camera Module 3).

`Picamera2Camera` drives the real camera via the picamera2 library; `MockCamera`
fakes it so the UI and tests run on a laptop. Use :func:`build_camera` to pick
one based on the ``--mock`` flag, mirroring the modem layer.
"""

from __future__ import annotations

import os
from datetime import datetime


def _photo_path(directory: str) -> str:
    os.makedirs(os.path.expanduser(directory), exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(os.path.expanduser(directory), f"IMG_{stamp}.jpg")


class MockCamera:
    """A camera that 'captures' by writing a placeholder file."""

    def __init__(self) -> None:
        self.captures: list[str] = []
        self._preview = False

    def available(self) -> bool:
        return True

    def start_preview(self) -> None:
        self._preview = True

    def stop_preview(self) -> None:
        self._preview = False

    def capture(self, directory: str = "~/.itayphone/photos") -> str:
        path = _photo_path(directory)
        with open(path, "wb") as f:
            f.write(b"ITAYPHONE_MOCK_JPEG")
        self.captures.append(path)
        return path


class Picamera2Camera:
    """Real Pi camera backend (lazy import so dev/tests don't need picamera2)."""

    def __init__(self) -> None:
        self._cam = None

    def available(self) -> bool:
        try:
            from picamera2 import Picamera2  # noqa: F401
            return True
        except Exception:
            return False

    def _ensure(self):
        if self._cam is None:
            from picamera2 import Picamera2
            self._cam = Picamera2()
            self._cam.configure(self._cam.create_still_configuration())
        return self._cam

    def start_preview(self) -> None:
        self._ensure().start()

    def stop_preview(self) -> None:
        if self._cam is not None:
            self._cam.stop()

    def capture(self, directory: str = "~/.itayphone/photos") -> str:
        path = _photo_path(directory)
        cam = self._ensure()
        cam.start()
        cam.capture_file(path)
        return path


def build_camera(mock: bool):
    return MockCamera() if mock else Picamera2Camera()
