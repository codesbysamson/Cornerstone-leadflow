from fastapi import FastAPI

app = FastAPI(title="Cornerstone LeadFlow API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
