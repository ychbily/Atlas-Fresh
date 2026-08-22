"""
Main FastAPI entry point for the Atlas Fresh planning workspace API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Atlas Fresh Daily Planning API",
    description="Stateless decision-support API for daily Production-Commercial apple allocation.",
    version="1.0.0",
)

# Configure CORS so the React frontend can seamlessly query the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root_status() -> dict[str, str]:
    """
    Root status endpoint to verify API server health.
    
    Returns:
        dict: Status message indicating the API is running.
    """
    return {"status": "ok", "message": "Atlas Fresh API is running"}
