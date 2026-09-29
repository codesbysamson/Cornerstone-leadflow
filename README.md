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

## Current State

**V1 — complete.** Milestones 1–6 are done, and the application is deployable.

```
Public website → enquiry → protected staff CRM → status & follow-up
              → quotation → WhatsApp sharing → accepted / rejected
```

| Milestone | Delivered |
| --------- | --------- |
| 1 | Project foundation + `GET /health` |
| 2 | Persistent lead capture (PostgreSQL, SQLAlchemy, Alembic) |
| 3 | Apex Facility Services customer website + five-step quote request |
| 4 | Staff CRM: lead list, status, activity history, follow-up, WhatsApp |
| 5 | Quotation workflow: editor, document preview, lifecycle, WhatsApp sharing |
| 6 | Staff authentication: opaque server-side sessions, HttpOnly cookies, CSRF, login throttling, CLI bootstrap |

Database migration head is **`0004`**.

### Public vs staff API

The `/api/leads` prefix carries two different audiences, and the boundary is
enforced on the server — hiding the CRM in the frontend is a convenience, not a
control.

| Public | Staff (session required) |
| ------ | ----------------------- |
| `POST /api/leads` — customer enquiry | `GET /api/leads`, `GET /api/leads/{id}` |
| `GET /health` | `POST /api/leads/{id}/status` |
| `POST /api/auth/login` | `GET|POST /api/leads/{id}/notes` |
| `GET /api/auth/session` | `POST /api/leads/{id}/follow-up` |
| | `GET|POST /api/leads/{id}/quotations` |
| | `GET /api/quotations/{id}`, `POST /api/quotations/{id}/update`, `POST /api/quotations/{id}/status` |

A customer submitting an enquiry has no session and never will, so the public
submission endpoint must never require one.

### Staff authentication

Staff reach the CRM at `/?view=crm` and sign in with a work email and password.

- Passwords are hashed with **Argon2id** and never stored or logged in plaintext.
- Sign-in issues an **opaque 256-bit token**; the browser holds it in an
  **HttpOnly** `leadflow_session` cookie, and the server stores only a SHA-256
  digest, so a database dump yields nothing replayable.
- Sessions expire **12 hours after login**, absolutely — activity does not
  extend them.
- A matching `leadflow_csrf` cookie must be echoed in an `X-CSRF-Token` header
  on state-changing requests, which prevents another site from driving the
  browser with a signed-in staff member's cookies.
- Repeated failures are throttled per account from a database-backed counter.
  Every failure looks identical, so the form cannot be used to discover which
  email addresses exist.
- Disabling an account invalidates its live sessions immediately.

## Project Structure

```
cornerstone-leadflow/
├── backend/          FastAPI service (Python)
│   ├── app/
│   │   ├── main.py         FastAPI app, router wiring, CORS
│   │   ├── config.py       Environment-driven settings + production validation
│   │   ├── database.py     Engine, session factory, get_db dependency
│   │   ├── models.py       SQLAlchemy models
│   │   ├── schemas.py      Pydantic request/response schemas
│   │   ├── security.py     Argon2id hashing, token digests, cookie attributes
│   │   ├── dependencies.py Staff session and CSRF enforcement
│   │   ├── cli.py          `create-staff` bootstrap command
│   │   └── routes/         API route modules
│   ├── tests/        pytest suite
│   ├── alembic/      Migration environment and versions (head: 0004)
│   ├── alembic.ini
│   └── .env.example  Template for local configuration
├── frontend/         React + Vite customer site + staff CRM
│   ├── src/
│   │   ├── App.jsx        Site / quote-flow / CRM view switch
│   │   ├── components/    Marketing sections, quote flow, staff CRM
│   │   ├── data/          Service and site copy
│   │   ├── lib/           API clients, auth, configuration
│   │   └── styles/        Design tokens and CSS
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

The frontend is served from a different origin to the API, so the browser
requires CORS. The API allows only explicit origins, read from `CORS_ORIGINS` in
`backend/.env`:

```ini
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

A wildcard is deliberately not used and is **rejected at startup**, because
credentials are enabled for staff sessions and a wildcard would let any site
make authenticated requests as a signed-in staff member. Credentials are allowed,
`GET` and `POST` are the permitted methods, and `X-CSRF-Token` is an allowed
request header.

## Run the API

```bash
uvicorn app.main:app --reload
```

