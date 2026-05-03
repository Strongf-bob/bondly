# Bondly

Bondly is a Telegram-based AI follow-up assistant. It extracts people, promises,
important dates, and follow-up reminders from natural language messages, then
reminds the user when action is needed.

The first MVP deliberately avoids a knowledge graph, vector database, and web
dashboard. The product loop is:

1. Write a normal Telegram message about a person or promise.
2. Let the LLM extract structured memory.
3. Store the memory locally.
4. Send reminders when promises are due.
5. Answer simple questions like "кто такой Саша?" and "что я обещал?".

## Current Scope

Version `0.1` includes:

- Telegram polling bot via `aiogram`;
- OpenAI-compatible chat completions integration for extraction/classification;
- SQLite by default, configurable through `DATABASE_URL`;
- Markdown memory mirror under `MEMORY_STORAGE_DIR`;
- SQLAlchemy models for people, facts, promises, important dates, reminders, and message logs;
- reminder dispatcher for due reminders;
- basic commands and natural-language routing.

Deferred:

- vector search;
- knowledge graph;
- Google Calendar;
- web dashboard;
- advanced deduplication;
- payment/SaaS infrastructure.

## Local Setup

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Fill `.env`:

```text
TELEGRAM_BOT_TOKEN=...
LLM_API_BASE_URL=https://your-llm-api.example/v1
LLM_API_KEY=...
LLM_MODEL=...
DATABASE_URL=sqlite:///storage/bondly.sqlite3
MEMORY_STORAGE_DIR=storage/memory
APP_TIMEZONE=Europe/Moscow
```

The LLM API is expected to support an OpenAI-compatible endpoint:

```text
POST {LLM_API_BASE_URL}/chat/completions
```

## Storage Model

Bondly uses a hybrid storage model:

```text
SQLite/Postgres = application source of truth
Markdown        = readable memory mirror
```

The database stores operational state: open/completed promises, pending/sent/done
reminders, person records, aliases, tags, facts, dates, and message logs. The bot
reads from the database when answering questions and sending reminders.

After memory changes, Bondly rebuilds Markdown files from the database:

```text
storage/
  bondly.sqlite3

  memory/
    users/
      123456789/
        people/
          1-саша.md
        index/
          people_index.json
        tasks/
          open_tasks.md
```

This keeps the Markdown files useful for reading, backup, and future Obsidian-style
workflows without making reminder delivery depend on parsing `.md` files.

## Run

```powershell
bondly-bot
```

or:

```powershell
python -m bondly.main
```

## Useful Messages

```text
Познакомился с Сашей из Яндекса. Он занимается ML-инфрой. Обещал скинуть ему статью про AI-агентов завтра.
кто такой Саша?
что я обещал?
кому надо написать?
да
```

## Verification

```powershell
python -m pytest
python -m ruff check .
python -m compileall src
```

## License

Apache-2.0. See [LICENSE](LICENSE).
