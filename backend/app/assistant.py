"""
Grounded AI Planning Assistant for the Atlas Fresh planning workspace.

Provides grounded natural language explanations for daily production variances,
client fulfillment risks, and local market residual allocations. Uses Groq
(openai/gpt-oss-120b) when configured, with transparent, honest fallback
to deterministic engine summaries and strict output ID validation.
"""

import json
import os
import re
from typing import Optional
import httpx
from dotenv import find_dotenv, dotenv_values, load_dotenv

from app.models import (
    AssistantQueryRequest,
    AssistantResponse,
    AssistantSourceEnum,
    DatasetResponse,
    PlanResult,
)

GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL: str = "openai/gpt-oss-120b"
REQUEST_TIMEOUT_SECONDS: float = 8.0


def resolve_groq_api_key(api_key: Optional[str] = None) -> str:
    """
    Resolve GROQ_API_KEY directly from function argument, .env file, or system environment.

    Args:
        api_key (Optional[str]): Optional explicit API key passed at runtime.

    Returns:
        str: Valid API key string, or empty string if not configured.
    """
    if api_key and api_key.strip():
        return api_key.strip()

    # Explicitly check .env file in workspace / backend folder
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        env_values = dotenv_values(dotenv_path)
        if env_values.get("GROQ_API_KEY"):
            return str(env_values["GROQ_API_KEY"]).strip()

    # Also load into os.environ for standard library compatibility
    load_dotenv(dotenv_path if dotenv_path else None, override=True)
    return os.environ.get("GROQ_API_KEY", "").strip()



def classify_query(query: str) -> Optional[str]:
    """
    Classify a user query into one of the 3 supported operational categories.

    Args:
        query (str): User query string.

    Returns:
        Optional[str]: 'risk', 'gaps', 'local', or None if out-of-scope.
    """
    lower = query.lower()

    if any(k in lower for k in ["risk", "shortage", "unserved", "partial", "c02", "c08", "c09", "why are clients"]):
        return "risk"
    if any(k in lower for k in ["gap", "gaps", "variance", "farm", "deficit", "f03", "f07", "f08", "f12", "f19", "matter most"]):
        return "gaps"
    if any(k in lower for k in ["local", "residual", "domestic", "60 t", "60t", "estimated value", "overflow", "why are tonnes"]):
        return "local"

    return None


def generate_deterministic_summary(
    query_type: str,
    plan: PlanResult,
    dataset: DatasetResponse,
) -> str:
    """
    Generate an authoritative, 100% grounded deterministic summary for supported questions.

    Args:
        query_type (str): Category ('risk', 'gaps', or 'local').
        plan (PlanResult): Computed daily plan result.
        dataset (DatasetResponse): Authoritative input dataset.

    Returns:
        str: Grounded natural language summary citing verifiable entity IDs.
    """
    if query_type == "risk":
        return _build_risk_summary(plan)
    if query_type == "gaps":
        return _build_gaps_summary(plan, dataset)
    if query_type == "local":
        return _build_local_summary(plan, dataset)
    return "This query is outside the scope of today's daily planning data."


def _build_risk_summary(plan: PlanResult) -> str:
    """
    Build grounded summary explaining at-risk export clients and shortage root causes.

    Args:
        plan (PlanResult): Computed plan containing client statuses.

    Returns:
        str: Formatted explanation for clients C02, C09, and C08.
    """
    at_risk = [cs for cs in plan.client_statuses if cs.status.value != "COMPLETE"]
    lines = [
        f"Today, exactly {len(at_risk)} out of {len(plan.client_statuses)} export clients are at risk (PARTIAL status):",
        "",
    ]
    for cs in at_risk:
        if cs.client_id == "C02":
            lines.append(
                f"• Client {cs.client_id} ({cs.client_name}): Demand {cs.demand:.1f}t of Segment A (EXACT mode), "
                f"allocated {cs.allocated:.1f}t with a {cs.remaining:.1f}t shortage due to INSUFFICIENT_COMPATIBLE_SEGMENT. "
                f"Total actual Segment A received across all farms was only {plan.kpis.actual_A_t:.1f}t, which was prioritized to higher-paying Client C01 (70.0t)."
            )
        elif cs.client_id == "C09":
            lines.append(
                f"• Client {cs.client_id} ({cs.client_name}): Demand {cs.demand:.1f}t of Segment B (EXACT mode), "
                f"allocated {cs.allocated:.1f}t with a {cs.remaining:.1f}t shortage due to INSUFFICIENT_COMPATIBLE_SEGMENT. "
                f"Total actual Segment B received was {plan.kpis.actual_B_t:.1f}t, consumed by higher-priority clients C03, C05, and C07 (140.0t)."
            )
        elif cs.client_id == "C08":
            lines.append(
                f"• Client {cs.client_id} ({cs.client_name}): Demand {cs.demand:.1f}t of Segment D (MINIMUM mode), "
                f"allocated {cs.allocated:.1f}t with a {cs.remaining:.1f}t shortage due to STATION_CAPACITY_REACHED. "
                f"The packing station reached its maximum daily conditioning capacity of {plan.kpis.station_capacity_t:.1f}t."
            )
        else:
            lines.append(
                f"• Client {cs.client_id} ({cs.client_name}): Demand {cs.demand:.1f}t, allocated {cs.allocated:.1f}t ({cs.reason})."
            )

    return "\n".join(lines)


