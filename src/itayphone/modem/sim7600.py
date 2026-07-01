"""High-level SIM7600G-H driver: calls, SMS and network status.

Built on top of an AT transport (real :class:`ATTransport` or
:class:`MockTransport`). Unsolicited events from the modem are translated into
Python callbacks the UI can subscribe to:

    modem.on_incoming_call = lambda number: ...
    modem.on_call_ended    = lambda: ...
    modem.on_new_sms       = lambda sms: ...

Audio note: on the SIM7600 the *voice path of a call* is analog and routed
through the module's own audio pins, not through the Pi. The dialer below only
controls call *signalling* (dial/answer/hang up). Wiring a speaker + electret
mic to the HAT, and selecting the audio channel (AT+CSDVC), is handled during
hardware bring-up — see PLAN.md.
"""

from __future__ import annotations

import re
from typing import Callable

from .models import SMS, CallState, NetworkStatus
from .transport import ATError

# +CSQ: <rssi>,<ber> ; rssi 0..31 maps linearly to -113..-51 dBm, 99 = unknown
_CSQ_RE = re.compile(r"\+CSQ:\s*(\d+),")
# +COPS: <mode>,<format>,"<operator>"[,<act>]
_COPS_RE = re.compile(r'\+COPS:\s*\d+,\d+,"([^"]*)"(?:,(\d+))?')
# +CLIP: "<number>",<type>,...
_CLIP_RE = re.compile(r'\+CLIP:\s*"([^"]*)"')
# +CMTI: "SM",<index>
_CMTI_RE = re.compile(r'\+CMTI:\s*"\w+",(\d+)')
# +CMGR: "<stat>","<sender>",,"<timestamp>"
_CMGR_HDR_RE = re.compile(r'\+CMGR:\s*"([^"]*)","([^"]*)",[^,]*,"([^"]*)"')

# 3GPP access technology codes from +COPS / +CREG act field.
_ACT = {
    "0": "GSM", "2": "WCDMA", "3": "GSM", "4": "WCDMA",
    "5": "WCDMA", "6": "WCDMA", "7": "LTE", "9": "LTE",
}


