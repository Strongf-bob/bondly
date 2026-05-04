from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bondly.storage.database import Base


class PromiseStatus(StrEnum):
    OPEN = "open"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReminderStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    DONE = "done"
    CANCELLED = "cancelled"


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (UniqueConstraint("user_id", "normalized_name", name="uq_people_user_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200), index=True)
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role_or_context: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    aliases: Mapped[list["PersonAlias"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
    facts: Mapped[list["Fact"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
    tags: Mapped[list["PersonTag"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
    promises: Mapped[list["Promise"]] = relationship(back_populates="person")
    important_dates: Mapped[list["ImportantDate"]] = relationship(back_populates="person")


class PersonAlias(Base):
    __tablename__ = "person_aliases"
    __table_args__ = (UniqueConstraint("user_id", "alias", name="uq_alias_user_alias"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    alias: Mapped[str] = mapped_column(String(200), index=True)

    person: Mapped[Person] = relationship(back_populates="aliases")


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    person: Mapped[Person] = relationship(back_populates="facts")


class PersonTag(Base):
    __tablename__ = "person_tags"
    __table_args__ = (UniqueConstraint("user_id", "person_id", "tag", name="uq_person_tag"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    tag: Mapped[str] = mapped_column(String(100), index=True)

    person: Mapped[Person] = relationship(back_populates="tags")


class Promise(Base):
    __tablename__ = "promises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    person_id: Mapped[int | None] = mapped_column(
        ForeignKey("people.id"),
        nullable=True,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    status: Mapped[PromiseStatus] = mapped_column(
        Enum(PromiseStatus),
        default=PromiseStatus.OPEN,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    person: Mapped[Person | None] = relationship(back_populates="promises")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="promise")


class ImportantDate(Base):
    __tablename__ = "important_dates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    person_id: Mapped[int | None] = mapped_column(
        ForeignKey("people.id"),
        nullable=True,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(200))
    date_text: Mapped[str] = mapped_column(String(100))
    next_occurrence_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    person: Mapped[Person | None] = relationship(back_populates="important_dates")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    chat_id: Mapped[int] = mapped_column(Integer, index=True)
    promise_id: Mapped[int | None] = mapped_column(
        ForeignKey("promises.id"),
        nullable=True,
        index=True,
    )
    important_date_id: Mapped[int | None] = mapped_column(
        ForeignKey("important_dates.id"),
        nullable=True,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus),
        default=ReminderStatus.PENDING,
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    promise: Mapped[Promise | None] = relationship(back_populates="reminders")


class MessageLog(Base):
    __tablename__ = "message_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    chat_id: Mapped[int] = mapped_column(Integer, index=True)
    direction: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
