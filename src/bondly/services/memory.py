from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from bondly.llm.schemas import MessageExtraction
from bondly.services.text import first_non_empty, normalize_name
from bondly.storage.models import (
    Fact,
    ImportantDate,
    MessageLog,
    Person,
    PersonAlias,
    PersonTag,
    Promise,
    PromiseStatus,
    Reminder,
    ReminderStatus,
)


class MemoryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def log_message(self, user_id: int, chat_id: int, direction: str, text: str) -> None:
        self._session.add(
            MessageLog(user_id=user_id, chat_id=chat_id, direction=direction, text=text)
        )

    def apply_extraction(
        self,
        user_id: int,
        chat_id: int,
        extraction: MessageExtraction,
    ) -> None:
        people_by_name: dict[str, Person] = {}
        for extracted in extraction.people:
            person = self.upsert_person(
                user_id=user_id,
                name=extracted.name,
                aliases=extracted.aliases,
                company=extracted.company,
                role_or_context=extracted.role_or_context,
                facts=extracted.facts,
                tags=extracted.tags,
            )
            people_by_name[normalize_name(extracted.name)] = person
            for alias in extracted.aliases:
                people_by_name[normalize_name(alias)] = person

        for extracted in extraction.promises:
            person = self._find_person_by_name(user_id, extracted.person_name, people_by_name)
            promise = Promise(
                user_id=user_id,
                person_id=person.id if person else None,
                text=extracted.text.strip(),
                due_at=extracted.due_at,
                status=PromiseStatus.OPEN,
            )
            self._session.add(promise)
            self._session.flush()
            if extracted.due_at:
                self._session.add(
                    Reminder(
                        user_id=user_id,
                        chat_id=chat_id,
                        promise_id=promise.id,
                        text=self._format_promise_reminder(person, promise.text),
                        remind_at=extracted.due_at,
                        status=ReminderStatus.PENDING,
                    )
                )

        for extracted in extraction.important_dates:
            person = self._find_person_by_name(user_id, extracted.person_name, people_by_name)
            important_date = ImportantDate(
                user_id=user_id,
                person_id=person.id if person else None,
                label=extracted.label.strip(),
                date_text=extracted.date_text.strip(),
                next_occurrence_at=extracted.next_occurrence_at,
            )
            self._session.add(important_date)
            self._session.flush()
            if extracted.next_occurrence_at:
                self._session.add(
                    Reminder(
                        user_id=user_id,
                        chat_id=chat_id,
                        important_date_id=important_date.id,
                        text=self._format_date_reminder(person, important_date.label),
                        remind_at=extracted.next_occurrence_at,
                        status=ReminderStatus.PENDING,
                    )
                )

    def upsert_person(
        self,
        user_id: int,
        name: str,
        aliases: list[str],
        company: str | None,
        role_or_context: str | None,
        facts: list[str],
        tags: list[str] | None = None,
    ) -> Person:
        normalized = normalize_name(name)
        person = self._session.scalar(
            select(Person).where(Person.user_id == user_id, Person.normalized_name == normalized)
        )
        if person is None:
            person = Person(user_id=user_id, name=name.strip(), normalized_name=normalized)
            self._session.add(person)
            self._session.flush()

        person.company = first_non_empty(company, person.company)
        person.role_or_context = first_non_empty(role_or_context, person.role_or_context)

        existing_facts = {fact.text.casefold() for fact in person.facts}
        for fact_text in facts:
            cleaned = fact_text.strip()
            if cleaned and cleaned.casefold() not in existing_facts:
                self._session.add(Fact(user_id=user_id, person_id=person.id, text=cleaned))
                existing_facts.add(cleaned.casefold())

        existing_aliases = {alias.alias for alias in person.aliases}
        for alias in aliases + [name]:
            cleaned_alias = normalize_name(alias)
            if cleaned_alias and cleaned_alias not in existing_aliases:
                self._session.add(
                    PersonAlias(user_id=user_id, person_id=person.id, alias=cleaned_alias)
                )
                existing_aliases.add(cleaned_alias)

        existing_tags = {tag.tag for tag in person.tags}
        for tag in tags or []:
            cleaned_tag = normalize_name(tag).replace(" ", "-")
            if cleaned_tag and cleaned_tag not in existing_tags:
                self._session.add(
                    PersonTag(user_id=user_id, person_id=person.id, tag=cleaned_tag)
                )
                existing_tags.add(cleaned_tag)

        return person

    def get_person_card(self, user_id: int, name: str) -> str | None:
        person = self._find_person_by_name(user_id, name)
        if person is None:
            return None

        lines = [f"{person.name}"]
        if person.company or person.role_or_context:
            details = ", ".join(
                part for part in [person.company, person.role_or_context] if part
            )
            lines.append(details)

        open_promises = [
            promise for promise in person.promises if promise.status == PromiseStatus.OPEN
        ]
        if person.facts:
            lines.append("")
            lines.append("Факты:")
            lines.extend(f"- {fact.text}" for fact in person.facts[-5:])
        if open_promises:
            lines.append("")
            lines.append("Открытые обещания:")
            lines.extend(f"- {promise.text}" for promise in open_promises)

        return "\n".join(lines)

    def list_open_promises(self, user_id: int) -> str:
        promises = self._session.scalars(
            select(Promise)
            .where(Promise.user_id == user_id, Promise.status == PromiseStatus.OPEN)
            .order_by(Promise.due_at.is_(None), Promise.due_at)
            .limit(20)
        ).all()
        if not promises:
            return "Открытых обещаний нет."

        lines = ["Открытые обещания:"]
        for index, promise in enumerate(promises, start=1):
            person = promise.person.name if promise.person else "Без контакта"
            due = f" до {promise.due_at:%Y-%m-%d %H:%M}" if promise.due_at else ""
            lines.append(f"{index}. {person} — {promise.text}{due}")
        return "\n".join(lines)

    def list_due_followups(self, user_id: int, now: datetime) -> str:
        reminders = self._session.scalars(
            select(Reminder)
            .where(
                Reminder.user_id == user_id,
                Reminder.status == ReminderStatus.PENDING,
                Reminder.remind_at <= now,
            )
            .order_by(Reminder.remind_at)
            .limit(20)
        ).all()
        if not reminders:
            return "Сейчас нет просроченных follow-up."

        lines = ["Нужно написать:"]
        lines.extend(
            f"{index}. {reminder.text}" for index, reminder in enumerate(reminders, start=1)
        )
        return "\n".join(lines)

    def mark_latest_sent_promise_done(self, user_id: int) -> bool:
        reminder = self._session.scalar(
            select(Reminder)
            .join(Promise, Reminder.promise_id == Promise.id)
            .where(
                Reminder.user_id == user_id,
                Reminder.status == ReminderStatus.SENT,
                Promise.status == PromiseStatus.OPEN,
            )
            .order_by(Reminder.sent_at.desc())
        )
        if reminder is None or reminder.promise is None:
            return False

        reminder.status = ReminderStatus.DONE
        reminder.promise.status = PromiseStatus.COMPLETED
        reminder.promise.completed_at = datetime.utcnow()
        return True

    def _find_person_by_name(
        self,
        user_id: int,
        name: str | None,
        prefetched: dict[str, Person] | None = None,
    ) -> Person | None:
        if not name:
            return None
        normalized = normalize_name(name)
        if prefetched and normalized in prefetched:
            return prefetched[normalized]

        person = self._session.scalar(
            select(Person).where(Person.user_id == user_id, Person.normalized_name == normalized)
        )
        if person:
            return person

        alias = self._session.scalar(
            select(PersonAlias).where(
                PersonAlias.user_id == user_id,
                PersonAlias.alias == normalized,
            )
        )
        return alias.person if alias else None

    def _format_promise_reminder(self, person: Person | None, text: str) -> str:
        if person:
            return f"Напоминание: ты обещал {person.name}: {text}"
        return f"Напоминание: {text}"

    def _format_date_reminder(self, person: Person | None, label: str) -> str:
        if person:
            return f"Важная дата: {label} у {person.name}"
        return f"Важная дата: {label}"
