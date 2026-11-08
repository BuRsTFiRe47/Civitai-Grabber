"""Speed limit, drag & drop re-ordering, 'all versions of a model', Breeze theme."""
import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QDropEvent  # noqa: E402

from civitai_grabber.core.downloader import download  # noqa: E402
from civitai_grabber.core.links import ParsedLink, parse_link  # noqa: E402
from civitai_grabber.core.ratelimit import RateLimiter  # noqa: E402
from civitai_grabber.core.storage import Settings  # noqa: E402
from civitai_grabber.ui import theme  # noqa: E402
from civitai_grabber.ui.table_model import MIME, IdRole  # noqa: E402
from tests.test_core import sess  # noqa: E402
from tests.test_queue import add, bare_engine, env, plain_http, wait_state  # noqa: E402,F401,F811


# ------------------------------------------------------------------ speed limit
def test_rate_limiter_unlimited_does_not_wait():
    lim = RateLimiter(0)
    t0 = time.monotonic()
    for _ in range(50):
        lim.throttle(10_000_000)
    assert time.monotonic() - t0 < 0.2


def test_rate_limiter_paces_and_can_be_cancelled():
    lim = RateLimiter(400_000)
    t0 = time.monotonic()
    lim.throttle(400_000)
    lim.throttle(400_000)          # 800 kB at 400 kB/s -> ~2 s minus the small burst allowance
    assert 1.5 <= time.monotonic() - t0 <= 3.0
    ev = threading.Event()
    lim.set_rate(1000)
    threading.Timer(0.2, ev.set).start()
    t0 = time.monotonic()
    lim.throttle(1_000_000, ev)    # would take 1000 s
    assert time.monotonic() - t0 < 2


def test_rate_limiter_chunk_gets_small_for_low_limits():
    assert RateLimiter(0).chunk_size(262144) == 262144
    assert RateLimiter(80_000).chunk_size(262144) == 10_000
    assert RateLimiter(100).chunk_size(262144) == 2048


def test_download_respects_the_limit(server, tmp_path, payload):
    t0 = time.monotonic()
    p = download(sess(), f"http://{server}/file", tmp_path / "a", "free.safetensors", expected_size=len(payload))
    free = time.monotonic() - t0
    t0 = time.monotonic()
    p2 = download(sess(), f"http://{server}/file", tmp_path / "b", "slow.safetensors", expected_size=len(payload),
                  limiter=RateLimiter(150_000))
    slow = time.monotonic() - t0
    assert p.read_bytes() == p2.read_bytes() == payload
    assert slow >= 1.5 and slow > free * 3


def test_limit_applies_to_all_downloads_together_and_changes_live(env, qtbot, payload):
    engine, win, server, tmp = env
    engine.set_settings(Settings(**{**engine.settings.to_dict(), "speed_limit_kbps": 200}))
    assert engine.limiter.rate == 200 * 1024
    engine.set_settings(Settings(**{**engine.settings.to_dict(), "speed_limit_kbps": 0}))
    assert engine.limiter.rate == 0


def test_status_bar_speed_combo_sets_the_limit(env, qtbot):
    engine, win, server, tmp = env
    idx = win.speed_combo.findData(2048)
    win.speed_combo.setCurrentIndex(idx)
    assert engine.settings.speed_limit_kbps == 2048 and engine.limiter.rate == 2048 * 1024
    # a custom value from the settings dialog shows up in the combo
    engine.set_settings(Settings(**{**engine.settings.to_dict(), "speed_limit_kbps": 3072}))
    win._apply_texts()
    assert win.speed_combo.currentData() == 3072 and "özel" in win.speed_combo.currentText()


def test_settings_dialog_speed_roundtrip(env, qtbot):
    from civitai_grabber.ui.dialogs import SettingsDialog
    engine, win, server, tmp = env
    d = SettingsDialog(Settings(speed_limit_kbps=1536))
    qtbot.addWidget(d)
    assert d.speed.value() == 1.5
    d.speed.setValue(0.5)
    assert d.value().speed_limit_kbps == 512
    d.speed.setValue(0)
    assert d.value().speed_limit_kbps == 0 and d.speed.text() == "Sınırsız"


# ------------------------------------------------------------------ drag & drop order
def test_move_to_cases(qtbot, tmp_path):
    e = bare_engine(qtbot, tmp_path)           # a b c d e
    assert e.move_to(["d"], "b") and e.order == list("adbce")
    assert e.move_to(["a"], "c", after=True) and e.order == list("dbcae")
    assert e.move_to(["b", "e"], None) and e.order == list("dcabe")   # to the end, keeps relative order
    assert not e.move_to(["a"], "a") and not e.move_to(["a"], "zzz") and not e.move_to([], "a")
    before = list(e.order)
    assert not e.move_to(["d"], "c", after=False) or e.order != before   # d already sits right before c
    assert e.order.index("d") == e.order.index("c") - 1


