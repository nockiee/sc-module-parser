import os
import re
import sys
from typing import Optional

from sc_parser_core import ParseOptions, ParseResult, parse_soundcloud_rank
from core_settings import load_settings


RESET = "\033[0m"
BOLD = "\033[1m"
SOFT = "\033[38;5;246m"
MUTED = "\033[38;5;243m"
PANEL = "\033[38;5;240m"
ACCENT = "\033[38;2;255;85;0m"
TRACK = "\033[38;5;237m"
FILL = "\033[38;2;255;85;0m"
DEBUG = "\033[38;5;245m"

RESOURCE_OPTIONS = {
    "1": ("user", "Artist"),
    "2": ("album", "Album"),
    "3": ("track", "Track"),
    "4": ("playlist", "Playlist"),
}

KIND_LABELS = {
    "user": "artist",
    "track": "track",
    "playlist": "playlist",
    "album": "album",
}

MODE_ALIASES = {
    "user": "user",
    "artist": "user",
    "album": "album",
    "track": "track",
    "playlist": "playlist",
}


def enable_ansi_colors() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def strip_ansi(value: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", value)


def prompt_input(label: str) -> str:
    return input(f"{MUTED}{label}{RESET} {ACCENT}›{RESET} ").strip()


def print_header() -> None:
    print(f"{ACCENT}{BOLD}sc-module-parser cli{RESET}")
    print(f"{MUTED}{BOLD}by nockieeteru{RESET}")
    print(f"{PANEL}{'─' * 24}{RESET}")
    print()


def normalize_mode(value: str) -> str:
    normalized = MODE_ALIASES.get(value.strip().lower(), value.strip().lower())
    if normalized not in KIND_LABELS:
        raise RuntimeError("Invalid mode. Use user, album, track, or playlist.")
    return normalized


def parse_named_args(argv: list[str]) -> Optional[tuple[str, str, str]]:
    if not argv or not any(item.startswith("--") for item in argv):
        return None

    values: dict[str, str] = {}
    index = 0
    while index < len(argv):
        key = argv[index]
        if not key.startswith("--"):
            raise RuntimeError("Invalid argument format. Use --mode --link --username.")
        if index + 1 >= len(argv):
            raise RuntimeError(f"Missing value for argument {key}.")
        values[key[2:].strip().lower()] = argv[index + 1]
        index += 2

    mode = values.get("mode")
    link = values.get("link")
    username = values.get("username")
    if not mode or not link or not username:
        raise RuntimeError("Arguments --mode, --link, and --username are required.")
    return normalize_mode(mode), link, username


def print_selected_mode(selected_kind: str) -> None:
    print(f"{MUTED}Selected{RESET} {ACCENT}›{RESET} {ACCENT}{KIND_LABELS.get(selected_kind, selected_kind)}{RESET}")
    print()


def prompt_resource_type() -> tuple[str, str]:
    print(f"{MUTED}What do you want to parse?{RESET}")
    for key, (_, label) in RESOURCE_OPTIONS.items():
        print(f"{SOFT}{key}.{RESET} {ACCENT}{label}{RESET}")
    print()

    while True:
        choice = prompt_input("Choice")
        option = RESOURCE_OPTIONS.get(choice)
        if option:
            print()
            return option
        print(f"{ACCENT}Enter a number from 1 to 4.{RESET}")


def render_line_box(title: str, rows: list[tuple[str, str]], spacer: bool = False) -> str:
    rendered_rows = [f"{MUTED}{label:<18}{RESET} {value}" for label, value in rows]
    content_width = max([len(strip_ansi(title))] + [len(strip_ansi(row)) for row in rendered_rows], default=0)
    top = f"{PANEL}┌{'─' * (content_width + 2)}┐{RESET}"
    centered_title = title.center(content_width)
    title_line = f"{PANEL}│{RESET} {BOLD}{ACCENT}{centered_title}{RESET} {PANEL}│{RESET}"
    body = [
        f"{PANEL}│{RESET} {row}{' ' * (content_width - len(strip_ansi(row)))} {PANEL}│{RESET}"
        for row in rendered_rows
    ]
    if spacer:
        body.insert(0, f"{PANEL}│{RESET} {' ' * content_width} {PANEL}│{RESET}")
    bottom = f"{PANEL}└{'─' * (content_width + 2)}┘{RESET}"
    return "\n".join([top, title_line, *body, bottom])


def render_progress(current: int, total: Optional[int], meta: Optional[dict] = None) -> None:
    if total and total > 0:
        width = 36
        ratio = min(current / total, 1)
        filled = int(width * ratio)
        bar = f"{FILL}{'█' * filled}{TRACK}{'░' * (width - filled)}{RESET}"
        percent = ratio * 100
        text = f"\r{SOFT}Scanning...{RESET} [{bar}] {ACCENT}{percent:5.1f}%{RESET} {SOFT}{current}/{total}{RESET}"
    else:
        text = f"\r{SOFT}Scanning...{RESET} {SOFT}{current}{RESET}"
    sys.stderr.write(text)
    sys.stderr.flush()


def render_progress_debug(current: int, total: Optional[int], meta: Optional[dict] = None) -> None:
    meta = meta or {}
    elapsed = float(meta.get("elapsed", 0.0))
    avg = float(meta.get("avg", 0.0))
    eta = meta.get("eta")

    if total and total > 0:
        width = 36
        ratio = min(current / total, 1)
        filled = int(width * ratio)
        bar = f"{FILL}{'█' * filled}{TRACK}{'░' * (width - filled)}{RESET}"
        percent = ratio * 100
        eta_text = f"{float(eta):.1f}s" if isinstance(eta, (int, float)) else "—"
        text = (
            f"\r{SOFT}Scanning...{RESET} [{bar}] {ACCENT}{percent:5.1f}%{RESET} "
            f"{SOFT}{current}/{total}{RESET} "
            f"{DEBUG}avg {avg:.3f}s eta {eta_text} elapsed {elapsed:.1f}s{RESET}"
        )
    else:
        text = (
            f"\r{SOFT}Scanning...{RESET} {SOFT}{current}{RESET} "
            f"{DEBUG}avg {avg:.3f}s elapsed {elapsed:.1f}s{RESET}"
        )
    sys.stderr.write(text)
    sys.stderr.flush()


def print_result(result: ParseResult) -> None:
    object_label = KIND_LABELS.get(result.actual_kind, "object")
    rank_label = "follower" if result.actual_kind == "user" else "like"
    position = f"{BOLD}{ACCENT}#{result.visible_rank}{RESET}" if result.visible_rank else f"{SOFT}—{RESET}"
    rows = [
        ("username", f"{ACCENT}{result.username}{RESET}"),
        (object_label, f"{SOFT}{result.title}{RESET}"),
        (rank_label, position),
    ]
    if result.saved_list_path:
        rows.append(("saved file", f"{SOFT}{result.saved_list_path}{RESET}"))
    print()
    print(
        render_line_box(
            "Parse Results",
            rows,
            spacer=True,
        )
    )
    if result.debug:
        print(
            render_line_box(
                "Debug",
                [
                    ("client_id", f"{DEBUG}{result.debug.get('client_id', '')}{RESET}"),
                    ("resource_id", f"{DEBUG}{result.debug.get('resource_id', '')}{RESET}"),
                    ("kind", f"{DEBUG}{result.debug.get('resource_kind', '')}{RESET}"),
                ],
            )
        )


def main() -> int:
    enable_ansi_colors()
    settings = load_settings()
    parse_options = ParseOptions(
        debug=settings.debug,
        save_user_list=settings.save_user_list,
        save_user_list_filename=settings.save_user_list_filename,
        save_user_list_mode=settings.save_user_list_mode,
        request_delay_seconds=settings.request_delay_seconds,
    )
    print_header()

    try:
        named_args = parse_named_args(sys.argv[1:])
        if named_args is not None:
            selected_kind, soundcloud_url, username = named_args
            print_selected_mode(selected_kind)
        elif len(sys.argv) >= 4:
            selected_kind = normalize_mode(sys.argv[1])
            soundcloud_url = sys.argv[2]
            username = sys.argv[3]
            print_selected_mode(selected_kind)
        else:
            selected_kind, _ = prompt_resource_type()
            soundcloud_url = prompt_input("SoundCloud link")
            username = prompt_input("Your SoundCloud username")
            print()

        if not soundcloud_url or not username:
            print("SoundCloud link and username are required.")
            return 1

        result = parse_soundcloud_rank(
            selected_kind,
            soundcloud_url,
            username,
            progress_callback=render_progress_debug if settings.debug else render_progress,
            options=parse_options,
        )
        sys.stderr.write("\n")
        sys.stderr.flush()
        print_result(result)
        return 0 if result.found else 2
    except KeyboardInterrupt:
        sys.stderr.write("\n")
        sys.stderr.flush()
        print(f"{ACCENT}Stopped by user.{RESET}")
        return 130
    except Exception as error:
        sys.stderr.write("\n")
        sys.stderr.flush()
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
