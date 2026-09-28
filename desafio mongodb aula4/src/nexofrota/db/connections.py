"""Fábricas de conexão para PostgreSQL e MongoDB."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from pymongo import MongoClient
from pymongo.database import Database

from nexofrota.config import Settings


class DatabaseClients:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._mongo_client: MongoClient[dict[str, Any]] = MongoClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=10_000,
            tz_aware=True,
        )

    @contextmanager
    def postgres(self) -> Iterator[Connection[dict[str, Any]]]:
        with psycopg.connect(**self._settings.postgres_kwargs, row_factory=dict_row) as connection:
            yield connection

    @property
    def mongo_database(self) -> Database[dict[str, Any]]:
        return self._mongo_client[self._settings.mongo_database]

    def ping(self) -> None:
        with self.postgres() as connection:
            connection.execute("SELECT 1")
        self._mongo_client.admin.command("ping")

    def close(self) -> None:
        self._mongo_client.close()