class SIM7600:
    def __init__(self, transport) -> None:
        self._t = transport
        # Wire ourselves in as the transport's URC handler.
        self._t.urc_callback = self._on_urc

        self.call_state: CallState = CallState.IDLE
        self.last_number: str = ""

        # Event hooks (set by the UI).
        self.on_incoming_call: Callable[[str], None] | None = None
        self.on_call_connected: Callable[[], None] | None = None
        self.on_call_ended: Callable[[], None] | None = None
        self.on_new_sms: Callable[[SMS], None] | None = None

    # -- lifecycle ---------------------------------------------------------
    def setup(self, pin: str | None = None) -> None:
        """Open the port and put the modem into a known state.

        Each configuration command is best-effort: with no SIM inserted (or
        before the modem is ready) commands like ``AT+CMGF`` return ``ERROR``,
        and the phone must still boot — just without cellular service. So we
        swallow :class:`ATError` per command instead of crashing at startup.
        """
        self._t.open()

        def _try(cmd: str) -> None:
            try:
                self._t.send(cmd)
            except ATError:
                pass

        _try("AT")            # sanity check / autobaud
        _try("ATE0")          # disable command echo
        if pin:
            _try(f'AT+CPIN="{pin}"')
        _try("AT+CMGF=1")     # SMS text mode
        _try("AT+CLIP=1")     # show caller id on incoming calls
        _try('AT+CNMI=2,1,0,0,0')  # notify on new SMS via +CMTI

    def close(self) -> None:
        self._t.close()

    # -- network -----------------------------------------------------------
    def network_status(self) -> NetworkStatus:
        status = NetworkStatus()
        try:
            reg = self._t.send("AT+CEREG?") or self._t.send("AT+CREG?")
            status.registered = any(",1" in r or ",5" in r for r in reg)
            for line in self._t.send("AT+CSQ"):
                m = _CSQ_RE.search(line)
                if m:
                    rssi = int(m.group(1))
                    status.signal_dbm = None if rssi == 99 else -113 + 2 * rssi
            for line in self._t.send("AT+COPS?"):
                m = _COPS_RE.search(line)
                if m:
                    status.operator = m.group(1)
                    status.technology = _ACT.get(m.group(2) or "", "")
        except Exception:
            pass
        return status

    # -- VoLTE -------------------------------------------------------------
    def configure_volte(self) -> dict[str, list[str]]:
        """Best-effort VoLTE setup + diagnostics.

        Israel shut down 2G/3G, so voice calls must run over LTE via VoLTE.
        Whether VoLTE works depends on BOTH the modem firmware and the
        carrier's provisioning, so this can't be guaranteed from AT commands
        alone — it nudges the common knobs and gathers status. Inspect the
        returned dict if calls still fail to connect (see PLAN.md).
        """
        results: dict[str, list[str]] = {}

        def run(cmd: str) -> None:
            try:
                results[cmd] = self._t.send(cmd)
            except Exception as exc:  # keep going; record the failure
                results[cmd] = [f"ERROR: {exc}"]

        run("AT+CNMP=2")     # network mode: automatic (keeps LTE available)
        run("AT+CNMP?")
        run("AT+CEREG?")     # EPS (LTE) registration status
        run("AT+CIREG?")     # IMS registration — VoLTE rides on IMS
        run("AT+CIREP=1")    # report IMS state changes
        run("AT+CPSI?")      # system info: serving band + whether IMS is up
        run("AT+CVOLTE=1")   # enable VoLTE (vendor cmd; may ERROR on some fw)
        return results

    # -- calls -------------------------------------------------------------
    def dial(self, number: str) -> None:
        self.last_number = number
        self.call_state = CallState.DIALING
        self._t.send(f"ATD{number};")   # ';' = voice call

    def answer(self) -> None:
        self._t.send("ATA")
        self.call_state = CallState.ACTIVE

    def hangup(self) -> None:
        self._t.send("AT+CHUP")
        self.call_state = CallState.IDLE

    def set_mute(self, muted: bool) -> None:
        """Mute/unmute the uplink microphone during a call."""
        self._t.send(f"AT+CMUT={1 if muted else 0}")

    # -- SMS ---------------------------------------------------------------
    def send_sms(self, number: str, text: str) -> None:
        """Send a text SMS. Requires text mode (AT+CMGF=1, set in setup)."""
        # The modem prompts with '>' after AT+CMGS; the body ends with Ctrl-Z.
        self._t.send(f'AT+CMGS="{number}"\r{text}\x1a', timeout=30.0)

    def read_sms(self, index: int) -> SMS | None:
        lines = self._t.send(f"AT+CMGR={index}")
        header = next((l for l in lines if l.startswith("+CMGR:")), None)
        if not header:
            return None
        m = _CMGR_HDR_RE.search(header)
        if not m:
            return None
        stat, sender, ts = m.group(1), m.group(2), m.group(3)
        body_idx = lines.index(header) + 1
        text = lines[body_idx] if body_idx < len(lines) else ""
        return SMS(index=index, sender=sender, timestamp=ts, text=text,
                   unread=stat.startswith("REC UNREAD"))

    def list_sms(self, which: str = "ALL") -> list[SMS]:
        """List stored messages. `which` is an AT status filter, e.g.
        'ALL', 'REC UNREAD', 'REC READ'."""
        messages: list[SMS] = []
        lines = self._t.send(f'AT+CMGL="{which}"')
        i = 0
        while i < len(lines):
            if lines[i].startswith("+CMGL:"):
                m = re.search(r'\+CMGL:\s*(\d+),"([^"]*)","([^"]*)",[^,]*,"([^"]*)"',
                              lines[i])
                if m and i + 1 < len(lines):
                    messages.append(SMS(
                        index=int(m.group(1)), sender=m.group(3),
                        timestamp=m.group(4), text=lines[i + 1],
                        unread=m.group(2).startswith("REC UNREAD"),
                    ))
                    i += 2
                    continue
            i += 1
        return messages

    def delete_sms(self, index: int) -> None:
        self._t.send(f"AT+CMGD={index}")

    # -- URC handling ------------------------------------------------------
    def _on_urc(self, line: str) -> None:
        if line.startswith("RING") or line.startswith("+CLIP:"):
            m = _CLIP_RE.search(line)
            number = m.group(1) if m else self.last_number
            if self.call_state != CallState.INCOMING:
                self.call_state = CallState.INCOMING
                if self.on_incoming_call:
                    self.on_incoming_call(number)
        elif line.startswith("VOICE CALL: BEGIN"):
            # The far end answered (outgoing) or our answer connected.
            self.call_state = CallState.ACTIVE
            if self.on_call_connected:
                self.on_call_connected()
        elif line.startswith("NO CARRIER") or line.startswith("VOICE CALL: END"):
            self.call_state = CallState.IDLE
            if self.on_call_ended:
                self.on_call_ended()
        elif line.startswith("+CMTI:"):
            m = _CMTI_RE.search(line)
            if m:
                sms = self.read_sms(int(m.group(1)))
                if sms and self.on_new_sms:
                    self.on_new_sms(sms)
