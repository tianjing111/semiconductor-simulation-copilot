from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .service import CopilotService


class Handler(BaseHTTPRequestHandler):
    service: CopilotService
    static_root: Path
    server_version = "SimulationCopilot/0.1"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[copilot] {self.address_string()} {fmt % args}")

    def send_json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2 * 1024 * 1024:
            raise ValueError("Request body must be between 1 byte and 2 MiB")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object")
        return payload

    def send_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        path = (self.static_root / relative).resolve()
        try:
            path.relative_to(self.static_root.resolve())
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/status":
                self.send_json(self.service.status())
            elif parsed.path == "/api/experiments":
                params = parse_qs(parsed.query)
                self.send_json({"results": self.service.experiments(params.get("q", [""])[0], int(params.get("limit", ["40"])[0]))})
            elif parsed.path == "/api/plan":
                self.send_json(self.service.plan())
            elif parsed.path.startswith("/api/"):
                self.send_json({"error": "Unknown API route"}, HTTPStatus.NOT_FOUND)
            else:
                self.send_static(parsed.path)
        except (OSError, ValueError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            payload = self.read_json()
            if parsed.path == "/api/diagnose":
                self.send_json(self.service.diagnose(str(payload.get("text", ""))))
            elif parsed.path == "/api/search":
                self.send_json({"results": self.service.search(
                    str(payload.get("query", "")),
                    int(payload.get("limit", 6)),
                    str(payload.get("mode", "hybrid")),
                )})
            elif parsed.path == "/api/ask":
                self.send_json(self.service.ask(
                    str(payload.get("question", "")),
                    str(payload.get("mode", "hybrid")),
                ))
            else:
                self.send_json({"error": "Unknown API route"}, HTTPStatus.NOT_FOUND)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the read-only simulation copilot")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    root = args.root.resolve()
    Handler.service = CopilotService(root)
    Handler.static_root = root / "web"
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Simulation Copilot: http://{args.host}:{args.port}", flush=True)
    print("Public demo data only. Solver execution is hard-blocked.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
