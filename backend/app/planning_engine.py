"""
Deterministic planning engine for the Atlas Fresh export allocation system.

Implements the official business rules:
- Highest-paying clients served first (tie-breaker: client_id alphabetical).
- Segment compatibility: EXACT match only, or MINIMUM (exact match preferred, then lowest upgrade).
- Hard packing station capacity constraint (500t max export).
- 5t incremental allocation chunks.
- Remaining fruit routed to local market at 10% reference price.
"""

from typing import Optional
from app.models import (
    Farm,
    Client,
    Station,
    DatasetResponse,
    QualitySegment,
    AcceptanceMode,
    ClientStatusEnum,
    PartialReasonEnum,
    Allocation,
    ClientStatus,
    FarmSummary,
    LocalDetail,
    KPIs,
    PlanResult,
)

# Quality grades rank: A is highest (3), D is lowest (0)
SEGMENT_RANKS: dict[QualitySegment, int] = {
    QualitySegment.D: 0,
    QualitySegment.C: 1,
    QualitySegment.B: 2,
    QualitySegment.A: 3,
}

ALL_SEGMENTS: list[QualitySegment] = [
    QualitySegment.A,
    QualitySegment.B,
    QualitySegment.C,
    QualitySegment.D,
]


def _build_supply_pool(farms: list[Farm]) -> dict[tuple[str, QualitySegment], float]:
    """
    Build a mutable supply pool tracking available actual tonnes per farm and segment.

    Args:
        farms (list[Farm]): Validated list of 20 farm objects.

    Returns:
        dict[tuple[str, QualitySegment], float]: Mapping of (farm_id, segment) to available tonnes.
    """
    pool: dict[tuple[str, QualitySegment], float] = {}
    for farm in farms:
        pool[(farm.farm_id, QualitySegment.A)] = farm.actual_A_t
        pool[(farm.farm_id, QualitySegment.B)] = farm.actual_B_t
        pool[(farm.farm_id, QualitySegment.C)] = farm.actual_C_t
        pool[(farm.farm_id, QualitySegment.D)] = farm.actual_D_t
    return pool


def _get_compatible_candidate_keys(
    farms: list[Farm],
    client: Client,
) -> list[tuple[int, str, QualitySegment]]:
    """
    Generate sorted candidate supply keys for a client based on quality compatibility and tie-breakers.

    Sorting hierarchy:
    1. Upgrade distance ascending (0 = exact match first, 1 = one grade up, etc.)
    2. Farm ID ascending (F01, F02, ... for determinism)

    Args:
        farms (list[Farm]): List of farms.
        client (Client): The client being fulfilled.

    Returns:
        list[tuple[int, str, QualitySegment]]: List of (upgrade_distance, farm_id, segment).
    """
    req_seg = client.requested_segment
    req_rank = SEGMENT_RANKS[req_seg]

    # Filter compatible segments
    if client.acceptance_mode == AcceptanceMode.EXACT:
        compatible_segs = [req_seg]
    else:
        # MINIMUM: requested segment or better
        compatible_segs = [seg for seg in ALL_SEGMENTS if SEGMENT_RANKS[seg] >= req_rank]

    candidate_keys: list[tuple[int, str, QualitySegment]] = []
    sorted_farms = sorted(farms, key=lambda f: f.farm_id)

    for seg in compatible_segs:
        upgrade_distance = SEGMENT_RANKS[seg] - req_rank
        for farm in sorted_farms:
            candidate_keys.append((upgrade_distance, farm.farm_id, seg))

    # Sort strictly by upgrade distance first, then farm_id
    candidate_keys.sort(key=lambda item: (item[0], item[1]))
    return candidate_keys


def _allocate_for_client(
    client: Client,
    farms: list[Farm],
    supply_pool: dict[tuple[str, QualitySegment], float],
    remaining_capacity: float,
) -> tuple[list[Allocation], float, float]:
    """
    Allocate tonnes from the supply pool to a single client within capacity and demand limits.

    Args:
        client (Client): Client requesting fruit.
        farms (list[Farm]): List of farms.
        supply_pool (dict[tuple[str, QualitySegment], float]): Mutable supply pool.
        remaining_capacity (float): Remaining station export capacity in tonnes.

    Returns:
        tuple[list[Allocation], float, float]: New allocations, total tonnes allocated to client,
        and updated remaining station capacity.
    """
    candidate_keys = _get_compatible_candidate_keys(farms, client)
    remaining_demand = client.demand_t
    allocated_to_client = 0.0
    allocations: list[Allocation] = []

    for upgrade_dist, farm_id, seg in candidate_keys:
        if remaining_demand <= 0 or remaining_capacity <= 0:
            break

        available = supply_pool.get((farm_id, seg), 0.0)
        if available <= 0:
            continue

        # Invariant: 5t multiple allocation constrained by demand, supply, and station capacity
        alloc_qty = min(remaining_demand, available, remaining_capacity)
        if alloc_qty > 0:
            supply_pool[(farm_id, seg)] -= alloc_qty
            remaining_demand -= alloc_qty
            remaining_capacity -= alloc_qty
            allocated_to_client += alloc_qty

            allocations.append(Allocation(
                farm_id=farm_id,
                segment=seg,
                client_id=client.client_id,
                tonnes=alloc_qty,
                quality_upgrade=(upgrade_dist > 0),
                export_revenue=alloc_qty * client.export_price_per_t_eur,
            ))

    return allocations, allocated_to_client, remaining_capacity


