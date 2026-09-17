"""SQLAlchemy engine, session factory and Base."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_reliability_columns() -> None:
    """Add reliability columns to existing DBs (create_all only covers fresh DBs)."""
    from sqlalchemy import inspect, text
    needed = {
        "processing_stage": "VARCHAR",
        "error_message": "TEXT",
        "processing_warning": "TEXT",
    }
    with engine.begin() as conn:
        existing = {c["name"] for c in inspect(conn).get_columns("documents")}
        for name, ddl in needed.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE documents ADD COLUMN {name} {ddl}"))