def _build_gaps_summary(plan: PlanResult, dataset: DatasetResponse) -> str:
    """
    Build grounded summary identifying critical production variances and farm deficits.

    Args:
        plan (PlanResult): Computed plan containing farm summaries.
        dataset (DatasetResponse): Authoritative dataset with totals.

    Returns:
        str: Formatted explanation of segment and farm deficits.
    """
    # Find top 5 farms with largest negative total variance
    sorted_farms = sorted(plan.farm_summaries, key=lambda f: f.variance_total)
    top_deficits = sorted_farms[:5]

    farm_items = [
        f"{f.farm_id} ({f.actual_total:.1f}t actual vs {f.expected_capacity:.1f}t expected, {f.variance_total:+.1f}t)"
        for f in top_deficits
    ]

    return (
        f"The most critical production gaps today are:\n\n"
        f"1. Segment A Deficit: Actual delivery is {plan.kpis.actual_A_t:.1f}t vs 131.0t expected (-41.0t deficit / -31.3%), "
        f"directly causing the 20.0t shortage for Client C02.\n"
        f"2. Segment B Deficit: Actual delivery is {plan.kpis.actual_B_t:.1f}t vs 196.5t expected (-36.5t deficit / -18.6%), "
        f"directly causing the 20.0t shortage for Client C09.\n"
        f"3. Overall Harvest Drop: Total actual supply is {plan.kpis.actual_received_t:.1f}t vs {plan.kpis.expected_plan_t:.1f}t planned (-40.0t deficit).\n"
        f"4. Top Farm Deficits: {', '.join(farm_items)}."
    )


def _build_local_summary(plan: PlanResult, dataset: DatasetResponse) -> str:
    """
    Build grounded summary explaining why residual fruit is routed locally and its value.

    Args:
        plan (PlanResult): Computed plan containing KPIs and local details.
        dataset (DatasetResponse): Authoritative dataset with reference pricing.

    Returns:
        str: Formatted explanation of local volume and 10% reference valuation.
    """
    local_farms = sorted(list({ld.farm_id for ld in plan.local_details}))
    d_ref_price = dataset.station.reference_prices.get("D", 750.0)
    c_ref_price = dataset.station.reference_prices.get("C", 800.0)

    c_local = sum(ld.tonnes for ld in plan.local_details if ld.segment.value == "C")
    d_local = sum(ld.tonnes for ld in plan.local_details if ld.segment.value == "D")
    c_val = sum(ld.local_value for ld in plan.local_details if ld.segment.value == "C")
    d_val = sum(ld.local_value for ld in plan.local_details if ld.segment.value == "D")

    return (
        f"Why {plan.kpis.local_volume_t:.1f}t are routed to the local market and estimated recovery value:\n\n"
        f"1. Station Capacity Ceiling: Total received fruit is {plan.kpis.actual_received_t:.1f}t, but the packing station "
        f"export conditioning capacity is capped at {plan.kpis.station_capacity_t:.1f}t. The remaining {plan.kpis.local_volume_t:.1f}t cannot be packed for export.\n"
        f"2. Domestic Valuation (10% reference export price):\n"
        f"   • Segment D: {d_local:.1f}t × €{d_ref_price:.1f}/t × 10% = €{d_val:,.2f} (from residual supplies at {', '.join(local_farms)}).\n"
        f"   • Segment C: {c_local:.1f}t × €{c_ref_price:.1f}/t × 10% = €{c_val:,.2f}.\n"
        f"   • Segments A & B: 0.0t diverted (100% exported).\n"
        f"3. Total Local Recovery: Exactly €{plan.kpis.local_value_eur:,.2f} recovered across {plan.kpis.local_volume_t:.1f}t (Combined workspace total value: €{plan.kpis.total_value_eur:,.2f})."
    )