def _evaluate_client_status(
    client: Client,
    allocated_tonnes: float,
    remaining_capacity: float,
) -> ClientStatus:
    """
    Determine fulfillment status and root cause reason for a client.

    Args:
        client (Client): The client evaluated.
        allocated_tonnes (float): Total tonnes successfully allocated.
        remaining_capacity (float): Remaining station capacity at evaluation time.

    Returns:
        ClientStatus: Summary status with root cause if not COMPLETE.
    """
    demand = client.demand_t
    remaining = demand - allocated_tonnes
    revenue = allocated_tonnes * client.export_price_per_t_eur

    if allocated_tonnes >= demand:
        return ClientStatus(
            client_id=client.client_id,
            client_name=client.client_name,
            demand=demand,
            allocated=allocated_tonnes,
            remaining=0.0,
            revenue=revenue,
            status=ClientStatusEnum.COMPLETE,
            reason=None,
        )

    # Partial or unserved
    status_enum = ClientStatusEnum.PARTIAL if allocated_tonnes > 0 else ClientStatusEnum.UNSERVED
    if remaining_capacity <= 0:
        reason_str = PartialReasonEnum.STATION_CAPACITY_REACHED.value
    else:
        reason_str = PartialReasonEnum.INSUFFICIENT_COMPATIBLE_SEGMENT.value

    return ClientStatus(
        client_id=client.client_id,
        client_name=client.client_name,
        demand=demand,
        allocated=allocated_tonnes,
        remaining=remaining,
        revenue=revenue,
        status=status_enum,
        reason=reason_str,
    )


def _compute_local_residuals(
    supply_pool: dict[tuple[str, QualitySegment], float],
    station: Station,
) -> list[LocalDetail]:
    """
    Calculate local residual tonnes and valuation for all unexported fruit.

    Args:
        supply_pool (dict[tuple[str, QualitySegment], float]): Remaining supply pool after exports.
        station (Station): Packing station parameters and reference pricing.

    Returns:
        list[LocalDetail]: Breakdown of local residual fruit per farm and segment.
    """
    local_details: list[LocalDetail] = []
    sorted_items = sorted(supply_pool.items(), key=lambda item: (item[0][0], SEGMENT_RANKS[item[0][1]]))

    for (farm_id, seg), residual_t in sorted_items:
        if residual_t > 0:
            ref_price = station.reference_prices.get(seg.value, 0.0)
            local_val = residual_t * station.local_market_ratio * ref_price
            local_details.append(LocalDetail(
                farm_id=farm_id,
                segment=seg,
                tonnes=residual_t,
                reference_price=ref_price,
                local_value=local_val,
            ))

    return local_details


def _build_farm_summaries(
    farms: list[Farm],
    supply_pool: dict[tuple[str, QualitySegment], float],
) -> list[FarmSummary]:
    """
    Calculate production variances and local residual totals for all farms.

    Args:
        farms (list[Farm]): List of farms with planned and actual production.
        supply_pool (dict[tuple[str, QualitySegment], float]): Residual supply pool after exports.

    Returns:
        list[FarmSummary]: Detailed production summaries for all 20 farms.
    """
    summaries: list[FarmSummary] = []
    sorted_farms = sorted(farms, key=lambda f: f.farm_id)

    for farm in sorted_farms:
        exp_a = farm.expected_daily_capacity_t * farm.expected_A_pct
        exp_b = farm.expected_daily_capacity_t * farm.expected_B_pct
        exp_c = farm.expected_daily_capacity_t * farm.expected_C_pct
        exp_d = farm.expected_daily_capacity_t * farm.expected_D_pct

        act_total = farm.actual_total_t
        var_total = act_total - farm.expected_daily_capacity_t

        local_t = (
            supply_pool.get((farm.farm_id, QualitySegment.A), 0.0)
            + supply_pool.get((farm.farm_id, QualitySegment.B), 0.0)
            + supply_pool.get((farm.farm_id, QualitySegment.C), 0.0)
            + supply_pool.get((farm.farm_id, QualitySegment.D), 0.0)
        )

        summaries.append(FarmSummary(
            farm_id=farm.farm_id,
            farm_name=farm.farm_name,
            expected_capacity=farm.expected_daily_capacity_t,
            actual_total=act_total,
            variance_total=var_total,
            expected_A=exp_a,
            actual_A=farm.actual_A_t,
            variance_A=farm.actual_A_t - exp_a,
            expected_B=exp_b,
            actual_B=farm.actual_B_t,
            variance_B=farm.actual_B_t - exp_b,
            expected_C=exp_c,
            actual_C=farm.actual_C_t,
            variance_C=farm.actual_C_t - exp_c,
            expected_D=exp_d,
            actual_D=farm.actual_D_t,
            variance_D=farm.actual_D_t - exp_d,
            local_residual_t=local_t,
        ))

    return summaries


