"""Acesso aos cadastros mantidos no PostgreSQL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nexofrota.db.connections import DatabaseClients
from nexofrota.models import FleetAsset


class RelationalRepository:
    def __init__(self, clients: DatabaseClients) -> None:
        self._clients = clients

    def initialize_schema(self) -> None:
        schema_path = Path(__file__).parents[1] / "db" / "schema.sql"
        with self._clients.postgres() as connection:
            connection.execute(schema_path.read_text(encoding="utf-8"))

    def upsert_drivers(self, drivers: list[dict[str, Any]]) -> None:
        statement = """
            INSERT INTO drivers (id, name, license_number, status)
            VALUES (%(id)s, %(name)s, %(license_number)s, %(status)s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                license_number = EXCLUDED.license_number,
                status = EXCLUDED.status
        """
        with self._clients.postgres() as connection:
            connection.executemany(statement, drivers)

    def upsert_vehicles(self, vehicles: list[dict[str, Any]]) -> None:
        statement = """
            INSERT INTO vehicles (id, plate, model, driver_id, active)
            VALUES (%(id)s, %(plate)s, %(model)s, %(driver_id)s, %(active)s)
            ON CONFLICT (id) DO UPDATE SET
                plate = EXCLUDED.plate,
                model = EXCLUDED.model,
                driver_id = EXCLUDED.driver_id,
                active = EXCLUDED.active
        """
        with self._clients.postgres() as connection:
            connection.executemany(statement, vehicles)

    def list_assets(self) -> list[FleetAsset]:
        statement = """
            SELECT
                v.id AS vehicle_id,
                v.plate,
                v.model,
                v.active,
                d.id AS driver_id,
                d.name AS driver_name,
                d.license_number,
                d.status AS driver_status
            FROM vehicles AS v
            INNER JOIN drivers AS d ON d.id = v.driver_id
            ORDER BY v.id
        """
        with self._clients.postgres() as connection:
            rows = connection.execute(statement).fetchall()
        return [FleetAsset(**row) for row in rows]

    def count_vehicles(self) -> int:
        with self._clients.postgres() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM vehicles").fetchone()
        return int(row["total"]) if row else 0

    def clear(self) -> None:
        with self._clients.postgres() as connection:
            connection.execute("TRUNCATE TABLE vehicles, drivers RESTART IDENTITY CASCADE")
