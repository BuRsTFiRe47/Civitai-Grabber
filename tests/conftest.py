"""A tiny local fake of Civitai + its CDN, used by the tests."""
from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

PAYLOAD = bytes((i * 7) % 256 for i in range(300_000))  # 300 KB, deterministic
CF_BODY = b"<html><title>Just a moment...</title><script src='/cdn-cgi/challenge-platform/x'></script></html>"

STATE = {"flaky_hits": 0, "echo": {}}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # silence
        pass

    def _send(self, code, body=b"", headers=None):
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode(), {"Content-Type": "application/json"})

    def _serve_payload(self, extra=None):
        extra = dict(extra or {})
        extra.setdefault("Content-Type", "application/octet-stream")
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d+)-", rng)
            start = int(m.group(1))
            if start >= len(PAYLOAD):
                return self._send(416, b"", {"Content-Range": f"bytes */{len(PAYLOAD)}"})
            body = PAYLOAD[start:]
            extra["Content-Range"] = f"bytes {start}-{len(PAYLOAD)-1}/{len(PAYLOAD)}"
            return self._send(206, body, extra)
        self._send(200, PAYLOAD, extra)

    def do_GET(self):
        path = self.path.split("?")[0]
        port = self.server.server_address[1]
        if path == "/file":
            return self._serve_payload({"Content-Disposition": 'attachment; filename="cd_name.safetensors"'})
        if path == "/norange":  # ignores Range header
            return self._send(200, PAYLOAD, {"Content-Type": "application/octet-stream"})
        if path == "/echo-redirect":  # redirect to a *different host name* (localhost)
            return self._send(302, b"", {"Location": f"http://localhost:{port}/echo"})
        if path == "/echo":
            STATE["echo"] = {"auth": self.headers.get("Authorization"), "cookie": self.headers.get("Cookie")}
            return self._send(200, b"ok", {"Content-Type": "application/octet-stream"})
        if path == "/html":
            return self._send(200, b"<html>please log in</html>", {"Content-Type": "text/html"})
        if path == "/cf":
            return self._send(403, CF_BODY, {"Content-Type": "text/html", "Server": "cloudflare", "CF-RAY": "8abc-IST"})
        if path == "/forbidden":
            return self._send(401, b"{}", {"Content-Type": "application/json"})
        if path == "/gone":
            return self._send(404, b"nope")
        if path == "/flaky":  # first response is cut half-way
            STATE["flaky_hits"] += 1
            if STATE["flaky_hits"] == 1:
                self.send_response(200)
                self.send_header("Content-Length", str(len(PAYLOAD)))
                self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                self.wfile.write(PAYLOAD[:100_000])
                self.wfile.flush()
                self.close_connection = True
                return
            return self._serve_payload()
        m = re.fullmatch(r"/api/v1/model-versions/(\d+)", path)
        if m:
            vid = int(m.group(1))
            if vid == 999:
                return self._send(404, b"{}", {"Content-Type": "application/json"})
            multi = {
                # primary is a .ckpt, but a .safetensors exists -> filter must pick the safetensors
                888: [("old.ckpt", True), ("good.safetensors", False), ("emb.pt", False), ("data.zip", False)],
                # nothing usable
                889: [("only.ckpt", True), ("pack.zip", False)],
                # pt and safetensors: order of the allowed list decides
                890: [("a.safetensors", True), ("b.pt", False)],
            }
            if vid in multi:
                return self._json({"id": vid, "modelId": 70, "name": "v", "model": {"name": "Multi", "type": "TextualInversion"},
                                   "creator": {"username": "emb_author"},
                                   "files": [{"name": n, "sizeKB": 1, "primary": p, "downloadUrl": f"http://127.0.0.1:{port}/file"}
                                             for n, p in multi[vid]]})
            return self._json(
                {
                    "id": vid,
                    "modelId": 55,
                    "name": "v1.0",
                    "baseModel": "SDXL 1.0",
                    "model": {"name": "Cool LoRA", "type": "LORA"},
                    "files": [
                        {"name": "aux.txt", "sizeKB": 1, "primary": False, "downloadUrl": f"http://127.0.0.1:{port}/gone"},
                        {
                            "name": "cool_lora.safetensors",
                            "sizeKB": 292.96875,
                            "primary": True,
                            "downloadUrl": f"http://127.0.0.1:{port}/file",
                            "hashes": {"SHA256": "ABCDEF"},
                        },
                    ],
                }
            )
        m = re.fullmatch(r"/api/v1/models/(\d+)", path)
        if m:
            return self._json(
                {
                    "id": int(m.group(1)),
                    "name": "Cool LoRA",
                    "type": "LORA",
                    "creator": {"username": "SomeCreator"},
                    "modelVersions": [
                        {"id": 777, "name": "v2", "baseModel": "Pony", "files": [{"name": "new.safetensors", "sizeKB": 10, "primary": True}]},
                        {"id": 776, "name": "v1", "files": []},
                    ],
                }
            )
        self._send(404, b"not found")


@pytest.fixture(scope="session")
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture
def payload():
    return PAYLOAD


@pytest.fixture(autouse=True)
def gc_on_main_thread_only():
    """Cyclic GC may run on any thread that allocates. A Qt object (Engine + its QTimers) collected on a
    worker thread is destroyed off its owner thread and corrupts Qt's timer list -> random segfaults.
    So: no automatic collections while a test runs, collect explicitly on the main thread afterwards."""
    import gc
    gc.disable()
    try:
        yield
    finally:
        gc.collect()
        gc.enable()
