"""Configuração central da aplicação."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    postgres_host: str
    postgres_port: int
    postgres_database: str
    postgres_user: str
    postgres_password: str
    mongo_uri: str
    mongo_database: str
    default_map_latitude: float
    default_map_longitude: float
    default_radius_km: float
    simulation_max_step_km: float

    @classmethod
    def from_environment(cls) -> Settings:
        load_dotenv()
        required = {
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "").strip(),
            "MONGO_URI": os.getenv("MONGO_URI", "").strip(),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Variáveis obrigatórias ausentes: {', '.join(missing)}.")

        settings = cls(
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=_integer("POSTGRES_PORT", 5433),
            postgres_database=os.getenv("POSTGRES_DATABASE", "nexofrota"),
            postgres_user=os.getenv("POSTGRES_USER", "nexofrota"),
            postgres_password=required["POSTGRES_PASSWORD"],
            mongo_uri=required["MONGO_URI"],
            mongo_database=os.getenv("MONGO_DATABASE", "nexofrota"),
            default_map_latitude=_floating("DEFAULT_MAP_LATITUDE", -23.5505),
            default_map_longitude=_floating("DEFAULT_MAP_LONGITUDE", -46.6333),
            default_radius_km=_floating("DEFAULT_RADIUS_KM", 25.0),
            simulation_max_step_km=_floating("SIMULATION_MAX_STEP_KM", 2.5),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not -90 <= self.default_map_latitude <= 90:
            raise ValueError("DEFAULT_MAP_LATITUDE está fora do intervalo válido.")
        if not -180 <= self.default_map_longitude <= 180:
            raise ValueError("DEFAULT_MAP_LONGITUDE está fora do intervalo válido.")
        if self.default_radius_km <= 0 or self.simulation_max_step_km <= 0:
            raise ValueError("Raios e deslocamentos devem ser maiores que zero.")

    @property
    def postgres_kwargs(self) -> dict[str, str | int]:
        return {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "dbname": self.postgres_database,
            "user": self.postgres_user,
            "password": self.postgres_password,
        }


def _integer(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} deve ser um número inteiro.") from error


def _floating(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        return float(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} deve ser um número.") from error
