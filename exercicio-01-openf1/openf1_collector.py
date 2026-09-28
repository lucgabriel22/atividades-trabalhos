"""Importa dados de uma sessão da OpenF1 para o MongoDB."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import requests
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient, UpdateOne
from pymongo.database import Database
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    """Configuração da importação, carregada de variáveis de ambiente."""

    mongo_uri: str
    mongo_database: str
    api_url: str
    session_key: int
    meeting_key: int | None

    @classmethod
    def from_environment(cls) -> Settings:
        load_dotenv()
        mongo_uri = os.getenv("MONGO_URI", "").strip()
        if not mongo_uri:
            raise ValueError("Defina MONGO_URI no ambiente ou no arquivo .env.")

        meeting_key = os.getenv("OPENF1_MEETING_KEY", "").strip()
        return cls(
            mongo_uri=mongo_uri,
            mongo_database=os.getenv("MONGO_DATABASE", "openf1_data"),
            api_url=os.getenv("OPENF1_API_URL", "https://api.openf1.org/v1").rstrip("/"),
            session_key=_required_integer("OPENF1_SESSION_KEY", default=9159),
            meeting_key=int(meeting_key) if meeting_key else None,
        )


@dataclass(frozen=True)
class Resource:
    endpoint: str
    collection: str
    identity_fields: tuple[str, ...]


RESOURCES = (
    Resource("sessions", "sessions", ("session_key",)),
    Resource("drivers", "drivers", ("session_key", "driver_number")),
    Resource("laps", "laps", ("session_key", "driver_number", "lap_number")),
)


def _required_integer(name: str, *, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} deve ser um número inteiro.") from error


class OpenF1Client:
    """Cliente HTTP com timeout e repetição para falhas transitórias."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 30) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._session = requests.Session()
        retry_policy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self._session.mount("https://", HTTPAdapter(max_retries=retry_policy))

    def fetch(self, endpoint: str, params: dict[str, int]) -> list[dict[str, Any]]:
        response = self._session.get(
            f"{self._base_url}/{endpoint}",
            params=params,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise ValueError(f"Resposta inesperada do endpoint {endpoint!r}.")
        return payload

    def close(self) -> None:
        self._session.close()


class MongoRepository:
    """Persiste recursos da OpenF1 sem duplicar documentos."""

    def __init__(self, database: Database[dict[str, Any]]) -> None:
        self._database = database

    def ensure_indexes(self) -> None:
        for resource in RESOURCES:
            keys = [(field, ASCENDING) for field in resource.identity_fields]
            self._database[resource.collection].create_index(keys, unique=True)

    def upsert_many(self, resource: Resource, records: list[dict[str, Any]]) -> int:
        collected_at = datetime.now(UTC)
        operations: list[UpdateOne] = []

        for record in records:
            identity = self._identity_for(record, resource)
            document = {**record, "collected_at": collected_at}
            operations.append(UpdateOne(identity, {"$set": document}, upsert=True))

        if not operations:
            return 0

        self._database[resource.collection].bulk_write(operations, ordered=False)
        return len(operations)

    @staticmethod
    def _identity_for(record: dict[str, Any], resource: Resource) -> dict[str, Any]:
        missing = [field for field in resource.identity_fields if record.get(field) is None]
        if missing:
            fields = ", ".join(missing)
            raise ValueError(f"Registro de {resource.endpoint!r} sem chave obrigatória: {fields}.")
        return {field: record[field] for field in resource.identity_fields}


def collect(settings: Settings) -> dict[str, int]:
    """Executa a coleta completa e devolve a contagem por coleção."""

    mongo_client: MongoClient[dict[str, Any]] = MongoClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=10_000,
    )
    api_client = OpenF1Client(settings.api_url)

    try:
        mongo_client.admin.command("ping")
        repository = MongoRepository(mongo_client[settings.mongo_database])
        repository.ensure_indexes()
        imported: dict[str, int] = {}

        for resource in RESOURCES:
            params = {"session_key": settings.session_key}
            if resource.endpoint == "sessions" and settings.meeting_key is not None:
                params["meeting_key"] = settings.meeting_key

            records = api_client.fetch(resource.endpoint, params)
            imported[resource.collection] = repository.upsert_many(resource, records)
            LOGGER.info("%s: %d registro(s) processado(s)", resource.collection, len(records))

        return imported
    finally:
        api_client.close()
        mongo_client.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        summary = collect(Settings.from_environment())
    except (OSError, ValueError, requests.RequestException) as error:
        LOGGER.error("Importação interrompida: %s", error)
        return 1
    except Exception:
        LOGGER.exception("Falha inesperada durante a importação.")
        return 1

    LOGGER.info("Importação concluída: %s", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