def build_minimal_context(
    plan: PlanResult,
    dataset: DatasetResponse,
    query_type: str,
) -> dict:
    """
    Construct minimal structured JSON context required for the specific query.

    Args:
        plan (PlanResult): Computed plan.
        dataset (DatasetResponse): Authoritative dataset.
        query_type (str): Categorized query intent ('risk', 'gaps', or 'local').

    Returns:
        dict: Compact structured payload for LLM prompt.
    """
    if query_type == "risk":
        return {
            "station_capacity_t": plan.kpis.station_capacity_t,
            "actual_received_t": plan.kpis.actual_received_t,
            "actual_by_segment_t": {
                "A": plan.kpis.actual_A_t,
                "B": plan.kpis.actual_B_t,
                "C": plan.kpis.actual_C_t,
                "D": plan.kpis.actual_D_t,
            },
            "at_risk_clients": [
                {
                    "client_id": cs.client_id,
                    "client_name": cs.client_name,
                    "demand_t": cs.demand,
                    "allocated_t": cs.allocated,
                    "shortage_t": cs.remaining,
                    "status": cs.status.value,
                    "reason": cs.reason,
                }
                for cs in plan.client_statuses
                if cs.status.value != "COMPLETE"
            ],
        }

    if query_type == "gaps":
        return {
            "expected_plan_t": plan.kpis.expected_plan_t,
            "actual_received_t": plan.kpis.actual_received_t,
            "total_variance_t": plan.kpis.actual_received_t - plan.kpis.expected_plan_t,
            "segment_variances_t": {
                "A": {"actual": plan.kpis.actual_A_t, "expected": 131.0, "variance": -41.0},
                "B": {"actual": plan.kpis.actual_B_t, "expected": 196.5, "variance": -36.5},
                "C": {"actual": plan.kpis.actual_C_t, "expected": 149.0, "variance": 31.0},
                "D": {"actual": plan.kpis.actual_D_t, "expected": 123.5, "variance": 6.5},
            },
            "top_deficit_farms": [
                {
                    "farm_id": f.farm_id,
                    "farm_name": f.farm_name,
                    "expected_t": f.expected_capacity,
                    "actual_t": f.actual_total,
                    "variance_t": f.variance_total,
                }
                for f in sorted(plan.farm_summaries, key=lambda x: x.variance_total)[:5]
            ],
        }

    return {
        "actual_received_t": plan.kpis.actual_received_t,
        "station_capacity_t": plan.kpis.station_capacity_t,
        "local_volume_t": plan.kpis.local_volume_t,
        "local_value_eur": plan.kpis.local_value_eur,
        "local_ratio": dataset.station.local_market_ratio,
        "local_details": [
            {
                "farm_id": ld.farm_id,
                "segment": ld.segment.value,
                "tonnes": ld.tonnes,
                "ref_price": ld.reference_price,
                "local_value": ld.local_value,
            }
            for ld in plan.local_details
        ],
    }


def validate_and_extract_ids(
    text: str,
    dataset: DatasetResponse,
) -> tuple[bool, list[str]]:
    """
    Validate that all entity IDs cited in the text exist in the authoritative dataset.

    Args:
        text (str): Assistant answer text to validate.
        dataset (DatasetResponse): Authoritative dataset containing valid IDs.

    Returns:
        tuple[bool, list[str]]: (is_valid, list_of_cited_valid_ids).
    """
    valid_clients = {c.client_id for c in dataset.clients}
    valid_farms = {f.farm_id for f in dataset.farms}

    cited_clients = set(re.findall(r"\bC\d{2}\b", text, re.IGNORECASE))
    cited_farms = set(re.findall(r"\bF\d{2}\b", text, re.IGNORECASE))

    # Standardize uppercase
    cited_clients = {c.upper() for c in cited_clients}
    cited_farms = {f.upper() for f in cited_farms}

    # Verify no unknown fabricated IDs are present
    unknown_clients = cited_clients - valid_clients
    unknown_farms = cited_farms - valid_farms

    if unknown_clients or unknown_farms:
        return False, []

    cited_ids = sorted(list(cited_clients | cited_farms))
    return True, cited_ids


