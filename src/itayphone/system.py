"""System radio controls — Wi-Fi and Bluetooth power, scanning, and connecting.

`PiSystem` shells out to the OS (NetworkManager for Wi-Fi, bluez for Bluetooth);
`MockSystem` fakes everything so the UI and tests run on a laptop. Pick one with
:func:`build_system`, mirroring the camera/modem ``build_*`` pattern.

Every call is best-effort: a missing tool, denied permission, or a device that
won't pair degrades to ``False`` / an empty list instead of crashing the app.

Scans and connects can block for several seconds, so callers (the Kivy screens)
run them on a background thread and marshal the result back to the UI thread.
"""

from __future__ import annotations

import shutil
import subprocess


def _run(cmd: list[str], timeout: float = 10) -> bool:
    try:
        subprocess.run(cmd, check=True, timeout=timeout,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _out(cmd: list[str], timeout: float = 15) -> str:
    """Run *cmd* and return its stdout (empty string on any failure)."""
    try:
        r = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
        return r.stdout or ""
    except Exception:
        return ""


class MockSystem:
    """In-memory backend (laptop/dev): remembers state, returns fake scans."""

    def __init__(self) -> None:
        self.wifi = True
        self.bluetooth = False
        self._nets = [
            {"ssid": "ElitzurMain", "signal": 82, "secure": True, "active": True},
            {"ssid": "NETGEAR-Guest", "signal": 57, "secure": True, "active": False},
            {"ssid": "CoffeeShop_Free", "signal": 38, "secure": False, "active": False},
        ]
        self._devs = [
            {"mac": "AA:BB:CC:11:22:33", "name": "JBL Flip 5", "connected": False},
            {"mac": "DD:EE:FF:44:55:66", "name": "Galaxy Buds", "connected": False},
        ]

    # radio power
    def set_wifi(self, on: bool) -> bool:
        self.wifi = on
        return True

    def set_bluetooth(self, on: bool) -> bool:
        self.bluetooth = on
        return True

    def wifi_enabled(self) -> bool:
        return self.wifi

    def bt_powered(self) -> bool:
        return self.bluetooth

    # wi-fi
    def wifi_scan(self) -> list[dict]:
        return [dict(n) for n in self._nets] if self.wifi else []

    def wifi_connect(self, ssid: str, password: str = "") -> bool:
        for n in self._nets:
            n["active"] = (n["ssid"] == ssid)
        return True

    # bluetooth
    def bt_scan(self, seconds: float = 6) -> None:
        pass

    def bt_list(self) -> list[dict]:
        return [dict(d) for d in self._devs] if self.bluetooth else []

    def bt_connect(self, mac: str) -> bool:
        for d in self._devs:
            if d["mac"] == mac:
                d["connected"] = True
        return True

    def bt_disconnect(self, mac: str) -> bool:
        for d in self._devs:
            if d["mac"] == mac:
                d["connected"] = False
        return True


class PiSystem:
    """Real backend for Raspberry Pi OS (NetworkManager + bluez)."""

    # -- radio power -------------------------------------------------------
    def set_wifi(self, on: bool) -> bool:
        # Toggling the radio needs root: polkit denies a non-seat (SSH-launched)
        # session, so go through passwordless sudo, which the default Pi user
        # has. Fall back to a plain call, then rfkill.
        state = "on" if on else "off"
        if shutil.which("nmcli"):
            if _run(["sudo", "-n", "nmcli", "radio", "wifi", state]):
                return True
            if _run(["nmcli", "radio", "wifi", state]):
                return True
        return _run(["sudo", "-n", "rfkill", "unblock" if on else "block", "wifi"])

    def set_bluetooth(self, on: bool) -> bool:
        # bluetoothctl talks to bluez over the user session bus (no root).
        if shutil.which("bluetoothctl"):
            if _run(["bluetoothctl", "power", "on" if on else "off"]):
                return True
        return _run(["sudo", "-n", "rfkill", "unblock" if on else "block",
                     "bluetooth"])

    def wifi_enabled(self) -> bool:
        return _out(["nmcli", "radio", "wifi"]).strip() == "enabled"

    def bt_powered(self) -> bool:
        return "Powered: yes" in _out(["bluetoothctl", "show"])

    # -- wi-fi -------------------------------------------------------------
    def wifi_scan(self) -> list[dict]:
        # A rescan needs root (best-effort); listing works as the plain user and
        # NetworkManager keeps the cache fresh anyway.
        _run(["sudo", "-n", "nmcli", "dev", "wifi", "rescan"], timeout=12)
        raw = _out(["nmcli", "-t", "-f", "IN-USE,SIGNAL,SECURITY,SSID",
                    "dev", "wifi", "list"])
        best: dict[str, dict] = {}
        for line in raw.splitlines():
            # SSID is last so an SSID containing ':' survives the maxsplit.
            parts = line.split(":", 3)
            if len(parts) < 4:
                continue
            in_use, signal, security, ssid = parts
            ssid = ssid.replace("\\:", ":").strip()
            if not ssid:
                continue
            try:
                sig = int(signal)
            except ValueError:
                sig = 0
            active = in_use.strip() == "*"
            net = {"ssid": ssid, "signal": sig,
                   "secure": bool(security.strip()), "active": active}
            cur = best.get(ssid)
            # Keep the strongest entry per SSID, preferring the connected one.
            if cur is None or active or sig > cur["signal"]:
                best[ssid] = net
        return sorted(best.values(),
                      key=lambda n: (n["active"], n["signal"]), reverse=True)

    def wifi_connect(self, ssid: str, password: str = "") -> bool:
        cmd = ["sudo", "-n", "nmcli", "dev", "wifi", "connect", ssid]
        if password:
            cmd += ["password", password]
        return _run(cmd, timeout=35)

    # -- bluetooth ---------------------------------------------------------
    def bt_scan(self, seconds: float = 6) -> None:
        # bluez 5.66+ supports --timeout: scan for N seconds then exit.
        _out(["bluetoothctl", "--timeout", str(int(seconds)), "scan", "on"],
             timeout=seconds + 5)

    def bt_list(self) -> list[dict]:
        connected = set()
        for line in _out(["bluetoothctl", "devices", "Connected"]).splitlines():
            p = line.split()
            if len(p) >= 2 and p[0] == "Device":
                connected.add(p[1])
        devs = []
        for line in _out(["bluetoothctl", "devices"]).splitlines():
            p = line.split(maxsplit=2)
            if len(p) >= 2 and p[0] == "Device":
                mac = p[1]
                name = p[2] if len(p) >= 3 else mac
                devs.append({"mac": mac, "name": name,
                             "connected": mac in connected})
        # Connected first, then alphabetical by name.
        return sorted(devs, key=lambda d: (not d["connected"], d["name"].lower()))

    def bt_connect(self, mac: str) -> bool:
        if _run(["bluetoothctl", "connect", mac], timeout=20):
            return True
        # Not paired yet: pair + trust, then connect.
        _run(["bluetoothctl", "pair", mac], timeout=25)
        _run(["bluetoothctl", "trust", mac], timeout=8)
        return _run(["bluetoothctl", "connect", mac], timeout=20)

    def bt_disconnect(self, mac: str) -> bool:
        return _run(["bluetoothctl", "disconnect", mac], timeout=12)


def build_system(mock: bool):
    return MockSystem() if mock else PiSystem()
