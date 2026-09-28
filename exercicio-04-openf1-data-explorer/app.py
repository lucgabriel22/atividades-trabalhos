"""Painel Streamlit para comparar tempos de volta da OpenF1."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from database import F1Repository, Settings, driver_label, session_label


@st.cache_resource
def get_repository() -> F1Repository:
    return F1Repository(Settings.from_environment())


@st.cache_data(ttl=60)
def load_years(_repository: F1Repository) -> list[int]:
    return _repository.available_years()


@st.cache_data(ttl=60)
def load_sessions(_repository: F1Repository, year: int) -> list[dict[str, Any]]:
    return _repository.sessions_for_year(year)


@st.cache_data(ttl=60)
def load_drivers(_repository: F1Repository, session_key: int) -> list[dict[str, Any]]:
    return _repository.drivers_for_session(session_key)


@st.cache_data(ttl=60)
def load_laps(
    _repository: F1Repository,
    session_key: int,
    driver_numbers: tuple[int, ...],
) -> list[dict[str, Any]]:
    return _repository.laps_for_drivers(session_key, list(driver_numbers))


def render_session_details(session: dict[str, Any]) -> None:
    st.subheader("Detalhes da sessão")
    country, circuit, start = st.columns(3)
    country.metric("País", session.get("country_name") or "—")
    circuit.metric("Circuito", session.get("circuit_short_name") or "—")
    start.metric("Início", _format_datetime(session.get("date_start")))


def _format_datetime(value: Any) -> str:
    if not value:
        return "—"
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return str(value)
    return parsed.strftime("%d/%m/%Y %H:%M UTC")


def render_lap_comparison(
    repository: F1Repository,
    session_key: int,
    selected_numbers: tuple[int, ...],
) -> None:
    laps = load_laps(repository, session_key, selected_numbers)
    if not laps:
        st.warning("Nenhuma volta foi encontrada para a seleção.")
        return

    frame = pd.DataFrame(laps)
    required_columns = {"lap_number", "lap_duration", "driver_number"}
    if not required_columns.issubset(frame.columns):
        st.error("Os documentos de voltas não possuem todos os campos esperados.")
        return

    chart_data = frame[list(required_columns)].copy()
    chart_data["lap_duration"] = pd.to_numeric(chart_data["lap_duration"], errors="coerce")
    chart_data["lap_number"] = pd.to_numeric(chart_data["lap_number"], errors="coerce")
    chart_data = chart_data.dropna(subset=["lap_number", "lap_duration"])

    if chart_data.empty:
        st.warning("As voltas encontradas não possuem duração válida para o gráfico.")
        return

    st.subheader("Duração por volta")
    pivot = chart_data.pivot_table(
        index="lap_number",
        columns="driver_number",
        values="lap_duration",
        aggfunc="first",
    ).sort_index()
    st.line_chart(pivot, x_label="Volta", y_label="Duração (s)")

    fastest = (
        chart_data.groupby("driver_number", as_index=False)["lap_duration"]
        .min()
        .rename(columns={"driver_number": "Piloto", "lap_duration": "Melhor volta (s)"})
    )
    st.dataframe(fastest, hide_index=True, use_container_width=True)

    with st.expander("Ver todas as voltas"):
        st.dataframe(frame, hide_index=True, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="OpenF1 Explorer", page_icon="🏁", layout="wide")
    st.title("🏁 OpenF1 Explorer")
    st.caption("Compare os tempos de volta armazenados no MongoDB.")

    try:
        repository = get_repository()
        years = load_years(repository)
    except Exception as error:
        st.error(f"Não foi possível conectar ao MongoDB: {error}")
        st.stop()

    if not years:
        st.info("Nenhuma sessão foi encontrada. Execute primeiro o exercício 01.")
        st.stop()

    selected_year = st.sidebar.selectbox("Temporada", years)
    sessions = load_sessions(repository, selected_year)
    if not sessions:
        st.info("Não há sessões para a temporada selecionada.")
        st.stop()

    sessions_by_label = {session_label(session): session for session in sessions}
    selected_session_label = st.sidebar.selectbox("Sessão", sessions_by_label)
    selected_session = sessions_by_label[selected_session_label]
    session_key = int(selected_session["session_key"])

    render_session_details(selected_session)
    drivers = load_drivers(repository, session_key)
    drivers_by_label = {driver_label(driver): int(driver["driver_number"]) for driver in drivers}
    selected_driver_labels = st.multiselect(
        "Pilotos",
        drivers_by_label,
        placeholder="Selecione um ou mais pilotos",
    )
    selected_numbers = tuple(drivers_by_label[label] for label in selected_driver_labels)

    if selected_numbers:
        render_lap_comparison(repository, session_key, selected_numbers)
    else:
        st.info("Selecione ao menos um piloto para exibir as voltas.")


if __name__ == "__main__":
    main()
