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
APP_TIMEZONE=Europe/Moscow
```

The LLM API is expected to support an OpenAI-compatible endpoint:

```text
POST {LLM_API_BASE_URL}/chat/completions
```

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
