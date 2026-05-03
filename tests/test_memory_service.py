from datetime import UTC, datetime, timedelta

from bondly.llm.schemas import ExtractedPerson, ExtractedPromise, MessageExtraction
from bondly.services.memory import MemoryService
from bondly.storage.database import create_session_factory, init_database
from bondly.storage.models import Person, Promise, Reminder, ReminderStatus


def make_session_factory():
    session_factory = create_session_factory("sqlite:///:memory:")
    init_database(session_factory)
    return session_factory


def test_apply_extraction_creates_person_promise_and_reminder():
    session_factory = make_session_factory()
    due_at = datetime.now(UTC) + timedelta(days=1)
    extraction = MessageExtraction(
        people=[
            ExtractedPerson(
                name="Саша",
                aliases=["Александр", "Саша из Яндекса"],
                company="Яндекс",
                role_or_context="занимается ML-инфрой",
                facts=["Познакомились на хакатоне"],
            )
        ],
        promises=[
            ExtractedPromise(
                person_name="Саша",
                text="скинуть статью про AI-агентов",
                due_at=due_at,
            )
        ],
        reply="Запомнил Сашу и поставил напоминание.",
    )

    with session_factory() as session:
        service = MemoryService(session)
        service.apply_extraction(user_id=1, chat_id=10, extraction=extraction)
        session.commit()

        person = session.query(Person).one()
        promise = session.query(Promise).one()
        reminder = session.query(Reminder).one()

        assert person.name == "Саша"
        assert person.company == "Яндекс"
        assert promise.person_id == person.id
        assert promise.text == "скинуть статью про AI-агентов"
        assert reminder.promise_id == promise.id
        assert reminder.status == ReminderStatus.PENDING


def test_person_card_and_open_promises_are_scoped_by_user():
    session_factory = make_session_factory()
    extraction = MessageExtraction(
        people=[ExtractedPerson(name="Дима", company="Т-Банк", facts=["Занимается антифродом"])],
        promises=[ExtractedPromise(person_name="Дима", text="отправить ссылку")],
        reply="Запомнил.",
    )

    with session_factory() as session:
        service = MemoryService(session)
        service.apply_extraction(user_id=1, chat_id=10, extraction=extraction)
        session.commit()

        assert "Дима" in service.get_person_card(user_id=1, name="Дима")
        assert service.get_person_card(user_id=2, name="Дима") is None
        assert "отправить ссылку" in service.list_open_promises(user_id=1)
        assert service.list_open_promises(user_id=2) == "Открытых обещаний нет."


def test_mark_latest_sent_promise_done():
    session_factory = make_session_factory()
    due_at = datetime.now(UTC) - timedelta(minutes=1)
    extraction = MessageExtraction(
        people=[ExtractedPerson(name="Катя")],
        promises=[
            ExtractedPromise(
                person_name="Катя",
                text="написать после защиты",
                due_at=due_at,
            )
        ],
        reply="Запомнил.",
    )

    with session_factory() as session:
        service = MemoryService(session)
        service.apply_extraction(user_id=1, chat_id=10, extraction=extraction)
        reminder = session.query(Reminder).one()
        reminder.status = ReminderStatus.SENT
        reminder.sent_at = due_at
        session.commit()

        assert service.mark_latest_sent_promise_done(user_id=1) is True
        assert "Открытых обещаний нет." == service.list_open_promises(user_id=1)
