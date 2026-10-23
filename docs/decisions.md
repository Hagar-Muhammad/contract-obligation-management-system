# Decisions

## Business decisions (SRS 13.2)

The SRS leaves 19 questions open. Development proceeds with the **defaults below**, chosen to be safe and
easy to change. Each row says where the default lives, so changing it is a contained edit.
The same list is tracked as a checklist in the GitHub issue **"Open business decisions"**; when the business
confirms or changes an item, update this table and tick the issue.

| ID | Question (13.2) | Default used | Where it lives / how to change |
|---|---|---|---|
| D-01 | Confirm final user roles and permissions. | The 6 roles of 2.3 and the 3.2 matrix. "Allowed" = granted within the role's scope, shown as "Scoped", and flagged for confirmation; "View" = read-only; "Limited" = restricted to own data. Property Managers are scoped to assigned properties, Employees to their assigned obligations. See [roles-and-permissions.md](./roles-and-permissions.md). | Seed data (`role_permissions`); changeable without code. |
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

## Change requests

Changes the project owner asked for that go beyond the SRS v0.1 text.

| ID | Change | Decided | Where it lives / how to change |
|---|---|---|---|
| CR-01 | **Open self sign-up.** Anyone can create an account from the login page and is signed in at once. New accounts get only the **Employee** role, whose data scope is "assigned obligations", so a new account sees no contract data until someone assigns it work. Administrators still create accounts with other roles (FR-USER-01) and can change roles or deactivate. | 2026-10-22, project owner (chosen over "request access" and "contact administrator") | Settings `SELF_SIGNUP_ENABLED` (default `true`) and `SELF_SIGNUP_ROLE` (default `employee`). With sign-up off, the link disappears and `POST /auth/register` returns `403`. |

