"""
Automated unit tests for the deterministic planning engine, allocation ordering, quality rules, and hard limits.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.data_loader import load_dataset, DataValidationError
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

client = TestClient(app)


def safe_load_dataset():
    """Safely load dataset or fail with a clear assertion message if Excel validation fails."""
    try:
        return load_dataset()
    except DataValidationError as exc:
        err_msgs = [f"{e.sheet}/{e.entity_id or 'General'}: {e.message}" for e in exc.errors]
        raise pytest.fail(f"Excel dataset validation failed: {err_msgs}") from None


def test_allocation_policy_ordering_and_compatibility():
    """Verify export price priority ordering, tie-breaking, EXACT mode rejection, and MINIMUM quality upgrades."""
    # 1. Test EXACT vs MINIMUM grade compatibility rules
    farm = Farm(
        farm_id="F01", farm_name="Test Farm", expected_daily_capacity_t=50.0,
        expected_A_pct=1.0, expected_B_pct=0.0, expected_C_pct=0.0, expected_D_pct=0.0,
        actual_A_t=25.0, actual_B_t=0.0, actual_C_t=0.0, actual_D_t=0.0,
    )
    exact_b_client = Client(
        client_id="C02", client_name="Exact B Client", acceptance_mode=AcceptanceMode.EXACT,
        requested_segment=QualitySegment.B, demand_t=20.0, export_price_per_t_eur=1000.0,
    )
    min_b_client = Client(
        client_id="C01", client_name="Min B Client", acceptance_mode=AcceptanceMode.MINIMUM,
        requested_segment=QualitySegment.B, demand_t=25.0, export_price_per_t_eur=1200.0,
    )
    station = Station(
        station_id="STATION-01", export_conditioning_capacity_t=500.0, local_market_ratio=0.10,
        reference_prices={"A": 1500.0, "B": 1250.0, "C": 1000.0, "D": 750.0},
    )
    dataset = DatasetResponse(
        farms=[farm], clients=[min_b_client, exact_b_client], station=station,
        total_expected_capacity_t=50.0, total_actual_supply_t=25.0,
        actual_by_segment_t={"A": 25.0, "B": 0.0, "C": 0.0, "D": 0.0},
    )

    result = run_planning_engine(dataset)
    # Higher price C01 MINIMUM B receives 25t of Segment A as a quality upgrade
    assert len(result.allocations) == 1
    assert result.allocations[0].client_id == "C01"
    assert result.allocations[0].segment == QualitySegment.A
    assert result.allocations[0].quality_upgrade is True

    # Lower price C02 EXACT B receives 0t and status UNSERVED (EXACT rejects A)
    status_map = {cs.client_id: cs for cs in result.client_statuses}
    assert status_map["C01"].status == ClientStatusEnum.COMPLETE
    assert status_map["C02"].status == ClientStatusEnum.UNSERVED
    assert status_map["C02"].reason == PartialReasonEnum.INSUFFICIENT_COMPATIBLE_SEGMENT.value


def test_hard_limits_invariants_and_local_residuals():
    """Verify station capacity ceiling, 5t multiple allocations, local market recovery, and GET /api/plan endpoint."""
    dataset = safe_load_dataset()
    result = run_planning_engine(dataset)
    kpis = result.kpis

    # Invariants
    assert kpis.export_volume_t <= kpis.station_capacity_t
    assert kpis.export_volume_t + kpis.local_volume_t == kpis.actual_received_t
    assert kpis.total_value_eur == kpis.export_revenue_eur + kpis.local_value_eur
    assert kpis.at_risk_clients == sum(1 for cs in result.client_statuses if cs.status.value != "COMPLETE")

    # 5t increments invariant
    for alloc in result.allocations:
        assert alloc.tonnes > 0 and alloc.tonnes % 5 == 0
    for local in result.local_details:
        assert local.tonnes > 0 and local.tonnes % 5 == 0

    # Local valuation check (10% reference price)
    for ld in result.local_details:
        expected_val = ld.tonnes * dataset.station.local_market_ratio * ld.reference_price
        assert abs(ld.local_value - expected_val) < 1e-4

    # API Endpoint check
    resp = client.get("/api/plan")
    assert resp.status_code == 200, f"GET /api/plan failed ({resp.status_code}): {resp.json()}"
    data = resp.json()
    assert "kpis" in data and "allocations" in data
