from datetime import datetime

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bondly.config import Settings
from bondly.llm.client import LlmClient, LlmError
from bondly.services.memory import MemoryService
from bondly.storage.database import SessionFactory
from bondly.storage.markdown import MarkdownMemoryMirror


def create_router(
    settings: Settings,
    session_factory: SessionFactory,
    llm_client: LlmClient,
    markdown_mirror: MarkdownMemoryMirror,
) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        await message.answer(
            "Привет. Напиши одной фразой, с кем познакомился и что обещал. "
            "Я запомню и поставлю напоминание."
        )

    @router.message()
    async def handle_text(message: Message) -> None:
        if not message.text or message.from_user is None:
            return

        user_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text.strip()

        with session_factory() as session:
            memory = MemoryService(session)
            memory.log_message(user_id=user_id, chat_id=chat_id, direction="in", text=text)
            session.commit()

            if text.casefold() in {"да", "готово", "выполнил", "сделал"}:
                if memory.mark_latest_sent_promise_done(user_id):
                    reply = "Отметил. Хочешь сделать follow-up через неделю?"
                else:
                    reply = "Не нашёл активного напоминания, которое можно закрыть."
                memory.log_message(user_id=user_id, chat_id=chat_id, direction="out", text=reply)
                session.commit()
                markdown_mirror.sync_user(session, user_id)
                await message.answer(reply)
                return

        try:
            intent = await llm_client.classify_intent(text)
        except LlmError:
            await message.answer("Не смог разобрать сообщение. Попробуй переформулировать.")
            return

        now = datetime.now(settings.timezone)
        with session_factory() as session:
            memory = MemoryService(session)

            if intent.kind == "who_is" and intent.person_name:
                reply = memory.get_person_card(user_id, intent.person_name)
                if reply is None:
                    reply = f"Пока не знаю, кто такой {intent.person_name}."
            elif intent.kind == "open_promises":
                reply = memory.list_open_promises(user_id)
            elif intent.kind == "due_followups":
                reply = memory.list_due_followups(user_id, now)
            else:
                try:
                    extraction = await llm_client.extract_message(
                        message=text,
                        now=now,
                        timezone=settings.app_timezone,
                    )
                except LlmError:
                    await message.answer("Не смог сохранить запись. Попробуй написать проще.")
                    return

                memory.apply_extraction(user_id=user_id, chat_id=chat_id, extraction=extraction)
                reply = extraction.reply

            memory.log_message(user_id=user_id, chat_id=chat_id, direction="out", text=reply)
            session.commit()
            if intent.kind not in {"who_is", "open_promises", "due_followups"}:
                markdown_mirror.sync_user(session, user_id)

        await message.answer(reply)

    return router
