"""Interface Streamlit da plataforma NexoFrota."""

from __future__ import annotations

import html
from datetime import UTC, datetime, timedelta

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from nexofrota.config import Settings
from nexofrota.db.connections import DatabaseClients
from nexofrota.models import FleetPosition, TelemetryReading
from nexofrota.repositories.relational import RelationalRepository
from nexofrota.repositories.telemetry import TelemetryRepository
from nexofrota.services.fleet import FleetService
from nexofrota.services.simulation import MovementSimulator
from streamlit_folium import st_folium


@st.cache_resource
def application_services() -> tuple[FleetService, MovementSimulator]:
    settings = Settings.from_environment()
    clients = DatabaseClients(settings)
    clients.ping()
    relational = RelationalRepository(clients)
    telemetry = TelemetryRepository(clients)
    telemetry.ensure_indexes()
    return FleetService(relational, telemetry), MovementSimulator(settings.simulation_max_step_km)


def fleet_map(
    positions: list[FleetPosition],
    *,
    latitude: float,
    longitude: float,
    radius_km: float,
) -> folium.Map:
    map_view = folium.Map(location=[latitude, longitude], zoom_start=11, control_scale=True)
    folium.Circle(
        location=[latitude, longitude],
        radius=radius_km * 1000,
        color="#2563eb",
        fill=True,
        fill_opacity=0.08,
        tooltip=f"Raio de {radius_km:.1f} km",
    ).add_to(map_view)

    for position in positions:
        reading = position.telemetry
        if reading is None:
            continue
        alerts = ", ".join(position.alert_labels) or "Operação normal"
        popup = (
            f"<b>{html.escape(position.asset.plate)}</b><br>"
            f"{html.escape(position.asset.model)}<br>"
            f"Motorista: {html.escape(position.asset.driver_name)}<br>"
            f"Velocidade: {reading.speed_kmh:.1f} km/h<br>"
            f"Temperatura: {reading.cargo_temperature_c:.1f} °C<br>"
            f"Situação: {html.escape(alerts)}"
        )
        folium.Marker(
            location=[reading.latitude, reading.longitude],
            popup=folium.Popup(popup, max_width=320),
            tooltip=f"{position.asset.plate} · {reading.speed_kmh:.0f} km/h",
            icon=folium.Icon(
                color="red" if position.severity == "alert" else "green",
                icon="truck",
                prefix="fa",
            ),
        ).add_to(map_view)
    return map_view


def overview_frame(positions: list[FleetPosition]) -> pd.DataFrame:
    rows = []
    for position in positions:
        reading = position.telemetry
        rows.append(
            {
                "Veículo": position.asset.vehicle_id,
                "Placa": position.asset.plate,
                "Modelo": position.asset.model,
                "Motorista": position.asset.driver_name,
                "Status do motorista": position.asset.driver_status,
                "Velocidade (km/h)": reading.speed_kmh if reading else None,
                "Temperatura (°C)": reading.cargo_temperature_c if reading else None,
                "Latitude": reading.latitude if reading else None,
                "Longitude": reading.longitude if reading else None,
                "Última leitura": reading.recorded_at if reading else None,
                "Alertas": ", ".join(position.alert_labels) or "Operação normal",
            }
        )
    return pd.DataFrame(rows)


def history_frame(readings: list[TelemetryReading]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Veículo": reading.vehicle_id,
                "Data": reading.recorded_at,
                "Velocidade (km/h)": reading.speed_kmh,
                "Temperatura (°C)": reading.cargo_temperature_c,
            }
            for reading in readings
        ]
    )


def render_metrics(positions: list[FleetPosition]) -> None:
    with_readings = [position for position in positions if position.telemetry]
    active = sum(position.asset.active for position in positions)
    speeding = sum(
        position.telemetry is not None and position.telemetry.speed_kmh > 80
        for position in positions
    )
    stopped = sum(
        position.telemetry is not None and position.telemetry.speed_kmh < 1
        for position in positions
    )
    average_temperature = (
        sum(position.telemetry.cargo_temperature_c for position in with_readings)
        / len(with_readings)
        if with_readings
        else 0
    )

    columns = st.columns(4)
    columns[0].metric("Frota ativa", active)
    columns[1].metric("Temperatura média", f"{average_temperature:.1f} °C")
    columns[2].metric("Acima de 80 km/h", speeding)
    columns[3].metric("Parados", stopped)


