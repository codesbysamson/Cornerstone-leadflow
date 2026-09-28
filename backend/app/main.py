import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.leads import router as leads_router
from app.routes.quotations import router as quotations_router

load_dotenv()

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

app = FastAPI(title="Cornerstone LeadFlow API")

# The Vite dev server runs on a different origin to the API, so browser
# requests to /api/leads need CORS. Origins are explicit and configurable via
# CORS_ORIGINS — a wildcard is deliberately not used, so this stays safe to
# tighten or extend for a real deployment.
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(leads_router)
app.include_router(quotations_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
