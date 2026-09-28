"""Casos de uso que combinam os dois bancos de dados."""

from __future__ import annotations

from datetime import datetime

from nexofrota.models import FleetAsset, FleetPosition, TelemetryReading
from nexofrota.repositories.relational import RelationalRepository
from nexofrota.repositories.telemetry import TelemetryRepository


class FleetService:
    def __init__(
        self,
        relational: RelationalRepository,
        telemetry: TelemetryRepository,
    ) -> None:
        self._relational = relational
        self._telemetry = telemetry

    def overview(self) -> list[FleetPosition]:
        assets = self._relational.list_assets()
        telemetry_by_vehicle = self._telemetry.latest_by_vehicle()
        return [
            FleetPosition(asset=asset, telemetry=telemetry_by_vehicle.get(asset.vehicle_id))
            for asset in assets
        ]

    def positions_within_radius(
        self,
        *,
        longitude: float,
        latitude: float,
        radius_km: float,
    ) -> list[FleetPosition]:
        readings = self._telemetry.positions_within_radius(
            longitude=longitude,
            latitude=latitude,
            radius_km=radius_km,
        )
        return self._join_readings(readings)

    def nearest_positions(
        self,
        *,
        longitude: float,
        latitude: float,
        limit: int = 5,
    ) -> list[FleetPosition]:
        readings = self._telemetry.nearest_positions(
            longitude=longitude,
            latitude=latitude,
            limit=limit,
        )
        return self._join_readings(readings)

    def history(
        self,
        vehicle_ids: list[int],
        *,
        since: datetime | None = None,
    ) -> list[TelemetryReading]:
        return self._telemetry.history(vehicle_ids, since=since)

    def save_readings(self, readings: list[TelemetryReading]) -> int:
        return self._telemetry.save_readings(readings)

    def _join_readings(self, readings: list[TelemetryReading]) -> list[FleetPosition]:
        assets_by_id: dict[int, FleetAsset] = {
            asset.vehicle_id: asset for asset in self._relational.list_assets()
        }
        return [
            FleetPosition(asset=assets_by_id[reading.vehicle_id], telemetry=reading)
            for reading in readings
            if reading.vehicle_id in assets_by_id
        ]
