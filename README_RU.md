# sc-module-parser

[<img src="https://flagcdn.com/16x12/gb.png" width="16" height="12" alt="English"> English](https://github.com/nockiee/sc-module-parser/blob/main/README.md) | <img src="https://flagcdn.com/16x12/ru.png" width="16" height="12" alt="Русский"> **Русский**

`sc-module-parser` — утилита для определения позиции пользователя в списках SoundCloud на основе публично доступных данных платформы.

Поддерживаемые типы ресурсов:

- `user` — позиция в списке подписчиков исполнителя;
- `track` — позиция в списке пользователей, поставивших лайк треку;
- `playlist` — позиция в списке пользователей, поставивших лайк плейлисту;
- `album` — позиция в списке пользователей, поставивших лайк альбому.

Проект предоставляет два прикладных интерфейса:

- CLI для интерактивного и параметризованного запуска;
- HTTP API для интеграции с внешними сервисами и пакетной обработки.

## Структура проекта

- [sc_parser_core.py](C:/Users/nockieeteru/Desktop/sc-parser/sc_parser_core.py) — ядро парсера и вся основная логика.
- [use_cli.py](C:/Users/nockieeteru/Desktop/sc-parser/use_cli.py) — пользовательский CLI-интерфейс.
- [use_api.py](C:/Users/nockieeteru/Desktop/sc-parser/use_api.py) — HTTP API.
- [core_settings.py](C:/Users/nockieeteru/Desktop/sc-parser/core_settings.py) — загрузчик настроек.
- [core_settings.json](C:/Users/nockieeteru/Desktop/sc-parser/core_settings.json) — файл настроек.
- [README.md](C:/Users/nockieeteru/Desktop/sc-parser/README.md) — английская документация.
- [README_RU.md](C:/Users/nockieeteru/Desktop/sc-parser/README_RU.md) — русская документация.

## Принцип работы

Алгоритм обработки запроса:

1. входное значение нормализуется до корректной ссылки SoundCloud;
2. из публичной страницы извлекается актуальный `client_id`;
3. через `resolve` определяется тип ресурса и его идентификатор;
4. выбирается соответствующий API-эндпоинт коллекции;
5. коллекция последовательно обходится по пагинации;
6. выполняется поиск целевого `username`;
7. вычисляется позиция на основе фактически просмотренного списка.

## Формат входных данных

Для поиска используется только `username` / handle SoundCloud, а не отображаемое имя профиля.

Корректные значения: `listener`, `@listener`, `artist`, `future-bass-lab`

Некорректные значения: `Listener Official`, `Artist Records`

Поддерживаемые форматы ссылок:

- `user`: `https://soundcloud.com/artist/followers/`, `https://soundcloud.com/artist/followers`, `https://soundcloud.com/artist/`, `https://soundcloud.com/artist`, `artist`
- `track`: `https://soundcloud.com/artist/track-name`
- `playlist`: `https://soundcloud.com/artist/sets/playlist-name`
- `album`: `https://soundcloud.com/artist/sets/album-name`

Для `user` короткая и полная форма ссылки автоматически нормализуются.

## Установка и запуск

Если Python уже установлен, запуск выполняется напрямую.

### Запуск интерактивного CLI

```powershell
start-cli.bat
```

Windows: `start-cli.bat`

Unix: `start-cli.sh`

### CLI с позиционными аргументами

```powershell
start-cli.bat user https://soundcloud.com/artist your_handle
```

### CLI с именованными аргументами

```powershell
start-cli.bat --mode playlist --username listener --link https://soundcloud.com/artist/sets/playlist-name
```

## Использование CLI

### Интерактивный режим

После запуска без аргументов появится меню:

```text
1. Artist
2. Album
3. Track
4. Playlist
```

Порядок работы: выбрать тип объекта, передать ссылку, указать `username`.

### Именованные аргументы

CLI поддерживает:

- `--mode`
- `--username`
- `--link`

Примеры:

```powershell
start-cli.bat --mode user --username listener --link artist
```

```powershell
start-cli.bat --mode track --username listener --link https://soundcloud.com/artist/track-name
```

```powershell
start-cli.bat --mode playlist --username listener --link https://soundcloud.com/artist/sets/playlist-name
```

Поддерживаемые значения `--mode`: `user` `album` `track` `playlist`

## Использование API

### Запуск API

```powershell
start-api.bat
```

По умолчанию сервер запускается на:

```text
http://127.0.0.1:8080
```

### Доступные эндпоинты

- `GET /health`
- `GET /parse`
- `POST /parse`
- `POST /parse-batch`

### Проверка API

```text
GET /health
```

Ответ:

```json
{
  "status": "ok"
}
```

### GET /parse

Пример:

```text
GET /parse?kind=user&url=https://soundcloud.com/artist&username=listener
```

Дополнительно можно передавать:

- `debug=true`
- `save_user_list=true`
- `save_user_list_filename=accounts.txt`
- `save_user_list_mode=both`

Полный пример:

```text
GET /parse?kind=user&url=https://soundcloud.com/artist&username=listener&debug=true&save_user_list=true&save_user_list_filename=accounts.txt&save_user_list_mode=both
```

### POST /parse

Пример запроса:

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

Пример ответа:

```json
{
  "requested_kind": "user",
  "actual_kind": "user",
  "username": "listener",
  "source_url": "https://soundcloud.com/artist",
  "title": "Artist Name",
  "status_text": "follower found",
  "visible_rank": 7,
  "checked": 87,
  "expected_total": 87,
  "found": true,
  "saved_list_path": "C:\\Users\\nockieeteru\\Desktop\\sc-parser\\accounts.txt",
  "debug": {}
}
```

### POST /parse-batch

Этот эндпоинт нужен для пакетной обработки нескольких задач.

Пример:

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

`worker_threads` полезен именно здесь, когда нужно выполнить несколько независимых задач параллельно.

Важно:

- для одного конкретного профиля или трека скорость почти не вырастет от `worker_threads`;
- один список SoundCloud обходится последовательно, потому что страницы связаны через `next_href`.

## Настройки

Файл настроек:

[core_settings.json](C:/Users/nockieeteru/Desktop/sc-parser/core_settings.json)

Пример:

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

### Описание полей

#### use_settings

Включает или отключает использование файла настроек: `true` — использовать, `false` — игнорировать.

#### debug

Режим отладки.

Если включен, CLI показывает `avg`, `eta`, `elapsed`, а результат содержит технические поля.

#### worker_threads

Количество потоков для `POST /parse-batch`.

Используется только для нескольких независимых задач в `POST /parse-batch`; одиночный проход не ускоряет.

#### request_delay_seconds

Задержка между страницами пагинации.

Рекомендуемое значение для максимальной скорости:

```json
0.0
```

#### save_user_list

Включает или отключает сохранение просмотренного списка аккаунтов в файл.

#### save_user_list_filename

Имя файла для сохранения.

Пример:

```json
"save_user_list_filename": "accounts.txt"
```

#### save_user_list_mode

Формат сохранения аккаунтов.

Поддерживаются: `username` `nickname` `both`

##### save_user_list_mode = username

Сохраняется только handle:

```text
wtfsodium
another_user
```

##### save_user_list_mode = nickname

Сохраняется только отображаемое имя:

```text
Ноки333eru
Another Display Name
```

##### save_user_list_mode = both

Сохраняются оба значения в формате `key=value`:

```text
username=wtfsodium | nickname=Ноки333eru
username=another_user | nickname=Another Display Name
```

## Архитектура приложения

### sc_parser_core.py

Ядро приложения: нормализация ссылок, извлечение `client_id`, `resolve`, обход пагинации, поиск `username`, вычисление позиции, экспорт списка аккаунтов.

### use_cli.py

CLI-обертка: меню, аргументы командной строки, прогресс, форматированный вывод, обработка `Ctrl+C`.

### use_api.py

HTTP-обертка: `GET/POST` эндпоинты, валидация входных данных, batch-обработка, JSON-ответы.

### core_settings.py / core_settings.json

Слой конфигурации: debug, batch-потоки, задержка запросов, экспорт списка аккаунтов, host/port API.

## Ограничения

- Позиция считается по тому порядку, который на текущий момент возвращает SoundCloud API.
- Если SoundCloud изменит фронтенд или API, извлечение `client_id` или обход списков может перестать работать.
- Для больших списков обработка может занимать заметное время.
- `worker_threads` не является ускорителем одного одиночного запроса к одному списку.

## Быстрые примеры

### Найти позицию среди подписчиков

```powershell
start-cli.bat --mode user --username listener --link artist
```

### Найти позицию среди лайков трека

```powershell
start-cli.bat --mode track --username listener --link https://soundcloud.com/artist/track-name
```

### Запустить API

```powershell
start-api.bat
```

### Сохранить список аккаунтов в файл

В `core_settings.json`:

```json
"save_user_list": true,
"save_user_list_filename": "accounts.txt",
"save_user_list_mode": "both"
```

После этого при парсинге будет сохранен файл со всеми просмотренными аккаунтами.
