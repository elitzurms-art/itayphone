"""Tests for the call history (recents) store."""

from datetime import datetime

from itayphone.history import CallLog


def make_log(tmp_path, when="2026-07-01T14:05:00"):
    fixed = datetime.fromisoformat(when)
    return CallLog(str(tmp_path / "history.json"), now=lambda: fixed)


def test_add_and_recent_order(tmp_path):
    log = make_log(tmp_path)
    log.add("0501111111", "out")
    log.add("0502222222", "in", answered=True)
    recent = log.recent()
    # Most recent first.
    assert [r.number for r in recent] == ["0502222222", "0501111111"]


def test_outgoing_is_never_missed(tmp_path):
    log = make_log(tmp_path)
    rec = log.add("0501111111", "out")
    assert rec.missed is False
    assert rec.seen is True
    assert log.missed_unseen() == 0


def test_missed_badge_counts_unanswered_incoming(tmp_path):
    log = make_log(tmp_path)
    log.add("0501111111", "in", answered=False)
    log.add("0502222222", "in", answered=False)
    log.add("0503333333", "in", answered=True)   # answered -> not missed
    assert log.missed_unseen() == 2
    log.mark_all_seen()
    assert log.missed_unseen() == 0


def test_persistence_round_trip(tmp_path):
    path = tmp_path / "history.json"
    log = CallLog(str(path), now=lambda: datetime.fromisoformat("2026-07-01T14:05:00"))
    log.add("0501111111", "in", answered=False)
    # Reload from disk into a fresh instance.
    reloaded = CallLog(str(path))
    assert len(reloaded.recent()) == 1
    assert reloaded.missed_unseen() == 1


def test_when_label_today_vs_other_day(tmp_path):
    log = make_log(tmp_path, when=datetime.now().replace(hour=9, minute=7).isoformat())
    rec = log.add("0501111111", "out")
    assert rec.when == "09:07"            # same day -> just the time
