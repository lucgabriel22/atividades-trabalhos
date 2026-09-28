"""NexoFrota: monitoramento geoespacial com SQLite e MongoDB."""

from __future__ import annotations

import html
import math
import os
import random
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, GEOSPHERE, MongoClient
from pymongo.database import Database
from streamlit_folium import st_folium

BASE_DIR = Path(__file__).resolve().parent

MOTORISTAS = (
    (1, "Carlos Andrade", "123456789", "Ativo"),
    (2, "Mariana Silva", "987654321", "Ativo"),
    (3, "Roberto Souza", "456789123", "Em Descanso"),
)

VEICULOS = (
    (101, "ABC-1A23", "Volvo FH 540", 1),
    (102, "XYZ-9876", "Scania R450", 2),
    (103, "KGB-4567", "Mercedes Actros", 3),
)

TELEMETRIA_INICIAL = (
    {
        "veiculo_id": 101,
        "localizacao": {"type": "Point", "coordinates": [-34.873, -7.115]},
        "temperatura": 4.2,
        "velocidade": 65.0,
        "timestamp": datetime(2026, 9, 11, 10, 0, tzinfo=UTC),
    },
    {
        "veiculo_id": 102,
        "localizacao": {"type": "Point", "coordinates": [-34.832, -7.121]},
        "temperatura": -18.5,
        "velocidade": 85.0,
        "timestamp": datetime(2026, 9, 11, 10, 5, tzinfo=UTC),
    },
    {
        "veiculo_id": 103,
        "localizacao": {"type": "Point", "coordinates": [-34.950, -7.150]},
        "temperatura": 22.0,
        "velocidade": 0.0,
        "timestamp": datetime(2026, 9, 11, 9, 45, tzinfo=UTC),
    },
)


@dataclass(frozen=True)
class Configuracao:
    """Configuração externa da aplicação."""

    mongo_uri: str
    mongo_database: str
    sqlite_path: Path
    latitude_inicial: float
    longitude_inicial: float
    raio_inicial_km: float

    @classmethod
    def carregar(cls) -> Configuracao:
        """Carrega valores do ambiente e aplica padrões seguros para uso local."""
        load_dotenv(BASE_DIR / ".env")
        caminho_sqlite = Path(os.getenv("SQLITE_PATH", "nexofrota.db"))
        if not caminho_sqlite.is_absolute():
            caminho_sqlite = BASE_DIR / caminho_sqlite

        return cls(
            mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
            mongo_database=os.getenv("MONGO_DATABASE", "nexofrota_db"),
            sqlite_path=caminho_sqlite,
            latitude_inicial=float(os.getenv("DEFAULT_MAP_LATITUDE", "-7.115")),
            longitude_inicial=float(os.getenv("DEFAULT_MAP_LONGITUDE", "-34.873")),
            raio_inicial_km=float(os.getenv("DEFAULT_RADIUS_KM", "10")),
        )


def conectar_sqlite(caminho: Path) -> sqlite3.Connection:
    """Abre o SQLite com integridade referencial e linhas nomeadas."""
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


@st.cache_resource(show_spinner=False)
def conectar_mongo(uri: str, nome_banco: str) -> tuple[MongoClient, Database]:
    """Cria e reutiliza a conexão MongoDB durante a sessão Streamlit."""
    cliente: MongoClient = MongoClient(uri, serverSelectionTimeoutMS=5_000)
    cliente.admin.command("ping")
    return cliente, cliente[nome_banco]


