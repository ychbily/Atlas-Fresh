"""
Main FastAPI entry point for the Atlas Fresh planning workspace API.

Provides endpoints to retrieve the parsed production and commercial dataset,
with structured business validation error handlers.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models import AssistantQueryRequest, AssistantResponse, DatasetResponse, PlanResult
from app.data_loader import load_dataset, DataValidationError
from app.planning_engine import run_planning_engine
from app.assistant import ask_assistant

app = FastAPI(
    title="Atlas Fresh Daily Planning API",
    description="Stateless decision-support API for daily Production-Commercial apple allocation.",
    version="1.0.0",
)

# Configure CORS so the React frontend can seamlessly query the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    """Ensure all API responses are never cached by browsers or proxies."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.exception_handler(DataValidationError)
def handle_validation_error(_request: Request, exc: DataValidationError) -> JSONResponse:
    """
    Handle server-side Excel data validation errors and return structured 422 response.

    Args:
        _request (Request): Incoming FastAPI request.
        exc (DataValidationError): Raised validation exception with details.

    Returns:
        JSONResponse: HTTP 422 with structured list of validation errors.
    """
    return JSONResponse(
        status_code=422,
        content={
            "error": "ExcelDataValidationError",
            "message": "The dataset contains business validation errors.",
            "detail": [err.model_dump() for err in exc.errors],
        },
    )


@app.exception_handler(FileNotFoundError)
def handle_not_found_error(_request: Request, exc: FileNotFoundError) -> JSONResponse:
    """
    Handle missing dataset file and return structured 404 response.

    Args:
        _request (Request): Incoming FastAPI request.
        exc (FileNotFoundError): Raised file not found exception.

    Returns:
        JSONResponse: HTTP 404 with error message.
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "FileNotFoundError",
            "message": str(exc),
        },
    )


@app.get("/", tags=["Health"])
def root_status() -> dict[str, str]:
    """
    Root status endpoint to verify API server health.

    Returns:
        dict[str, str]: Status message indicating the API is running.
    """
    return {"status": "ok", "message": "Atlas Fresh API is running"}


@app.get("/api/data", response_model=DatasetResponse, tags=["Dataset"])
def get_dataset() -> DatasetResponse:
    """
    Retrieve and validate the authoritative daily production and commercial dataset.

    Returns:
        DatasetResponse: All 20 farms, 10 clients, station parameters, and aggregated totals.
    """
    return load_dataset()


@app.get("/api/plan", response_model=PlanResult, tags=["Planning"])
def get_plan() -> PlanResult:
    """
    Execute the deterministic allocation planning engine and return complete daily plan.

    Loads the authoritative dataset, performs business validations, applies the 
    reference allocation policy, computes local residuals, and aggregates executive KPIs.

    Returns:
        PlanResult: Structured plan containing KPIs, allocations, client statuses,
        farm summaries, and local residual breakdowns.
    """
    dataset = load_dataset()
    return run_planning_engine(dataset)


@app.post("/api/assistant/ask", response_model=AssistantResponse, tags=["Assistant"])
def query_assistant(request: AssistantQueryRequest) -> AssistantResponse:
    """
    Query the grounded AI planning assistant with natural language questions.

    Executes grounded explanation against the current daily dataset and computed plan.
    Uses Groq (openai/gpt-oss-120b) when configured, or returns an honest, clearly
    labelled deterministic engine summary with verifiable entity IDs.

    Args:
        request (AssistantQueryRequest): User query string.

    Returns:
        AssistantResponse: Structured explanation, resolution source, status label,
        and list of cited verifiable entity IDs.
    """
    dataset = load_dataset()
    plan = run_planning_engine(dataset)
    return ask_assistant(request=request, plan=plan, dataset=dataset)


