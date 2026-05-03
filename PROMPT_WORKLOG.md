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
