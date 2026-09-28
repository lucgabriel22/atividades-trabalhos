from __future__ import annotations

from datetime import UTC, datetime

import pytest
from nexofrota.models import FleetAsset, FleetPosition, TelemetryReading


def make_asset() -> FleetAsset:
    return FleetAsset(
        vehicle_id=101,
        plate="NFX1A01",
        model="Volvo FH 540",
        active=True,
        driver_id=1,
        driver_name="Marina Costa",
        license_number="CNH-584102",
        driver_status="active",
    )


def make_reading(*, speed: float = 50, temperature: float = 4) -> TelemetryReading:
    return TelemetryReading(
        vehicle_id=101,
        longitude=-46.6333,
        latitude=-23.5505,
        speed_kmh=speed,
        cargo_temperature_c=temperature,
        recorded_at=datetime(2026, 9, 27, 12, tzinfo=UTC),
    )


def test_geojson_round_trip() -> None:
    original = make_reading()
    rebuilt = TelemetryReading.from_document(original.to_document())

    assert rebuilt == original
    assert original.to_document()["location"] == {
        "type": "Point",
        "coordinates": [-46.6333, -23.5505],
    }


@pytest.mark.parametrize(
    ("speed", "temperature", "expected"),
    [
        (50, 4, ()),
        (88, 4, ("Excesso de velocidade",)),
        (0, 18, ("Veículo parado", "Temperatura crítica")),
    ],
)
def test_alert_classification(speed: float, temperature: float, expected: tuple[str, ...]) -> None:
    position = FleetPosition(make_asset(), make_reading(speed=speed, temperature=temperature))
    assert position.alert_labels == expected


def test_rejects_invalid_coordinates() -> None:
    with pytest.raises(ValueError, match="Latitude"):
        TelemetryReading(
            vehicle_id=101,
            longitude=-46,
            latitude=100,
            speed_kmh=10,
            cargo_temperature_c=3,
            recorded_at=datetime.now(UTC),
        )
