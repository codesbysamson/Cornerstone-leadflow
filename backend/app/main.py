import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.auth import router as auth_router
from app.routes.leads import public_router as leads_public_router
from app.routes.leads import staff_router as leads_staff_router
from app.routes.quotations import router as quotations_router

load_dotenv()

# Kept as module attributes because the existing CORS tests assert against them.
allowed_origins = settings.allowed_origins

# The OpenAPI schema publishes every internal route and payload, including the
# shape of the CRM, so it is a development affordance rather than something to
# expose publicly.
app = FastAPI(
    title="Cornerstone LeadFlow API",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

# The Vite dev server runs on a different origin to the API, so browser requests
# need CORS.
#
# Credentials are now enabled because staff authentication is cookie-based and
# the cookie is scoped to the API's own origin. That makes this allowlist a
# security control rather than a convenience: any origin permitted here could
# make authenticated, credentialed requests as a signed-in staff member. A
# wildcard is therefore never used, and app.config.validate refuses to start if
# one is configured alongside credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    # X-CSRF-Token is required on state-changing authenticated requests.
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

# Public: the customer website and the authentication entry points.
app.include_router(leads_public_router)
app.include_router(auth_router)

# Staff: everything below is behind require_staff.
app.include_router(leads_staff_router)
app.include_router(quotations_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
