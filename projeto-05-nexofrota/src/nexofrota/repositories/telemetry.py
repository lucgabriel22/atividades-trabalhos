"""Persistência e consultas geoespaciais de telemetria."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo import ASCENDING, DESCENDING, GEOSPHERE, ReplaceOne

from nexofrota.db.connections import DatabaseClients
from nexofrota.models import TelemetryReading


class TelemetryRepository:
    HISTORY_COLLECTION = "telemetry"
    CURRENT_COLLECTION = "current_positions"

    def __init__(self, clients: DatabaseClients) -> None:
        database = clients.mongo_database
        self._history = database[self.HISTORY_COLLECTION]
        self._current = database[self.CURRENT_COLLECTION]

    def ensure_indexes(self) -> None:
        self._history.create_index([("location", GEOSPHERE)])
        self._history.create_index(
            [("vehicle_id", ASCENDING), ("recorded_at", DESCENDING)],
            name="vehicle_recorded_at",
        )
        self._current.create_index([("location", GEOSPHERE)])
        self._current.create_index([("recorded_at", DESCENDING)])

    def save_readings(self, readings: list[TelemetryReading]) -> int:
        if not readings:
            return 0

        documents = [reading.to_document() for reading in readings]
        self._history.insert_many(documents, ordered=False)
        latest_by_vehicle: dict[int, TelemetryReading] = {}
        for reading in readings:
            current = latest_by_vehicle.get(reading.vehicle_id)
            if current is None or reading.recorded_at > current.recorded_at:
                latest_by_vehicle[reading.vehicle_id] = reading

        replacements = [
            ReplaceOne(
                {"_id": reading.vehicle_id},
                {"_id": reading.vehicle_id, **reading.to_document()},
                upsert=True,
            )
            for reading in latest_by_vehicle.values()
        ]
        self._current.bulk_write(replacements, ordered=False)
        return len(readings)

    def latest_by_vehicle(self) -> dict[int, TelemetryReading]:
        return {
            int(document["vehicle_id"]): TelemetryReading.from_document(document)
            for document in self._current.find({})
        }

    def positions_within_radius(
        self,
        *,
        longitude: float,
        latitude: float,
        radius_km: float,
        limit: int = 100,
    ) -> list[TelemetryReading]:
        pipeline: list[dict[str, Any]] = [
            {
                "$geoNear": {
                    "near": {"type": "Point", "coordinates": [longitude, latitude]},
                    "distanceField": "distance_meters",
                    "maxDistance": radius_km * 1000,
                    "spherical": True,
                }
            },
            {"$limit": limit},
        ]
        return [
            TelemetryReading.from_document(document)
            for document in self._current.aggregate(pipeline)
        ]

    def nearest_positions(
        self,
        *,
        longitude: float,
        latitude: float,
        limit: int = 5,
    ) -> list[TelemetryReading]:
        pipeline: list[dict[str, Any]] = [
            {
                "$geoNear": {
                    "near": {"type": "Point", "coordinates": [longitude, latitude]},
                    "distanceField": "distance_meters",
                    "spherical": True,
                }
            },
            {"$limit": limit},
        ]
        return [
            TelemetryReading.from_document(document)
            for document in self._current.aggregate(pipeline)
        ]

    def history(
        self,
        vehicle_ids: list[int],
        *,
        since: datetime | None = None,
        limit: int = 2000,
    ) -> list[TelemetryReading]:
        query: dict[str, Any] = {"vehicle_id": {"$in": vehicle_ids}}
        if since is not None:
            query["recorded_at"] = {"$gte": since}
        cursor = self._history.find(query).sort("recorded_at", ASCENDING).limit(limit)
        return [TelemetryReading.from_document(document) for document in cursor]

    def has_data(self) -> bool:
        return self._current.find_one({}, {"_id": 1}) is not None

    def clear(self) -> None:
        self._history.delete_many({})
        self._current.delete_many({})