def _drop(win, ids, row, lower_half=False):
    md = QMimeData()
    md.setData(MIME, "\n".join(ids).encode())
    v = win.view
    if row is None:
        pos = QPointF(10, v.viewport().height() - 2)
    else:
        rect = v.visualRect(win.proxy.index(row, 0))
        pos = QPointF(20, rect.bottom() - 3 if lower_half else rect.top() + 3)
    ev = QDropEvent(pos, Qt.MoveAction, md, Qt.LeftButton, Qt.NoModifier)
    v.dropEvent(ev)


def test_drag_drop_reorders_rows_in_the_table(env, qtbot):
    engine, win, server, tmp = env
    add(engine, server, 101, 201, 301, 401)
    wait_state(qtbot, engine, "ready")
    ids = list(engine.order)
    _drop(win, [ids[3]], 0)                         # last row onto the top half of row 0
    assert engine.order == [ids[3], ids[0], ids[1], ids[2]]
    assert [win.proxy.index(r, 0).data(IdRole) for r in range(4)] == engine.order
    _drop(win, [ids[3]], 2, lower_half=True)        # below the third row
    assert engine.order == [ids[0], ids[1], ids[3], ids[2]]
    _drop(win, [ids[0], ids[1]], None)              # empty area -> end of the queue
    assert engine.order == [ids[3], ids[2], ids[0], ids[1]]
    sel = {ix.data(IdRole) for ix in win.view.selectionModel().selectedRows()}
    assert sel == {ids[0], ids[1]}


def test_drop_resets_column_sort_so_the_result_is_visible(env, qtbot):
    engine, win, server, tmp = env
    add(engine, server, 101, 201)
    wait_state(qtbot, engine, "ready")
    win.view.sortByColumn(0, Qt.DescendingOrder)
    ids = list(engine.order)
    _drop(win, [ids[1]], 0)
    assert win.view.horizontalHeader().sortIndicatorSection() == -1
    assert engine.order[0] == ids[1]


def test_table_drag_still_targets_groups(env, qtbot):
    engine, win, server, tmp = env
    add(engine, server, 101)
    wait_state(qtbot, engine, "ready")
    md = win.model.mimeData([win.model.index(0, 0)])
    assert md.hasFormat(MIME)
    assert win.view.dragEnabled() and win.view.acceptDrops()


# ------------------------------------------------------------------ all versions of a model
def model_link(server, url):
    lk = parse_link(url)
    return ParsedLink(lk.url, server, lk.kind, lk.model_id, lk.version_id)


def test_model_link_without_version_adds_every_version(env, qtbot):
    engine, win, server, tmp = env
    g = engine.add_group("G", str(tmp / "g"))
    assert engine.add_links([model_link(server, "https://civitai.com/models/60/some-outfit")]) == 1
    qtbot.waitUntil(lambda: len(engine.order) == 2, timeout=10000)
    wait_state(qtbot, engine, "ready")
    items = [engine.items[i] for i in engine.order]
    assert [i.version_id for i in items] == [777, 776]           # newest first, side by side
    assert all(i.kind == "version" and "modelVersionId=" in i.url for i in items)
    assert win.model.rowCount() == 2
    # adding the same model link again does not duplicate anything
    assert engine.add_links([model_link(server, "https://civitai.com/models/60/some-outfit")]) == 1
    qtbot.waitUntil(lambda: len(engine.order) == 2, timeout=10000)
    qtbot.wait(300)
    assert len(engine.order) == 2 and g


def test_versions_inherit_group_and_autostart(env, qtbot):
    engine, win, server, tmp = env
    g = engine.add_group("G", str(tmp / "g"))
    engine.add_links([model_link(server, "https://civitai.com/models/61")])
    it = engine.items[engine.order[0]]
    engine.set_group([it.id], g.id)
    engine.start([it.id])                                         # pressed start while still resolving
    qtbot.waitUntil(lambda: len(engine.order) == 2, timeout=10000)
    assert {engine.items[i].group_id for i in engine.order} == {g.id}
    wait_state(qtbot, engine, "done", timeout=20000)


def test_link_with_version_id_adds_only_that_version(env, qtbot):
    engine, win, server, tmp = env
    engine.add_links([model_link(server, "https://civitai.com/models/60/x?modelVersionId=776")])
    wait_state(qtbot, engine, "ready")
    assert [engine.items[i].version_id for i in engine.order] == [776]


def test_setting_off_keeps_the_old_newest_version_behaviour(env, qtbot):
    engine, win, server, tmp = env
    engine.set_settings(Settings(**{**engine.settings.to_dict(), "all_versions": False}))
    engine.add_links([model_link(server, "https://civitai.com/models/62")])
    wait_state(qtbot, engine, "ready")
    assert [engine.items[i].version_id for i in engine.order] == [777]