def inicializar_sqlite(caminho: Path) -> None:
    """Cria o modelo relacional e aplica o seed de forma idempotente."""
    with closing(conectar_sqlite(caminho)) as conexao, conexao:
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS motoristas (
                id INTEGER PRIMARY KEY,
                nome TEXT NOT NULL,
                cnh TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS veiculos (
                id INTEGER PRIMARY KEY,
                placa TEXT NOT NULL UNIQUE,
                modelo TEXT NOT NULL,
                motorista_id INTEGER NOT NULL,
                FOREIGN KEY (motorista_id) REFERENCES motoristas(id)
            );
            """
        )
        conexao.executemany(
            """
            INSERT INTO motoristas (id, nome, cnh, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                nome = excluded.nome,
                cnh = excluded.cnh,
                status = excluded.status
            """,
            MOTORISTAS,
        )
        conexao.executemany(
            """
            INSERT INTO veiculos (id, placa, modelo, motorista_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                placa = excluded.placa,
                modelo = excluded.modelo,
                motorista_id = excluded.motorista_id
            """,
            VEICULOS,
        )


def inicializar_mongo(banco: Database) -> None:
    """Cria índices e aplica a telemetria inicial sem duplicar documentos."""
    telemetria = banco["telemetria"]
    posicoes = banco["posicoes_atuais"]
    telemetria.create_index([("localizacao", GEOSPHERE)], name="localizacao_2dsphere")
    telemetria.create_index(
        [("veiculo_id", ASCENDING), ("timestamp", DESCENDING)],
        name="veiculo_timestamp",
    )
    posicoes.create_index([("localizacao", GEOSPHERE)], name="localizacao_2dsphere")

    for leitura in TELEMETRIA_INICIAL:
        chave = {
            "veiculo_id": leitura["veiculo_id"],
            "timestamp": leitura["timestamp"],
        }
        telemetria.update_one(chave, {"$setOnInsert": leitura}, upsert=True)
        posicoes.update_one(
            {"veiculo_id": leitura["veiculo_id"]},
            {"$setOnInsert": leitura},
            upsert=True,
        )


def listar_cadastros(caminho: Path) -> list[dict[str, Any]]:
    """Retorna veículos e motoristas já associados pelo modelo relacional."""
    consulta = """
        SELECT
            v.id AS veiculo_id,
            v.placa,
            v.modelo,
            m.nome AS motorista,
            m.status
        FROM veiculos AS v
        JOIN motoristas AS m ON m.id = v.motorista_id
        ORDER BY v.id
    """
    with closing(conectar_sqlite(caminho)) as conexao:
        return [dict(linha) for linha in conexao.execute(consulta).fetchall()]


def listar_posicoes(banco: Database) -> list[dict[str, Any]]:
    """Obtém uma posição atual por veículo."""
    return list(banco["posicoes_atuais"].find({}, {"_id": 0}).sort("veiculo_id", ASCENDING))


def buscar_no_raio(
    banco: Database,
    latitude: float,
    longitude: float,
    raio_km: float,
) -> list[dict[str, Any]]:
    """Busca posições atuais no raio informado com uma agregação geoespacial."""
    pipeline = [
        {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [longitude, latitude]},
                "distanceField": "distancia_m",
                "maxDistance": raio_km * 1_000,
                "spherical": True,
            }
        },
        {"$project": {"_id": 0}},
    ]
    return list(banco["posicoes_atuais"].aggregate(pipeline))


def listar_historico(banco: Database) -> list[dict[str, Any]]:
    """Retorna o histórico em ordem cronológica para os gráficos."""
    return list(
        banco["telemetria"]
        .find({}, {"_id": 0})
        .sort([("veiculo_id", ASCENDING), ("timestamp", ASCENDING)])
    )


def unir_dados(
    cadastros: list[dict[str, Any]],
    posicoes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combina em memória os cadastros SQLite e a última telemetria MongoDB."""
    cadastro_por_veiculo = {item["veiculo_id"]: item for item in cadastros}
    resultado: list[dict[str, Any]] = []

    for posicao in posicoes:
        cadastro = cadastro_por_veiculo.get(posicao["veiculo_id"])
        if cadastro is None:
            continue
        longitude, latitude = posicao["localizacao"]["coordinates"]
        resultado.append(
            {
                **cadastro,
                "temperatura": float(posicao["temperatura"]),
                "velocidade": float(posicao["velocidade"]),
                "latitude": float(latitude),
                "longitude": float(longitude),
                "timestamp": posicao["timestamp"],
                "distancia_km": (
                    float(posicao["distancia_m"]) / 1_000 if "distancia_m" in posicao else None
                ),
            }
        )

    return resultado


def simular_movimentacao(banco: Database) -> int:
    """Gera novas leituras próximas e atualiza histórico e posição atual."""
    gerador = random.SystemRandom()
    quantidade = 0

    for posicao in listar_posicoes(banco):
        longitude, latitude = posicao["localizacao"]["coordinates"]
        distancia_km = gerador.uniform(0.15, 1.2)
        angulo = gerador.uniform(0, 2 * math.pi)
        delta_latitude = (distancia_km / 111.0) * math.sin(angulo)
        fator_longitude = max(math.cos(math.radians(latitude)), 0.01)
        delta_longitude = (distancia_km / (111.0 * fator_longitude)) * math.cos(angulo)

        leitura = {
            "veiculo_id": posicao["veiculo_id"],
            "localizacao": {
                "type": "Point",
                "coordinates": [longitude + delta_longitude, latitude + delta_latitude],
            },
            "temperatura": round(float(posicao["temperatura"]) + gerador.uniform(-0.8, 0.8), 1),
            "velocidade": round(gerador.uniform(0, 100), 1),
            "timestamp": datetime.now(UTC),
        }
        banco["telemetria"].insert_one(leitura.copy())
        banco["posicoes_atuais"].replace_one(
            {"veiculo_id": leitura["veiculo_id"]},
            leitura.copy(),
            upsert=True,
        )
        quantidade += 1

    return quantidade


def criar_mapa(
    latitude: float,
    longitude: float,
    raio_km: float,
    veiculos: list[dict[str, Any]],
) -> folium.Map:
    """Monta o mapa, o raio de busca e os marcadores dos veículos."""
    mapa = folium.Map(location=[latitude, longitude], zoom_start=12, control_scale=True)
    folium.Circle(
        location=[latitude, longitude],
        radius=raio_km * 1_000,
        color="#2563eb",
        fill=True,
        fill_opacity=0.08,
        tooltip=f"Raio de {raio_km:.1f} km",
    ).add_to(mapa)
    folium.Marker(
        [latitude, longitude],
        tooltip="Ponto de referência",
        icon=folium.Icon(color="blue", icon="crosshairs", prefix="fa"),
    ).add_to(mapa)

    for veiculo in veiculos:
        alerta = veiculo["velocidade"] > 80
        distancia = veiculo.get("distancia_km")
        distancia_texto = f"{distancia:.2f} km" if distancia is not None else "não calculada"
        popup = (
            f"<strong>{html.escape(veiculo['placa'])}</strong><br>"
            f"Motorista: {html.escape(veiculo['motorista'])}<br>"
            f"Temperatura: {veiculo['temperatura']:.1f} °C<br>"
            f"Velocidade: {veiculo['velocidade']:.1f} km/h<br>"
            f"Distância: {distancia_texto}"
        )
        folium.Marker(
            [veiculo["latitude"], veiculo["longitude"]],
            tooltip=veiculo["placa"],
            popup=folium.Popup(popup, max_width=300),
            icon=folium.Icon(
                color="red" if alerta else "green",
                icon="truck",
                prefix="fa",
            ),
        ).add_to(mapa)

    return mapa


def criar_dataframe_unificado(dados: list[dict[str, Any]]) -> pd.DataFrame:
    """Formata a visão unificada com os campos exigidos no estudo de caso."""
    registros = [
        {
            "Motorista": item["motorista"],
            "Placa": item["placa"],
            "Última Temperatura": f"{item['temperatura']:.1f} °C",
            "Velocidade": f"{item['velocidade']:.1f} km/h",
            "Coordenadas Atualizadas": f"{item['latitude']:.6f}, {item['longitude']:.6f}",
        }
        for item in dados
    ]
    return pd.DataFrame(registros)


def renderizar_dashboard(
    configuracao: Configuracao,
    banco: Database,
) -> None:
    """Renderiza os controles, indicadores, mapa, tabela e gráficos."""
    cadastros = listar_cadastros(configuracao.sqlite_path)
    posicoes = listar_posicoes(banco)
    dados = unir_dados(cadastros, posicoes)

    st.sidebar.header("Busca geoespacial")
    latitude = st.sidebar.number_input(
        "Latitude de referência",
        value=configuracao.latitude_inicial,
        format="%.6f",
    )
    longitude = st.sidebar.number_input(
        "Longitude de referência",
        value=configuracao.longitude_inicial,
        format="%.6f",
    )
    raio_km = st.sidebar.slider(
        "Raio (km)",
        min_value=1.0,
        max_value=50.0,
        value=configuracao.raio_inicial_km,
        step=0.5,
    )

    if st.sidebar.button("Simular Movimentação", type="primary", use_container_width=True):
        total = simular_movimentacao(banco)
        st.sidebar.success(f"{total} posições atualizadas.")
        st.rerun()

    ativos = sum(1 for cadastro in cadastros if cadastro["status"] == "Ativo")
    temperatura_media = sum(item["temperatura"] for item in dados) / len(dados) if dados else 0
    alertas = sum(1 for item in dados if item["velocidade"] > 80)

    coluna_1, coluna_2, coluna_3 = st.columns(3)
    coluna_1.metric("Frota ativa", ativos)
    coluna_2.metric("Temperatura média", f"{temperatura_media:.1f} °C")
    coluna_3.metric("Alertas acima de 80 km/h", alertas)

    aba_mapa, aba_unificada, aba_dashboard = st.tabs(
        ["Veículos no raio", "Visão unificada", "Dashboard"]
    )

    with aba_mapa:
        proximos = unir_dados(
            cadastros,
            buscar_no_raio(banco, latitude, longitude, raio_km),
        )
        st.subheader(f"{len(proximos)} veículo(s) em até {raio_km:.1f} km")
        mapa = criar_mapa(latitude, longitude, raio_km, proximos)
        st_folium(mapa, use_container_width=True, height=520, returned_objects=[])

    with aba_unificada:
        st.subheader("Cadastro SQLite + última telemetria MongoDB")
        st.dataframe(
            criar_dataframe_unificado(dados),
            hide_index=True,
            use_container_width=True,
        )

    with aba_dashboard:
        historico = listar_historico(banco)
        placa_por_veiculo = {item["veiculo_id"]: item["placa"] for item in cadastros}
        registros_historico = [
            {
                "Placa": placa_por_veiculo.get(item["veiculo_id"], str(item["veiculo_id"])),
                "Data e hora": item["timestamp"],
                "Temperatura (°C)": item["temperatura"],
            }
            for item in historico
        ]
        figura_temperatura = px.line(
            pd.DataFrame(registros_historico),
            x="Data e hora",
            y="Temperatura (°C)",
            color="Placa",
            markers=True,
            title="Histórico de temperatura por veículo",
        )
        st.plotly_chart(figura_temperatura, use_container_width=True)

        distribuicao = (
            pd.DataFrame(cadastros)
            .groupby("status", as_index=False)
            .size()
            .rename(columns={"status": "Status", "size": "Motoristas"})
        )
        figura_status = px.pie(
            distribuicao,
            names="Status",
            values="Motoristas",
            hole=0.45,
            title="Distribuição do status dos motoristas",
        )
        st.plotly_chart(figura_status, use_container_width=True)


def main() -> None:
    """Inicializa as bases e executa a interface web."""
    st.set_page_config(page_title="NexoFrota", page_icon="🚚", layout="wide")
    st.title("NexoFrota")
    st.caption("Telemetria logística, geolocalização e persistência poliglota")

    configuracao = Configuracao.carregar()
    try:
        inicializar_sqlite(configuracao.sqlite_path)
        _, banco = conectar_mongo(configuracao.mongo_uri, configuracao.mongo_database)
        inicializar_mongo(banco)
        renderizar_dashboard(configuracao, banco)
    except (OSError, sqlite3.Error, ValueError) as erro:
        st.error(f"Não foi possível inicializar o SQLite: {erro}")
        st.stop()
    except Exception as erro:  # PyMongo expõe exceções específicas em tempo de execução.
        st.error(
            "Não foi possível conectar ao MongoDB. Verifique se o serviço está ativo "
            f"e revise o arquivo .env. Detalhes: {erro}"
        )
        st.stop()


if __name__ == "__main__":
    main()
