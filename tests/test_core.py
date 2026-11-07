import threading

import pytest

from civitai_grabber.core import api
from civitai_grabber.core.api import (
    CloudflareBlocked,
    LoginRequired,
    NotFound,
    make_session,
    resolve,
)
from civitai_grabber.core.downloader import (
    DownloadCancelled,
    download,
    filename_from_headers,
    safe_filename,
)
from civitai_grabber.core.storage import Settings


@pytest.fixture(autouse=True)
def plain_http(monkeypatch):
    monkeypatch.setattr(api, "SCHEME", "http")


def sess(**kw):
    return make_session(Settings(**kw), host="127.0.0.1")


# ------------------------------------------------------------------ resolve
def test_resolve_version(server):
    r = resolve(sess(), server, None, 123)
    assert r.name == "Cool LoRA" and r.model_type == "LORA"
    assert r.creator == "SomeCreator"            # came from the follow-up /models call
    assert r.filename == "cool_lora.safetensors"  # primary file, not aux.txt
    assert r.size == 300000 and r.sha256 == "abcdef"
    assert r.download_url.endswith("/file") and r.base_model == "SDXL 1.0"


def test_resolve_model_takes_newest_version(server):
    r = resolve(sess(), server, 55, None)
    assert (r.version_id, r.filename, r.creator) == (777, "new.safetensors", "SomeCreator")


def test_resolve_not_found(server):
    with pytest.raises(NotFound):
        resolve(sess(), server, None, 999)


# ------------------------------------------------------------------ download
def test_download_basic(server, tmp_path, payload):
    seen = []
    p = download(sess(), f"http://{server}/file", tmp_path / "a", "my.safetensors",
                 progress=lambda d, t: seen.append((d, t)))
    assert p.name == "my.safetensors" and p.read_bytes() == payload
    assert seen[-1] == (len(payload), len(payload))
    assert not list((tmp_path / "a").glob("*.part"))


def test_filename_from_content_disposition(server, tmp_path, payload):
    p = download(sess(), f"http://{server}/file", tmp_path)
    assert p.name == "cd_name.safetensors"


def test_resume_from_part_file(server, tmp_path, payload):
    (tmp_path / "m.safetensors.part").write_bytes(payload[:120_000])
    first = []
    p = download(sess(), f"http://{server}/file", tmp_path, "m.safetensors", progress=lambda d, t: first.append(d))
    assert p.read_bytes() == payload
    assert first[0] == 120_000  # started from the offset, did not restart


def test_server_ignoring_range_restarts_cleanly(server, tmp_path, payload):
    (tmp_path / "m.bin.part").write_bytes(b"garbage" * 1000)
    p = download(sess(), f"http://{server}/norange", tmp_path, "m.bin")
    assert p.read_bytes() == payload


def test_complete_part_gets_finalized_via_416(server, tmp_path, payload):
    (tmp_path / "m.bin.part").write_bytes(payload)
    p = download(sess(), f"http://{server}/file", tmp_path, "m.bin")
    assert p.read_bytes() == payload


def test_pause_keeps_part_and_can_resume(server, tmp_path, payload):
    cancel = threading.Event()

    def prog(d, t):
        if d > 50_000:
            cancel.set()

    with pytest.raises(DownloadCancelled):
        download(sess(), f"http://{server}/file", tmp_path, "m.bin", progress=prog, cancel=cancel)
    part = tmp_path / "m.bin.part"
    assert part.exists() and 0 < part.stat().st_size < len(payload)
    p = download(sess(), f"http://{server}/file", tmp_path, "m.bin")
    assert p.read_bytes() == payload


def test_retries_after_dropped_connection(server, tmp_path, payload):
    from tests.conftest import STATE
    STATE["flaky_hits"] = 0
    p = download(sess(), f"http://{server}/flaky", tmp_path, "f.bin", retries=2, backoff=0.01)
    assert p.read_bytes() == payload and STATE["flaky_hits"] >= 2


def test_existing_identical_file_is_not_duplicated(server, tmp_path, payload):
    (tmp_path / "m.bin").write_bytes(payload)
    p = download(sess(), f"http://{server}/file", tmp_path, "m.bin")
    assert p.name == "m.bin" and sorted(x.name for x in tmp_path.iterdir()) == ["m.bin"]


def test_existing_different_file_gets_new_name(server, tmp_path, payload):
    (tmp_path / "m.bin").write_bytes(b"old")
    p = download(sess(), f"http://{server}/file", tmp_path, "m.bin")
    assert p.name == "m (1).bin" and (tmp_path / "m.bin").read_bytes() == b"old"


def test_hash_verification(server, tmp_path, payload):
    import hashlib
    from civitai_grabber.core.api import HashMismatch
    good = hashlib.sha256(payload).hexdigest()
    assert download(sess(), f"http://{server}/file", tmp_path, "ok.bin", sha256=good, verify=True).exists()
    with pytest.raises(HashMismatch):
        download(sess(), f"http://{server}/file", tmp_path, "bad.bin", sha256="00" * 32, verify=True)
    assert not (tmp_path / "bad.bin").exists() and not (tmp_path / "bad.bin.part").exists()


# ------------------------------------------------------------------ errors
def test_cloudflare_is_detected(server, tmp_path):
    with pytest.raises(CloudflareBlocked):
        download(sess(), f"http://{server}/cf", tmp_path, "x.bin")


