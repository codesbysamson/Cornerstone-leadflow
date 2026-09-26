# Cornerstone LeadFlow

A sales demonstration and business workflow application by **Cornerstone Digital**.

Cornerstone LeadFlow shows service businesses how a professional website turns
stray customer enquiries into structured, trackable leads — and how those leads
move cleanly into quotations and follow-up.

## Workflow

```
Website → Structured Enquiry → FastAPI → PostgreSQL → Lead CRM → Quotation → Follow-up
```

Every stage of that pipeline is designed to be demonstrable to a non-technical
audience: a visitor submits a quote request, the API validates and structures it,
it is persisted as a lead, and the business works the lead through to a quotation.

## First Demo Vertical

The initial demonstration is built for a fictional client, **Apex Facility
Services** — a commercial cleaning and facilities maintenance provider. It
showcases the full enquiry-to-quotation journey for a typical service business.

## Current Milestone

**Milestone 1 — Project foundation + API health check**

- Repository hygiene (`.gitignore`, this README)
- Minimal FastAPI application with a `GET /health` endpoint
- Automated test coverage of that endpoint

The frontend, database, and CRM stages are built in later milestones.

## Project Structure

```
cornerstone-leadflow/
├── backend/          FastAPI service (Python)
├── frontend/         React + Vite client (added in a later milestone)
├── README.md
└── .gitignore
```

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn app.main:app --reload
```

The service is then available at `http://127.0.0.1:8000`, with interactive docs at
`/docs` and the health check at `GET /health`.

## Run the Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

## API

| Method | Endpoint | Response |
| ------ | -------- | -------- |
| GET    | `/health` | `{"status": "ok"}` |
