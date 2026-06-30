"""Waydroid control: launch Android apps (e.g. WhatsApp) from our launcher.

`Waydroid` shells out to the ``waydroid`` CLI on the Pi; `MockWaydroid` returns
canned data so the Apps screen and tests work without a container. Use
:func:`build_waydroid`.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

# Apps we surface prominently in the launcher, with their Android package ids.
FEATURED = [
    ("WhatsApp", "com.whatsapp"),
    ("Telegram", "org.telegram.messenger"),
    ("Chrome", "com.android.chrome"),
]


@dataclass
class AndroidApp:
    name: str
    package: str


class MockWaydroid:
    def __init__(self) -> None:
        self.launched: list[str] = []
        self.session_started = False

    def available(self) -> bool:
        return True

    def ensure_session(self) -> None:
        self.session_started = True

    def list_apps(self) -> list[AndroidApp]:
        return [AndroidApp(n, p) for n, p in FEATURED]

    def launch(self, package: str) -> None:
        self.ensure_session()
        self.launched.append(package)

    def launch_whatsapp(self) -> None:
        self.launch("com.whatsapp")


class Waydroid:
    def available(self) -> bool:
        try:
            subprocess.run(["waydroid", "status"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def ensure_session(self) -> None:
        # Start the container session if it isn't already running.
        try:
            status = subprocess.run(["waydroid", "status"], capture_output=True,
                                    text=True, timeout=10)
            if "RUNNING" not in status.stdout:
                subprocess.Popen(["waydroid", "session", "start"])
        except Exception:
            pass

    def list_apps(self) -> list[AndroidApp]:
        apps: list[AndroidApp] = []
        try:
            out = subprocess.run(["waydroid", "app", "list"], capture_output=True,
                                 text=True, timeout=15).stdout
            name = None
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("Name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("packageName:") and name:
                    apps.append(AndroidApp(name, line.split(":", 1)[1].strip()))
                    name = None
        except Exception:
            pass
        # Fall back to the featured list if enumeration failed.
        return apps or [AndroidApp(n, p) for n, p in FEATURED]

    def launch(self, package: str) -> None:
        self.ensure_session()
        try:
            subprocess.Popen(["waydroid", "app", "launch", package])
        except Exception:
            pass

    def launch_whatsapp(self) -> None:
        self.launch("com.whatsapp")


def build_waydroid(mock: bool):
    """Real Waydroid when available, else the mock.

    Even in --mock (simulated modem) we use real Waydroid if the binary is
    installed, so Android apps (WhatsApp/Chrome) actually launch on the Pi.
    """
    if not mock:
        return Waydroid()
    import shutil
    return Waydroid() if shutil.which("waydroid") else MockWaydroid()
