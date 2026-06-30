"""ItayPhone entry point.

Examples
--------
Run against real hardware (SIM7600 on /dev/ttyUSB2)::

    python -m itayphone.main --port /dev/ttyUSB2

Run on a laptop without hardware (simulated modem)::

    python -m itayphone.main --mock

Headless smoke test of the modem layer (no Kivy needed)::

    python -m itayphone.main --mock --demo
"""

from __future__ import annotations

import argparse
import os

from .camera import build_camera
from .config import Config
from .contacts import ContactStore
from .history import CallLog
from .modem import SIM7600
from .modem.transport import ATTransport, MockTransport
from .system import build_system
from .waydroid import build_waydroid


def build_modem(cfg: Config) -> SIM7600:
    if cfg.mock:
        transport = MockTransport()
    else:
        transport = ATTransport(cfg.serial_port, cfg.baudrate)
    modem = SIM7600(transport)
    modem.setup(pin=cfg.sim_pin)
    return modem


def run_demo(modem: SIM7600) -> None:
    """Exercise the modem layer without a GUI — useful before parts arrive."""
    status = modem.network_status()
    print(f"Operator : {status.operator} ({status.technology})")
    print(f"Signal   : {status.signal_dbm} dBm  [{status.bars}/4 bars]")
    print(f"Registered: {status.registered}")

    # Simulate an incoming call + SMS through the mock transport.
    modem.on_incoming_call = lambda n: print(f"\n[event] Incoming call from {n}")
    modem.on_new_sms = lambda s: print(f"[event] New SMS from {s.sender}: {s.text}")
    t = modem._t
    if isinstance(t, MockTransport):
        t.set_response("AT+CMGR=1",
                       ['+CMGR: "REC UNREAD","+972500000000",,"26/07/01,10:00:00+12"',
                        "Hello from ItayPhone!"])
        t.inject_urc('+CLIP: "+972500000000",145')
        t.inject_urc('+CMTI: "SM",1')
    print("\nDemo finished.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="itayphone")
    parser.add_argument("--port", default=Config.serial_port,
                        help="serial port for the SIM7600 AT interface")
    parser.add_argument("--pin", default=None, help="SIM PIN if locked")
    parser.add_argument("--mock", action="store_true",
                        help="use a simulated modem (no hardware)")
    parser.add_argument("--demo", action="store_true",
                        help="run a headless modem smoke test and exit")
    parser.add_argument("--volte", action="store_true",
                        help="run VoLTE setup/diagnostics and exit")
    args = parser.parse_args()

    cfg = Config(serial_port=args.port, sim_pin=args.pin, mock=args.mock)
    modem = build_modem(cfg)
    contacts = ContactStore(cfg.contacts_file)
    history = CallLog(cfg.history_file)

    if args.volte:
        print("VoLTE setup / diagnostics (Israel 2G/3G are off — calls need VoLTE):")
        for cmd, lines in modem.configure_volte().items():
            print(f"  {cmd:<12} -> {lines or 'OK'}")
        modem.close()
        return

    if args.demo:
        run_demo(modem)
        modem.close()
        return

    camera = build_camera(cfg.mock)
    waydroid = build_waydroid(cfg.mock)
    system = build_system(cfg.mock)

    # Stop Kivy from parsing our argv (it would choke on --mock), and use a
    # borderless phone-shaped window. Borderless on EVERY platform: on the Pi a
    # normal window gets a window-manager title bar that overlaps/cuts the status
    # bar and clock at the top, so we drop the decoration everywhere (Esc closes).
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    import sys as _sys
    from kivy.config import Config as KivyConfig
    _PHONE_W, _PHONE_H = 360, 720
    KivyConfig.set("graphics", "width", str(_PHONE_W))
    KivyConfig.set("graphics", "height", str(_PHONE_H))
    KivyConfig.set("graphics", "resizable", "0")
    KivyConfig.set("graphics", "borderless", "1")
    # Fixed, on-screen position (manual centring via GetSystemMetrics fought with
    # Windows DPI scaling and pushed the window off-screen). Overrides any stale
    # position cached in ~/.kivy/config.ini.
    KivyConfig.set("graphics", "position", "custom")
    KivyConfig.set("graphics", "left", "60")
    KivyConfig.set("graphics", "top", "40")

    # Import Kivy lazily so --demo / tests don't require it.
    from .ui.app import ItayPhoneApp

    try:
        ItayPhoneApp(
            modem=modem, contacts=contacts, history=history,
            camera=camera, waydroid=waydroid, photos_dir=cfg.photos_path,
            system=system,
        ).run()
    finally:
        modem.close()


if __name__ == "__main__":
    main()
