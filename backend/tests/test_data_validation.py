"""
Automated unit tests for Excel data loading and business validation in Atlas Fresh backend.
"""

from pathlib import Path
import pytest
import openpyxl
from fastapi.testclient import TestClient

from app.main import app
from app.data_loader import load_dataset, DataValidationError, DEFAULT_DATA_PATH


@pytest.fixture
def client() -> TestClient:
    """
    Create a FastAPI test client instance.

    Returns:
        TestClient: Initialized test client.
    """
    return TestClient(app)


def test_load_authoritative_dataset() -> None:
    """Verify that the official Excel workbook loads without any errors and matches exact baseline counts."""
    data = load_dataset()

    assert len(data.farms) == 20
    assert len(data.clients) == 10
    assert data.station.station_id == "STATION-01"
    assert data.station.export_conditioning_capacity_t == 500.0
    assert data.station.local_market_ratio == 0.10

    # Baseline quantity checks
    assert data.total_expected_capacity_t == 600.0
    assert data.total_actual_supply_t == 560.0
    assert data.actual_by_segment_t == {
        "A": 90.0,
        "B": 160.0,
        "C": 180.0,
        "D": 130.0,
    }


def test_api_get_data_endpoint(client: TestClient) -> None:
    """Verify that GET /api/data endpoint returns HTTP 200 with structured JSON."""
    response = client.get("/api/data")
    assert response.status_code == 200

    body = response.json()
    assert len(body["farms"]) == 20
    assert len(body["clients"]) == 10
    assert body["total_expected_capacity_t"] == 600.0
    assert body["total_actual_supply_t"] == 560.0
    assert body["actual_by_segment_t"]["A"] == 90.0
    assert body["actual_by_segment_t"]["B"] == 160.0
    assert body["actual_by_segment_t"]["C"] == 180.0
    assert body["actual_by_segment_t"]["D"] == 130.0


def test_validation_catches_invalid_mix_sum(tmp_path: Path) -> None:
    """Verify that a modified workbook with mix sum != 1.0 triggers DataValidationError."""
    wb = openpyxl.load_workbook(DEFAULT_DATA_PATH)
    sheet = wb["Farms"]
    # Alter F01 expected_A_pct to 0.95 (sum becomes 1.05)
    sheet.cell(5, 4).value = 0.95

    bad_file = tmp_path / "invalid_mix.xlsx"
    wb.save(bad_file)

    with pytest.raises(DataValidationError) as exc_info:
        load_dataset(bad_file)

    errors = exc_info.value.errors
    assert any("Mix percentages sum to" in err.message for err in errors)


def test_validation_catches_invalid_client_mode(tmp_path: Path) -> None:
    """Verify that an invalid client acceptance mode is rejected."""
    wb = openpyxl.load_workbook(DEFAULT_DATA_PATH)
    sheet = wb["Clients"]
    # Alter C01 acceptance_mode to INVALID_MODE
    sheet.cell(5, 3).value = "INVALID_MODE"

    bad_file = tmp_path / "invalid_mode.xlsx"
    wb.save(bad_file)

    with pytest.raises(DataValidationError) as exc_info:
        load_dataset(bad_file)

    errors = exc_info.value.errors
    assert any("Acceptance mode must be 'EXACT' or 'MINIMUM'" in err.message for err in errors)


def test_validation_catches_non_multiple_of_five(tmp_path: Path) -> None:
    """Verify that actual tonnes not in 5t multiples are flagged."""
    wb = openpyxl.load_workbook(DEFAULT_DATA_PATH)
    sheet = wb["Farms"]
    # Alter F01 actual_A_t to 23 (not a multiple of 5)
    sheet.cell(5, 8).value = 23

    bad_file = tmp_path / "invalid_multiples.xlsx"
    wb.save(bad_file)

    with pytest.raises(DataValidationError) as exc_info:
        load_dataset(bad_file)

    errors = exc_info.value.errors
    assert any("must be a multiple of 5" in err.message for err in errors)
