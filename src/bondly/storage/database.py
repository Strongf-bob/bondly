from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


SessionFactory = sessionmaker[Session]


def create_session_factory(database_url: str) -> SessionFactory:
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.removeprefix("sqlite:///"))
        if db_path.parent != Path("."):
            db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    )
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_database(session_factory: SessionFactory) -> None:
    import bondly.storage.models  # noqa: F401

    engine = session_factory.kw["bind"]
    if not isinstance(engine, Engine):
        raise RuntimeError("Session factory is not bound to an engine.")
    Base.metadata.create_all(engine)


def session_scope(session_factory: SessionFactory) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
