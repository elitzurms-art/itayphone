"""Tests for the SIM7600 driver, using the simulated transport (no hardware)."""

from itayphone.modem import SIM7600
from itayphone.modem.models import CallState
from itayphone.modem.transport import MockTransport


def make_modem() -> SIM7600:
    modem = SIM7600(MockTransport())
    modem.setup()
    return modem


def test_network_status_parsing():
    modem = make_modem()
    status = modem.network_status()
    assert status.registered is True
    assert status.operator == "Partner IL"
    assert status.technology == "LTE"
    assert status.signal_dbm == -65          # +CSQ: 24 -> -113 + 48
    assert status.bars == 4


def test_dial_sends_atd_voice():
    modem = make_modem()
    modem.dial("0501234567")
    assert "ATD0501234567;" in modem._t.sent
    assert modem.call_state is CallState.DIALING


def test_hangup_resets_state():
    modem = make_modem()
    modem.dial("0501234567")
    modem.hangup()
    assert "AT+CHUP" in modem._t.sent
    assert modem.call_state is CallState.IDLE


def test_send_sms_uses_ctrl_z():
    modem = make_modem()
    modem.send_sms("0501234567", "hi")
    sent = modem._t.sent[-1]
    assert sent.startswith('AT+CMGS="0501234567"')
    assert sent.endswith("\x1a")            # Ctrl-Z terminates the body


def test_incoming_call_urc_fires_callback():
    modem = make_modem()
    seen = []
    modem.on_incoming_call = seen.append
    modem._t.inject_urc('+CLIP: "+972500000000",145')
    assert seen == ["+972500000000"]
    assert modem.call_state is CallState.INCOMING


def test_new_sms_urc_reads_and_fires_callback():
    modem = make_modem()
    modem._t.set_response(
        "AT+CMGR=3",
        ['+CMGR: "REC UNREAD","+972500000000",,"26/07/01,10:00:00+12"',
         "Hello!"],
    )
    received = []
    modem.on_new_sms = received.append
    modem._t.inject_urc('+CMTI: "SM",3')
    assert len(received) == 1
    assert received[0].sender == "+972500000000"
    assert received[0].text == "Hello!"
    assert received[0].unread is True


def test_configure_volte_sets_network_mode_and_runs_diagnostics():
    modem = make_modem()
    results = modem.configure_volte()
    # Network mode set to automatic, and the IMS/VoLTE diagnostics were issued.
    assert "AT+CNMP=2" in modem._t.sent
    for cmd in ("AT+CEREG?", "AT+CIREG?", "AT+CPSI?", "AT+CVOLTE=1"):
        assert cmd in results


def test_set_mute_sends_cmut():
    modem = make_modem()
    modem.set_mute(True)
    assert "AT+CMUT=1" in modem._t.sent
    modem.set_mute(False)
    assert "AT+CMUT=0" in modem._t.sent


def test_voice_call_begin_urc_fires_connected():
    modem = make_modem()
    connected = []
    modem.on_call_connected = lambda: connected.append(True)
    modem._t.inject_urc("VOICE CALL: BEGIN")
    assert connected == [True]
    assert modem.call_state is CallState.ACTIVE


def test_call_ended_urc():
    modem = make_modem()
    modem.call_state = CallState.ACTIVE
    ended = []
    modem.on_call_ended = lambda: ended.append(True)
    modem._t.inject_urc("NO CARRIER")
    assert ended == [True]
    assert modem.call_state is CallState.IDLE
