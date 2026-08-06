"""Alembic baseline test — the migration builds exactly the models' schema, and downgrades cleanly.

Runs the real migration against a throwaway SQLite file (offline; no Postgres) and asserts the created
tables match ``Base.metadata`` — so a model added without a migration (or vice-versa) fails CI.

Runs with ``--noconftest`` (it manages its own DB and must not inherit the shared aiosqlite fixtures).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

_BACKEND = Path(__file__).resolve().parents[2]


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND / "app" / "db" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _user_tables(path: str) -> set[str]:
    con = sqlite3.connect(path)
    try:
        rows = con.execute(
            "select name from sqlite_master where type='table' and name not like 'sqlite_%'"
        ).fetchall()
    finally:
        con.close()
    return {r[0] for r in rows} - {"alembic_version"}


def test_migration_matches_models_and_round_trips(tmp_path, monkeypatch):
    from app.db.base import Base
    import app.models  # noqa: F401  (registers every table on Base.metadata)

    db_file = tmp_path / "migrated.db"
    url = f"sqlite+aiosqlite:///{db_file}"
    # env.py reads DATABASE_URL; point it (and the config) at the throwaway file.
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = _alembic_config(url)

    command.upgrade(cfg, "head")
    created = _user_tables(str(db_file))
    expected = set(Base.metadata.tables.keys())
    assert created == expected, f"migration/model drift: {expected ^ created}"

    command.downgrade(cfg, "base")
    assert _user_tables(str(db_file)) == set()  # downgrade drops every table
