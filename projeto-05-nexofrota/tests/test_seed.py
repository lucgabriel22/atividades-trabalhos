from __future__ import annotations

from datetime import UTC, datetime

from nexofrota.seed import BASE_POSITIONS, build_demo_readings


def test_demo_seed_is_complete_and_deterministic() -> None:
    end = datetime(2026, 9, 27, 12, tzinfo=UTC)
    readings = build_demo_readings(end_at=end)

    assert len(readings) == 36
    assert {reading.vehicle_id for reading in readings} == {101, 102, 103}

    latest = {reading.vehicle_id: reading for reading in readings if reading.recorded_at == end}
    for vehicle_id, (longitude, latitude, speed, temperature) in BASE_POSITIONS.items():
        assert latest[vehicle_id].longitude == longitude
        assert latest[vehicle_id].latitude == latitude
        assert latest[vehicle_id].speed_kmh == speed
        assert latest[vehicle_id].cargo_temperature_c == temperature
