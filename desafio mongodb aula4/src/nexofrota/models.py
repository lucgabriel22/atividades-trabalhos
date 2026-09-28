"""Modelos de domínio independentes da interface e dos bancos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class FleetAsset:
    vehicle_id: int
    plate: str
    model: str
    active: bool
    driver_id: int
    driver_name: str
    license_number: str
    driver_status: str


@dataclass(frozen=True)
class TelemetryReading:
    vehicle_id: int
    longitude: float
    latitude: float
    speed_kmh: float
    cargo_temperature_c: float
    recorded_at: datetime
    distance_km: float | None = None

    def __post_init__(self) -> None:
        if self.vehicle_id <= 0:
            raise ValueError("vehicle_id deve ser positivo.")
        if not -180 <= self.longitude <= 180:
            raise ValueError("Longitude fora do intervalo válido.")
        if not -90 <= self.latitude <= 90:
            raise ValueError("Latitude fora do intervalo válido.")
        if self.speed_kmh < 0:
            raise ValueError("Velocidade não pode ser negativa.")
        if self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at deve possuir fuso horário.")

    def to_document(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "location": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude],
            },
            "speed_kmh": round(self.speed_kmh, 2),
            "cargo_temperature_c": round(self.cargo_temperature_c, 2),
            "recorded_at": self.recorded_at.astimezone(UTC),
        }

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> TelemetryReading:
        longitude, latitude = document["location"]["coordinates"]
        recorded_at = document["recorded_at"]
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=UTC)
        distance_meters = document.get("distance_meters")
        return cls(
            vehicle_id=int(document["vehicle_id"]),
            longitude=float(longitude),
            latitude=float(latitude),
            speed_kmh=float(document["speed_kmh"]),
            cargo_temperature_c=float(document["cargo_temperature_c"]),
            recorded_at=recorded_at,
            distance_km=float(distance_meters) / 1000 if distance_meters is not None else None,
        )


@dataclass(frozen=True)
class FleetPosition:
    asset: FleetAsset
    telemetry: TelemetryReading | None

    @property
    def alert_labels(self) -> tuple[str, ...]:
        if self.telemetry is None:
            return ("Sem telemetria",)

        alerts: list[str] = []
        if self.telemetry.speed_kmh > 80:
            alerts.append("Excesso de velocidade")
        if self.telemetry.speed_kmh < 1:
            alerts.append("Veículo parado")
        if not -20 <= self.telemetry.cargo_temperature_c <= 8:
            alerts.append("Temperatura crítica")
        return tuple(alerts)

    @property
    def severity(self) -> str:
        return "alert" if self.alert_labels else "normal"
