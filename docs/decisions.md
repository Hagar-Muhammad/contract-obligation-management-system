# Decisions

## Business decisions (SRS 13.2)

The SRS leaves 19 questions open. Development proceeds with the **defaults below**, chosen to be safe and
easy to change. Each row says where the default lives, so changing it is a contained edit.
The same list is tracked as a checklist in the GitHub issue **"Open business decisions"**; when the business
confirms or changes an item, update this table and tick the issue.

| ID | Question (13.2) | Default used | Where it lives / how to change |
|---|---|---|---|
| D-01 | Confirm final user roles and permissions. | The 6 roles of 2.3 and the 3.2 matrix. "Allowed" = granted but flagged for confirmation; "View" = read-only; "Limited" = restricted to own data. Property Managers are scoped to assigned properties, Employees to their assigned obligations. See [roles-and-permissions.md](./roles-and-permissions.md). | Seed data (`role_permissions`); changeable without code. |
| D-02 | One company or multi-tenant? | **Single company.** No tenant column. | Adding tenancy later means a `tenant_id` on top-level tables; IDs are UUIDs so data can be merged. |
| D-03 | Final contract types. | The 10 types of 4.4. | `contract_types` lookup table (seed). |
| D-04 | Can a contract be linked to multiple properties? | **Yes** (many-to-many), as FR-PROP-01 says "one or more". | `contract_properties` table. Restricting to one is a validation rule. |
| D-05 | Required fields for individual and company parties? | Individual: full name required; national ID/passport, email, phone optional. Organization: company name required; registration no., tax no., contact optional. | Pydantic schema for parties. |
| D-06 | Mandatory contract fields. | As 7.2: number, title, type, start date, status, at least one party. End date required only when the contract is time-bound; currency required when a value is entered. | Contract schema + service. |
| D-07 | Mandatory obligation fields. | As 7.3: contract, title, description, responsible party, priority, status. Due date required unless the obligation is ongoing (no deadline). | Obligation schema + service. |
| D-08 | Penalties as structured data? | **Free-text `penalty_text`** on the obligation for Release 1; no penalty calculation. | Column on `obligations`. Structured penalties are in Future Enhancements (13.3). |
| D-09 | Renewal dates and renewal reminders? | **Yes**: optional `renewal_date` on contracts, reminded with the same schedule as obligations. | `contracts.renewal_date` + reminder job. |
| D-10 | Reminder schedule? | **7, 3 and 1 days** before the due date, plus on the day it becomes overdue. | Setting `REMINDER_DAYS_BEFORE=7,3,1`. |
| D-11 | Notification channels? | **Both in-app and email.** Email is sent via SMTP (Mailpit locally). | Settings `NOTIFY_EMAIL_ENABLED`, `SMTP_*`. |
| D-12 | Document formats and maximum size? | **PDF, DOCX, PNG, JPG**, up to **20 MB** per file. | Settings `UPLOAD_ALLOWED_TYPES`, `UPLOAD_MAX_BYTES`. |
| D-13 | Is OCR/AI extraction mandatory for Release 1? | **Included in Release 1** using text-layer reading + OCR + rules. An external AI (LLM) provider exists as an adapter but is **off by default**. | Setting `EXTRACTION_PROVIDER`; providers are pluggable (see architecture.md §4). |
| D-14 | Exactly which information must be extracted? | Release 1: contract number, title/type, parties, start/end dates, value/currency, renewal date, obligations with due dates and responsible parties. Termination conditions, penalties and clauses are captured as text snippets when found. | Extraction result schema (one place). |
| D-15 | Must every extracted result be reviewed before saving? | **Yes, always** (BR-05). Nothing extracted becomes official data without an authorized user's confirmation. | Not configurable by design. |
| D-16 | Arabic contracts/documents? | **Yes**: UI in English and Arabic (RTL), Arabic + English OCR, search that works on Arabic text. | i18n locale files; OCR language setting. |
| D-17 | Final contract statuses and transitions? | `draft → active → expired / terminated`; `draft → cancelled`. Archiving is separate from status (an archived contract keeps its status). | `contract_statuses` lookup + transition map in the contract service. |
| D-18 | Expected volumes? | Planned for up to ~200 users, ~50,000 contracts, ~500,000 obligations, ~200,000 documents. Server-side pagination and indexes from day one. | Revisit with real numbers before production sizing. |
| D-19 | Backup and document retention? | Daily database backups kept 30 days; document storage included in backups; documents retained indefinitely while their contract exists. No automatic deletion. | Deployment/infrastructure configuration (not application code). |

## Technical decisions

| ID | Decision | Reason |
|---|---|---|
| T-01 | Backend: Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL 16. | OpenAPI generated from code (10.2); strongest OCR/document ecosystem for extraction. |
| T-02 | Frontend: React 19 + TypeScript + Vite + Ant Design 6 + react-i18next. | React 19 / Ant Design 6 were current when the project started; Ant Design has mature tables/forms and built-in RTL + Arabic locale. |
| T-03 | Frontend linting with **oxlint** (the Vite template default) + Prettier, instead of ESLint. | Same role, much faster, zero-config for React/TS. ESLint can be added later if a rule is missing. |
| T-04 | Local Postgres is published on host port **5433** (not 5432). | 5432 is commonly taken by a locally installed Postgres. Override with `POSTGRES_PORT`. |
| T-05 | Tests use a separate `coms_test` database. | Tests never touch development data. |
| T-06 | Background jobs with Celery + Redis (added in the modules that need them). | Mature scheduling (Beat) and separate queues so extraction scales independently (NFR-SCALE-02). |
| T-07 | UUID primary keys. | IDs in URLs do not reveal record counts; easier future data merging. |