The service is then available at `http://127.0.0.1:8000`, with interactive docs at
`/docs` in development. Docs and the OpenAPI schema are **disabled when
`APP_ENV=production`**, because they publish every internal route and payload.

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
```

The API base URL is read from `VITE_API_BASE_URL` at **build** time, because
Vite inlines it into the bundle. Changing it later requires a rebuild.

```ini
VITE_API_BASE_URL=http://127.0.0.1:8000
```

It **must use the same host name as the page**, not merely the same machine. The
session cookie is `SameSite=Lax` and host-scoped, so a page on `localhost`
talking to an API on `127.0.0.1` can neither read the CSRF cookie nor have the
session cookie sent back, and sign-in fails with a bare 403. See
`frontend/src/lib/apiConfig.js`.

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

The CRM is at `http://localhost:5173/?view=crm`. It needs a staff account — see
[Creating the first staff account](#creating-the-first-staff-account).

## Creating the first staff account

No account is ever seeded by a migration, so a fresh database has no way in.
Create one explicitly:

```bash
cd backend
python -m app.cli create-staff you@example.com --display-name "Your Name"
```

The password is prompted for twice with `getpass`, must be at least 12
characters, and is never echoed, logged, or passed as an argument. A duplicate
email is refused rather than overwritten. For automation, `--password-env VAR`
reads it from an environment variable instead.

The `DATABASE_URL` in your environment must point at the migrated database —
run `alembic upgrade head` first.

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

## Production Deployment

### Environment variables

Required on the API. The API validates these at startup and **refuses to start**
on an unsafe combination rather than serve a weaker service than intended.

| Variable | Production value | Why |
| -------- | ---------------- | --- |
| `DATABASE_URL` | Neon **pooled** URL (`-pooler`) with `sslmode=require` | Secret. Pooling keeps a web service from exhausting the connection limit. |
| `APP_ENV` | `production` | Enables the checks below and disables `/docs` and `/openapi.json`. |
| `COOKIE_SECURE` | `true` | **Mandatory in production**; startup fails without it. Marks cookies HTTPS-only. |
| `CORS_ORIGINS` | the frontend's origin, e.g. `https://www.example.com` | Explicit origins only. A `*` is rejected at startup. |

Optional, with defaults: `SESSION_MAX_AGE_SECONDS=43200`,
`LOGIN_MAX_FAILURES=5`, `LOGIN_WINDOW_MINUTES=15`, `ARGON2_TIME_COST=3`,
`ARGON2_MEMORY_COST=65536`, `ARGON2_PARALLELISM=4`. Reduced Argon2 costs are
rejected in production. All of these are documented in `backend/.env.example`.

`DATABASE_URL` is the only secret. Never commit `backend/.env`.

### Same-site requirement

The frontend and API must be on the **same site** — the same registrable domain
and scheme, such as `www.example.com` and `api.example.com`. The session cookie
is `SameSite=Lax`, so a browser withholds it from a different site entirely: sign-in
would appear to succeed and then every later request would fail with a 401.

Subdomains of one domain satisfy this. Unrelated hosts (`vercel.app` and
`render.com`) do not.

### Commands

API, from the `backend/` directory:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health check: `GET /health`. It is a liveness check and does not query the
database.

Frontend, from the `frontend/` directory:

```bash
npm ci
VITE_API_BASE_URL=https://api.example.com npm run build
```

Publish the `dist/` directory as static files. There is no client-side router —
the CRM is a `?view=crm` query parameter — so no SPA rewrite rule is needed.

## API

| Method | Endpoint                     | Response                                     |
| ------ | ---------------------------- | -------------------------------------------- |
| GET    | `/health`                    | `{"status": "ok"}`                           |
| POST   | `/api/leads`                 | `201` with the created lead *(public)*       |
| GET    | `/api/leads`                 | `200` with all leads, newest first *(staff)* |
| GET    | `/api/leads/{id}`            | `200` with the lead, or `404` if unknown *(staff)* |
| POST   | `/api/leads/{id}/status`     | `200` with the updated lead *(staff)*        |
| GET    | `/api/leads/{id}/notes`      | `200` with the activity history, newest first *(staff)* |
| POST   | `/api/leads/{id}/notes`      | `201` with the created note *(staff)*        |
| POST   | `/api/leads/{id}/follow-up`  | `200` with the updated lead *(staff)*        |
| GET    | `/api/leads/{id}/quotations` | `200` with the lead's quotations, newest first *(staff)* |
| POST   | `/api/leads/{id}/quotations` | `201` with the created draft quotation *(staff)* |
| GET    | `/api/quotations/{id}`       | `200` with the quotation, or `404` if unknown *(staff)* |
| POST   | `/api/quotations/{id}/update` | `200` with the updated draft *(staff)*      |
| POST   | `/api/quotations/{id}/status` | `200` with the updated quotation *(staff)*  |
| GET    | `/api/auth/session`          | `200` with the current session and CSRF token *(public)* |
| POST   | `/api/auth/login`            | `200` with the staff member *(public)*       |
| POST   | `/api/auth/logout`           | `204` *(public, CSRF-protected)*             |
| GET    | `/api/auth/me`               | `200` with the current staff member *(staff)* |

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

Notes are append-only and record what happened and when. They carry no author:
the endpoint is staff-only, and the account that wrote the note is available from
`GET /api/auth/me` for the current session.

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
