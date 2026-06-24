# sc-module-parser

<img src="https://flagcdn.com/16x12/gb.png" width="16" height="12" alt="English"> **English** | [<img src="https://flagcdn.com/16x12/ru.png" width="16" height="12" alt="Русский"> Русский](C:/Users/nockieeteru/Desktop/sc-parser/README_RU.md)

`sc-module-parser` is a utility for resolving a user's position inside SoundCloud lists using publicly available platform data.

Supported resource types:

- `user` — rank inside follower list
- `track` — rank inside liker list
- `playlist` — rank inside liker list
- `album` — rank inside liker list

Interfaces:

- CLI for interactive or parameterized runs
- HTTP API for integrations and batch processing

## Structure

- [sc_parser_core.py](C:/Users/nockieeteru/Desktop/sc-parser/sc_parser_core.py) — core parsing and rank calculation
- [use_cli.py](C:/Users/nockieeteru/Desktop/sc-parser/use_cli.py) — CLI entrypoint
- [use_api.py](C:/Users/nockieeteru/Desktop/sc-parser/use_api.py) — HTTP API entrypoint
- [core_settings.py](C:/Users/nockieeteru/Desktop/sc-parser/core_settings.py) — settings loader
- [core_settings.json](C:/Users/nockieeteru/Desktop/sc-parser/core_settings.json) — settings file
- [start-cli.bat](C:/Users/nockieeteru/Desktop/sc-parser/start-cli.bat) — Windows launcher for CLI
- [start-api.bat](C:/Users/nockieeteru/Desktop/sc-parser/start-api.bat) — Windows launcher for API
- [start-cli.sh](C:/Users/nockieeteru/Desktop/sc-parser/start-cli.sh) — Unix launcher for CLI
- [start-api.sh](C:/Users/nockieeteru/Desktop/sc-parser/start-api.sh) — Unix launcher for API

## Workflow

Request processing pipeline:

1. normalize the input value into a valid SoundCloud URL
2. extract current `client_id` from the public page
3. resolve the resource type and ID
4. choose the matching collection endpoint
5. traverse paginated collection items
6. match the target `username`
7. compute rank from the scanned list

## Input format

The parser uses SoundCloud `username` / handle only, not the display name.

Valid values: `listener`, `@listener`, `artist`, `future-bass-lab`

Invalid values: `Listener Official`, `Artist Records`

Supported link formats:

- `user`: `https://soundcloud.com/artist/followers/`, `https://soundcloud.com/artist/followers`, `https://soundcloud.com/artist/`, `https://soundcloud.com/artist`, `artist`
- `track`: `https://soundcloud.com/artist/track-name`
- `playlist`: `https://soundcloud.com/artist/sets/playlist-name`
- `album`: `https://soundcloud.com/artist/sets/album-name`

For `user`, short and full profile links are normalized automatically.

## CLI

Interactive CLI:

```powershell
start-cli.bat
```

Windows: `start-cli.bat`

Unix: `start-cli.sh`

Launcher:

```powershell
start-cli.bat
```

Unix:

```bash
chmod +x start-cli.sh start-api.sh
./start-cli.sh
```

Positional arguments:

```powershell
start-cli.bat user https://soundcloud.com/artist your_handle
```

Named arguments:

```powershell
start-cli.bat --mode playlist --username listener --link https://soundcloud.com/artist/sets/playlist-name
```

Supported `--mode` values: `user` `album` `track` `playlist`

Behavior:

1. renders a minimal CLI interface
2. skips the menu when `--mode`, `--username`, and `--link` are provided
3. shows progress while scanning
4. prints the human-readable rank
5. exits cleanly on `Ctrl+C`

Examples:

```powershell
start-cli.bat --mode user --username listener --link artist
```

```powershell
start-cli.bat --mode track --username listener --link https://soundcloud.com/artist/track-name
```

## API

Start:

```powershell
start-api.bat
```

Launcher:

```powershell
start-api.bat
```

Unix:

```bash
chmod +x start-cli.sh start-api.sh
./start-api.sh
```

Default address:

```text
http://127.0.0.1:8080
```

Endpoints:

- `GET /health`
- `GET /parse`
- `POST /parse`
- `POST /parse-batch`

Example:

```text
GET /parse?kind=user&url=https://soundcloud.com/artist&username=listener
```

Optional query/body fields: `debug`, `save_user_list`, `save_user_list_filename`, `save_user_list_mode`

`POST /parse` example:

```json
{
  "kind": "user",
  "url": "https://soundcloud.com/artist",
  "username": "listener",
  "debug": true,
  "save_user_list": true,
  "save_user_list_filename": "accounts.txt",
  "save_user_list_mode": "both"
}
```

`POST /parse-batch` example:

```json
{
  "debug": true,
  "worker_threads": 4,
  "save_user_list": false,
  "tasks": [
    {
      "kind": "user",
      "url": "https://soundcloud.com/artist",
      "username": "listener"
    },
    {
      "kind": "track",
      "url": "https://soundcloud.com/artist/track-name",
      "username": "listener"
    }
  ]
}
```

`worker_threads` is relevant for `POST /parse-batch` only. A single SoundCloud list is still traversed sequentially because pagination is chained.

## Settings

Settings file: [core_settings.json](C:/Users/nockieeteru/Desktop/sc-parser/core_settings.json)

```json
{
  "use_settings": true,
  "debug": false,
  "worker_threads": 4,
  "request_delay_seconds": 0.0,
  "save_user_list": false,
  "save_user_list_filename": "accounts.txt",
  "save_user_list_mode": "both",
  "api": {
    "host": "127.0.0.1",
    "port": 8080
  }
}
```

Fields:

- `use_settings` — enable or ignore settings file
- `debug` — enable extended progress and technical output
- `worker_threads` — thread count for `POST /parse-batch`
- `request_delay_seconds` — delay between paginated requests
- `save_user_list` — enable list export
- `save_user_list_filename` — output filename
- `save_user_list_mode` — `username` `nickname` `both`
- `api.host` / `api.port` — API bind address

Export mode details:

- `username` — handle only
- `nickname` — display name only
- `both` — `username=value | nickname=value`

## Architecture

### sc_parser_core.py

Core layer: URL normalization, `client_id` extraction, `resolve`, pagination traversal, username matching, rank calculation, optional account export.

### use_cli.py

CLI layer: menu, argument parsing, progress rendering, formatted output, `Ctrl+C` handling.

### use_api.py

API layer: request parsing, validation, JSON responses, batch execution.

### core_settings.py / core_settings.json

Configuration layer: debug mode, batch threads, request delay, account export, API host and port.

## Limitations

- rank is based on the order currently returned by the SoundCloud API
- `client_id` extraction or traversal may break if SoundCloud changes frontend or API behavior
- large lists can take noticeable time
- `worker_threads` does not accelerate a single list traversal
