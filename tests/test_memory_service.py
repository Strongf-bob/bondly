from datetime import UTC, datetime, timedelta

from bondly.llm.schemas import ExtractedPerson, ExtractedPromise, MessageExtraction
from bondly.services.memory import MemoryService
from bondly.storage.database import create_session_factory, init_database
from bondly.storage.markdown import MarkdownMemoryMirror
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
                tags=["yandex", "ml", "infra"],
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
        assert {tag.tag for tag in person.tags} == {"infra", "ml", "yandex"}
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
        assert "Дима" in service.list_people(user_id=1)
        assert service.list_people(user_id=2) == "Пока никого не записал."


def test_empty_name_only_extraction_is_not_memory_payload():
    session_factory = make_session_factory()
    extraction = MessageExtraction(
        people=[ExtractedPerson(name="рим громов", display_name="рим громов")],
        reply="Записал.",
    )

    with session_factory() as session:
        service = MemoryService(session)
        assert service.has_memory_payload(extraction) is False


def test_canonical_name_is_primary_and_display_name_is_alias():
    session_factory = make_session_factory()
    extraction = MessageExtraction(
        people=[
            ExtractedPerson(
                name="Рим Громов",
                display_name="Римом Громовым",
                facts=["Познакомились 1 сентября 2025 года"],
            )
        ],
        reply="Запомнил.",
    )

    with session_factory() as session:
        service = MemoryService(session)
        service.apply_extraction(user_id=1, chat_id=10, extraction=extraction)
        session.commit()

        assert service.get_person_card(user_id=1, name="Рим Громов") is not None
        assert service.get_person_card(user_id=1, name="Римом Громовым") is not None


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


def test_markdown_mirror_writes_profiles_index_and_open_tasks(tmp_path):
    session_factory = make_session_factory()
    due_at = datetime.now(UTC) + timedelta(days=1)
    extraction = MessageExtraction(
        people=[
            ExtractedPerson(
                name="Саша",
                aliases=["Саша из Яндекса"],
                company="Яндекс",
                role_or_context="занимается ML-инфрой",
                facts=["Познакомились на хакатоне"],
                tags=["yandex", "ml infra"],
            )
        ],
        promises=[
            ExtractedPromise(
                person_name="Саша",
                text="скинуть статью про AI-агентов",
                due_at=due_at,
            )
        ],
        reply="Запомнил.",
    )

    with session_factory() as session:
        service = MemoryService(session)
        service.apply_extraction(user_id=1, chat_id=10, extraction=extraction)
        session.commit()

        mirror = MarkdownMemoryMirror(tmp_path)
        mirror.sync_user(session, user_id=1)

    user_root = tmp_path / "users" / "1"
    profile_files = list((user_root / "people").glob("*.md"))
    assert len(profile_files) == 1

    profile = profile_files[0].read_text(encoding="utf-8")
    assert "# Саша" in profile
    assert "Компания: Яндекс" in profile
    assert "[[company:яндекс]]" in profile
    assert "[[topic:ml-infra]]" in profile
    assert "скинуть статью про AI-агентов" in profile

    people_index = (user_root / "index" / "people_index.json").read_text(encoding="utf-8")
    assert '"name": "Саша"' in people_index
    assert '"file": "people/1-саша.md"' in people_index

    open_tasks = (user_root / "tasks" / "open_tasks.md").read_text(encoding="utf-8")
    assert "# Open Tasks" in open_tasks
    assert "- [ ] Саша: скинуть статью про AI-агентов" in open_tasks