def main() -> None:
    st.set_page_config(page_title="NexoFrota", page_icon="🚚", layout="wide")
    st.title("🚚 NexoFrota")
    st.caption("Telemetria logística e persistência poliglota em uma visão operacional.")

    try:
        settings = Settings.from_environment()
        fleet_service, simulator = application_services()
        positions = fleet_service.overview()
    except Exception as error:
        st.error(f"Falha ao iniciar a aplicação: {error}")
        st.info("Confira o arquivo .env, inicie os bancos e execute o seed.")
        st.stop()

    if not positions:
        st.warning("Nenhum veículo cadastrado. Execute `python -m nexofrota.seed --if-empty`.")
        st.stop()

    st.sidebar.header("Área de consulta")
    latitude = st.sidebar.number_input(
        "Latitude", min_value=-90.0, max_value=90.0, value=settings.default_map_latitude
    )
    longitude = st.sidebar.number_input(
        "Longitude", min_value=-180.0, max_value=180.0, value=settings.default_map_longitude
    )
    radius_km = st.sidebar.slider(
        "Raio (km)", min_value=1, max_value=100, value=int(settings.default_radius_km)
    )

    if st.sidebar.button("Simular movimentação", type="primary", use_container_width=True):
        current = [position.telemetry for position in positions if position.telemetry is not None]
        created = fleet_service.save_readings(simulator.next_batch(current))
        st.toast(f"{created} nova(s) leitura(s) gravada(s).")
        st.rerun()

    render_metrics(positions)
    map_tab, overview_tab, dashboard_tab, history_tab = st.tabs(
        ["Mapa", "Visão geral", "Dashboard", "Histórico"]
    )

    with map_tab:
        nearby = fleet_service.positions_within_radius(
            longitude=longitude,
            latitude=latitude,
            radius_km=radius_km,
        )
        st.subheader(f"Veículos no raio: {len(nearby)}")
        st_folium(
            fleet_map(nearby, latitude=latitude, longitude=longitude, radius_km=radius_km),
            use_container_width=True,
            height=560,
        )
        nearest = fleet_service.nearest_positions(
            longitude=longitude,
            latitude=latitude,
            limit=5,
        )
        st.markdown("#### Mais próximos")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Placa": position.asset.plate,
                        "Motorista": position.asset.driver_name,
                        "Distância (km)": position.telemetry.distance_km,
                    }
                    for position in nearest
                    if position.telemetry
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

    with overview_tab:
        st.dataframe(overview_frame(positions), hide_index=True, use_container_width=True)

    with dashboard_tab:
        chart_data = overview_frame(positions)
        chart_columns = st.columns(2)
        with chart_columns[0]:
            st.plotly_chart(
                px.bar(
                    chart_data,
                    x="Placa",
                    y="Velocidade (km/h)",
                    color="Alertas",
                    title="Velocidade atual por veículo",
                ),
                use_container_width=True,
            )
        with chart_columns[1]:
            st.plotly_chart(
                px.bar(
                    chart_data,
                    x="Placa",
                    y="Temperatura (°C)",
                    color="Alertas",
                    title="Temperatura atual da carga",
                ),
                use_container_width=True,
            )

    with history_tab:
        labels = {
            f"{position.asset.plate} · {position.asset.model}": position.asset.vehicle_id
            for position in positions
        }
        selected_labels = st.multiselect("Veículos", labels, default=list(labels))
        hours = st.select_slider("Período", options=[1, 6, 12, 24, 48, 72], value=24)
        selected_ids = [labels[label] for label in selected_labels]
        readings = fleet_service.history(
            selected_ids,
            since=datetime.now(UTC) - timedelta(hours=hours),
        )
        frame = history_frame(readings)
        if frame.empty:
            st.info("Não há leituras no período selecionado.")
        else:
            temperature, speed = st.columns(2)
            with temperature:
                st.plotly_chart(
                    px.line(
                        frame,
                        x="Data",
                        y="Temperatura (°C)",
                        color="Veículo",
                        markers=True,
                        title="Histórico de temperatura",
                    ),
                    use_container_width=True,
                )
            with speed:
                st.plotly_chart(
                    px.line(
                        frame,
                        x="Data",
                        y="Velocidade (km/h)",
                        color="Veículo",
                        markers=True,
                        title="Histórico de velocidade",
                    ),
                    use_container_width=True,
                )


if __name__ == "__main__":
    main()
