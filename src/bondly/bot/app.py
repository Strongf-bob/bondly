import asyncio
import contextlib

from aiogram import Bot, Dispatcher

from bondly.bot.handlers import create_router
from bondly.config import get_settings
from bondly.llm.client import LlmClient
from bondly.services.reminders import ReminderDispatcher
from bondly.storage import create_session_factory, init_database
from bondly.storage.markdown import MarkdownMemoryMirror


async def run_bot() -> None:
    settings = get_settings()
    session_factory = create_session_factory(settings.database_url)
    init_database(session_factory)

    bot = Bot(token=settings.telegram_bot_token.get_secret_value())
    dispatcher = Dispatcher()
    llm_client = LlmClient(
        base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        model=settings.llm_model,
    )
    markdown_mirror = MarkdownMemoryMirror(settings.memory_storage_dir)
    dispatcher.include_router(create_router(settings, session_factory, llm_client, markdown_mirror))

    reminders = ReminderDispatcher(
        bot=bot,
        session_factory=session_factory,
        timezone=settings.timezone,
        poll_interval_seconds=settings.reminder_poll_interval_seconds,
    )
    reminder_task = asyncio.create_task(reminders.run())
    try:
        await dispatcher.start_polling(bot)
    finally:
        reminder_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reminder_task
        await bot.session.close()
