from fastapi import FastAPI

from app.routes.leads import router as leads_router

app = FastAPI(title="Cornerstone LeadFlow API")

app.include_router(leads_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
