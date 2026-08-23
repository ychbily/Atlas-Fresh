"""
Automated unit tests for the Grounded AI Planning Assistant, entity ID citations, and guardrails.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
import httpx

from app.main import app
from app.data_loader import load_dataset, DataValidationError
from app.planning_engine import run_planning_engine
from app.models import AssistantQueryRequest, AssistantSourceEnum
from app.assistant import (
    classify_query,
    validate_and_extract_ids,
    ask_assistant,
)

client = TestClient(app)


def safe_load_dataset():
    """Safely load dataset or fail with a clear assertion message if Excel validation fails."""
    try:
        return load_dataset()
    except DataValidationError as exc:
        err_msgs = [f"{e.sheet}/{e.entity_id or 'General'}: {e.message}" for e in exc.errors]
        raise pytest.fail(f"Excel dataset validation failed: {err_msgs}") from None


def get_plan_and_dataset():
    """Load authoritative dataset and compute plan dynamically."""
    dataset = safe_load_dataset()
    plan = run_planning_engine(dataset)
    return dataset, plan


def test_grounded_assistant_citations():
    """Verify query classification, dynamic ID citations from dataset, and POST /api/assistant/ask route."""
    # Query intent classification
    assert classify_query("Which clients are at risk and why?") == "risk"
    assert classify_query("Which farm/segment gaps matter most today?") == "gaps"
    assert classify_query("Why are tonnes going local?") == "local"

    dataset, plan = get_plan_and_dataset()
    req = AssistantQueryRequest(query="Which clients are at risk and why?")
    
    # Force deterministic summary mode by setting empty API key
    with patch("app.assistant.resolve_groq_api_key", return_value=""):
        res = ask_assistant(req, plan, dataset, api_key="")

    assert res.source == AssistantSourceEnum.DETERMINISTIC_SUMMARY
    assert "Deterministic Summary" in res.status_label
    
    # Verify citations match active at-risk clients or 0 count
    at_risk_ids = [cs.client_id for cs in plan.client_statuses if cs.status.value != "COMPLETE"]
    if at_risk_ids:
        assert set(at_risk_ids).issubset(set(res.cited_ids))

    # API Endpoint check
    resp = client.post("/api/assistant/ask", json={"query": "Which clients are at risk and why?"})
    assert resp.status_code == 200, f"POST /api/assistant/ask failed ({resp.status_code}): {resp.json()}"
    data = resp.json()
    assert "answer" in data and len(data["answer"]) > 0


def test_assistant_fallbacks_and_guardrails():
    """Verify ID validation, rejection of hallucinated IDs, LLM mocking, provider timeout fallback, and out-of-scope guardrail."""
    dataset, plan = get_plan_and_dataset()
    valid_c1 = dataset.clients[0].client_id
    valid_f1 = dataset.farms[0].farm_id

    # 1. Valid vs Hallucinated ID Validation
    valid_text = f"Client {valid_c1} received fruit from Farm {valid_f1}."
    is_valid, cited = validate_and_extract_ids(valid_text, dataset)
    assert is_valid is True and cited == sorted([valid_c1, valid_f1])

    hallucinated_text = "Client C99 from Farm F88 had issues."
    is_valid_fake, cited_fake = validate_and_extract_ids(hallucinated_text, dataset)
    assert is_valid_fake is False and cited_fake == []

    # 2. Dynamic Mocked LLM Success
    req = AssistantQueryRequest(query="Which clients are at risk and why?")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": f"Client {valid_c1} fulfilled from Farm {valid_f1}."}}]
    }
    with patch("httpx.Client.post", return_value=mock_resp):
        res_llm = ask_assistant(req, plan, dataset, api_key="fake-groq-key")
        assert res_llm.source == AssistantSourceEnum.LLM
        assert res_llm.cited_ids == sorted([valid_c1, valid_f1])

    # 3. Provider Timeout Fallback
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Request timed out")):
        res_fallback = ask_assistant(req, plan, dataset, api_key="fake-groq-key")
        assert res_fallback.source == AssistantSourceEnum.DETERMINISTIC_SUMMARY
        assert "Provider Unavailable" in res_fallback.status_label

    # 4. Out-of-scope Guardrail
    out_of_scope = AssistantQueryRequest(query="What is the weather in Agadir tomorrow?")
    res_unsupported = ask_assistant(out_of_scope, plan, dataset, api_key="")
    assert res_unsupported.source == AssistantSourceEnum.UNSUPPORTED
    assert "outside the scope" in res_unsupported.answer.lower()
