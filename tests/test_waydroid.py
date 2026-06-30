"""Tests for the Waydroid controller (mock)."""

from itayphone.waydroid import MockWaydroid, build_waydroid


def test_build_waydroid_mock_returns_mock():
    assert isinstance(build_waydroid(mock=True), MockWaydroid)


def test_list_apps_includes_whatsapp():
    wd = MockWaydroid()
    packages = [a.package for a in wd.list_apps()]
    assert "com.whatsapp" in packages


def test_launch_starts_session_and_records():
    wd = MockWaydroid()
    wd.launch("com.whatsapp")
    assert wd.session_started is True
    assert wd.launched == ["com.whatsapp"]


def test_launch_whatsapp_helper():
    wd = MockWaydroid()
    wd.launch_whatsapp()
    assert wd.launched == ["com.whatsapp"]
