"""End-to-end tests of engine + main window against the local fake Civitai (offscreen Qt)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from civitai_grabber.ui.table_model import COLS  # noqa: E402
import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from civitai_grabber.core import api  # noqa: E402
from civitai_grabber.core.engine import Engine  # noqa: E402
from civitai_grabber.core.models import DONE, ERROR, READY  # noqa: E402
from civitai_grabber.core.storage import Settings, Storage  # noqa: E402
from civitai_grabber.i18n import set_language  # noqa: E402
from civitai_grabber.ui import theme  # noqa: E402
from civitai_grabber.ui.main_window import NONE, MainWindow  # noqa: E402


@pytest.fixture(autouse=True)
def plain_http(monkeypatch):
    monkeypatch.setattr(api, "SCHEME", "http")
    set_language("tr")


@pytest.fixture
def env(qtbot, tmp_path, server):
    storage = Storage(tmp_path / "cfg")
    settings = Settings(start_delay=0.0, max_concurrent=2, retries=0)
    engine = Engine(storage, settings)
    app = QApplication.instance()
    theme.apply_theme(app, "dark")
    win = MainWindow(engine)
    qtbot.addWidget(win)
    win.show()
    engine.begin()
    yield engine, win, server, tmp_path
    engine.shutdown()


def add(engine, server, *vids):
    from civitai_grabber.core.links import ParsedLink
    links = [ParsedLink(f"https://civitai.com/api/download/models/{v}", server, "version", version_id=v) for v in vids]
    return engine.add_links(links)


def wait_state(qtbot, engine, state, ids=None, timeout=15000):
    def ok():
        its = [engine.items[i] for i in (ids or engine.order)]
        assert its and all(i.state == state for i in its), [(i.state, i.error) for i in its]
    qtbot.waitUntil(ok, timeout=timeout)


def test_dark_theme_is_default_and_window_renders(env):
    engine, win, server, tmp = env
    assert win.palette().window().color().name() == theme.colors("dark")["bg"]
    assert "Civitai" in win.windowTitle()
    assert win.stack.currentIndex() == 0  # empty hint first


def test_resolve_group_and_download(env, qtbot, payload):
    engine, win, server, tmp = env
    assert add(engine, server, 101, 102) == 2
    assert add(engine, server, 101) == 0  # duplicate ignored
    wait_state(qtbot, engine, READY)
    items = [engine.items[i] for i in engine.order]
    assert win.stack.currentIndex() == 1 and win.model.rowCount() == 2
    assert {i.creator for i in items} == {"SomeCreator"} and items[0].filename == "cool_lora.safetensors"

    # group by creator -> one group + one folder under base
    base = str(tmp / "models")
    engine.set_settings(Settings(**{**engine.settings.to_dict(), "base_folder": base}))
    created, assigned = engine.auto_group_by_creator(engine.order, base)
    assert (created, assigned) == (1, 2)
    g = engine.groups[0]
    assert g.name == "SomeCreator" and g.folder.endswith("SomeCreator")

    # group list shows the group with count, filter works
    qtbot.waitUntil(lambda: win.group_list.count() == 3)
    assert "(2)" in win.group_list.item(2).text() and "(0)" in win.group_list.item(1).text()
    win.group_list.setCurrentRow(1)  # ungrouped
    assert win.proxy.rowCount() == 0
    win.group_list.setCurrentRow(2)
    assert win.proxy.rowCount() == 2

    # start everything shown; second file has the same primary file -> both land in group folder
    win._start(win._view_ids())
    # same filename + same content: second download recognises the identical file
    wait_state(qtbot, engine, DONE)
    files = sorted(p.name for p in (tmp / "models" / "SomeCreator").iterdir())
    assert files == ["cool_lora.safetensors"]
    assert (tmp / "models" / "SomeCreator" / files[0]).read_bytes() == payload
    assert win.proxy.index(0, 0).data(Qt.DisplayRole) == "Cool LoRA"


def test_manual_group_dialog_logic_and_drag_drop(env, qtbot):
    engine, win, server, tmp = env
    add(engine, server, 201)
    wait_state(qtbot, engine, READY)
    g = engine.add_group("Elle", str(tmp / "elle"))
    qtbot.waitUntil(lambda: win.group_list.count() == 3)
    # simulate the drop handler (drag source = table rows, target = group in list)
    ids = list(engine.order)
    win._on_drop(ids, g.id)
    assert engine.items[ids[0]].group_id == g.id
    win._on_drop(ids, NONE)
    assert engine.items[ids[0]].group_id == ""
    # model exposes drag mime
    md = win.model.mimeData([win.model.index(0, 0)])
    assert bytes(md.data("application/x-civitai-grabber-ids")).decode() == ids[0]


def test_pause_and_resume(env, qtbot, payload):
    engine, win, server, tmp = env
    add(engine, server, 301)
    wait_state(qtbot, engine, READY)
    it = engine.items[engine.order[0]]
    g = engine.add_group("G", str(tmp / "g"))
    engine.set_group([it.id], g.id)
    engine.start([it.id])
    wait_state(qtbot, engine, DONE)
    assert (tmp / "g" / "cool_lora.safetensors").read_bytes() == payload
    engine.clear_finished()
    assert not engine.items and win.stack.currentIndex() == 0


def test_error_item_is_shown_with_translated_message(env, qtbot):
    engine, win, server, tmp = env
    add(engine, server, 999)  # 404 on the fake API
    wait_state(qtbot, engine, ERROR)
    it = engine.items[engine.order[0]]
    status = win.model.status_text(it)
    assert status.startswith("Bulunamadı")
    set_language("en")
    assert win.model.status_text(it).startswith("Not found")


def test_start_without_folder_marks_error(env, qtbot, monkeypatch):
    engine, win, server, tmp = env
    add(engine, server, 401)
    wait_state(qtbot, engine, READY)
    engine.start(list(engine.order))  # engine itself (no dialog): no folder anywhere
    assert engine.items[engine.order[0]].error == "nofolder"


def test_cloudflare_stops_the_queue(env, qtbot, monkeypatch):
    """With the 'stop the waiting queue on Cloudflare' setting on (default is: carry on)."""
    engine, win, server, tmp = env
    engine.settings.stop_on_cloudflare = True
    engine.settings.max_concurrent = 1
    add(engine, server, 501, 502)
    wait_state(qtbot, engine, READY)
    g = engine.add_group("G", str(tmp / "cf"))
    engine.set_group(engine.order, g.id)
    first, second = (engine.items[i] for i in engine.order)
    first.download_url = f"http://{server}/cf"     # first one gets the Cloudflare page
    second.download_url = f"http://{server}/file"
    msgs = []
    engine.message.connect(lambda c, d: msgs.append(c))
    engine.start(engine.order)
    qtbot.waitUntil(lambda: first.state == ERROR, timeout=10000)
    assert first.error.startswith("cloudflare")
    assert second.state == READY            # parked, not hammered
    assert "queue_stopped_cf" in msgs


def test_state_survives_restart(env, qtbot, tmp_path):
    engine, win, server, tmp = env
    add(engine, server, 601)
    wait_state(qtbot, engine, READY)
    g = engine.add_group("Keep", str(tmp / "keep"))
    engine.set_group(engine.order, g.id)
    engine.save_now()
    groups, items = Storage(tmp / "cfg").load_state()
    assert [x.name for x in groups] == ["Keep"]
    assert items[0].group_id == g.id and items[0].state == READY and items[0].creator == "SomeCreator"


def test_clipboard_text_grabbing(env, qtbot):
    engine, win, server, tmp = env
    # host in the link is civitai.com (real host) -> resolve will fail offline, but the row is added
    n = win._grab_text("lol https://civitai.com/models/1/x and https://civitai.com/models/1/x https://nope.com")
    assert n == 1 and win.model.rowCount() == 1
    assert win._grab_text("https://civitai.com/models/1") == 0


def test_progress_over_2gib_does_not_overflow(env, qtbot):
    """Regression: the progress signal used C int32 -> OverflowError for files > 2 GiB."""
    from civitai_grabber.core.models import DOWNLOADING
    engine, win, server, tmp = env
    add(engine, server, 701)
    wait_state(qtbot, engine, READY)
    it = engine.items[engine.order[0]]
    it.state = DOWNLOADING
    engine._sig_progress.emit(it.id, 3_000_000_000, 7_000_000_000)
    qtbot.waitUntil(lambda: it.done_bytes == 3_000_000_000)
    assert it.size == 7_000_000_000 and abs(it.progress - 3 / 7) < 1e-9
    assert win.model.data(win.model.index(0, COLS.index("size"))).endswith("GB")
    from civitai_grabber.ui.table_model import SortRole
    assert win.model.data(win.model.index(0, COLS.index("size")), SortRole) == 7_000_000_000


def test_filter_error_is_shown_and_logged(env, qtbot):
    engine, win, server, tmp = env
    add(engine, server, 889)  # only .ckpt/.zip files
    wait_state(qtbot, engine, ERROR)
    it = engine.items[engine.order[0]]
    assert it.error.startswith("nofile:") and "only.ckpt" in it.error
    assert "Uzantı filtresine" in win.model.status_text(it)
    tip = win.model.data(win.model.index(0, COLS.index("status")), Qt.ToolTipRole)
    assert "only.ckpt" in tip
    # the log panel got the explanation (live handler), filterable by the row code
    code = f"#{it.id[:6]}"
    qtbot.waitUntil(lambda: any(code in text for _, _, text in win.log_panel._lines))
    win.show_log_for(it.id)
    assert win.log_dock.isVisible() and win.a_log.isChecked()
    text = win.log_panel.view.toPlainText()
    assert "only.ckpt" in text and code in text


def test_cloudflare_error_info_is_kept_on_the_row_and_in_the_log(env, qtbot):
    engine, win, server, tmp = env
    add(engine, server, 801)
    wait_state(qtbot, engine, READY)
    it = engine.items[engine.order[0]]
    g = engine.add_group("G", str(tmp / "cf2"))
    engine.set_group([it.id], g.id)
    it.download_url = f"http://{server}/cf"
    engine.start([it.id])
    qtbot.waitUntil(lambda: it.state == ERROR, timeout=10000)
    assert "cf-ray=8abc-IST" in it.error_info
    tip = win.model.data(win.model.index(0, COLS.index("status")), Qt.ToolTipRole)
    assert "Cloudflare" in tip and "cf-ray=8abc-IST" in tip
    win.show_log_for(it.id)
    assert "İndirilemedi" in win.log_panel.view.toPlainText()


def test_settings_dialog_roundtrips_file_extensions(env, qtbot):
    from civitai_grabber.ui.dialogs import SettingsDialog
    engine, win, server, tmp = env
    d = SettingsDialog(engine.settings)
    qtbot.addWidget(d)
    assert d.exts.text() == "safetensors, pt"
    d.exts.setText("safetensors")
    assert d.value().file_extensions == "safetensors"
