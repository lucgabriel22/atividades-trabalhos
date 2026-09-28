"""Acesso tipado e enxuto aos dados da OpenF1 no MongoDB."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.database import Database


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_database: str

    @classmethod
    def from_environment(cls) -> Settings:
        load_dotenv()
        mongo_uri = os.getenv("MONGO_URI", "").strip()
        if not mongo_uri:
            raise ValueError("Defina MONGO_URI no ambiente ou no arquivo .env.")
        return cls(
            mongo_uri=mongo_uri,
            mongo_database=os.getenv("MONGO_DATABASE", "openf1_data"),
        )


class F1Repository:
    def __init__(self, settings: Settings) -> None:
        self._client: MongoClient[dict[str, Any]] = MongoClient(
            settings.mongo_uri,
            serverSelectionTimeoutMS=10_000,
        )
        self._client.admin.command("ping")
        self._database: Database[dict[str, Any]] = self._client[settings.mongo_database]

    def available_years(self) -> list[int]:
        years = self._database.sessions.distinct("year", {"year": {"$type": "number"}})
        return sorted((int(year) for year in years), reverse=True)

    def sessions_for_year(self, year: int) -> list[dict[str, Any]]:
        projection = {
            "_id": 0,
            "session_key": 1,
            "meeting_name": 1,
            "session_name": 1,
            "session_type": 1,
            "country_name": 1,
            "circuit_short_name": 1,
            "date_start": 1,
            "date_end": 1,
        }
        return list(
            self._database.sessions.find({"year": year}, projection).sort("date_start", ASCENDING)
        )

    def drivers_for_session(self, session_key: int) -> list[dict[str, Any]]:
        projection = {
            "_id": 0,
            "driver_number": 1,
            "full_name": 1,
            "name_acronym": 1,
            "team_name": 1,
        }
        return list(
            self._database.drivers.find({"session_key": session_key}, projection).sort(
                "driver_number", ASCENDING
            )
        )

    def laps_for_drivers(
        self,
        session_key: int,
        driver_numbers: list[int],
    ) -> list[dict[str, Any]]:
        if not driver_numbers:
            return []

        projection = {
            "_id": 0,
            "driver_number": 1,
            "lap_number": 1,
            "lap_duration": 1,
            "duration_sector_1": 1,
            "duration_sector_2": 1,
            "duration_sector_3": 1,
            "is_pit_out_lap": 1,
            "date_start": 1,
        }
        query = {
            "session_key": session_key,
            "driver_number": {"$in": driver_numbers},
        }
        return list(
            self._database.laps.find(query, projection).sort(
                [("lap_number", ASCENDING), ("driver_number", ASCENDING)]
            )
        )


def session_label(session: dict[str, Any]) -> str:
    meeting = session.get("meeting_name") or "Evento"
    name = session.get("session_name") or session.get("session_type") or "Sessão"
    return f"{meeting} — {name} (#{session['session_key']})"


def driver_label(driver: dict[str, Any]) -> str:
    name = driver.get("full_name") or driver.get("name_acronym") or "Piloto"
    team = driver.get("team_name")
    suffix = f" · {team}" if team else ""
    return f"#{driver['driver_number']} {name}{suffix}"
