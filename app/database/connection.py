from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator


class Database:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        with self.connect() as connection:
            connection.executescript(schema)
            episode_columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(episodes)"
                ).fetchall()
            }
            if "generation_status" not in episode_columns:
                connection.execute(
                    """
                    ALTER TABLE episodes
                    ADD COLUMN generation_status TEXT
                    NOT NULL DEFAULT 'story_ready'
                    """
                )
            for column, definition in {
                "rejection_reason": "TEXT",
                "rejected_at": "TEXT",
                "approved_at": "TEXT",
            }.items():
                if column not in episode_columns:
                    connection.execute(
                        f"ALTER TABLE episodes ADD COLUMN {column} {definition}"
                    )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
