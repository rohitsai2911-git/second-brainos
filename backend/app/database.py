"""SQLAlchemy engine, session factory and Base."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings


def normalize_database_url(url: str) -> str:
    """Accept hosted-Postgres URL forms (Render/Railway/Neon/Supabase).

    Render and Heroku expose `postgres://...`; SQLAlchemy requires
    `postgresql+psycopg2://...`. Local/dev URLs already in the long
    form pass through untouched.

    Also tolerates common paste mistakes: surrounding quotes, leading
    `psql ` prefix, and stray whitespace/newlines.
    """
    cleaned = (url or "").strip()
    if (cleaned.startswith("'") and cleaned.endswith("'")) or (
        cleaned.startswith('"') and cleaned.endswith('"')
    ):
        cleaned = cleaned[1:-1].strip()
    if cleaned.lower().startswith("psql "):
        cleaned = cleaned[5:].strip()
    if cleaned.lower().startswith("postgres://"):
        return cleaned.replace("postgres://", "postgresql+psycopg2://", 1)
    if cleaned.lower().startswith("postgresql://"):
        return cleaned.replace("postgresql://", "postgresql+psycopg2://", 1)
    return cleaned


def _validate_database_url(url: str) -> str:
    """Fail fast with a password-safe message if the URL is missing/malformed."""
    from sqlalchemy.engine.url import make_url

    if not url:
        raise RuntimeError(
            "DATABASE_URL is empty — set it to your Postgres connection "
            "string (Neon dashboard → Connect → pooled URL)."
        )
    try:
        make_url(url)
    except Exception:
        scheme = url.split("://", 1)[0] if "://" in url else "(no scheme)"
        raise RuntimeError(
            "DATABASE_URL is malformed "
            f"(scheme={scheme!r}, length={len(url)}). Paste the full "
            "connection string exactly as shown by Neon, e.g. "
            "postgres://USER:PASSWORD@HOST/DBNAME?sslmode=require "
            "— no quotes, no `psql ` prefix, single line."
        )
    return url


engine = create_engine(_validate_database_url(normalize_database_url(settings.DATABASE_URL)), pool_pre_ping=True, pool_size=10, max_overflow=20)
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
