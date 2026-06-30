"""Packaged entry point (Android APK / desktop preview).

python-for-android looks for a top-level ``main.py``. On a phone there is no
SIM7600 / Waydroid / NetworkManager, so the cellular layer runs on the mock
modem, while the things Android *can* do for real — launching apps, dialing,
SMS, the flashlight, the camera, the Wi-Fi/Bluetooth panels — go through the
Android backends (see ``itayphone.android_backends``).

Run on a laptop the same way with ``python main.py`` (everything mock).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.utils import platform  # noqa: E402

from itayphone.camera import build_camera  # noqa: E402
from itayphone.config import Config  # noqa: E402
from itayphone.contacts import ContactStore  # noqa: E402
from itayphone.history import CallLog  # noqa: E402
from itayphone.modem import SIM7600  # noqa: E402
from itayphone.modem.transport import MockTransport  # noqa: E402
from itayphone.system import build_system  # noqa: E402
from itayphone.waydroid import build_waydroid  # noqa: E402


def _storage_base() -> str:
    """A writable base directory for contacts/history/photos."""
    if platform == "android":
        try:
            from android.storage import app_storage_path
            return app_storage_path()
        except Exception:
            pass
    return os.path.expanduser("~")


def main() -> None:
    base = _storage_base()
    cfg = Config(
        mock=True,
        contacts_path=os.path.join(base, ".itayphone", "contacts.json"),
        history_path=os.path.join(base, ".itayphone", "history.json"),
        photos_path=os.path.join(base, ".itayphone", "photos"),
    )

    modem = SIM7600(MockTransport())
    modem.setup()

    if platform == "android":
        from itayphone.android_backends import (AndroidApps, AndroidCamera,
                                                AndroidSystem, request_permissions)
        request_permissions()
        waydroid = AndroidApps()
        system = AndroidSystem()
        camera = AndroidCamera(cfg.photos_path)
    else:
        waydroid = build_waydroid(True)
        system = build_system(True)
        camera = build_camera(True)

    from itayphone.ui.app import ItayPhoneApp
    app = ItayPhoneApp(
        modem=modem, contacts=ContactStore(cfg.contacts_file),
        history=CallLog(cfg.history_file), camera=camera, waydroid=waydroid,
        system=system, photos_dir=cfg.photos_path,
    )
    if platform == "android":
        from itayphone.android_backends import AndroidPhone
        app.android = AndroidPhone()      # routes calls/SMS to the OS
    app.run()


if __name__ == "__main__":
    main()
