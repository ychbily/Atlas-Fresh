/**
 * Quality grades of apples ordered from premium (A) to basic (D).
 */
export type QualitySegment = 'A' | 'B' | 'C' | 'D';

/**
 * Quality acceptance rules for export clients.
 */
export type AcceptanceMode = 'EXACT' | 'MINIMUM';

/**
 * Fulfillment status of a client order.
 */
export type ClientStatusEnum = 'COMPLETE' | 'PARTIAL' | 'UNSERVED';

/**
 * Daily production actuals and seasonal plan for a single farm.
 */
export interface Farm {
  farm_id: string;
  farm_name: string;
  expected_daily_capacity_t: number;
  expected_A_pct: number;
  expected_B_pct: number;
  expected_C_pct: number;
  expected_D_pct: number;
  actual_A_t: number;
  actual_B_t: number;
  actual_C_t: number;
  actual_D_t: number;
}

/**
 * Commercial demand and quality constraints for an export client.
 */
export interface Client {
  client_id: string;
  client_name: string;
  acceptance_mode: AcceptanceMode;
  requested_segment: QualitySegment;
  demand_t: number;
  export_price_per_t_eur: number;
}

/**
 * Configuration for the export packing station and local market valuation.
 */
export interface Station {
  station_id: string;
  export_conditioning_capacity_t: number;
  local_market_ratio: number;
  reference_prices: Record<QualitySegment, number>;
}

/**
 * Full dataset payload returned by GET /api/data.
 */
export interface DatasetResponse {
  farms: Farm[];
  clients: Client[];
  station: Station;
  total_expected_capacity_t: number;
  total_actual_supply_t: number;
  actual_by_segment_t: Record<QualitySegment, number>;
}

/**
 * Traceable assignment of apples from a farm to an export client.
 */
export interface Allocation {
  farm_id: string;
  segment: QualitySegment;
  client_id: string;
  tonnes: number;
  quality_upgrade: boolean;
  export_revenue: number;
}

/**
 * Fulfillment summary for a client in the daily export plan.
 */
export interface ClientStatus {
  client_id: string;
  client_name: string;
  demand: number;
  allocated: number;
  remaining: number;
  revenue: number;
  status: ClientStatusEnum;
  reason: string | null;
}

/**
 * Production variance and residual summary for a single farm.
 */
export interface FarmSummary {
  farm_id: string;
  farm_name: string;
  expected_capacity: number;
  actual_total: number;
  variance_total: number;
  expected_A: number;
  actual_A: number;
  variance_A: number;
  expected_B: number;
  actual_B: number;
  variance_B: number;
  expected_C: number;
  actual_C: number;
  variance_C: number;
  expected_D: number;
  actual_D: number;
  variance_D: number;
  local_residual_t: number;
}

/**
 * Breakdown of unexported fruit sent to the local market at residual value.
 */
export interface LocalDetail {
  farm_id: string;
  segment: QualitySegment;
  tonnes: number;
  reference_price: number;
  local_value: number;
}

/**
 * High-level executive metrics for the daily export plan.
 */
export interface KPIs {
  expected_plan_t: number;
  actual_received_t: number;
  station_capacity_t: number;
  actual_A_t: number;
  actual_B_t: number;
  actual_C_t: number;
  actual_D_t: number;
  export_volume_t: number;
  local_volume_t: number;
  export_rate_pct: number;
  export_revenue_eur: number;
  local_value_eur: number;
  total_value_eur: number;
  at_risk_clients: number;
}

/**
 * Complete output payload of the deterministic daily planning engine.
 */
export interface PlanResult {
  kpis: KPIs;
  allocations: Allocation[];
  client_statuses: ClientStatus[];
  farm_summaries: FarmSummary[];
  local_details: LocalDetail[];
}

export interface AssistantPreset {
  id: string;
  question: string;
  answer?: string;
}

export type AssistantSource = 'llm' | 'deterministic_summary' | 'unsupported';

/**
 * Structured response from the planning assistant endpoint.
 */
export interface AssistantResponse {
  query: string;
  answer: string;
  source: AssistantSource;
  status_label: string;
  model?: string | null;
  cited_ids: string[];
}

/**
 * Structured validation error item for Excel sheet data.
 */
export interface ValidationErrorDetail {
  sheet: string;
  entity_id: string | null;
  field: string | null;
  message: string;
}

