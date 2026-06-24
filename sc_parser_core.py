import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable, Optional


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

SUPPORTED_KINDS = {"user", "album", "track", "playlist"}


@dataclass
class ParseResult:
    requested_kind: str
    actual_kind: str
    username: str
    source_url: str
    title: str
    status_text: str
    visible_rank: Optional[int]
    checked: int
    expected_total: Optional[int]
    found: bool
    saved_list_path: Optional[str] = None
    debug: dict = field(default_factory=dict)


@dataclass
class ParseOptions:
    debug: bool = False
    save_user_list: bool = False
    save_user_list_filename: str = "accounts.txt"
    save_user_list_mode: str = "both"
    request_delay_seconds: float = 0.0


class ScriptSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "script":
            return
        src = dict(attrs).get("src")
        if src:
            self.sources.append(src)


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url: str) -> dict:
    return json.loads(fetch_text(url))


def normalize_soundcloud_url(url: str, requested_kind: str) -> str:
    raw_value = url.strip()
    if not raw_value:
        return raw_value

    if requested_kind == "user" and "soundcloud.com" not in raw_value and "/" not in raw_value:
        raw_value = f"https://soundcloud.com/{raw_value.lstrip('@')}"
    elif not raw_value.startswith(("http://", "https://")):
        raw_value = f"https://{raw_value.lstrip('/')}"

    parsed = urllib.parse.urlparse(raw_value)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if requested_kind == "user":
        if host.endswith("soundcloud.com") and path_parts:
            handle = path_parts[0]
            normalized_path = f"/{handle}"
            return urllib.parse.urlunparse(
                parsed._replace(path=normalized_path, params="", query="", fragment="")
            )
        if not host:
            return f"https://soundcloud.com/{raw_value.strip('/').lstrip('@')}"

    return urllib.parse.urlunparse(parsed._replace(fragment=""))


def normalize_username(value: str) -> str:
    value = value.strip().lower()
    if value.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(value)
        return parsed.path.strip("/").split("/")[0].lower()
    return value.lstrip("@")


def ensure_client_id(url: str, client_id: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if not query.get("client_id"):
        query["client_id"] = [client_id]
    rebuilt_query = urllib.parse.urlencode(query, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=rebuilt_query))


def extract_client_id(script_body: str) -> Optional[str]:
    patterns = [
        r'client_id["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
        r'[?&]client_id=([a-zA-Z0-9]{20,})',
    ]
    for pattern in patterns:
        match = re.search(pattern, script_body)
        if match:
            return match.group(1)
    return None


def discover_client_id(soundcloud_url: str) -> str:
    html = fetch_text(soundcloud_url)

    direct_match = extract_client_id(html)
    if direct_match:
        return direct_match

    parser = ScriptSrcParser()
    parser.feed(html)

    candidates: list[str] = []
    for source in parser.sources:
        if "sndcdn.com" not in source:
            continue
        if source.startswith("//"):
            candidates.append(f"https:{source}")
        elif source.startswith("/"):
            candidates.append(urllib.parse.urljoin(soundcloud_url, source))
        else:
            candidates.append(source)

    for script_url in candidates:
        try:
            body = fetch_text(script_url)
        except urllib.error.URLError:
            continue
        client_id = extract_client_id(body)
        if client_id:
            return client_id

    raise RuntimeError("Failed to get SoundCloud client_id.")


def resolve_resource(soundcloud_url: str, client_id: str) -> dict:
    params = urllib.parse.urlencode(
        {"url": soundcloud_url, "client_id": client_id, "app_locale": "en"}
    )
    return fetch_json(f"https://api-v2.soundcloud.com/resolve?{params}")


def normalize_resource_kind(resource: dict) -> str:
    kind = str(resource.get("kind", ""))
    if kind == "playlist" and resource.get("is_album"):
        return "album"
    return kind


def build_collection_url(resource: dict, client_id: str) -> tuple[str, str, str]:
    kind = normalize_resource_kind(resource)

    if kind == "user":
        return (
            "follower found",
            resource.get("username") or "SoundCloud profile",
            "https://api-v2.soundcloud.com/users/"
            f"{resource['id']}/followers?client_id={client_id}&limit=200&linked_partitioning=1"
            "&app_version=1731422810&app_locale=en",
        )

    if kind == "track":
        return (
            "like found",
            resource.get("title") or "SoundCloud track",
            "https://api-v2.soundcloud.com/tracks/"
            f"{resource['id']}/likers?client_id={client_id}&limit=200&linked_partitioning=1"
            "&app_version=1731422810&app_locale=en",
        )

    if kind in {"playlist", "album"}:
        return (
            "like found",
            resource.get("title") or ("SoundCloud album" if kind == "album" else "SoundCloud playlist"),
            "https://api-v2.soundcloud.com/playlists/"
            f"{resource['id']}/likers?client_id={client_id}&limit=200&linked_partitioning=1"
            "&app_version=1731422810&app_locale=en",
        )

    raise RuntimeError("Only user, album, track, and playlist are supported.")