Known follow-ups for CR-01: e-mail address verification and sign-up rate limiting (with module 8, which adds
e-mail delivery). Until then an address is not proven to belong to the person who registered it.

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
| T-08 | Access token in memory + single-use refresh token in an httpOnly cookie, both bound to a server-side session. | Scripts cannot read the refresh token; logout and deactivation take effect immediately instead of when a token expires (FR-AUTH-04, FR-USER-03). |
| T-09 | Password policy: 8–128 characters, no composition rules. | Follows current NIST guidance (length over complexity). Change `PASSWORD_MIN_LENGTH` in `users/schemas.py` and `UserFormPage.tsx`. |
| T-10 | E-mail addresses are validated strictly; reserved domains such as `.local` are rejected. | Avoids accounts that can never receive notification e-mails (module 8). If the company uses an internal domain, relax the check in `users/schemas.py`. |
| T-11 | Frontend API types generated with `openapi-typescript`, run through `npx` with TypeScript 5. | `openapi-typescript` does not yet support TypeScript 6 as a peer; the generated file is committed, so CI does not need it. |
| T-12 | Product name **ConTrack** (not translated); logo = open "C" track closing on a check. | Requested by the project owner. Brand assets and colours: [brand/README.md](./brand/README.md). |
| T-13 | Administrators cannot deactivate themselves or remove their own Administrator role. | Prevents locking the system out of its only administrator. |
| T-14 | **UI follows [design/ConTrack-UI.pdf](./design/ConTrack-UI.pdf)** (8 screens). Each module builds its screen from it; sidebar links to pages of later modules show a "coming soon" page until then. | Design supplied by the project owner on 2026-10-22. Fonts: Manrope + IBM Plex Sans Arabic (self-hosted via @fontsource, no external font requests). |
| T-15 | "Keep me signed in on this device": unticked (default) = browser-session cookie and a 12-hour session; ticked = 7-day cookie. | Shared or public computers do not stay signed in by accident. `UNREMEMBERED_SESSION_HOURS`, `REFRESH_TOKEN_TTL_DAYS`. |
| T-16 | "Forgot password?" explains that an administrator resets passwords until e-mail delivery exists (module 8). | Self-service reset needs e-mail. |
| T-17 | Top-bar search and notification bell from the design are added with modules 7 (search) and 8 (notifications). | They would do nothing yet; showing dead controls misleads users. |
| T-18 | **Audited events (module 2):** sign-in, sign-out, failed sign-in to an *existing* account, reuse of a stolen refresh token, and every account change (created by an admin, self sign-up, `create-admin`, edits, password resets, deactivation, reactivation). Not audited: reads, token refresh, failed sign-in with an unknown e-mail. | Covers who got in and who changed access, without noise. An unknown e-mail has no account to attach the record to, and storing what was typed could store a password typed into the wrong box. Add or remove actions in `app/modules/audit/actions.py` and the service that records them. |
| T-19 | Audit records are kept indefinitely; the application never deletes them. | FR-AUD-03; volumes are small (D-18). A retention period, if the business wants one, would be an archiving job run by a database administrator. |
| T-20 | The append-only guarantee is a database trigger. **In production the API must connect as a database role that does not own the tables**, so its credentials cannot drop the trigger. | Follow-up for deployment configuration; locally and in tests the app user owns the schema. |
| T-21 | There is no dedicated audit screen in the design; the Audit log page uses the design's Activity panel (actor, coloured dot, action, time) inside the Users & roles table layout. | Consistent with the design until the owner supplies a screen. |
| T-22 | **Party and property visibility.** Parties: users with all-records scope or `party:manage` see the whole directory; Employees see none until contracts exist. Properties: all-records scope sees all; Property Managers see their assigned properties; Employees see none yet. Out-of-scope ids return 404. | Open self sign-up (CR-01) creates Employees; they must not browse national IDs and company data. `_in_scope()` in `parties/service.py` and `properties/service.py`. |
| T-23 | Party type cannot change after creation; an official number (national ID, passport, registration no.) belongs to one party; numbers are stored without spaces, upper-cased. | A person does not become a company; duplicates would split one party's contracts. Remove the partial unique indexes to allow duplicates. |
| T-24 | Property types: residential, retail, office, industrial, land, mixed use, other. Property codes are upper-cased and unique. | Not in the SRS; a short fixed list. Make it a lookup table (like contract types) if the business wants to edit it. |
| T-25 | Only active users with the Property Manager role can be assigned to a property. | Assignments only define that role's scope; assigning anyone else would have no effect. |
| T-26 | Contract defaults: currency **EGP**, suggested numbers `CT-<year>-<NNNN>` (next after the highest used that year), and a contract is **expiring soon** when active and ending within **60 days**. | Matches the design. Settings `DEFAULT_CURRENCY`, `CONTRACT_NUMBER_PREFIX`, `EXPIRING_SOON_DAYS`. "Expiring" is shown, not stored: the status stays Active. |
| T-27 | A Property Manager's contracts are those on their assigned properties, so a contract they create or edit must stay linked to at least one of their properties, and they can link only properties they can see. | Keeps every contract they work on inside their scope (D-01). `_properties()` in `contracts/service.py`. |
| T-28 | The list's "Expired" tab (design) is named **Ended** and holds expired, terminated and cancelled contracts. | Terminated and cancelled contracts also need a home; one tab keeps the bar short. |
| T-29 | End date is optional (an open-ended contract has none); D-06's "time-bound" means "has an end date". | The SRS does not define time-bound; a flag could be added if the business needs one. |
| T-30 | One role per party in a contract. | Matches the design (one role select per party). Allowing several roles means adding `role` to the primary key. |
| T-31 | Archived contracts are read-only until restored; status changes follow D-17 with no way back to a previous status. | Archive is "put away", not "edit later"; corrections to ended contracts go through a new contract or an administrator. |
| T-32 | A contract's activity (who changed what, without IP or request id) is visible to everyone who can see the contract; the full audit log stays Admin-only. | The design shows an Activity panel on every contract. `GET /contracts/{id}/activity`. |
| T-33 | Document kinds: **Original** (the signed contract), Amendment, Annex, Other. Evidence for obligations comes with module 6. | Matches the design ("Original"); one list for every upload. |
| T-34 | Users cannot delete or replace an uploaded document in Release 1; a wrong upload stays and a corrected one is added. | FR-DOC-02 (preserve the original) and the audit trail. A "withdraw" flag could hide mistakes later without deleting the file. |
| T-35 | File type is decided by content: PDF, DOCX (not macro-enabled), PNG, JPG. The extension is ignored. | NFR-SEC-06: a renamed program or HTML page is refused. Macro-enabled Word files can carry code. |
| T-36 | Every download is recorded in the audit log (`document.downloaded`); uploads also appear in the contract's activity. | Contracts are confidential (NFR-SEC-05); the access trail shows who opened which original. |
| T-37 | Request bodies above the upload limit (20 MB + envelope) are refused for every route, before they are read. | Stops oversized uploads from filling memory or disk; no other request comes close to that size. In production the reverse proxy should apply the same limit. |
| T-38 | Local disk storage (`STORAGE_DIR`) for now; the folder must be included in backups (D-19, NFR-BACK-02). | Simple and enough for one server; an S3-compatible backend fits the same interface when hosting is decided. |
