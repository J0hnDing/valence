import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


def default_database_url() -> str:
    configured = os.environ.get("VALENCE_DATABASE_URL")
    if configured:
        return configured
    path = Path(__file__).resolve().parents[2] / "data" / "valence.db"
    return "sqlite:///" + path.as_posix()


class Database:
    def __init__(self, url: str | None = None):
        url = url or default_database_url()
        parsed = make_url(url)
        if parsed.get_backend_name() != "sqlite":
            raise ValueError("Valence v1 requires a SQLite database")
        in_memory = parsed.database in (None, "", ":memory:")
        if not in_memory:
            Path(parsed.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        options = {"check_same_thread": False, "timeout": 30}
        self.engine = create_engine(
            url, connect_args=options, **({"poolclass": StaticPool} if in_memory else {})
        )

        @event.listens_for(self.engine, "connect")
        def configure_sqlite(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=30000")

        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        # create_all does not add columns to existing SQLite tables. This additive
        # upgrade keeps every existing person, version, and evaluation untouched.
        with self.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(persons)")}
            if "deleted_at" not in columns:
                connection.exec_driver_sql("ALTER TABLE persons ADD COLUMN deleted_at VARCHAR")
            action_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(actions)")}
            if "net_money_cost" not in action_columns:
                connection.exec_driver_sql("ALTER TABLE actions ADD COLUMN net_money_cost FLOAT NOT NULL DEFAULT 0")
            if "feature_duration_minutes" not in action_columns:
                connection.exec_driver_sql("ALTER TABLE actions ADD COLUMN feature_duration_minutes JSON")

    def dispose(self) -> None:
        self.engine.dispose()
