import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy import select

from bondly.storage.database import SessionFactory
from bondly.storage.models import Reminder, ReminderStatus

logger = logging.getLogger(__name__)


class ReminderDispatcher:
    def __init__(
        self,
        bot: Bot,
        session_factory: SessionFactory,
        timezone: ZoneInfo,
        poll_interval_seconds: int,
    ) -> None:
        self._bot = bot
        self._session_factory = session_factory
        self._timezone = timezone
        self._poll_interval_seconds = poll_interval_seconds
        self._running = True

    async def run(self) -> None:
        while self._running:
            await self.dispatch_due_reminders()
            await asyncio.sleep(self._poll_interval_seconds)

    async def dispatch_due_reminders(self) -> None:
        now = datetime.now(self._timezone)
        with self._session_factory() as session:
            reminders = session.scalars(
                select(Reminder)
                .where(Reminder.status == ReminderStatus.PENDING, Reminder.remind_at <= now)
                .order_by(Reminder.remind_at)
                .limit(50)
            ).all()

            for reminder in reminders:
                try:
                    await self._bot.send_message(reminder.chat_id, reminder.text)
                except Exception:
                    logger.exception("Failed to send reminder %s", reminder.id)
                    continue

                reminder.status = ReminderStatus.SENT
                reminder.sent_at = now
            session.commit()
