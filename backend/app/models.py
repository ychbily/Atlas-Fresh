"""
Pydantic data models for the Atlas Fresh planning workspace.

Defines data structures for Farms, Clients, Packing Station configuration,
Allocations, and validation error reporting.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class QualitySegment(str, Enum):
    """Quality grades of apples ordered from premium (A) to basic (D)."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class AcceptanceMode(str, Enum):
    """Quality acceptance rules for export clients."""
    EXACT = "EXACT"
    MINIMUM = "MINIMUM"


class ClientStatusEnum(str, Enum):
    """Fulfillment status of a client order."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNSERVED = "UNSERVED"


class PartialReasonEnum(str, Enum):
    """Root cause explanation when a client order cannot be completely fulfilled."""
    INSUFFICIENT_COMPATIBLE_SEGMENT = "INSUFFICIENT_COMPATIBLE_SEGMENT"
    STATION_CAPACITY_REACHED = "STATION_CAPACITY_REACHED"


class ValidationErrorDetail(BaseModel):
    """Structured validation error item for Excel sheet data."""
    sheet: str = Field(description="Name of the Excel sheet with invalid data")
    entity_id: Optional[str] = Field(default=None, description="Entity identifier if applicable (e.g. F01, C02)")
    field: Optional[str] = Field(default=None, description="Specific field name failing validation")
    message: str = Field(description="Human-readable explanation of the validation failure")


class Farm(BaseModel):
    """Daily production actuals and seasonal plan for a single farm."""
    farm_id: str = Field(description="Unique farm identifier, e.g. F01")
    farm_name: str = Field(description="Human-readable farm name")
    expected_daily_capacity_t: float = Field(description="Planned daily delivery in tonnes")
    expected_A_pct: float = Field(description="Planned share of Segment A [0.0 - 1.0]")
    expected_B_pct: float = Field(description="Planned share of Segment B [0.0 - 1.0]")
    expected_C_pct: float = Field(description="Planned share of Segment C [0.0 - 1.0]")
    expected_D_pct: float = Field(description="Planned share of Segment D [0.0 - 1.0]")
    actual_A_t: float = Field(description="Actual Segment A apples received today in tonnes")
    actual_B_t: float = Field(description="Actual Segment B apples received today in tonnes")
    actual_C_t: float = Field(description="Actual Segment C apples received today in tonnes")
    actual_D_t: float = Field(description="Actual Segment D apples received today in tonnes")

    @property
    def actual_total_t(self) -> float:
        """Calculate total actual tonnes delivered by this farm today."""
        return self.actual_A_t + self.actual_B_t + self.actual_C_t + self.actual_D_t


class Client(BaseModel):
    """Commercial demand and quality constraints for an export client."""
    client_id: str = Field(description="Unique client identifier, e.g. C01")
    client_name: str = Field(description="Human-readable client name")
    acceptance_mode: AcceptanceMode = Field(description="EXACT (exact match only) or MINIMUM (exact match or upgrade)")
    requested_segment: QualitySegment = Field(description="Desired apple quality segment (A, B, C, or D)")
    demand_t: float = Field(description="Maximum export demand in tonnes (multiple of 5t)")
    export_price_per_t_eur: float = Field(description="Agreed export price per tonne in EUR")


class Station(BaseModel):
    """Configuration for the export packing station and local market valuation."""
    station_id: str = Field(description="Unique station identifier, e.g. STATION-01")
    export_conditioning_capacity_t: float = Field(description="Maximum daily export capacity in tonnes (500t)")
    local_market_ratio: float = Field(description="Fraction of reference price obtained locally (0.10 = 10%)")
    reference_prices: dict[str, float] = Field(description="Reference export prices per segment in EUR/t for local valuation")


class DatasetResponse(BaseModel):
    """Full dataset payload returned by GET /api/data."""
    farms: list[Farm] = Field(description="List of all 20 farms with planned and actual figures")
    clients: list[Client] = Field(description="List of all 10 export clients and commercial terms")
    station: Station = Field(description="Packing station capacity and reference pricing")
    total_expected_capacity_t: float = Field(description="Sum of all planned farm capacities in tonnes (600.0 t)")
    total_actual_supply_t: float = Field(description="Sum of all actual farm deliveries in tonnes (560.0 t)")
    actual_by_segment_t: dict[str, float] = Field(description="Total actual tonnes aggregated by quality segment")


class Allocation(BaseModel):
    """Traceable assignment of apples from a farm to an export client."""
    farm_id: str = Field(description="Originating farm ID")
    segment: QualitySegment = Field(description="Physical apple quality segment allocated")
    client_id: str = Field(description="Receiving client ID")
    tonnes: float = Field(description="Allocated quantity in tonnes (5t increments)")
    quality_upgrade: bool = Field(description="True if client received a segment higher than requested")
    export_revenue: float = Field(description="Revenue generated (tonnes * client_price) in EUR")


class ClientStatus(BaseModel):
    """Fulfillment summary for a client in the daily export plan."""
    client_id: str = Field(description="Unique client ID")
    client_name: str = Field(description="Client name")
    demand: float = Field(description="Target demand in tonnes")
    allocated: float = Field(description="Total tonnes allocated in export plan")
    remaining: float = Field(description="Unfulfilled demand in tonnes")
    revenue: float = Field(description="Total export revenue from this client in EUR")
    status: ClientStatusEnum = Field(description="Fulfillment status: COMPLETE, PARTIAL, or UNSERVED")
    reason: Optional[str] = Field(default=None, description="Root cause explanation if not COMPLETE")


class FarmSummary(BaseModel):
    """Production variance and residual summary for a single farm."""
    farm_id: str = Field(description="Unique farm ID")
    farm_name: str = Field(description="Farm name")
    expected_capacity: float = Field(description="Planned capacity in tonnes")
    actual_total: float = Field(description="Actual total tonnes received")
    variance_total: float = Field(description="Difference between actual and planned total tonnes")
    expected_A: float = Field(description="Planned tonnes for Segment A")
    actual_A: float = Field(description="Actual tonnes for Segment A")
    variance_A: float = Field(description="Variance for Segment A in tonnes")
    expected_B: float = Field(description="Planned tonnes for Segment B")
    actual_B: float = Field(description="Actual tonnes for Segment B")
    variance_B: float = Field(description="Variance for Segment B in tonnes")
    expected_C: float = Field(description="Planned tonnes for Segment C")
    actual_C: float = Field(description="Actual tonnes for Segment C")
    variance_C: float = Field(description="Variance for Segment C in tonnes")
    expected_D: float = Field(description="Planned tonnes for Segment D")
    actual_D: float = Field(description="Actual tonnes for Segment D")
    variance_D: float = Field(description="Variance for Segment D in tonnes")
    local_residual_t: float = Field(description="Tonnes from this farm diverted to local market")


class LocalDetail(BaseModel):
    """Breakdown of unexported fruit sent to the local market at residual value."""
    farm_id: str = Field(description="Originating farm ID")
    segment: QualitySegment = Field(description="Quality grade of local residual fruit")
    tonnes: float = Field(description="Volume diverted to local market in tonnes")
    reference_price: float = Field(description="Reference export price per tonne in EUR")
    local_value: float = Field(description="Realized local market value (tonnes * 0.10 * ref_price) in EUR")


class KPIs(BaseModel):
    """High-level executive metrics for the daily export plan."""
    expected_plan_t: float = Field(description="Total planned delivery across all farms (600.0 t)")
    actual_received_t: float = Field(description="Total actual delivery across all farms (560.0 t)")
    station_capacity_t: float = Field(description="Maximum export capacity of packing station (500.0 t)")
    actual_A_t: float = Field(description="Total actual Segment A tonnes (90.0 t)")
    actual_B_t: float = Field(description="Total actual Segment B tonnes (160.0 t)")
    actual_C_t: float = Field(description="Total actual Segment C tonnes (180.0 t)")
    actual_D_t: float = Field(description="Total actual Segment D tonnes (130.0 t)")
    export_volume_t: float = Field(description="Total tonnes allocated to export clients (500.0 t)")
    local_volume_t: float = Field(description="Total tonnes routed to local market (60.0 t)")
    export_rate_pct: float = Field(description="Percentage of received fruit exported (89.3%)")
    export_revenue_eur: float = Field(description="Total revenue generated from export allocations (€549,500)")
    local_value_eur: float = Field(description="Total value recovered from local market sales (€4,500)")
    total_value_eur: float = Field(description="Combined export revenue and local market value (€554,000)")
    at_risk_clients: int = Field(description="Count of clients receiving PARTIAL or UNSERVED status (3)")


class PlanResult(BaseModel):
    """Complete output payload of the deterministic daily planning engine."""
    kpis: KPIs
    allocations: list[Allocation]
    client_statuses: list[ClientStatus]
    farm_summaries: list[FarmSummary]
    local_details: list[LocalDetail]


class AssistantSourceEnum(str, Enum):
    """Origin source of the planning assistant response."""
    LLM = "llm"
    DETERMINISTIC_SUMMARY = "deterministic_summary"
    UNSUPPORTED = "unsupported"


class AssistantQueryRequest(BaseModel):
    """User prompt query payload sent to the assistant endpoint."""
    query: str = Field(description="Operational question or preset query text", min_length=1)


class AssistantResponse(BaseModel):
    """Structured response payload returned by the planning assistant."""
    query: str = Field(description="Original user query")
    answer: str = Field(description="Grounded explanation citing verifiable entity IDs")
    source: AssistantSourceEnum = Field(description="Resolution source: llm, deterministic_summary, or unsupported")
    status_label: str = Field(description="Honest UI status label indicating execution mode")
    model: Optional[str] = Field(default=None, description="Model identifier if resolved via LLM")
    cited_ids: list[str] = Field(default_factory=list, description="Verifiable entity IDs cited in the answer")

