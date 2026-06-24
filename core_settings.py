import json
from dataclasses import dataclass
from pathlib import Path


SETTINGS_PATH = Path(__file__).with_name("core_settings.json")


@dataclass
class AppSettings:
    use_settings: bool = True
    debug: bool = False
    worker_threads: int = 4
    request_delay_seconds: float = 0.0
    save_user_list: bool = False
    save_user_list_filename: str = "accounts.txt"
    save_user_list_mode: str = "both"
    api_host: str = "127.0.0.1"
    api_port: int = 8080


def load_settings() -> AppSettings:
    defaults = AppSettings()
    if not SETTINGS_PATH.exists():
        return defaults

    try:
        payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults

    if not bool(payload.get("use_settings", True)):
        return defaults

    api_payload = payload.get("api", {})
    worker_threads = int(payload.get("worker_threads", defaults.worker_threads) or defaults.worker_threads)
    worker_threads = max(1, worker_threads)

    return AppSettings(
        use_settings=True,
        debug=bool(payload.get("debug", defaults.debug)),
        worker_threads=worker_threads,
        request_delay_seconds=float(payload.get("request_delay_seconds", defaults.request_delay_seconds)),
        save_user_list=bool(payload.get("save_user_list", defaults.save_user_list)),
        save_user_list_filename=str(
            payload.get("save_user_list_filename", defaults.save_user_list_filename)
        ),
        save_user_list_mode=str(payload.get("save_user_list_mode", defaults.save_user_list_mode)).strip().lower(),
        api_host=str(api_payload.get("host", defaults.api_host)),
        api_port=int(api_payload.get("port", defaults.api_port)),
    )
