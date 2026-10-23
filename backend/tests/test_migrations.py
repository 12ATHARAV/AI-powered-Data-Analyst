from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.config import get_settings


@pytest.mark.integration
def test_alembic_migrations_on_postgres() -> None:
    """Test applying alembic migrations to the running Postgres container."""
    settings = get_settings()
    assert "postgresql" in settings.database_url or "psycopg" in settings.database_url

    backend_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))

    # Run upgrade head
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    for expected in ["users", "files", "conversations", "messages", "pins"]:
        assert expected in table_names, f"Table {expected} was not created by Alembic"

    # Insert and read a row on users table
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO users (id, clerk_user_id, email, created_at) VALUES (gen_random_uuid(), :cid, :email, now()) ON CONFLICT (clerk_user_id) DO NOTHING"),
            {"cid": "test_mig_clerk_id", "email": "mig@example.com"},
        )
        row = conn.execute(
            text("SELECT clerk_user_id, email FROM users WHERE clerk_user_id = :cid"),
            {"cid": "test_mig_clerk_id"},
        ).fetchone()
        assert row is not None
        assert row[0] == "test_mig_clerk_id"
