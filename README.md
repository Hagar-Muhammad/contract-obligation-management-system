<p align="center"><img src="docs/brand/contrack-logo.svg" alt="ConTrack" width="280"></p>

# ConTrack — Contract & Obligation Management System

**ConTrack** is a web platform for managing real estate contracts and tracking contractual obligations: contracts, parties,
properties, contract documents, extraction of key information from existing documents (with human review),
obligations with deadlines and recurrence, reminders, dashboards, reports, audit trail and role-based access control.

The requirements baseline is the **SRS v0.1** — [docs/SRS.md](docs/SRS.md) (original: [docx](docs/Contract_Obligation_SRS_Draft.docx)).

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 |
| Background jobs | Celery + Redis (added with the modules that need them) |
| Frontend | React 19, TypeScript, Vite, Ant Design 6, react-i18next (English + Arabic / RTL) |
| Quality | ruff, mypy, pytest · oxlint, Prettier, tsc, Vitest · GitHub Actions CI |

Why these choices: [docs/architecture.md](docs/architecture.md) and [docs/decisions.md](docs/decisions.md).

## Repository layout

```
backend/     FastAPI application, migrations and tests
frontend/    React single-page application
docs/        SRS, architecture, database schema, roles, API standards, traceability, decisions
docs/brand/  ConTrack logo files and colours
docs/design/ UI design (ConTrack-UI.pdf) — the visual spec for every screen
infra/       Local infrastructure helpers (Postgres init scripts)
.github/     CI workflow, PR and issue templates
docker-compose.yml   Local infrastructure (Postgres)
```

## Getting started

### Prerequisites

- Python 3.12+
- Node.js 22+ (CI uses 24)
- Docker with Docker Compose

### 1. Configure and start infrastructure

```bash
cp .env.example .env
docker compose up -d --wait
```

This starts PostgreSQL on **localhost:5433** with two databases: `coms` (development) and `coms_test` (tests).

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.cli create-admin --email you@example.com --name "Your Name"   # first administrator
uvicorn app.main:app --reload
```

`create-admin` asks for a password (or reads `COMS_ADMIN_PASSWORD`). Sign in with that account, then create other
users from **Users** in the app. People can also register themselves with **Create an account** on the login page;
they start with the Employee role (`SELF_SIGNUP_ENABLED` / `SELF_SIGNUP_ROLE` in `.env`).

- API: http://localhost:8000/api/v1
- Swagger UI: http://localhost:8000/api/docs
- Health: http://localhost:8000/api/v1/health and `/api/v1/health/ready`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Requests to `/api` are proxied to the backend on port 8000.

### API types for the frontend

The frontend's request/response types are generated from the backend's OpenAPI document. After changing an endpoint
or schema, run (with the backend virtual environment active):

```bash
cd frontend
npm run api:generate   # writes src/api/openapi.json and src/api/schema.d.ts
```

A backend test fails if the committed `openapi.json` no longer matches the API.

## Running checks

| | Backend (`backend/`) | Frontend (`frontend/`) |
|---|---|---|
| Lint | `ruff check .` | `npm run lint` |
| Format | `ruff format --check .` | `npm run format:check` |
| Types | `mypy app tests` | `npm run typecheck` |
| Tests | `pytest` (needs `docker compose up`) | `npm test` |

CI runs all of these on every pull request.

## Documentation

| Document | Contents |
|---|---|
| [SRS.md](docs/SRS.md) | The requirements (source of truth) |
| [architecture.md](docs/architecture.md) | Components, modules, extraction isolation, background jobs, security |
| [database-schema.md](docs/database-schema.md) | Entities, fields, relationships, constraints |
| [roles-and-permissions.md](docs/roles-and-permissions.md) | Roles, permission matrix, data scope, enforcement |
| [api-standards.md](docs/api-standards.md) | REST conventions, errors, pagination, auth |
| [traceability.md](docs/traceability.md) | Requirement → use case → frontend → backend → test case |
| [decisions.md](docs/decisions.md) | Defaults for open business questions and technical decisions |

## Delivery plan

Work is delivered module by module, each in its own branch and pull request into `develop`
(see [CONTRIBUTING.md](CONTRIBUTING.md)).

| # | Module | Requirements | Status |
|---|---|---|---|
| 0 | Repository foundation | — | ✅ |
| 1 | Auth, users & RBAC | FR-AUTH-*, FR-USER-*, 3.2, NFR-SEC-01..04 | 🚧 in review |
| 2 | Audit trail | FR-AUD-* | ⏳ |
| 3 | Parties & properties | FR-PARTY-*, FR-PROP-* | ⏳ |
| 4 | Contracts | FR-CON-*, 4.4, BR-02, BR-03, BR-06, BR-07 | ⏳ |
| 5 | Documents | FR-DOC-*, BR-09, NFR-SEC-05, NFR-SEC-06 | ⏳ |
| 6 | Obligations | FR-OBL-*, 4.10, BR-01, BR-04, BR-08 | ⏳ |
| 7 | Search & filtering | FR-SEARCH-*, NFR-PERF-02 | ⏳ |
| 8 | Notifications | FR-NOTIF-* | ⏳ |
| 9 | Extraction | FR-EXT-*, §8, BR-05, NFR-PERF-03, NFR-REL-03 | ⏳ |
| 10 | Dashboard & reports | FR-REP-* | ⏳ |
