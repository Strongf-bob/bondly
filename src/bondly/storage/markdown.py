import json
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from bondly.storage.models import Person, Promise, PromiseStatus


class MarkdownMemoryMirror:
    def __init__(self, root_dir: str | Path) -> None:
        self._root_dir = Path(root_dir)

    def sync_user(self, session: Session, user_id: int) -> None:
        people = session.scalars(
            select(Person)
            .where(Person.user_id == user_id)
            .options(
                selectinload(Person.aliases),
                selectinload(Person.facts),
                selectinload(Person.tags),
                selectinload(Person.promises),
                selectinload(Person.important_dates),
            )
            .order_by(Person.name)
        ).all()

        user_root = self._root_dir / "users" / str(user_id)
        people_dir = user_root / "people"
        index_dir = user_root / "index"
        tasks_dir = user_root / "tasks"
        people_dir.mkdir(parents=True, exist_ok=True)
        index_dir.mkdir(parents=True, exist_ok=True)
        tasks_dir.mkdir(parents=True, exist_ok=True)

        index: list[dict[str, object]] = []
        expected_files: set[Path] = set()
        for person in people:
            path = people_dir / self._person_filename(person)
            path.write_text(self.render_person(person), encoding="utf-8")
            expected_files.add(path)
            index.append(
                {
                    "id": person.id,
                    "name": person.name,
                    "company": person.company,
                    "role_or_context": person.role_or_context,
                    "tags": sorted(tag.tag for tag in person.tags),
                    "file": str(path.relative_to(user_root)).replace("\\", "/"),
                }
            )

        for stale_file in people_dir.glob("*.md"):
            if stale_file not in expected_files:
                stale_file.unlink()

        (index_dir / "people_index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (tasks_dir / "open_tasks.md").write_text(
            self.render_open_tasks(session, user_id),
            encoding="utf-8",
        )

    def sync_people(self, session: Session, user_id: int, people: list[Person]) -> None:
        # The index and task views depend on cross-person state, so rebuild the user mirror.
        self.sync_user(session, user_id)

    def render_person(self, person: Person) -> str:
        aliases = sorted(
            alias.alias for alias in person.aliases if alias.alias != person.normalized_name
        )
        tags = sorted(tag.tag for tag in person.tags)
        facts = [fact.text for fact in sorted(person.facts, key=lambda item: item.created_at)]
        open_promises = [
            promise for promise in person.promises if promise.status == PromiseStatus.OPEN
        ]
        completed_promises = [
            promise for promise in person.promises if promise.status == PromiseStatus.COMPLETED
        ]

        lines = [
            "---",
            f"id: person_{person.id}",
            f"name: {self._yaml_string(person.name)}",
            "aliases:",
            *self._yaml_list(aliases),
            "status: active",
            f"created_at: {self._format_datetime(person.created_at)}",
            f"updated_at: {self._format_datetime(person.updated_at)}",
            "tags:",
            *self._yaml_list(tags),
            "---",
            "",
            f"# {person.name}",
            "",
            "## Кратко",
            self._summary(person),
            "",
            "## Основные факты",
            *self._markdown_list(facts, empty="Фактов пока нет."),
            "",
            "## Актуальное состояние",
            f"- Компания: {person.company or 'неизвестно'}",
            f"- Контекст: {person.role_or_context or 'неизвестно'}",
            "",
            "## Важные даты",
            *self._important_dates(person),
            "",
            "## Интересы и теги",
            *self._markdown_list(tags, empty="Тегов пока нет."),
            "",
            "## Связи",
            *self._relationships(person),
            "",
            "## Открытые задачи",
            *self._promise_lines(open_promises, empty="Нет открытых задач."),
            "",
            "## Завершённые задачи",
            *self._promise_lines(completed_promises, empty="Нет завершённых задач."),
            "",
            "## История взаимодействий",
            "Пока история хранится в SQLite `message_logs`.",
            "",
            "## История изменений",
            f"- {self._format_datetime(person.updated_at)}: профиль синхронизирован из SQLite.",
            "",
        ]
        return "\n".join(lines)

    def render_open_tasks(self, session: Session, user_id: int) -> str:
        promises = session.scalars(
            select(Promise)
            .where(Promise.user_id == user_id, Promise.status == PromiseStatus.OPEN)
            .order_by(Promise.due_at.is_(None), Promise.due_at)
        ).all()

        lines = ["# Open Tasks", ""]
        if not promises:
            lines.append("Нет открытых задач.")
            lines.append("")
            return "\n".join(lines)

        for promise in promises:
            person = promise.person.name if promise.person else "Без контакта"
            due = self._format_datetime(promise.due_at) if promise.due_at else "без срока"
            lines.append(f"- [ ] {person}: {promise.text}")
            lines.append(f"  - due: {due}")
            lines.append(f"  - id: promise_{promise.id}")
        lines.append("")
        return "\n".join(lines)

    def _person_filename(self, person: Person) -> str:
        return f"{person.id}-{self._slug(person.name)}.md"

    def _slug(self, value: str) -> str:
        slug = re.sub(r"[^\w]+", "-", value.strip().casefold(), flags=re.UNICODE)
        slug = slug.strip("-")
        return slug or "person"

    def _summary(self, person: Person) -> str:
        parts = [person.name]
        if person.company:
            parts.append(f"из {person.company}")
        if person.role_or_context:
            parts.append(person.role_or_context)
        if len(parts) == 1:
            return f"{person.name}: краткое описание пока не заполнено."
        return ", ".join(parts) + "."

    def _relationships(self, person: Person) -> list[str]:
        links: list[str] = []
        if person.company:
            links.append(f"- [[company:{self._slug(person.company)}]] — связан с компанией")
        for tag in sorted(person.tags, key=lambda item: item.tag):
            links.append(f"- [[topic:{tag.tag}]] — связан с темой")
        return links or ["Связей пока нет."]

    def _important_dates(self, person: Person) -> list[str]:
        if not person.important_dates:
            return ["- День рождения: неизвестно"]
        return [
            f"- {date.label}: {date.date_text}"
            for date in sorted(person.important_dates, key=lambda item: item.label)
        ]

    def _promise_lines(self, promises: list[Promise], empty: str) -> list[str]:
        if not promises:
            return [empty]
        lines: list[str] = []
        for promise in sorted(promises, key=lambda item: item.due_at or datetime.max):
            due = self._format_datetime(promise.due_at) if promise.due_at else "без срока"
            checkbox = "[x]" if promise.status == PromiseStatus.COMPLETED else "[ ]"
            lines.append(f"- {checkbox} {promise.text}")
            lines.append(f"  - due: {due}")
            lines.append(f"  - id: promise_{promise.id}")
        return lines

    def _markdown_list(self, values: list[str], empty: str) -> list[str]:
        if not values:
            return [empty]
        return [f"- {value}" for value in values]

    def _yaml_list(self, values: list[str]) -> list[str]:
        if not values:
            return ["  []"]
        return [f"  - {self._yaml_string(value)}" for value in values]

    def _yaml_string(self, value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return "unknown"
        return value.isoformat()
