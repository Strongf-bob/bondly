## 2026-05-03 18:21 (Local Time)
- Task/request: Start implementing the AI Follow-up Assistant MVP in the GitHub repository.
- What was analyzed: Product relaunch brief, empty repository state, Apache-2.0 license, backend security checklist, and Git branch/remote setup.
- Existing backend patterns reused: No existing application patterns were present; created a small layered Python structure with bot, LLM, storage, and service boundaries.
- What was implemented: Initial Python project scaffold, Telegram bot entrypoint, settings, LLM extraction/classification contracts, SQLAlchemy models, memory service, reminder dispatcher, environment example, README, and focused service tests.
- Verification performed: `python -m pytest`, `python -m ruff check .`, and `python -m compileall src` all passed.
- Files changed: README.md, pyproject.toml, .gitignore, .env.example, PROMPT_WORKLOG.md, src/bondly/*, tests/*.
- Assumptions made: The user LLM API is OpenAI-compatible at /chat/completions; polling is acceptable for local MVP; SQLite is sufficient locally and can later be swapped through DATABASE_URL.
- Remaining risks or follow-up ideas: Add migrations before production, refine duplicate matching, add voice input, add daily digest, and harden deployment secrets handling.

## 2026-05-03 18:36 (Local Time)
- Task/request: Implement hybrid storage where SQLite/Postgres remains the source of truth and Markdown is a readable memory mirror.
- What was analyzed: Markdown-first Personal CRM technical brief, current SQLAlchemy models, MemoryService write flow, and bot handler persistence boundaries.
- Existing backend patterns reused: Kept the existing layered package structure and SQLAlchemy source-of-truth model; added Markdown output as a storage adapter instead of moving domain logic into file parsing.
- What was implemented: Added person tags, `MarkdownMemoryMirror`, per-user Markdown profile export, `people_index.json`, `open_tasks.md`, `MEMORY_STORAGE_DIR`, bot synchronization after memory mutations, README storage documentation, and mirror tests.
- Verification performed: `python -m pytest`, `python -m ruff check .`, and `python -m compileall src` all passed.
- Files changed: README.md, .env.example, .gitignore, PROMPT_WORKLOG.md, src/bondly/config.py, src/bondly/bot/*, src/bondly/services/memory.py, src/bondly/storage/*, tests/test_memory_service.py.
- Assumptions made: Markdown is generated from the database and should not be manually edited as the source of truth in MVP 0.1.
- Remaining risks or follow-up ideas: Add Alembic migrations before production, enrich Markdown history from message logs, add graph exports, and add conflict/update logic for changed facts.

## 2026-05-03 18:50 (Local Time)
- Task/request: Run the project locally after the user filled `.env`.
- What was analyzed: Local startup logs from `storage/logs/bondly.err.log` and Windows `zoneinfo` failure.
- Existing backend patterns reused: Kept timezone configuration in `Settings`; fixed the runtime dependency instead of special-casing Windows timezone behavior.
- What was implemented: Added `tzdata` as a runtime dependency so `ZoneInfo("Europe/Moscow")` works on Windows.
- Verification performed: Reinstalled the project in `.venv`, started the bot successfully, confirmed polling for `@bondly_strongf_bot`, and ran `.venv\Scripts\python.exe -m pytest`, `.venv\Scripts\python.exe -m ruff check .`, and `.venv\Scripts\python.exe -m compileall src`.
- Files changed: pyproject.toml, PROMPT_WORKLOG.md.
- Assumptions made: `APP_TIMEZONE=Europe/Moscow` should remain the default local timezone.
- Remaining risks or follow-up ideas: Add a startup health check command that validates environment and timezone before polling Telegram.

## 2026-05-03 18:59 (Local Time)
- Task/request: Check whether the bot wrote anything to the database after user interaction.
- What was analyzed: SQLite table counts, `message_logs`, runtime logs, and the LLM request failure stack trace.
- Existing backend patterns reused: Kept LLM failures represented as `LlmError` and kept raw Telegram input logging inside `MemoryService`.
- What was implemented: Committed inbound message logs before LLM calls and wrapped `httpx.RequestError` as `LlmError` so network failures return a user-facing bot reply instead of bubbling through aiogram.
- Verification performed: `.venv\Scripts\python.exe -m pytest`, `.venv\Scripts\python.exe -m ruff check .`, and `.venv\Scripts\python.exe -m compileall src` all passed.
- Files changed: src/bondly/bot/handlers.py, src/bondly/llm/client.py, PROMPT_WORKLOG.md.
- Assumptions made: Raw inbound messages should be retained for debugging and recovery even when extraction fails.
- Remaining risks or follow-up ideas: Validate the configured LLM base URL and add a startup/config health check.

## 2026-05-03 19:08 (Local Time)
- Task/request: Re-check whether NeuralDeep still fails and diagnose the current local startup/config state.
- What was analyzed: Direct NeuralDeep chat completion request, Telegram API reachability, and settings loading from `.env`.
- Existing backend patterns reused: Kept central settings validation in `Settings`.
- What was implemented: Changed `.env` decoding to `utf-8-sig` so Windows PowerShell-created UTF-8 files with BOM do not break `TELEGRAM_BOT_TOKEN` parsing.
- Verification performed: Direct `LlmClient.classify_intent` returned valid JSON for a Russian question; `.venv\Scripts\python.exe -m pytest`, `.venv\Scripts\python.exe -m ruff check .`, and `.venv\Scripts\python.exe -m compileall src` all passed.
- Files changed: src/bondly/config.py, PROMPT_WORKLOG.md.
- Assumptions made: Supporting BOM-tolerant `.env` files is safer on Windows and does not change behavior for normal UTF-8 files.
- Remaining risks or follow-up ideas: Add a preflight command for env parsing, Telegram connectivity, and LLM JSON response validation.

## 2026-05-03 19:22 (Local Time)
- Task/request: Harden LLM prompts against prompt injection and improve Russian name handling after a bad surname/name recognition case.
- What was analyzed: Current system prompts, LLM extraction schema, MemoryService name/alias flow, and a live extraction probe for a Russian inflected name.
- Existing backend patterns reused: Kept LLM extraction as a typed boundary and name lookup through aliases.
- What was implemented: Added explicit prompt-injection boundaries, required the model to ignore injected instructions while still extracting ordinary CRM facts, changed name handling so canonical `name` is stored as the primary profile title and exact inflected `display_name` becomes an alias, and added a regression test for this alias behavior.
- Verification performed: `.venv\Scripts\python.exe -m pytest`, `.venv\Scripts\python.exe -m ruff check .`, and `.venv\Scripts\python.exe -m compileall src` all passed.
- Files changed: src/bondly/llm/prompts.py, src/bondly/llm/schemas.py, src/bondly/services/memory.py, tests/test_memory_service.py, PROMPT_WORKLOG.md.
- Assumptions made: For MVP, the model may propose an obvious nominative Russian profile title, but the exact user phrase must remain searchable as an alias.
- Remaining risks or follow-up ideas: Add an explicit correction flow like “исправь имя Рим Громов на ...” and maybe a confidence/confirmation field for uncertain names.

## 2026-05-03 19:53 (Local Time)
- Task/request: Fix bug where “с кем я знаком?” was not recognized as a contact list query and a bare name reply created an empty duplicate person.
- What was analyzed: SQLite counts and recent message logs showing duplicate `рим громов`, aiogram logs, and current intent/extraction prompts.
- Existing backend patterns reused: Kept routing through `ChatIntent` and memory writes through `MemoryService`.
- What was implemented: Added `list_people` intent, `MemoryService.list_people`, `MemoryService.has_memory_payload`, and a guard that refuses to save extractions containing only a bare name without facts/promises/dates.
- Verification performed: `.venv\Scripts\python.exe -m pytest`, `.venv\Scripts\python.exe -m ruff check .`, and `.venv\Scripts\python.exe -m compileall src` all passed; removed the local duplicate `people.id=2`, rebuilt the Markdown mirror, and restarted the bot.
- Files changed: src/bondly/llm/prompts.py, src/bondly/llm/schemas.py, src/bondly/bot/handlers.py, src/bondly/services/memory.py, tests/test_memory_service.py, PROMPT_WORKLOG.md.
- Assumptions made: A bare name alone should not create a new person unless accompanied by at least one fact, tag, role/company, promise, or important date.
- Remaining risks or follow-up ideas: Add conversational state so after “уточните, о ком речь” a bare name is interpreted as the missing query parameter instead of a new record.
