"""Importa o retrato atual do mercado do Cartola FC para o MongoDB."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import requests
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.database import Database
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_database: str
    api_url: str

    @classmethod
    def from_environment(cls) -> Settings:
        load_dotenv()
        mongo_uri = os.getenv("MONGO_URI", "").strip()
        if not mongo_uri:
            raise ValueError("Defina MONGO_URI no ambiente ou no arquivo .env.")

        return cls(
            mongo_uri=mongo_uri,
            mongo_database=os.getenv("MONGO_DATABASE", "cartola_fc"),
            api_url=os.getenv(
                "CARTOLA_API_URL",
                "https://api.cartola.globo.com/atletas/mercado",
            ),
        )


@dataclass(frozen=True)
class MarketSnapshot:
    clubs: dict[str, dict[str, Any]]
    athletes: list[dict[str, Any]]
    statuses: dict[str, dict[str, Any]]

    @classmethod
    def from_payload(cls, payload: Any) -> MarketSnapshot:
        if not isinstance(payload, dict):
            raise ValueError("A API do Cartola retornou um conteúdo inesperado.")

        clubs = payload.get("clubes")
        athletes = payload.get("atletas")
        statuses = payload.get("status")
        if not isinstance(clubs, dict) or not isinstance(athletes, list):
            raise ValueError("A resposta não contém clubes e atletas no formato esperado.")
        if not isinstance(statuses, dict):
            statuses = {}
        if not all(isinstance(item, dict) for item in athletes):
            raise ValueError("A lista de atletas contém um registro inválido.")
        if not clubs or not athletes:
            raise ValueError("A API retornou um mercado vazio; a carga atual foi preservada.")

        return cls(clubs=clubs, athletes=athletes, statuses=statuses)


class CartolaClient:
    def __init__(self, api_url: str, *, timeout_seconds: float = 30) -> None:
        self._api_url = api_url
        self._timeout_seconds = timeout_seconds
        self._session = requests.Session()
        retry_policy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self._session.mount("https://", HTTPAdapter(max_retries=retry_policy))

    def fetch_market(self) -> MarketSnapshot:
        response = self._session.get(self._api_url, timeout=self._timeout_seconds)
        response.raise_for_status()
        return MarketSnapshot.from_payload(response.json())

    def close(self) -> None:
        self._session.close()


class MarketRepository:
    """Mantém somente o retrato mais recente do mercado nas coleções."""

    def __init__(self, database: Database[dict[str, Any]]) -> None:
        self._database = database

    def replace_current_snapshot(self, snapshot: MarketSnapshot) -> dict[str, int]:
        snapshot_id = str(uuid4())
        collected_at = datetime.now(UTC)

        club_count = self._upsert_clubs(snapshot, snapshot_id, collected_at)
        athlete_count = self._upsert_athletes(snapshot, snapshot_id, collected_at)
        self._save_market_metadata(snapshot, snapshot_id, collected_at)

        # A limpeza acontece apenas depois dos upserts bem-sucedidos.
        self._database.clubes_rodada_atual.delete_many({"snapshot_id": {"$ne": snapshot_id}})
        self._database.atletas_rodada_atual.delete_many({"snapshot_id": {"$ne": snapshot_id}})
        return {"clubes": club_count, "atletas": athlete_count}

    def _upsert_clubs(
        self,
        snapshot: MarketSnapshot,
        snapshot_id: str,
        collected_at: datetime,
    ) -> int:
        operations: list[UpdateOne] = []
        for raw_id, club in snapshot.clubs.items():
            if not isinstance(club, dict):
                raise ValueError(f"Clube {raw_id!r} possui formato inválido.")
            club_id = _integer_identifier(club.get("id", raw_id), label="clube")
            document = {
                **club,
                "_id": club_id,
                "snapshot_id": snapshot_id,
                "collected_at": collected_at,
            }
            operations.append(UpdateOne({"_id": club_id}, {"$set": document}, upsert=True))

        if operations:
            self._database.clubes_rodada_atual.bulk_write(operations, ordered=False)
        return len(operations)

    def _upsert_athletes(
        self,
        snapshot: MarketSnapshot,
        snapshot_id: str,
        collected_at: datetime,
    ) -> int:
        operations: list[UpdateOne] = []
        for athlete in snapshot.athletes:
            athlete_id = _integer_identifier(athlete.get("atleta_id"), label="atleta")
            document = {
                **athlete,
                "_id": athlete_id,
                "snapshot_id": snapshot_id,
                "collected_at": collected_at,
            }
            operations.append(UpdateOne({"_id": athlete_id}, {"$set": document}, upsert=True))

        if operations:
            self._database.atletas_rodada_atual.bulk_write(operations, ordered=False)
        return len(operations)

    def _save_market_metadata(
        self,
        snapshot: MarketSnapshot,
        snapshot_id: str,
        collected_at: datetime,
    ) -> None:
        rounds = {
            athlete["rodada_id"]
            for athlete in snapshot.athletes
            if athlete.get("rodada_id") is not None
        }
        document = {
            "_id": "atual",
            "snapshot_id": snapshot_id,
            "collected_at": collected_at,
            "rodada_id": next(iter(rounds)) if len(rounds) == 1 else None,
            "total_clubes": len(snapshot.clubs),
            "total_atletas": len(snapshot.athletes),
            "status_atletas": list(snapshot.statuses.values()),
        }
        self._database.mercado_rodada_atual.replace_one(
            {"_id": "atual"},
            document,
            upsert=True,
        )


def _integer_identifier(value: Any, *, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Registro de {label} sem identificador válido: {value!r}.") from error


def import_market(settings: Settings) -> dict[str, int]:
    mongo_client: MongoClient[dict[str, Any]] = MongoClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=10_000,
    )
    api_client = CartolaClient(settings.api_url)

    try:
        mongo_client.admin.command("ping")
        snapshot = api_client.fetch_market()
        repository = MarketRepository(mongo_client[settings.mongo_database])
        return repository.replace_current_snapshot(snapshot)
    finally:
        api_client.close()
        mongo_client.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        summary = import_market(Settings.from_environment())
    except (OSError, ValueError, requests.RequestException) as error:
        LOGGER.error("Importação interrompida: %s", error)
        return 1
    except Exception:
        LOGGER.exception("Falha inesperada durante a importação.")
        return 1

    LOGGER.info(
        "Mercado atualizado: %d clube(s) e %d atleta(s).",
        summary["clubes"],
        summary["atletas"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
