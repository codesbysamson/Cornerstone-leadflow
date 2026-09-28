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

The lead CRM and quotation builder are built in later milestones.

**Milestone 4 — Staff CRM (4A lead management, 4B lead action & follow-up)**

- `GET /api/leads` — all leads, newest first
- `POST /api/leads/{id}/status` — pipeline status, persisted
- `GET|POST /api/leads/{id}/notes` — append-only staff activity history
- `POST /api/leads/{id}/follow-up` — set, reschedule or clear the next follow-up
- Internal CRM at `/?view=crm`: dashboard, lead list, lead detail, status,
  activity history, follow-up, and click-to-WhatsApp
- Due Today and Overdue follow-up queues, excluding closed leads

**Milestone 5 — Quotation workflow**

- `GET|POST /api/leads/{id}/quotations` — quotation history for a lead, and creation
- `GET /api/quotations/{id}` — full quotation document
- `POST /api/quotations/{id}/update` — edit a draft
- `POST /api/quotations/{id}/status` — DRAFT → SENT → ACCEPTED/REJECTED
- Quotation editor, document preview, and click-to-WhatsApp sharing
- Sending a quotation sets the lead to `QUOTE_SENT`; accepting or rejecting
  deliberately leaves the lead status to staff
- All money is `Decimal`/`NUMERIC(12, 2)`, priced by the server, with the
  currency stored as an ISO 4217 code

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

| Method | Endpoint                     | Response                                     |
| ------ | ---------------------------- | -------------------------------------------- |
| GET    | `/health`                    | `{"status": "ok"}`                           |
| POST   | `/api/leads`                 | `201` with the created lead                  |
| GET    | `/api/leads`                 | `200` with all leads, newest first           |
| GET    | `/api/leads/{id}`            | `200` with the lead, or `404` if unknown     |
| POST   | `/api/leads/{id}/status`     | `200` with the updated lead                  |
| GET    | `/api/leads/{id}/notes`      | `200` with the activity history, newest first |
| POST   | `/api/leads/{id}/notes`      | `201` with the created note                  |
| POST   | `/api/leads/{id}/follow-up`  | `200` with the updated lead                  |
| GET    | `/api/leads/{id}/quotations` | `200` with the lead's quotations, newest first |
| POST   | `/api/leads/{id}/quotations` | `201` with the created draft quotation       |
| GET    | `/api/quotations/{id}`       | `200` with the quotation, or `404` if unknown |
| POST   | `/api/quotations/{id}/update` | `200` with the updated draft               |
| POST   | `/api/quotations/{id}/status` | `200` with the updated quotation            |

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


### Staff activity and follow-up

Add a note to a lead:

```bash
curl -X POST http://127.0.0.1:8000/api/leads/1/notes \
  -H "Content-Type: application/json" \
  -d '{"body": "Called and left a voicemail. Wants a quote for the second floor."}'
```

Notes are append-only and have no author: authentication and users are out of
scope for this milestone, so a note records what happened and when, not who did
it.

Set, reschedule or clear the next follow-up:

```bash
# Set or reschedule (reschedule is just a second POST of the same shape)
curl -X POST http://127.0.0.1:8000/api/leads/1/follow-up \
  -H "Content-Type: application/json" \
  -d '{"due_at": "2026-10-05T14:30:00Z", "action": "Send revised quote"}'

# Clear
curl -X POST http://127.0.0.1:8000/api/leads/1/follow-up \
  -H "Content-Type: application/json" \
  -d '{"clear": true}'
```

`due_at` **must include a timezone offset**. A naive value such as
`2026-10-05T14:30` — which is what an HTML `datetime-local` control produces —
is rejected with `422`, because PostgreSQL would otherwise silently interpret
it in the database server's own zone. The CRM converts the staff member's local
wall-clock value to a UTC timestamp before sending it.

Due Today and Overdue are computed in the browser against the viewing staff
member's own clock, and exclude `WON` and `LOST` leads. Closed leads keep any
stored follow-up so it reappears if the deal is reopened.

### Click-to-WhatsApp

The CRM builds a `wa.me` deep link from the lead's existing phone number with a
short prefilled message. There is no messaging provider, API key or webhook, and
nothing is sent automatically — the link opens WhatsApp and the staff member
chooses whether to send.

Phone numbers are visitor-supplied free text and are never validated, so
normalisation is deliberately conservative. Accepted: an explicit `+` country
code (any country), the `00` international prefix, and the known Apex UK mobile
national format. Anything that would require guessing a country code is refused,
and the phone is then shown as plain text with no link.

### Quotations

A quotation is created from a lead, priced by the server, and moved through
`DRAFT → SENT → ACCEPTED | REJECTED`. A lead can carry several quotations over
its life, so a rejected quote can be followed by a fresh one without losing the
old.

```bash
curl -X POST http://127.0.0.1:8000/api/leads/1/quotations \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "GBP",
    "discount": "50.00",
    "notes": "Prices exclude VAT. Valid for 30 days.",
    "items": [
      {"description": "Deep clean", "quantity": "2", "unit_price": "150.00"},
      {"description": "Carpet shampoo", "quantity": "1", "unit_price": "85.50"}
    ]
  }'
```

The request sends descriptions, quantities and unit prices only. Line totals,
the subtotal and the final total are computed by the server, and any attempt to
supply them is rejected — a client cannot assert its own figures.

**Money is never binary floating point.** Amounts are persisted as
`NUMERIC(12, 2)` and handled as Python `Decimal` throughout, rounded half-up
(not banker's rounding). In JSON they are strings, because a JSON number is an
IEEE-754 double and `0.1 + 0.2` would not survive the round trip. The
`currency` column holds an ISO 4217 code, so another deployment can quote in
NGN or USD with no schema change; `Intl.NumberFormat` does the display
formatting.

Rejected with `422`: zero or negative quantity, negative unit price, negative
discount, a discount greater than the subtotal, an empty item list, and a blank
item description.

**Status transitions.** A quotation is editable only while it is `DRAFT`; once
`SENT` it is a document the customer has already seen, and editing returns
`409`. `ACCEPTED` and `REJECTED` are terminal.

Sending a quotation sets the lead to `QUOTE_SENT`. Accepting or rejecting
deliberately does **not** move the lead to `WON` or `LOST` — staff keep control
of the pipeline, and can close the lead themselves once a won quote has been
scoped.

Quotations can be shared by click-to-WhatsApp, reusing the same conservative
phone normalisation as lead follow-up. The prefilled message carries only the
customer's first name, the service, the reference and the total; it never
includes the quotation's internal notes.
