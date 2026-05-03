import re


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().casefold())


def first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None
