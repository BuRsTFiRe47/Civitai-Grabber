"""Queue order, skip-existing, error handling and the 'when done' power action."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from civitai_grabber.core import api, power  # noqa: E402
from civitai_grabber.core.downloader import download, part_path  # noqa: E402
from civitai_grabber.core.engine import Engine  # noqa: E402
from civitai_grabber.core.links import ParsedLink  # noqa: E402
from civitai_grabber.core.models import DONE, ERROR, PAUSED, QUEUED, READY, Item  # noqa: E402
from civitai_grabber.core.storage import Settings, Storage  # noqa: E402
from civitai_grabber.i18n import set_language  # noqa: E402
from civitai_grabber.ui import theme  # noqa: E402
from civitai_grabber.ui.main_window import MainWindow  # noqa: E402
from civitai_grabber.ui.table_model import IdRole  # noqa: E402
from tests.test_core import sess  # noqa: E402


@pytest.fixture(autouse=True)
def plain_http(monkeypatch):
    monkeypatch.setattr(api, "SCHEME", "http")
    set_language("tr")


@pytest.fixture
def env(qtbot, tmp_path, server):
    engine = Engine(Storage(tmp_path / "cfg"), Settings(start_delay=0.0, max_concurrent=2, retries=0))
    engine.cf_cooldown = 0.0
    theme.apply_theme(QApplication.instance(), "dark")
    win = MainWindow(engine)
    qtbot.addWidget(win)
    win.show()
    engine.begin()
    yield engine, win, server, tmp_path
    engine.shutdown()


def add(engine, server, *vids):
    return engine.add_links([ParsedLink(f"https://civitai.com/api/download/models/{v}", server, "version", version_id=v) for v in vids])


def wait_state(qtbot, engine, state, ids=None, timeout=15000):
    def ok():
        its = [engine.items[i] for i in (ids or engine.order)]
        assert its and all(i.state == state for i in its), [(i.state, i.error) for i in its]
    qtbot.waitUntil(ok, timeout=timeout)


def bare_engine(qtbot, tmp_path, names="abcde"):
    e = Engine(Storage(tmp_path / "cfg"), Settings())
    for n in names:
        e.items[n] = Item(url=n, id=n, state=READY, download_url="x", filename=f"{n}.safetensors", version_id=ord(n))
        e.order.append(n)
    return e


# ------------------------------------------------------------------ queue ordering
@pytest.mark.parametrize("sel,how,visible,expected", [
    (["c"], "up", None, "acbde"),
    (["a"], "up", None, "abcde"),                 # already first: nothing to do
    (["b", "c"], "up", None, "bcade"),            # a block moves together
    (["b", "c"], "down", None, "adbce"),
    (["b", "d"], "up", None, "badce"),            # non-contiguous selection
    (["b", "d"], "down", None, "acbed"),
    (["d", "e"], "top", None, "deabc"),
    (["a"], "bottom", None, "bcdea"),
    (["e"], "down", None, "abcde"),               # already last
    (["c"], "up", ["a", "c", "e"], "cabde"),      # group filter: jumps over the previous *visible* row
    (["e"], "top", ["a", "c", "e"], "eabcd"),
    (["a"], "bottom", ["a", "c", "e"], "bcdea"),
])
def test_move(qtbot, tmp_path, sel, how, visible, expected):
    e = bare_engine(qtbot, tmp_path)
    changed = e.move(sel, how, visible)
    assert "".join(e.order) == expected
    assert changed == (expected != "abcde")


def test_order_is_saved_and_restored(qtbot, tmp_path):
    e = bare_engine(qtbot, tmp_path)
    e.move(["e"], "top")
    e.save_now()
    _, items = Storage(tmp_path / "cfg").load_state()
    assert [i.id for i in items] == list("eabcd")


def test_scheduler_follows_the_queue_order(qtbot, tmp_path, monkeypatch):
    e = bare_engine(qtbot, tmp_path, "abc")
    e.settings.default_folder = str(tmp_path / "dl")
    e.settings.start_delay = 0.0
    e.settings.max_concurrent = 3
    started = []
    monkeypatch.setattr(e, "_spawn_download", lambda it: (started.append(it.id), setattr(it, "state", "downloading")))
    e.move(["c"], "top")
    e.start(list(e.order))
    for _ in range(3):
        e._schedule()
    assert started == ["c", "a", "b"]


def test_window_reorders_rows_and_keeps_selection(env, qtbot):
    engine, win, server, tmp = env
    add(engine, server, 101, 102, 103)
    wait_state(qtbot, engine, READY)
    order0 = list(engine.order)
    win.view.sortByColumn(2, Qt.AscendingOrder)          # a column sort is active ...
    win.view.selectRow(2)
    win.a_top.trigger()                                  # ... moving resets it to queue order
    assert engine.order == [order0[2], order0[0], order0[1]]
    assert [win.proxy.index(r, 0).data(IdRole) for r in range(3)] == engine.order
    assert win._selected_ids() == [order0[2]]            # still selected, now on top
    win.a_down.trigger()
    assert engine.order == [order0[0], order0[2], order0[1]] and win._selected_ids() == [order0[2]]


# ------------------------------------------------------------------ skip existing + part files
def test_existing_file_with_same_size_is_skipped_without_any_request(tmp_path, payload):
    (tmp_path / "m.safetensors").write_bytes(payload)
    seen = []
    p = download(sess(), "http://127.0.0.1:9/never-reachable", tmp_path, "m.safetensors", expected_size=len(payload),
                 skip_existing=True, progress=lambda d, t: seen.append((d, t)))
    assert p == tmp_path / "m.safetensors" and seen[-1] == (len(payload), len(payload))


def test_existing_file_with_other_size_is_downloaded_next_to_it(server, tmp_path, payload):
    (tmp_path / "m.bin").write_bytes(b"old")
    p = download(sess(), f"http://{server}/file", tmp_path, "m.bin", expected_size=len(payload), skip_existing=True)
    assert p.name == "m (1).bin" and p.read_bytes() == payload and (tmp_path / "m.bin").read_bytes() == b"old"


def test_skip_can_be_switched_off(server, tmp_path, payload):
    (tmp_path / "m.bin").write_bytes(payload)
    seen = []
    download(sess(), f"http://{server}/file", tmp_path, "m.bin", expected_size=len(payload), skip_existing=False,
             progress=lambda d, t: seen.append(d))
    assert seen and seen[0] == 0     # it really went to the network


def test_same_file_name_in_one_folder_uses_separate_part_files(server, tmp_path, payload):
    assert part_path(tmp_path, "model.safetensors", "11") != part_path(tmp_path, "model.safetensors", "22")
    (part_path(tmp_path, "model.safetensors", "11")).write_bytes(payload[:120_000])
    (part_path(tmp_path, "model.safetensors", "22")).write_bytes(payload[:50_000])
    starts = []
    # each download resumes *its own* part (same folder, one after the other)
    a = download(sess(), f"http://{server}/file", tmp_path, "model.safetensors", part_suffix="11",
                 progress=lambda d, t: starts.append(d))
    assert starts[0] == 120_000 and a.read_bytes() == payload
    starts.clear()
    b = download(sess(), f"http://{server}/file", tmp_path, "model.safetensors", part_suffix="22",
                 progress=lambda d, t: starts.append(d))
    assert starts[0] == 50_000 and b.read_bytes() == payload
    assert not list(tmp_path.glob("*.part"))


def test_engine_skips_an_already_downloaded_file(env, qtbot, payload):
    engine, win, server, tmp = env
    add(engine, server, 201)
    wait_state(qtbot, engine, READY)
    it = engine.items[engine.order[0]]
    assert it.size == len(payload)                       # API size is rounded to the exact byte count
    g = engine.add_group("G", str(tmp / "g"))
    engine.set_group([it.id], g.id)
    (tmp / "g").mkdir()
    (tmp / "g" / it.filename).write_bytes(payload)
    it.download_url = f"http://{server}/gone"           # would 404 if it were requested
    engine.start([it.id])
    wait_state(qtbot, engine, DONE)


# ------------------------------------------------------------------ errors do not stop the queue
def test_cloudflare_on_one_file_does_not_stop_the_next(env, qtbot, payload):
    engine, win, server, tmp = env
    engine.settings.max_concurrent = 1
    add(engine, server, 301, 302)
    wait_state(qtbot, engine, READY)
    g = engine.add_group("G", str(tmp / "q"))
    engine.set_group(engine.order, g.id)
    first, second = (engine.items[i] for i in engine.order)
    second.filename = "second.safetensors"
    first.download_url = f"http://{server}/cf"
    engine.start(engine.order)
    qtbot.waitUntil(lambda: first.state == ERROR and second.state == DONE, timeout=15000)
    assert first.error.startswith("cloudflare")
    assert (tmp / "q" / "second.safetensors").read_bytes() == payload


def test_login_error_also_moves_on(env, qtbot):
    engine, win, server, tmp = env
    engine.settings.max_concurrent = 1
    add(engine, server, 311, 312)
    wait_state(qtbot, engine, READY)
    g = engine.add_group("G", str(tmp / "q2"))
    engine.set_group(engine.order, g.id)
    first, second = (engine.items[i] for i in engine.order)
    second.filename = "two.safetensors"
    first.download_url = f"http://{server}/forbidden"
    engine.start(engine.order)
    qtbot.waitUntil(lambda: first.state == ERROR and second.state == DONE, timeout=15000)


def test_cloudflare_stop_queue_is_still_available_as_a_setting(env, qtbot):
    engine, win, server, tmp = env
    engine.settings.max_concurrent = 1
    engine.settings.stop_on_cloudflare = True
    add(engine, server, 321, 322)
    wait_state(qtbot, engine, READY)
    g = engine.add_group("G", str(tmp / "q3"))
    engine.set_group(engine.order, g.id)
    first, second = (engine.items[i] for i in engine.order)
    first.download_url = f"http://{server}/cf"
    engine.start(engine.order)
    qtbot.waitUntil(lambda: first.state == ERROR, timeout=10000)
    assert second.state == READY


# ------------------------------------------------------------------ power action
def test_power_commands_per_platform():
    assert power.command_for("hibernate", "win32") == ["shutdown", "/h"]
    assert power.command_for("shutdown", "win32") == ["shutdown", "/s", "/t", "0"]
    assert power.command_for("hibernate", "linux") == ["systemctl", "hibernate"]
    assert power.command_for("shutdown", "linux") == ["systemctl", "poweroff"]
    assert power.command_for("hibernate", "darwin")[0] == "pmset"
    assert power.command_for("none", "win32") is None


def test_power_fires_once_after_the_last_download(env, qtbot):
    engine, win, server, tmp = env
    add(engine, server, 401, 402)
    wait_state(qtbot, engine, READY)
    g = engine.add_group("G", str(tmp / "p"))
    engine.set_group(engine.order, g.id)
    for n, i in enumerate(engine.order):
        engine.items[i].filename = f"p{n}.safetensors"
    fired = []
    engine.allFinished.connect(fired.append)
    engine.set_power_mode("shutdown")
    assert win.power_combo.currentData() == "shutdown"
    engine.start(engine.order)
    qtbot.waitUntil(lambda: bool(fired), timeout=15000)
    assert fired == ["shutdown"] and engine.power_mode == "none"
    assert win.power_combo.currentData() == "none"       # disarmed again, no repeat
    assert win.log_dock is not None


def test_power_not_fired_when_idle_or_paused(qtbot, tmp_path):
    e = bare_engine(qtbot, tmp_path, "ab")
    fired = []
    e.allFinished.connect(fired.append)
    e.set_power_mode("hibernate")                          # armed on an idle queue: nothing to wait for
    e._maybe_all_finished()
    assert fired == []
    e._power_activity = True
    e.items["a"].state = PAUSED                            # user paused something -> do not shut down
    e._maybe_all_finished()
    assert fired == []
    e.items["a"].state = DONE
    e._maybe_all_finished()
    assert fired == ["hibernate"]


def test_power_armed_while_downloading_counts(qtbot, tmp_path):
    e = bare_engine(qtbot, tmp_path, "ab")
    e.items["a"].state = QUEUED
    e.set_power_mode("shutdown")
    assert e._power_activity is True
    e.items["a"].state = DONE
    fired = []
    e.allFinished.connect(fired.append)
    e._maybe_all_finished()
    assert fired == ["shutdown"]


def test_power_mode_is_never_persisted(qtbot, tmp_path):
    assert "power" not in " ".join(Settings().to_dict())
    e = bare_engine(qtbot, tmp_path)
    e.set_power_mode("shutdown")
    e.save_now()
    e2 = Engine(Storage(tmp_path / "cfg"), Settings())
    assert e2.power_mode == "none"


def test_countdown_runs_action_when_it_expires(env, monkeypatch):
    engine, win, server, tmp = env
    ran = []
    monkeypatch.setattr(power, "run", lambda mode: ran.append(mode) or ["fake"])
    win._on_all_finished("hibernate")
    dlg = win._power_dialog
    assert dlg.b_cancel.isDefault() and not dlg.b_now.isDefault()   # Enter must never confirm
    assert "60" in dlg.lbl.text()
    dlg.left = 1
    dlg.tick()
    assert ran == ["hibernate"]


def test_countdown_cancel_does_not_run(env, monkeypatch):
    engine, win, server, tmp = env
    ran = []
    monkeypatch.setattr(power, "run", lambda mode: ran.append(mode))
    win._on_all_finished("shutdown")
    win._power_dialog.b_cancel.click()
    win._power_dialog.tick()          # a stray timer tick after cancel must not fire anything
    assert ran == [] and not win._power_dialog.timer.isActive()


def test_failed_power_command_is_reported(env, monkeypatch):
    engine, win, server, tmp = env
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown.append(a[2]))
    monkeypatch.setattr(power, "run", lambda mode: (_ for _ in ()).throw(OSError("hibernate is off")))
    win._run_power("hibernate")
    assert shown and "hibernate is off" in shown[0] and "powercfg" in shown[0]