def test_login_html_page_is_detected(server, tmp_path):
    with pytest.raises(LoginRequired):
        download(sess(), f"http://{server}/html", tmp_path, "x.bin")


def test_401_and_404(server, tmp_path):
    with pytest.raises(LoginRequired):
        download(sess(), f"http://{server}/forbidden", tmp_path, "x.bin")
    with pytest.raises(NotFound):
        download(sess(), f"http://{server}/gone", tmp_path, "x.bin")


# ------------------------------------------------------------------ credentials
def test_api_key_header_not_forwarded_to_other_host(server, tmp_path):
    from tests.conftest import STATE
    s = sess(api_key="SECRET")
    download(s, f"http://{server}/echo-redirect", tmp_path, "e.bin")
    assert STATE["echo"]["auth"] is None  # redirected to "localhost": header stripped


def test_api_key_is_sent_to_the_civitai_host(server, tmp_path):
    from tests.conftest import STATE
    s = sess(api_key="SECRET")
    download(s, f"http://{server}/echo", tmp_path, "e.bin")
    assert STATE["echo"]["auth"] == "Bearer SECRET"


def test_cookie_scoped_to_civitai_host_only(server, tmp_path):
    from tests.conftest import STATE
    s = sess(cookie="cf_clearance=abc123; other=1")
    download(s, f"http://{server}/echo", tmp_path, "e1.bin")
    assert "cf_clearance=abc123" in (STATE["echo"]["cookie"] or "")
    download(s, f"http://{server}/echo-redirect", tmp_path, "e2.bin")
    assert STATE["echo"]["cookie"] is None


# ------------------------------------------------------------------ helpers
def test_filename_helpers():
    assert safe_filename('a:b/c*d?.safetensors') == "a_b_c_d_.safetensors"
    h = {"content-disposition": "attachment; filename*=UTF-8''g%C3%BCzel%20model.safetensors"}
    assert filename_from_headers(h, "http://x/y") == "güzel model.safetensors"
    assert filename_from_headers({}, "http://x/path/file%20one.bin?x=1") == "file one.bin"


# ------------------------------------------------------------------ file type filter
def test_filter_prefers_allowed_extension_over_primary(server):
    r = resolve(sess(), server, None, 888, ["safetensors", "pt"])
    assert r.filename == "good.safetensors"          # not the primary .ckpt, not .pt (lower preference), not .zip


def test_filter_order_is_preference(server):
    assert resolve(sess(), server, None, 890, ["safetensors", "pt"]).filename == "a.safetensors"
    assert resolve(sess(), server, None, 890, ["pt", "safetensors"]).filename == "b.pt"


def test_no_filter_uses_primary_file(server):
    assert resolve(sess(), server, None, 888, []).filename == "old.ckpt"


def test_filter_without_match_raises_and_lists_files(server):
    from civitai_grabber.core.api import NoMatchingFile
    with pytest.raises(NoMatchingFile) as ei:
        resolve(sess(), server, None, 889, ["safetensors", "pt"])
    assert "only.ckpt" in ei.value.detail and "pack.zip" in ei.value.detail
    assert ei.value.as_text().startswith("nofile:")


def test_extension_setting_parsing():
    assert Settings(file_extensions="safetensors, .PT ; *.bin").allowed_extensions() == ["safetensors", "pt", "bin"]
    assert Settings(file_extensions="").allowed_extensions() == []
    assert Settings().allowed_extensions() == ["safetensors", "pt"]


# ------------------------------------------------------------------ technical error info + log hygiene
def test_cloudflare_error_carries_technical_info(server, tmp_path):
    with pytest.raises(CloudflareBlocked) as ei:
        download(sess(), f"http://{server}/cf", tmp_path, "x.bin")
    info = ei.value.info
    assert "HTTP 403" in info and "cloudflare" in info and "cf-ray=8abc-IST" in info and "Just a moment" in info


def test_log_redacts_secrets_and_writes_file(server, tmp_path):
    import logging
    from civitai_grabber.core.logsetup import redact, setup_logging
    assert redact("https://x/y?type=Model&token=SECRET123&a=1") == "https://x/y?type=Model&token=***&a=1"
    buf = setup_logging(tmp_path / "logs")
    try:
        logging.getLogger("civgrab.test").info("GET https://civitai.com/api/download/models/1?token=SECRET123")
        for h in logging.getLogger("civgrab").handlers:
            h.flush()
        text = (tmp_path / "logs" / "civitai-grabber.log").read_text(encoding="utf-8")
        assert "token=***" in text and "SECRET123" not in text
        assert all("SECRET123" not in m for _, _, m in buf.records)
    finally:
        setup_logging(tmp_path / "logs2")  # leave no handler on the removed tmp dir
        for h in list(logging.getLogger("civgrab").handlers):
            logging.getLogger("civgrab").removeHandler(h)
            h.close()


def test_download_logs_start_and_done(server, tmp_path, caplog):
    import logging
    with caplog.at_level(logging.DEBUG, logger="civgrab"):
        download(sess(), f"http://{server}/file", tmp_path, "l.bin", tag="[#abc123 x]")
    msgs = " ".join(r.getMessage() for r in caplog.records)
    assert "[#abc123 x]" in msgs and "l.bin" in msgs and "HTTP 200" in msgs
