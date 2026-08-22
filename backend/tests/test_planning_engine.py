"""
Automated unit tests for the deterministic planning engine and invariants in Atlas Fresh.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.data_loader import load_dataset
from app.models import (
    Farm,
    Client,
    Station,
    DatasetResponse,
    QualitySegment,
    AcceptanceMode,
    ClientStatusEnum,
    PartialReasonEnum,
)
from app.planning_engine import run_planning_engine


@pytest.fixture
def test_client() -> TestClient:
    """
    Create a FastAPI test client instance.

    Returns:
        TestClient: Initialized test client.
    """
    return TestClient(app)


def test_official_baseline_metrics() -> None:
    """
    Verify that executing the planning engine on the authoritative dataset matches
    every single metric in the official baseline specification.
    """
    dataset = load_dataset()
    result = run_planning_engine(dataset)
    kpis = result.kpis

    # Top-level volume KPIs
    assert kpis.expected_plan_t == 600.0
    assert kpis.actual_received_t == 560.0
    assert kpis.station_capacity_t == 500.0
    assert kpis.actual_A_t == 90.0
    assert kpis.actual_B_t == 160.0
    assert kpis.actual_C_t == 180.0
    assert kpis.actual_D_t == 130.0

    # Output KPIs
    assert kpis.export_volume_t == 500.0
    assert kpis.local_volume_t == 60.0
    assert kpis.export_rate_pct == 89.3
    assert kpis.export_revenue_eur == 549500.0
    assert kpis.local_value_eur == 4500.0
    assert kpis.total_value_eur == 554000.0
    assert kpis.at_risk_clients == 3

    # Total conservation invariant: Export + Local = Total Actual
    assert kpis.export_volume_t + kpis.local_volume_t == kpis.actual_received_t


def test_official_client_fulfillment_statuses() -> None:
    """
    Verify exact fulfillment status and root cause reason for all 10 export clients.
    """
    dataset = load_dataset()
    result = run_planning_engine(dataset)
    status_map = {cs.client_id: cs for cs in result.client_statuses}

    # Verify 7 COMPLETE clients
    complete_ids = ["C01", "C03", "C04", "C05", "C06", "C07", "C10"]
    for c_id in complete_ids:
        assert status_map[c_id].status == ClientStatusEnum.COMPLETE
        assert status_map[c_id].allocated == status_map[c_id].demand
        assert status_map[c_id].remaining == 0.0
        assert status_map[c_id].reason is None

    # Verify 3 PARTIAL (at-risk) clients and their specific root causes
    c02 = status_map["C02"]
    assert c02.status == ClientStatusEnum.PARTIAL
    assert c02.demand == 50.0
    assert c02.allocated == 40.0
    assert c02.remaining == 10.0
    assert c02.reason == PartialReasonEnum.INSUFFICIENT_COMPATIBLE_SEGMENT.value

    c09 = status_map["C09"]
    assert c09.status == ClientStatusEnum.PARTIAL
    assert c09.demand == 50.0
    assert c09.allocated == 30.0
    assert c09.remaining == 20.0
    assert c09.reason == PartialReasonEnum.INSUFFICIENT_COMPATIBLE_SEGMENT.value

    c08 = status_map["C08"]
    assert c08.status == ClientStatusEnum.PARTIAL
    assert c08.demand == 50.0
    assert c08.allocated == 20.0
    assert c08.remaining == 30.0
    assert c08.reason == PartialReasonEnum.STATION_CAPACITY_REACHED.value


def test_invariants_and_five_tonne_increments() -> None:
    """
    Verify fundamental business invariants:
    - All allocations are strictly in 5t multiples.
    - No client receives more than demand_t.
    - No farm provides more than its actual delivery per segment.
    - Export revenue equals sum of (tonnes * client_price).
    """
    dataset = load_dataset()
    result = run_planning_engine(dataset)

    # Invariant: 5t increments
    for alloc in result.allocations:
        assert alloc.tonnes > 0
        assert alloc.tonnes % 5 == 0

    for local in result.local_details:
        assert local.tonnes > 0
        assert local.tonnes % 5 == 0

    # Invariant: No client exceeds demand
    client_totals: dict[str, float] = {}
    for alloc in result.allocations:
        client_totals[alloc.client_id] = client_totals.get(alloc.client_id, 0.0) + alloc.tonnes

    client_demands = {c.client_id: c.demand_t for c in dataset.clients}
    for c_id, tot_allocated in client_totals.items():
        assert tot_allocated <= client_demands[c_id]

    # Invariant: No farm segment exceeds actual
    farm_alloc_totals: dict[tuple[str, QualitySegment], float] = {}
    for alloc in result.allocations:
        key = (alloc.farm_id, alloc.segment)
        farm_alloc_totals[key] = farm_alloc_totals.get(key, 0.0) + alloc.tonnes

    for local in result.local_details:
        key = (local.farm_id, local.segment)
        farm_alloc_totals[key] = farm_alloc_totals.get(key, 0.0) + local.tonnes

    for farm in dataset.farms:
        assert farm_alloc_totals.get((farm.farm_id, QualitySegment.A), 0.0) == farm.actual_A_t
        assert farm_alloc_totals.get((farm.farm_id, QualitySegment.B), 0.0) == farm.actual_B_t
        assert farm_alloc_totals.get((farm.farm_id, QualitySegment.C), 0.0) == farm.actual_C_t
        assert farm_alloc_totals.get((farm.farm_id, QualitySegment.D), 0.0) == farm.actual_D_t


def test_exact_mode_strictly_rejects_other_segments() -> None:
    """
    Verify that an EXACT mode client never receives fruit outside its requested segment.
    """
    farm = Farm(
        farm_id="F01",
        farm_name="Test Farm",
        expected_daily_capacity_t=50.0,
        expected_A_pct=0.5,
        expected_B_pct=0.5,
        expected_C_pct=0.0,
        expected_D_pct=0.0,
        actual_A_t=25.0,
        actual_B_t=0.0,
        actual_C_t=0.0,
        actual_D_t=0.0,
    )
    # Client wants EXACT B, but only A is available
    client = Client(
        client_id="C_EXACT_B",
        client_name="Exact B Client",
        acceptance_mode=AcceptanceMode.EXACT,
        requested_segment=QualitySegment.B,
        demand_t=20.0,
        export_price_per_t_eur=1000.0,
    )
    station = Station(
        station_id="STATION-01",
        export_conditioning_capacity_t=500.0,
        local_market_ratio=0.10,
        reference_prices={"A": 1500.0, "B": 1250.0, "C": 1000.0, "D": 750.0},
    )
    custom_dataset = DatasetResponse(
        farms=[farm],
        clients=[client],
        station=station,
        total_expected_capacity_t=50.0,
        total_actual_supply_t=25.0,
        actual_by_segment_t={"A": 25.0, "B": 0.0, "C": 0.0, "D": 0.0},
    )

    result = run_planning_engine(custom_dataset)
    assert len(result.allocations) == 0
    assert result.client_statuses[0].status == ClientStatusEnum.UNSERVED
    assert result.client_statuses[0].reason == PartialReasonEnum.INSUFFICIENT_COMPATIBLE_SEGMENT.value
    assert result.kpis.export_volume_t == 0.0
    assert result.kpis.local_volume_t == 25.0


def test_minimum_mode_upgrades_quality_when_needed() -> None:
    """
    Verify that a MINIMUM mode client accepts a higher quality segment when exact is unavailable.
    """
    farm = Farm(
        farm_id="F01",
        farm_name="Test Farm",
        expected_daily_capacity_t=50.0,
        expected_A_pct=1.0,
        expected_B_pct=0.0,
        expected_C_pct=0.0,
        expected_D_pct=0.0,
        actual_A_t=25.0,
        actual_B_t=0.0,
        actual_C_t=0.0,
        actual_D_t=0.0,
    )
    # Client accepts MINIMUM B (accepts B or A), and only A is available
    client = Client(
        client_id="C_MIN_B",
        client_name="Min B Client",
        acceptance_mode=AcceptanceMode.MINIMUM,
        requested_segment=QualitySegment.B,
        demand_t=25.0,
        export_price_per_t_eur=1200.0,
    )
    station = Station(
        station_id="STATION-01",
        export_conditioning_capacity_t=500.0,
        local_market_ratio=0.10,
        reference_prices={"A": 1500.0, "B": 1250.0, "C": 1000.0, "D": 750.0},
    )
    custom_dataset = DatasetResponse(
        farms=[farm],
        clients=[client],
        station=station,
        total_expected_capacity_t=50.0,
        total_actual_supply_t=25.0,
        actual_by_segment_t={"A": 25.0, "B": 0.0, "C": 0.0, "D": 0.0},
    )

    result = run_planning_engine(custom_dataset)
    assert len(result.allocations) == 1
    alloc = result.allocations[0]
    assert alloc.segment == QualitySegment.A
    assert alloc.tonnes == 25.0
    assert alloc.quality_upgrade is True
    assert result.client_statuses[0].status == ClientStatusEnum.COMPLETE


def test_api_get_plan_endpoint(test_client: TestClient) -> None:
    """
    Verify that GET /api/plan returns HTTP 200 with the full validated plan result.
    """
    response = test_client.get("/api/plan")
    assert response.status_code == 200

    data = response.json()
    assert "kpis" in data
    assert "allocations" in data
    assert "client_statuses" in data
    assert "farm_summaries" in data
    assert "local_details" in data

    assert data["kpis"]["export_volume_t"] == 500.0
    assert data["kpis"]["local_volume_t"] == 60.0
    assert data["kpis"]["export_revenue_eur"] == 549500.0
    assert data["kpis"]["local_value_eur"] == 4500.0
    assert data["kpis"]["total_value_eur"] == 554000.0
    assert data["kpis"]["at_risk_clients"] == 3
    assert len(data["farm_summaries"]) == 20
    assert len(data["client_statuses"]) == 10