def get_expected_total(resource: dict) -> Optional[int]:
    for key in ("followers_count", "likes_count", "liker_count", "favoritings_count"):
        value = resource.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return None


def iter_collection(collection_url: str, client_id: str, request_delay_seconds: float = 0.0) -> Iterable[dict]:
    next_url = collection_url
    while next_url:
        data = fetch_json(ensure_client_id(next_url, client_id))
        for item in data.get("collection", []):
            yield item
        next_url = data.get("next_href")
        if next_url and request_delay_seconds > 0:
            time.sleep(request_delay_seconds)


def matches_username(item: dict, target_username: str) -> bool:
    permalink = str(item.get("permalink", "")).strip().lower()
    return target_username == permalink


def serialize_account(item: dict) -> str:
    username = str(item.get("permalink", "")).strip()
    display_name = str(item.get("username", "")).strip()
    return username or display_name


def serialize_account_by_mode(item: dict, mode: str) -> str:
    username = str(item.get("permalink", "")).strip()
    nickname = str(item.get("username", "")).strip()
    normalized_mode = (mode or "both").strip().lower()

    if normalized_mode == "username":
        return username or nickname
    if normalized_mode == "nickname":
        return nickname or username

    parts: list[str] = []
    if username:
        parts.append(f"username={username}")
    if nickname:
        parts.append(f"nickname={nickname}")
    return " | ".join(parts) if parts else serialize_account(item)


def write_account_list(items: list[str], filename: str) -> str:
    path = Path(filename)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    path.write_text("\n".join(items), encoding="utf-8")
    return str(path)


def find_visible_rank(
    resource: dict,
    username: str,
    client_id: str,
    collection_url: str,
    progress_callback: Optional[Callable[[int, Optional[int], dict], None]] = None,
    options: Optional[ParseOptions] = None,
) -> tuple[Optional[int], int]:
    checked = 0
    api_rank: Optional[int] = None
    expected_total = get_expected_total(resource)
    started_at = time.monotonic()
    collected_accounts: list[str] = []

    request_delay_seconds = options.request_delay_seconds if options else 0.0

    for checked, item in enumerate(
        iter_collection(collection_url, client_id, request_delay_seconds=request_delay_seconds), start=1
    ):
        if options and options.save_user_list:
            collected_accounts.append(serialize_account_by_mode(item, options.save_user_list_mode))
        if progress_callback and (checked == 1 or checked % 25 == 0):
            elapsed = time.monotonic() - started_at
            avg = elapsed / checked if checked else 0.0
            eta = max((expected_total or 0) - checked, 0) * avg if expected_total else None
            progress_callback(
                checked,
                expected_total,
                {"elapsed": elapsed, "avg": avg, "eta": eta, "debug": bool(options and options.debug)},
            )
        if api_rank is None and matches_username(item, username):
            api_rank = checked

    if progress_callback and checked:
        elapsed = time.monotonic() - started_at
        avg = elapsed / checked if checked else 0.0
        progress_callback(
            checked,
            expected_total or checked,
            {"elapsed": elapsed, "avg": avg, "eta": 0.0, "debug": bool(options and options.debug)},
        )

    if options is not None:
        setattr(options, "_collected_accounts", collected_accounts)

    if api_rank is None:
        return None, checked
    return checked - api_rank + 1, checked


def parse_soundcloud_rank(
    requested_kind: str,
    soundcloud_url: str,
    username: str,
    progress_callback: Optional[Callable[[int, Optional[int], dict], None]] = None,
    options: Optional[ParseOptions] = None,
) -> ParseResult:
    requested_kind = requested_kind.strip().lower()
    if requested_kind not in SUPPORTED_KINDS:
        raise RuntimeError("Unsupported type. Use user, album, track, or playlist.")

    soundcloud_url = normalize_soundcloud_url(soundcloud_url, requested_kind)
    username = normalize_username(username)

    client_id = discover_client_id(soundcloud_url)
    resource = resolve_resource(soundcloud_url, client_id)
    actual_kind = normalize_resource_kind(resource)
    if actual_kind != requested_kind:
        raise RuntimeError("The link does not match the selected type.")

    status_text, title, collection_url = build_collection_url(resource, client_id)
    visible_rank, checked = find_visible_rank(
        resource,
        username,
        client_id,
        collection_url,
        progress_callback=progress_callback,
        options=options,
    )

    saved_list_path = None
    if options and options.save_user_list:
        collected_accounts = getattr(options, "_collected_accounts", [])
        saved_list_path = write_account_list(collected_accounts, options.save_user_list_filename)

    return ParseResult(
        requested_kind=requested_kind,
        actual_kind=actual_kind,
        username=username,
        source_url=soundcloud_url,
        title=title,
        status_text=status_text,
        visible_rank=visible_rank,
        checked=checked,
        expected_total=get_expected_total(resource),
        found=visible_rank is not None,
        saved_list_path=saved_list_path,
        debug={
            "client_id": client_id,
            "resource_id": resource.get("id"),
            "resource_kind": actual_kind,
            "collection_url": collection_url,
        }
        if options and options.debug
        else {},
    )
