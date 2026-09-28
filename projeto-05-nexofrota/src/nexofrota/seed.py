"""Prepara o esquema e os dados de demonstração da NexoFrota."""

from __future__ import annotations

import argparse
import logging
import random
import time
from datetime import UTC, datetime, timedelta

from nexofrota.config import Settings
from nexofrota.db.connections import DatabaseClients
from nexofrota.models import TelemetryReading
from nexofrota.repositories.relational import RelationalRepository
from nexofrota.repositories.telemetry import TelemetryRepository

LOGGER = logging.getLogger(__name__)

DRIVERS = [
    {"id": 1, "name": "Marina Costa", "license_number": "CNH-584102", "status": "active"},
    {"id": 2, "name": "João Mendes", "license_number": "CNH-671934", "status": "active"},
    {"id": 3, "name": "Beatriz Rocha", "license_number": "CNH-730285", "status": "active"},
]

VEHICLES = [
    {"id": 101, "plate": "NFX1A01", "model": "Volvo FH 540", "driver_id": 1, "active": True},
    {"id": 102, "plate": "NFX2B02", "model": "Scania R 450", "driver_id": 2, "active": True},
    {"id": 103, "plate": "NFX3C03", "model": "DAF XF 530", "driver_id": 3, "active": True},
]

BASE_POSITIONS = {
    101: (-46.6333, -23.5505, 56.0, 4.0),
    102: (-46.6819, -23.5874, 88.0, -14.0),
    103: (-46.5987, -23.5329, 0.0, 18.0),
}


def build_demo_readings(*, end_at: datetime | None = None) -> list[TelemetryReading]:
    end = end_at or datetime.now(UTC).replace(second=0, microsecond=0)
    generator = random.Random(2026)
    readings: list[TelemetryReading] = []

    for vehicle_id, (
        longitude,
        latitude,
        target_speed,
        target_temperature,
    ) in BASE_POSITIONS.items():
        for index in range(12):
            is_last = index == 11
            readings.append(
                TelemetryReading(
                    vehicle_id=vehicle_id,
                    longitude=longitude
                    if is_last
                    else longitude + generator.uniform(-0.012, 0.012),
                    latitude=latitude if is_last else latitude + generator.uniform(-0.009, 0.009),
                    speed_kmh=(
                        target_speed
                        if is_last
                        else max(0, target_speed + generator.uniform(-10, 10))
                    ),
                    cargo_temperature_c=(
                        target_temperature
                        if is_last
                        else target_temperature + generator.uniform(-1.2, 1.2)
                    ),
                    recorded_at=end - timedelta(minutes=(11 - index) * 10),
                )
            )
    return readings


def seed(*, reset: bool, if_empty: bool) -> None:
    settings = Settings.from_environment()
    clients = DatabaseClients(settings)
    relational = RelationalRepository(clients)
    telemetry = TelemetryRepository(clients)

    try:
        _wait_for_databases(clients)
        relational.initialize_schema()
        telemetry.ensure_indexes()

        if reset:
            telemetry.clear()
            relational.clear()
            LOGGER.info("Dados anteriores removidos.")

        relational_is_empty = relational.count_vehicles() == 0
        telemetry_is_empty = not telemetry.has_data()
        if if_empty and not relational_is_empty and not telemetry_is_empty:
            LOGGER.info("Os bancos já possuem dados; nenhuma alteração foi feita.")
            return

        if relational_is_empty or not if_empty:
            relational.upsert_drivers(DRIVERS)
            relational.upsert_vehicles(VEHICLES)
        if telemetry_is_empty or not if_empty:
            telemetry.save_readings(build_demo_readings())

        LOGGER.info("Seed concluído: %d veículos e 36 leituras.", len(VEHICLES))
    finally:
        clients.close()


def _wait_for_databases(clients: DatabaseClients, attempts: int = 12) -> None:
    for attempt in range(1, attempts + 1):
        try:
            clients.ping()
            return
        except Exception as error:
            if attempt == attempts:
                raise ConnectionError("Os bancos não ficaram disponíveis a tempo.") from error
            LOGGER.info("Aguardando os bancos (%d/%d)...", attempt, attempts)
            time.sleep(2)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--reset", action="store_true", help="apaga e recria os dados de demonstração"
    )
    mode.add_argument(
        "--if-empty",
        action="store_true",
        help="insere dados apenas se os dois bancos estiverem vazios",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    arguments = parse_arguments()
    try:
        seed(reset=arguments.reset, if_empty=arguments.if_empty)
    except Exception:
        LOGGER.exception("Não foi possível preparar os dados.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
