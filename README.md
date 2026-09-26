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

**Milestone 2 — Persistent Lead Capture**

- PostgreSQL persistence via SQLAlchemy 2.x, with Alembic migrations
- `POST /api/leads` — structured enquiry validated, persisted, and returned
- `GET /api/leads/{id}` — retrieve a single lead
- Automated coverage of both endpoints

The frontend, lead CRM, and quotation stages are built in later milestones.

## Project Structure

```
cornerstone-leadflow/
├── backend/          FastAPI service (Python)
│   ├── app/
│   │   ├── main.py       FastAPI app and router wiring
│   │   ├── database.py   Engine, session factory, get_db dependency
│   │   ├── models.py     SQLAlchemy Lead model
│   │   ├── schemas.py    Pydantic request/response schemas
│   │   └── routes/       API route modules
│   ├── tests/        pytest suite
│   ├── alembic/      Migration environment and versions
│   ├── alembic.ini
│   └── .env.example  Template for local configuration
├── frontend/         React + Vite client (added in a later milestone)
├── README.md
└── .gitignore
```

## Requirements

- Python 3.12+
- **PostgreSQL** — required to run the API or apply migrations. Tests do
  **not** require a running server; see [Testing](#testing).

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Database Configuration

The connection string is read from the `DATABASE_URL` environment variable. No
credentials are hard-coded. Copy the template and edit it:

```bash
cp .env.example .env
```

```ini
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/leadflow
```

Create the database once, then apply migrations:

```bash
createdb leadflow
alembic upgrade head
```

Use `alembic downgrade base` to roll back, and `alembic upgrade head --sql` to
preview the SQL without applying it.

## Run the API

```bash
uvicorn app.main:app --reload
```

The service is then available at `http://127.0.0.1:8000`, with interactive docs at
`/docs`.

## Testing

```bash
cd backend
source .venv/bin/activate
pytest
```

The suite runs against an isolated in-memory SQLite database that is created and
dropped per test, so **no PostgreSQL server is needed to run the tests**. To
exercise the suite against a real PostgreSQL database instead, set
`TEST_DATABASE_URL` (see `.env.example`).

## API

| Method | Endpoint            | Response                                     |
| ------ | ------------------- | -------------------------------------------- |
| GET    | `/health`           | `{"status": "ok"}`                           |
| POST   | `/api/leads`        | `201` with the created lead                  |
| GET    | `/api/leads/{id}`   | `200` with the lead, or `404` if unknown     |

### Create a lead

```bash
curl -X POST http://127.0.0.1:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Sarah Johnson",
    "email": "sarah@example.com",
    "phone": "+44 7700 900123",
    "service": "Office Cleaning",
    "property_type": "Office",
    "location": "Manchester",
    "property_size": "2,500 sq ft",
    "frequency": "Weekly",
    "preferred_date": "2026-10-05",
    "requirements": "Cleaning required outside normal office hours."
  }'
```

Only customer-submitted fields are accepted. `id`, `status`, `source`, and
`created_at` are owned by the system; the API defaults them to `status="NEW"`,
`source="WEBSITE"`, and a generated timestamp. Submitting any of them returns
`422`.

Apex Facility Services currently offers: Office Cleaning, Deep Cleaning,
Move-In / Move-Out Cleaning, Facility Maintenance, and Commercial Cleaning.

