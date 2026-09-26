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

**Milestone 3 — Apex Facility Services customer website + quote request**

- React + Vite single-page marketing site for the demo company
- Five-step quote request mapping exactly to the `LeadCreate` API schema
- Progress indicator, per-step validation, review-and-edit, and submission states
- Minimal environment-driven CORS on the API for local development

The lead CRM, quotation builder, and follow-up stages are built in later milestones.

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
├── frontend/         React + Vite customer site
│   ├── src/
│   │   ├── App.jsx        Site / quote-flow view switch
│   │   ├── components/   Marketing sections and quote flow
│   │   ├── data/         Service and site copy
│   │   ├── lib/          API client and validation
│   │   └── styles/       Design tokens and CSS
│   └── .env.example  Template for VITE_API_BASE_URL
├── README.md
└── .gitignore
```

## Requirements

- Python 3.12+
- Node.js 20+
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

## CORS

The Vite dev server runs on a different origin to the API, so the browser
requires CORS on `/api/leads`. The API allows only explicit origins, read from
`CORS_ORIGINS` in `backend/.env`:

```ini
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

A wildcard is deliberately not used. Only `GET` and `POST` and the
`Content-Type` header are allowed, and credentials are not permitted.

## Run the API

```bash
uvicorn app.main:app --reload
```

The service is then available at `http://127.0.0.1:8000`, with interactive docs at
`/docs`.

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
```

The API base URL is read from `VITE_API_BASE_URL` at build time:

```ini
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Run the Frontend

```bash
cd frontend
npm run dev
```

The site is then available at `http://localhost:5173`. `npm run build` produces a
production bundle in `dist/`, and `npm run preview` serves that bundle locally.

## Local Development Flow

Run these in two terminals from the project root:

```bash
# Terminal 1 — API
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload

# Terminal 2 — website
cd frontend
npm run dev
```

Then open `http://localhost:5173`, choose **Request a Quote**, complete the five
steps, and submit. The enquiry is validated by the browser, posted to
`POST /api/leads`, persisted to PostgreSQL, and confirmed on screen with a
generated reference number. Confirm it was stored with `psql`, or via
`GET /api/leads/{id}` on the `/docs` page.

## Testing

Backend:

```bash
cd backend
source .venv/bin/activate
pytest
```

The suite runs against an isolated in-memory SQLite database that is created and
dropped per test, so **no PostgreSQL server is needed to run the tests**. To
exercise the suite against a real PostgreSQL database instead, set
`TEST_DATABASE_URL` (see `.env.example`).

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

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

