"""Tests for the system radio controls (mock backend + builder)."""

from itayphone.system import MockSystem, PiSystem, build_system


def test_mock_tracks_wifi_state():
    sysc = MockSystem()
    assert sysc.wifi is True
    assert sysc.set_wifi(False) is True
    assert sysc.wifi is False


def test_mock_tracks_bluetooth_state():
    sysc = MockSystem()
    assert sysc.bluetooth is False
    assert sysc.set_bluetooth(True) is True
    assert sysc.bluetooth is True


def test_build_system_picks_backend():
    assert isinstance(build_system(mock=True), MockSystem)
    assert isinstance(build_system(mock=False), PiSystem)
