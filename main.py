import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import hubspot_mock, deals, analytics, insights, transcripts
from services.mock_hubspot import generate_data
from services.mock_fireflies import generate_transcripts

app = FastAPI(title="Win/Loss Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        os.getenv("FRONTEND_URL", "https://*.github.io"),  # Production (set via env var)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hubspot_mock.router, prefix="/api/hubspot", tags=["HubSpot Mock"])
app.include_router(deals.router, prefix="/api/deals", tags=["Deals"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(insights.router, prefix="/api/insights", tags=["AI Insights"])
app.include_router(transcripts.router, prefix="/api/transcripts", tags=["Transcripts"])


@app.on_event("startup")
def startup():
    generate_data()
    generate_transcripts()


@app.get("/api/health")
def health():
    return {"status": "ok"}
