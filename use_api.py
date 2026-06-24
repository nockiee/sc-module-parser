import json
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from sc_parser_core import ParseOptions, ParseResult, parse_soundcloud_rank
from core_settings import load_settings


SETTINGS = load_settings()
HOST = SETTINGS.api_host
PORT = SETTINGS.api_port


def result_to_dict(result: ParseResult) -> dict:
    return {
        "requested_kind": result.requested_kind,
        "actual_kind": result.actual_kind,
        "username": result.username,
        "source_url": result.source_url,
        "title": result.title,
        "status_text": result.status_text,
        "visible_rank": result.visible_rank,
        "checked": result.checked,
        "expected_total": result.expected_total,
        "found": result.found,
        "saved_list_path": result.saved_list_path,
        "debug": result.debug,
    }


def coerce_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def coerce_int(value, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


def coerce_str(value, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


class SoundCloudApiHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self.send_json(200, {"status": "ok"})
            return

        if parsed.path == "/parse":
            query = parse_qs(parsed.query)
            kind = query.get("kind", [""])[0]
            url = query.get("url", [""])[0]
            username = query.get("username", [""])[0]
            debug = coerce_bool(query.get("debug", [""])[0], SETTINGS.debug)
            save_user_list = coerce_bool(query.get("save_user_list", [""])[0], SETTINGS.save_user_list)
            save_user_list_filename = coerce_str(
                query.get("save_user_list_filename", [""])[0],
                SETTINGS.save_user_list_filename,
            )
            save_user_list_mode = coerce_str(
                query.get("save_user_list_mode", [""])[0],
                SETTINGS.save_user_list_mode,
            )
            self.handle_parse(
                kind,
                url,
                username,
                debug=debug,
                save_user_list=save_user_list,
                save_user_list_filename=save_user_list_filename,
                save_user_list_mode=save_user_list_mode,
            )
            return

        if parsed.path == "/parse-batch":
            self.send_json(405, {"error": "Use POST for /parse-batch"})
            return

        self.send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/parse", "/parse-batch"}:
            self.send_json(404, {"error": "Not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(400, {"error": "Invalid JSON body"})
            return

        if parsed.path == "/parse":
            kind = str(payload.get("kind", ""))
            url = str(payload.get("url", ""))
            username = str(payload.get("username", ""))
            debug = coerce_bool(payload.get("debug"), SETTINGS.debug)
            save_user_list = coerce_bool(payload.get("save_user_list"), SETTINGS.save_user_list)
            save_user_list_filename = coerce_str(
                payload.get("save_user_list_filename"), SETTINGS.save_user_list_filename
            )
            save_user_list_mode = coerce_str(
                payload.get("save_user_list_mode"), SETTINGS.save_user_list_mode
            )
            self.handle_parse(
                kind,
                url,
                username,
                debug=debug,
                save_user_list=save_user_list,
                save_user_list_filename=save_user_list_filename,
                save_user_list_mode=save_user_list_mode,
            )
            return

        self.handle_parse_batch(payload)

    def handle_parse(
        self,
        kind: str,
        url: str,
        username: str,
        debug: bool,
        save_user_list: bool,
        save_user_list_filename: str,
        save_user_list_mode: str,
    ) -> None:
        if not kind or not url or not username:
            self.send_json(400, {"error": "kind, url and username are required"})
            return

        try:
            result = parse_soundcloud_rank(
                kind,
                url,
                username,
                options=ParseOptions(
                    debug=debug,
                    save_user_list=save_user_list,
                    save_user_list_filename=save_user_list_filename,
                    save_user_list_mode=save_user_list_mode,
                    request_delay_seconds=SETTINGS.request_delay_seconds,
                ),
            )
        except KeyboardInterrupt:
            self.send_json(499, {"error": "Cancelled"})
            return
        except Exception as error:
            self.send_json(400, {"error": str(error)})
            return

        self.send_json(200, result_to_dict(result))

    def handle_parse_batch(self, payload: dict) -> None:
        tasks = payload.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            self.send_json(400, {"error": "tasks array is required"})
            return

        debug = coerce_bool(payload.get("debug"), SETTINGS.debug)
        worker_threads = coerce_int(payload.get("worker_threads"), SETTINGS.worker_threads)
        save_user_list = coerce_bool(payload.get("save_user_list"), SETTINGS.save_user_list)
        save_user_list_filename = coerce_str(
            payload.get("save_user_list_filename"), SETTINGS.save_user_list_filename
        )
        save_user_list_mode = coerce_str(
            payload.get("save_user_list_mode"), SETTINGS.save_user_list_mode
        )

        def run_task(task: dict) -> dict:
            kind = str(task.get("kind", ""))
            url = str(task.get("url", ""))
            username = str(task.get("username", ""))
            if not kind or not url or not username:
                return {"ok": False, "error": "kind, url and username are required", "task": task}
            try:
                task_filename = coerce_str(task.get("save_user_list_filename"), save_user_list_filename)
                task_save_list = coerce_bool(task.get("save_user_list"), save_user_list)
                task_save_mode = coerce_str(task.get("save_user_list_mode"), save_user_list_mode)
                result = parse_soundcloud_rank(
                    kind,
                    url,
                    username,
                    options=ParseOptions(
                        debug=debug,
                        save_user_list=task_save_list,
                        save_user_list_filename=task_filename,
                        save_user_list_mode=task_save_mode,
                        request_delay_seconds=SETTINGS.request_delay_seconds,
                    ),
                )
                return {"ok": True, "result": result_to_dict(result)}
            except Exception as error:
                return {"ok": False, "error": str(error), "task": task}

        with ThreadPoolExecutor(max_workers=worker_threads) as executor:
            results = list(executor.map(run_task, tasks))

        self.send_json(
            200,
            {"worker_threads": worker_threads, "debug": debug, "count": len(results), "results": results},
        )

    def send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), SoundCloudApiHandler)
    print(f"use_api http://{HOST}:{PORT}")
    print("GET  /health")
    print("GET  /parse?kind=user&url=...&username=...&debug=true")
    print("POST /parse")
    print("POST /parse-batch")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAPI stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