def test_all_versions_setting_roundtrips_in_dialog(qtbot):
    from civitai_grabber.ui.dialogs import SettingsDialog
    d = SettingsDialog(Settings())
    qtbot.addWidget(d)
    assert d.allv.isChecked() and d.value().all_versions
    d.allv.setChecked(False)
    assert not d.value().all_versions


# ------------------------------------------------------------------ Breeze look
def test_breeze_palette_and_custom_widgets(qtbot):
    assert theme.colors("dark")["bg"] == "#181826" and theme.colors("dark")["accent"] == "#d94a4f"
    assert theme.colors("light")["bg"] == "#eff0f1"
    for name in ("dark", "light"):
        assert theme.build_qss(theme.colors(name)).count("{") == theme.build_qss(theme.colors(name)).count("}")
    c = theme.Check("x")
    qtbot.addWidget(c)
    c.show()
    c.setChecked(True)
    assert c.grab().width() > 0
    cb = theme.Combo()
    qtbot.addWidget(cb)
    cb.addItem("a")
    cb.show()
    assert cb.grab().width() > 0


# ------------------------------------------------------------------ folder picking shortcuts
def test_start_dir_uses_nearest_existing_parent(tmp_path):
    from pathlib import Path
    from civitai_grabber.ui.dialogs import start_dir
    (tmp_path / "models").mkdir()
    assert start_dir(str(tmp_path / "models" / "new_group" / "deeper")) == str(tmp_path / "models")
    assert start_dir("", str(tmp_path / "models")) == str(tmp_path / "models")
    assert start_dir("", "/definitely/not/here/xyz") == str(Path.home()) or Path(start_dir("/definitely/not/here/xyz")).is_dir()


def test_engine_remembers_where_groups_were_put(qtbot, tmp_path):
    e = bare_engine(qtbot, tmp_path, "a")
    assert e.suggest_base() == ""
    e.add_group("one", str(tmp_path / "D" / "Models" / "one"))
    assert e.suggest_base() == str(tmp_path / "D" / "Models")
    e.add_group("two", str(tmp_path / "E" / "Other" / "two"))
    assert e.settings.recent_folders == [str(tmp_path / "E" / "Other"), str(tmp_path / "D" / "Models")]
    e.add_group("three", str(tmp_path / "D" / "Models" / "three"))     # moves to the front, no duplicate
    assert e.settings.recent_folders[0] == str(tmp_path / "D" / "Models") and len(e.settings.recent_folders) == 2
    e.settings.base_folder = str(tmp_path / "base")
    assert e.suggest_base() == str(tmp_path / "base")                   # an explicit base folder wins
    for i in range(12):
        e.add_group("g", str(tmp_path / f"loc{i}" / "g"))
    assert len(e.settings.recent_folders) == 8
    # survives a restart
    from civitai_grabber.core.storage import Storage
    assert Storage(tmp_path / "cfg").load_settings().recent_folders == e.settings.recent_folders


def test_group_dialog_suggests_folder_from_last_location(qtbot, tmp_path):
    from civitai_grabber.ui.dialogs import GroupDialog
    base = str(tmp_path / "Models")
    d = GroupDialog(base_folder=base, recents=[base, str(tmp_path / "Old")])
    qtbot.addWidget(d)
    d.name.setText("affa1988")
    assert d.folder.edit.text() == str(tmp_path / "Models" / "affa1988")
    # a recent location from the drop-down re-bases the suggestion, also while typing
    d.folder.recentPicked.emit(str(tmp_path / "Old"))
    assert d.folder.edit.text() == str(tmp_path / "Old" / "affa1988")
    d.name.setText("kimi")
    assert d.folder.edit.text() == str(tmp_path / "Old" / "kimi")
    # a folder chosen by hand is never overwritten by later name edits
    d.folder.edit.setText(str(tmp_path / "Hand" / "x"))
    d.folder.userPicked.emit()
    d.name.setText("other")
    assert d.folder.edit.text() == str(tmp_path / "Hand" / "x")


def test_assign_dialog_has_recents_and_no_dropdown_without_them(qtbot, tmp_path):
    from civitai_grabber.ui.dialogs import AssignGroupDialog, GroupDialog
    d = AssignGroupDialog(None, [], 2, str(tmp_path / "M"), [str(tmp_path / "M")])
    qtbot.addWidget(d)
    assert d.folder.recent_btn is not None
    d.name.setText("abc")
    assert d.folder.edit.text() == str(tmp_path / "M" / "abc")
    d.folder.recentPicked.emit(str(tmp_path / "Z"))
    assert d.folder.edit.text() == str(tmp_path / "Z" / "abc")
    d2 = GroupDialog()
    qtbot.addWidget(d2)
    assert d2.folder.recent_btn is None
