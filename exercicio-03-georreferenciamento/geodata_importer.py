"""Converte um CSV remoto em documentos GeoJSON e os grava no MongoDB."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import math
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import requests
from dotenv import load_dotenv
from pymongo import GEOSPHERE, MongoClient, UpdateOne
from pymongo.collection import Collection
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_database: str
    mongo_collection: str
    data_url: str
    latitude_column: str
    longitude_column: str

    @classmethod
    def from_environment(cls) -> Settings:
        load_dotenv()
        required = {
            "MONGO_URI": os.getenv("MONGO_URI", "").strip(),
            "DATA_URL": os.getenv("DATA_URL", "").strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Defina as variáveis obrigatórias: {', '.join(missing)}.")

        return cls(
            mongo_uri=required["MONGO_URI"],
            mongo_database=os.getenv("MONGO_DATABASE", "georreferenciamento"),
            mongo_collection=os.getenv("MONGO_COLLECTION", "unidades_basicas_saude"),
            data_url=required["DATA_URL"],
            latitude_column=os.getenv("LATITUDE_COLUMN", "latitude"),
            longitude_column=os.getenv("LONGITUDE_COLUMN", "longitude"),
        )


def download_csv(url: str, *, timeout_seconds: float = 30) -> str:
    session = requests.Session()
    retry_policy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry_policy))

    try:
        response = session.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        return response.text.removeprefix("\ufeff")
    finally:
        session.close()


def csv_to_geo_documents(
    content: str,
    *,
    latitude_column: str,
    longitude_column: str,
) -> list[dict[str, Any]]:
    """Valida as coordenadas e converte cada linha em um documento GeoJSON."""

    dialect = _detect_dialect(content)
    reader = csv.DictReader(io.StringIO(content), dialect=dialect)
    fieldnames = set(reader.fieldnames or [])
    missing = {latitude_column, longitude_column} - fieldnames
    if missing:
        raise ValueError(f"Coluna(s) ausente(s) no CSV: {', '.join(sorted(missing))}.")

    documents: list[dict[str, Any]] = []
    rejected_rows = 0
    for line_number, row in enumerate(reader, start=2):
        try:
            latitude = _coordinate(row.get(latitude_column), minimum=-90, maximum=90)
            longitude = _coordinate(row.get(longitude_column), minimum=-180, maximum=180)
        except ValueError as error:
            LOGGER.warning("Linha %d ignorada: %s", line_number, error)
            rejected_rows += 1
            continue

        properties = {key: value.strip() if value else "" for key, value in row.items() if key}
        document_id = _stable_identifier(properties)
        documents.append(
            {
                "_id": document_id,
                "properties": properties,
                "location": {
                    "type": "Point",
                    "coordinates": [longitude, latitude],
                },
            }
        )

    if not documents:
        raise ValueError("Nenhuma linha do CSV possui coordenadas válidas.")
    if rejected_rows:
        LOGGER.info("%d linha(s) inválida(s) foram descartadas.", rejected_rows)
    return documents


def _detect_dialect(content: str) -> type[csv.Dialect] | csv.Dialect:
    sample = content[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def _coordinate(raw_value: str | None, *, minimum: float, maximum: float) -> float:
    if raw_value is None or not raw_value.strip():
        raise ValueError("coordenada vazia")

    normalized = raw_value.strip().replace(",", ".")
    try:
        value = float(normalized)
    except ValueError as error:
        raise ValueError(f"coordenada inválida: {raw_value!r}") from error

    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"coordenada fora do intervalo: {raw_value!r}")
    return value


def _stable_identifier(properties: dict[str, str]) -> str:
    canonical = json.dumps(properties, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def replace_dataset(
    collection: Collection[dict[str, Any]],
    documents: list[dict[str, Any]],
) -> int:
    """Atualiza a carga e remove registros antigos somente após os upserts."""

    snapshot_id = str(uuid4())
    imported_at = datetime.now(UTC)
    operations = [
        UpdateOne(
            {"_id": document["_id"]},
            {"$set": {**document, "snapshot_id": snapshot_id, "imported_at": imported_at}},
            upsert=True,
        )
        for document in documents
    ]

    collection.bulk_write(operations, ordered=False)
    collection.create_index([("location", GEOSPHERE)])
    collection.delete_many({"snapshot_id": {"$ne": snapshot_id}})
    return len(documents)


def import_dataset(settings: Settings) -> int:
    content = download_csv(settings.data_url)
    documents = csv_to_geo_documents(
        content,
        latitude_column=settings.latitude_column,
        longitude_column=settings.longitude_column,
    )

    client: MongoClient[dict[str, Any]] = MongoClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=10_000,
    )
    try:
        client.admin.command("ping")
        collection = client[settings.mongo_database][settings.mongo_collection]
        return replace_dataset(collection, documents)
    finally:
        client.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        imported_count = import_dataset(Settings.from_environment())
    except (OSError, ValueError, requests.RequestException) as error:
        LOGGER.error("Importação interrompida: %s", error)
        return 1
    except Exception:
        LOGGER.exception("Falha inesperada durante a importação.")
        return 1

    LOGGER.info("Importação concluída: %d local(is).", imported_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
