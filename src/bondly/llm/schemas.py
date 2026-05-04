from datetime import datetime

from pydantic import BaseModel, Field


class ExtractedPerson(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    aliases: list[str] = Field(default_factory=list)
    company: str | None = Field(default=None, max_length=200)
    role_or_context: str | None = Field(default=None, max_length=500)
    facts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ExtractedPromise(BaseModel):
    person_name: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=1)
    due_at: datetime | None = None


class ExtractedImportantDate(BaseModel):
    person_name: str | None = Field(default=None, max_length=200)
    label: str = Field(min_length=1, max_length=200)
    date_text: str = Field(min_length=1, max_length=100)
    next_occurrence_at: datetime | None = None


class MessageExtraction(BaseModel):
    people: list[ExtractedPerson] = Field(default_factory=list)
    promises: list[ExtractedPromise] = Field(default_factory=list)
    important_dates: list[ExtractedImportantDate] = Field(default_factory=list)
    reply: str = Field(min_length=1)


class ChatIntent(BaseModel):
    kind: str = Field(
        pattern="^(record|who_is|list_people|open_promises|due_followups|unknown)$"
    )
    person_name: str | None = Field(default=None, max_length=200)
