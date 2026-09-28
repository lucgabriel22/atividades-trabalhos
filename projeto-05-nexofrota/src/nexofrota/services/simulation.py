"""Geração controlada de novas leituras para demonstração."""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime

from nexofrota.models import TelemetryReading


class MovementSimulator:
    def __init__(
        self,
        max_step_km: float,
        *,
        random_source: random.Random | None = None,
    ) -> None:
        if max_step_km <= 0:
            raise ValueError("max_step_km deve ser maior que zero.")
        self._max_step_km = max_step_km
        self._random = random_source or random.Random()

    def next_reading(
        self,
        previous: TelemetryReading,
        *,
        recorded_at: datetime | None = None,
    ) -> TelemetryReading:
        angle = self._random.uniform(0, 2 * math.pi)
        distance_km = self._random.uniform(0.15, self._max_step_km)
        latitude_delta = math.sin(angle) * distance_km / 111.0
        longitude_scale = max(math.cos(math.radians(previous.latitude)), 0.1)
        longitude_delta = math.cos(angle) * distance_km / (111.0 * longitude_scale)

        speed_change = self._random.uniform(-12, 12)
        temperature_change = self._random.uniform(-0.8, 0.8)
        return TelemetryReading(
            vehicle_id=previous.vehicle_id,
            longitude=_wrap_longitude(previous.longitude + longitude_delta),
            latitude=_clamp(previous.latitude + latitude_delta, -90, 90),
            speed_kmh=max(0, min(previous.speed_kmh + speed_change, 120)),
            cargo_temperature_c=previous.cargo_temperature_c + temperature_change,
            recorded_at=recorded_at or datetime.now(UTC),
        )

    def next_batch(
        self,
        current_positions: list[TelemetryReading],
        *,
        recorded_at: datetime | None = None,
    ) -> list[TelemetryReading]:
        instant = recorded_at or datetime.now(UTC)
        return [self.next_reading(position, recorded_at=instant) for position in current_positions]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _wrap_longitude(value: float) -> float:
    return ((value + 180) % 360) - 180
