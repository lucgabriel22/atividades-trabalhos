from __future__ import annotations

import math
import random
from datetime import UTC, datetime

from nexofrota.models import TelemetryReading
from nexofrota.services.simulation import MovementSimulator


def haversine_km(first: TelemetryReading, second: TelemetryReading) -> float:
    earth_radius_km = 6371
    latitude_1 = math.radians(first.latitude)
    latitude_2 = math.radians(second.latitude)
    latitude_delta = latitude_2 - latitude_1
    longitude_delta = math.radians(second.longitude - first.longitude)
    coefficient = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1) * math.cos(latitude_2) * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_km * math.asin(math.sqrt(coefficient))


def test_simulated_movement_respects_limits() -> None:
    instant = datetime(2026, 9, 27, 13, tzinfo=UTC)
    previous = TelemetryReading(101, -46.6333, -23.5505, 60, 4, instant)
    simulator = MovementSimulator(2.5, random_source=random.Random(7))

    generated = simulator.next_reading(previous, recorded_at=instant)

    assert 0.1 < haversine_km(previous, generated) <= 2.55
    assert 0 <= generated.speed_kmh <= 120
    assert generated.recorded_at == instant


def test_batch_preserves_vehicle_count() -> None:
    instant = datetime(2026, 9, 27, 13, tzinfo=UTC)
    current = [
        TelemetryReading(vehicle_id, -46.63, -23.55, 40, 4, instant)
        for vehicle_id in (101, 102, 103)
    ]
    simulator = MovementSimulator(1.0, random_source=random.Random(9))

    generated = simulator.next_batch(current, recorded_at=instant)

    assert [reading.vehicle_id for reading in generated] == [101, 102, 103]
