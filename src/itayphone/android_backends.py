"""Android-native backends — only imported when running on an Android phone.

Bridges ItayPhone's actions to real Android features through pyjnius (Java
reflection) and intents, so they work on a real device:

* **Apps** — launch the *actual* installed WhatsApp / Telegram / Chrome.
* **Phone** — dial a number / open SMS through the system apps.
* **Flashlight** — the real camera torch.
* **Wi-Fi / Bluetooth** — read state; open the system panels (modern Android
  forbids third-party apps from silently scanning/toggling these).
* **Camera** — capture via the system camera (plyer).

Everything is best-effort and defensive: a failure returns ``False`` / an empty
list rather than crashing the UI.
"""

from __future__ import annotations

import os
import time

_NEW_TASK = 0x10000000   # Intent.FLAG_ACTIVITY_NEW_TASK


def _activity():
    from jnius import autoclass
    return autoclass("org.kivy.android.PythonActivity").mActivity


def _start(intent):
    intent.addFlags(_NEW_TASK)
    _activity().startActivity(intent)


def _view(uri_str, action="android.intent.action.VIEW"):
    from jnius import autoclass
    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    _start(Intent(action, Uri.parse(uri_str)))


def _settings(action):
    from jnius import autoclass
    Intent = autoclass("android.content.Intent")
    _start(Intent(action))


def request_permissions():
    """Ask for the runtime permissions the features need (no-op off Android)."""
    try:
        from android.permissions import Permission, request_permissions as req
        req([Permission.CALL_PHONE, Permission.SEND_SMS, Permission.CAMERA,
             Permission.ACCESS_FINE_LOCATION, Permission.WRITE_EXTERNAL_STORAGE,
             Permission.READ_EXTERNAL_STORAGE])
    except Exception:
        pass


class AndroidPhone:
    """Routes in-app call / SMS actions to the system phone & messaging apps."""

    def call(self, number: str) -> bool:
        try:
            _view("tel:" + number, "android.intent.action.DIAL")
            return True
        except Exception:
            return False

    def sms(self, number: str, body: str = "") -> bool:
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            intent = Intent("android.intent.action.SENDTO",
                            Uri.parse("smsto:" + number))
            if body:
                intent.putExtra("sms_body", body)
            _start(intent)
            return True
        except Exception:
            return False


class AndroidApps:
    """Drop-in for the Waydroid backend: launches real installed apps."""

    def available(self) -> bool:
        return True

    def ensure_session(self) -> None:
        pass

    def list_apps(self):
        from .waydroid import FEATURED, AndroidApp
        return [AndroidApp(n, p) for n, p in FEATURED]

    def launch(self, package: str) -> None:
        try:
            act = _activity()
            intent = act.getPackageManager().getLaunchIntentForPackage(package)
            if intent is None:                       # not installed -> store page
                _view("market://details?id=" + package)
                return
            _start(intent)
        except Exception:
            pass

    def launch_whatsapp(self) -> None:
        self.launch("com.whatsapp")


class AndroidSystem:
    """Real radio state + flashlight; opens system panels for scan/connect."""

    def __init__(self) -> None:
        self._cam_id = None

    # -- radio power / state ----------------------------------------------
    def set_wifi(self, on: bool) -> bool:
        _settings("android.settings.WIFI_SETTINGS")
        return True

    def set_bluetooth(self, on: bool) -> bool:
        _settings("android.settings.BLUETOOTH_SETTINGS")
        return True

    def wifi_enabled(self) -> bool:
        try:
            from jnius import autoclass
            Context = autoclass("android.content.Context")
            wm = _activity().getSystemService(Context.WIFI_SERVICE)
            return bool(wm.isWifiEnabled())
        except Exception:
            return False

    def bt_powered(self) -> bool:
        try:
            from jnius import autoclass
            BA = autoclass("android.bluetooth.BluetoothAdapter")
            ad = BA.getDefaultAdapter()
            return bool(ad and ad.isEnabled())
        except Exception:
            return False

    # -- scan / connect open the system panels (Android restricts the rest) -
    def wifi_scan(self):
        _settings("android.settings.WIFI_SETTINGS")
        return []

    def wifi_connect(self, ssid: str, password: str = "") -> bool:
        _settings("android.settings.WIFI_SETTINGS")
        return False

    def bt_scan(self, seconds: float = 6) -> None:
        _settings("android.settings.BLUETOOTH_SETTINGS")

    def bt_list(self):
        return []

    def bt_connect(self, mac: str) -> bool:
        _settings("android.settings.BLUETOOTH_SETTINGS")
        return False

    def bt_disconnect(self, mac: str) -> bool:
        return False

    # -- flashlight (real torch) ------------------------------------------
    def set_flashlight(self, on: bool) -> bool:
        try:
            from jnius import autoclass
            Context = autoclass("android.content.Context")
            cm = _activity().getSystemService(Context.CAMERA_SERVICE)
            if self._cam_id is None:
                self._cam_id = cm.getCameraIdList()[0]
            cm.setTorchMode(self._cam_id, bool(on))
            return True
        except Exception:
            return False


class AndroidCamera:
    """Capture a photo via the system camera (best-effort, async result)."""

    def __init__(self, photos_dir: str) -> None:
        self._dir = photos_dir

    def available(self) -> bool:
        return True

    def start_preview(self) -> None:
        pass

    def stop_preview(self) -> None:
        pass

    def capture(self, directory: str | None = None) -> str:
        d = os.path.expanduser(directory or self._dir)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, time.strftime("IMG_%Y%m%d_%H%M%S.jpg"))
        try:
            from plyer import camera
            camera.take_picture(filename=path, on_complete=lambda *_: None)
        except Exception:
            pass
        return path