def _calculate_kpis(
    dataset: DatasetResponse,
    allocations: list[Allocation],
    local_details: list[LocalDetail],
    client_statuses: list[ClientStatus],
) -> KPIs:
    """
    Aggregate high-level KPIs for executive review.

    Args:
        dataset (DatasetResponse): Input dataset with totals.
        allocations (list[Allocation]): List of export allocations.
        local_details (list[LocalDetail]): List of local residual fruit assignments.
        client_statuses (list[ClientStatus]): Fulfillment statuses of all clients.

    Returns:
        KPIs: Complete set of top-level performance indicators.
    """
    export_vol = sum(a.tonnes for a in allocations)
    local_vol = sum(ld.tonnes for ld in local_details)
    export_rev = sum(a.export_revenue for a in allocations)
    local_val = sum(ld.local_value for ld in local_details)

    export_rate = (export_vol / dataset.total_actual_supply_t * 100.0) if dataset.total_actual_supply_t > 0 else 0.0
    at_risk_count = sum(1 for cs in client_statuses if cs.status != ClientStatusEnum.COMPLETE)

    return KPIs(
        expected_plan_t=dataset.total_expected_capacity_t,
        actual_received_t=dataset.total_actual_supply_t,
        station_capacity_t=dataset.station.export_conditioning_capacity_t,
        actual_A_t=dataset.actual_by_segment_t.get("A", 0.0),
        actual_B_t=dataset.actual_by_segment_t.get("B", 0.0),
        actual_C_t=dataset.actual_by_segment_t.get("C", 0.0),
        actual_D_t=dataset.actual_by_segment_t.get("D", 0.0),
        export_volume_t=export_vol,
        local_volume_t=local_vol,
        export_rate_pct=round(export_rate, 1),
        export_revenue_eur=export_rev,
        local_value_eur=local_val,
        total_value_eur=export_rev + local_val,
        at_risk_clients=at_risk_count,
    )


def run_planning_engine(dataset: DatasetResponse) -> PlanResult:
    """
    Execute the deterministic allocation planning engine on the provided dataset.

    Args:
        dataset (DatasetResponse): Validated production, commercial, and station dataset.

    Returns:
        PlanResult: Full deterministic planning result including KPIs, allocations,
        client statuses, farm summaries, and local residual details.
    """
    supply_pool = _build_supply_pool(dataset.farms)
    remaining_capacity = dataset.station.export_conditioning_capacity_t

    # Sort clients: highest export price first; tie-breaker client_id ascending
    sorted_clients = sorted(
        dataset.clients,
        key=lambda c: (-c.export_price_per_t_eur, c.client_id),
    )

    all_allocations: list[Allocation] = []
    client_status_map: dict[str, ClientStatus] = {}

    for client in sorted_clients:
        client_allocs, allocated_t, remaining_capacity = _allocate_for_client(
            client=client,
            farms=dataset.farms,
            supply_pool=supply_pool,
            remaining_capacity=remaining_capacity,
        )
        all_allocations.extend(client_allocs)

        status_obj = _evaluate_client_status(
            client=client,
            allocated_tonnes=allocated_t,
            remaining_capacity=remaining_capacity,
        )
        client_status_map[client.client_id] = status_obj

    # Order client statuses by original client order or client_id
    sorted_statuses = [client_status_map[c.client_id] for c in sorted(dataset.clients, key=lambda c: c.client_id)]

    local_details = _compute_local_residuals(supply_pool, dataset.station)
    farm_summaries = _build_farm_summaries(dataset.farms, supply_pool)
    kpis = _calculate_kpis(dataset, all_allocations, local_details, sorted_statuses)

    return PlanResult(
        kpis=kpis,
        allocations=all_allocations,
        client_statuses=sorted_statuses,
        farm_summaries=farm_summaries,
        local_details=local_details,
    )