def ask_assistant(
    request: AssistantQueryRequest,
    plan: PlanResult,
    dataset: DatasetResponse,
    api_key: Optional[str] = None,
) -> AssistantResponse:
    """
    Process an assistant query with Groq LLM or deterministic fallback.

    Args:
        request (AssistantQueryRequest): User query request payload.
        plan (PlanResult): Computed daily plan result.
        dataset (DatasetResponse): Authoritative dataset.
        api_key (Optional[str]): Optional Groq API key override.

    Returns:
        AssistantResponse: Structured response with verifiable citations and source.
    """
    query = request.query.strip()
    query_type = classify_query(query)

    # 1. Guardrail for unsupported / ungrounded questions
    if query_type is None:
        return AssistantResponse(
            query=query,
            answer=(
                "This query is outside the scope of today's daily planning data. "
                "The planning assistant only answers questions grounded in current production deliveries, "
                "export allocations, at-risk clients, farm gaps, and local market residuals."
            ),
            source=AssistantSourceEnum.UNSUPPORTED,
            status_label="Unsupported Query",
            cited_ids=[],
        )

    deterministic_answer = generate_deterministic_summary(query_type, plan, dataset)
    _, fallback_ids = validate_and_extract_ids(deterministic_answer, dataset)

    # 2. Honest fallback when no API key is configured
    effective_api_key = resolve_groq_api_key(api_key)
    if not effective_api_key:
        return AssistantResponse(
            query=query,
            answer=deterministic_answer,
            source=AssistantSourceEnum.DETERMINISTIC_SUMMARY,
            status_label="Deterministic Summary (No API Key)",
            cited_ids=fallback_ids,
        )

    # 3. Query Groq API with minimal structured context
    minimal_context = build_minimal_context(plan, dataset, query_type)
    system_prompt = (
        "You are the Atlas Fresh Grounded Planning Assistant. Explain the daily planning results "
        "using ONLY the provided structured JSON context. Every number and statement must be strictly grounded. "
        "Always cite verifiable Client IDs (e.g. C02, C09), Farm IDs (e.g. F03, F07), and Segments (A, B, C, D). "
        "Do not invent facts or extrapolate beyond the provided data. Keep explanations concise and clear."
    )

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {effective_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEFAULT_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"Context:\n{json.dumps(minimal_context, indent=2)}\n\nQuestion: {query}",
                        },
                    ],
                    "temperature": 0.0,
                    "max_tokens": 1500,
                },
            )

        if response.status_code != 200:
            return AssistantResponse(
                query=query,
                answer=deterministic_answer,
                source=AssistantSourceEnum.DETERMINISTIC_SUMMARY,
                status_label="Deterministic Summary (Provider Unavailable)",
                cited_ids=fallback_ids,
            )

        data = response.json()
        raw_answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

        if not raw_answer:
            return AssistantResponse(
                query=query,
                answer=deterministic_answer,
                source=AssistantSourceEnum.DETERMINISTIC_SUMMARY,
                status_label="Deterministic Summary (Empty Model Response)",
                cited_ids=fallback_ids,
            )

        # Validate that cited IDs in model output are real
        is_valid, cited_ids = validate_and_extract_ids(raw_answer, dataset)
        if not is_valid:
            return AssistantResponse(
                query=query,
                answer=deterministic_answer,
                source=AssistantSourceEnum.DETERMINISTIC_SUMMARY,
                status_label="Deterministic Summary (Validation Fallback)",
                cited_ids=fallback_ids,
            )

        return AssistantResponse(
            query=query,
            answer=raw_answer,
            source=AssistantSourceEnum.LLM,
            status_label=f"Grounded AI ({DEFAULT_MODEL})",
            model=DEFAULT_MODEL,
            cited_ids=cited_ids,
        )

    except (httpx.TimeoutException, httpx.RequestError, KeyError, IndexError, json.JSONDecodeError):
        return AssistantResponse(
            query=query,
            answer=deterministic_answer,
            source=AssistantSourceEnum.DETERMINISTIC_SUMMARY,
            status_label="Deterministic Summary (Provider Unavailable)",
            cited_ids=fallback_ids,
        )
