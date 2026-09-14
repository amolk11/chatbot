"""Migration validation test executing Alembic upgrade head against SQLite."""

import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_creates_expected_schema() -> None:
    """Verify that alembic upgrade head applies cleanly and creates tables and indices."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "migration_test.db"
        sync_db_url = f"sqlite:///{db_path}"
        async_db_url = f"sqlite+aiosqlite:///{db_path}"

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", async_db_url)

        # Run migration upgrade to head
        command.upgrade(alembic_cfg, "head")

        # Inspect generated database schema using synchronous SQLite engine
        sync_engine = create_engine(sync_db_url)
        try:
            inspector = inspect(sync_engine)

            table_names = inspector.get_table_names()
            assert "conversations" in table_names
            assert "messages" in table_names
            assert "alembic_version" in table_names

            # Verify columns on conversations table
            conv_columns = {col["name"]: col for col in inspector.get_columns("conversations")}
            assert "id" in conv_columns
            assert "created_at" in conv_columns
            assert "updated_at" in conv_columns

            # Verify columns on messages table
            msg_columns = {col["name"]: col for col in inspector.get_columns("messages")}
            assert "id" in msg_columns
            assert "conversation_id" in msg_columns
            assert "role" in msg_columns
            assert "content_type" in msg_columns
            assert "content" in msg_columns
            assert "sequence_number" in msg_columns
            assert "created_at" in msg_columns

            # Verify foreign keys
            foreign_keys = inspector.get_foreign_keys("messages")
            assert len(foreign_keys) > 0
            assert foreign_keys[0]["referred_table"] == "conversations"
            assert foreign_keys[0]["referred_columns"] == ["id"]
        finally:
            sync_engine.dispose()
