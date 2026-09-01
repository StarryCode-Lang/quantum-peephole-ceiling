"""Single-worker telemetry wrapper around GUOQ's official ``bqskit_io``.

The Java artifact hard-codes http://localhost:8080/bqskit.  This wrapper keeps
that wire contract and calls the unmodified function loaded from the pinned
official ``resynth.py``.  The only behavioral configuration difference is
``Compiler(num_workers=1)`` instead of the artifact script's hard-coded 64.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

OFFICIAL_RESYNTH_SHA256 = (
    "f396195935932a3d682cd76fdfc798b561905346bcf465799e3df0eda256634f"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _load_official(path: Path):
    if _sha256(path) != OFFICIAL_RESYNTH_SHA256:
        raise RuntimeError("official resynth.py SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location("guoq_official_resynth", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load official resynth.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def serve(official_resynth: Path, log_path: Path) -> None:
    module = _load_official(official_resynth.resolve())
    compiler = module.Compiler(num_workers=1)
    request_counter = 0

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *args) -> None:
            return

        def do_GET(self) -> None:
            payload = json.dumps({
                "status": "ready", "workers": 1,
                "official_resynth_sha256": OFFICIAL_RESYNTH_SHA256,
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            nonlocal request_counter
            parsed_path = urllib.parse.urlparse(self.path)
            if parsed_path.path != "/bqskit":
                self.send_error(404)
                return
            request_counter += 1
            request_id = request_counter
            body = self.rfile.read(int(self.headers["Content-Length"]))
            parsed = json.loads(body)
            started_wall = time.time()
            started_perf = time.perf_counter()
            started_cpu = time.process_time()
            start_record = {
                "event": "request_start", "request_id": request_id,
                "started_unix": started_wall,
                "input_sha256": hashlib.sha256(
                    parsed["circuit"].encode("utf-8")
                ).hexdigest(),
                "opt_level": int(parsed["opt_level"]),
                "epsilon": float(parsed["epsilon"]),
                "target_gateset": parsed["target_gateset"],
            }
            _append_jsonl(log_path, start_record)
            data: dict = {}
            try:
                output = module.bqskit_io(
                    compiler, data, parsed["circuit"],
                    int(parsed["opt_level"]), float(parsed["epsilon"]),
                    parsed["target_gateset"],
                )
                payload = output.encode("utf-8")
                record = {
                    "event": "request_complete", "request_id": request_id,
                    "status": "ok",
                    "wall_seconds": time.perf_counter() - started_perf,
                    "server_cpu_seconds": time.process_time() - started_cpu,
                    "finished_unix": time.time(),
                    "original_size": data.get("original_size"),
                    "original_2q_size": data.get("original_2q_size"),
                    "resynth_size": data.get("resynth_size"),
                    "resynth_2q_size": data.get("resynth_2q_size"),
                    "output_sha256": hashlib.sha256(payload).hexdigest(),
                    "output_bytes": len(payload),
                }
                _append_jsonl(log_path, record)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as exc:
                record = {
                    "event": "request_complete", "request_id": request_id,
                    "status": "error",
                    "wall_seconds": time.perf_counter() - started_perf,
                    "server_cpu_seconds": time.process_time() - started_cpu,
                    "finished_unix": time.time(),
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                }
                _append_jsonl(log_path, record)
                payload = json.dumps(record).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 8080), Handler)
    _append_jsonl(log_path, {
        "event": "server_ready", "workers": 1, "pid": os.getpid(),
        "official_resynth_sha256": OFFICIAL_RESYNTH_SHA256,
    })
    try:
        server.serve_forever()
    finally:
        server.server_close()
        close = getattr(compiler, "close", None)
        if close is not None:
            close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-resynth", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    arguments = parser.parse_args()
    serve(arguments.official_resynth, arguments.log)


if __name__ == "__main__":
    main()
