"""Tests for the camera backend (mock)."""

import os

from itayphone.camera import MockCamera, build_camera


def test_build_camera_mock_returns_mock():
    assert isinstance(build_camera(mock=True), MockCamera)


def test_mock_capture_writes_file(tmp_path):
    cam = MockCamera()
    assert cam.available() is True
    path = cam.capture(str(tmp_path))
    assert os.path.exists(path)
    assert path.endswith(".jpg")
    assert cam.captures == [path]


def test_preview_toggles(tmp_path):
    cam = MockCamera()
    cam.start_preview()
    assert cam._preview is True
    cam.stop_preview()
    assert cam._preview is False
