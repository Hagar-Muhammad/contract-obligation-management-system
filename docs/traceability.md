# Traceability Matrix

Maps every functional requirement and business rule to a use case, frontend work item, backend work item and test
case (SRS section 12). **Updated in every module PR**: when a requirement is implemented, its row gets the real
page/endpoint names and its status changes to ✅.

**Where tests live:** backend `backend/tests/test_<area>.py`; frontend next to the feature (`features/<module>/*.test.tsx`).

**Test naming:** test case `TC-CON-01` is the pytest function `test_TC_CON_01_<description>` (or a Vitest
`describe('TC-CON-01 …')`), tagged `@pytest.mark.req("FR-CON-01")`. Search the code for the TC ID to find its tests.

Status: ⏳ planned · 🚧 in progress · ✅ done (implemented and tested)

## Use cases

| ID | Use case | SRS |
|---|---|---|
| UC-01 | Log in, use the system, log out | 4.1 |
| UC-02 | Manage users and roles | 4.2, 3.2 |
| UC-03 | Manual contract creation | 9.1 |
| UC-04 | Contract creation from existing document | 9.2 |
| UC-05 | Obligation tracking | 9.3 |
| UC-06 | Manage parties | 4.5 |
| UC-07 | Manage properties and view property records | 4.6 |
| UC-08 | Manage contract documents | 4.7 |
| UC-09 | Search, filter and sort records | 4.11 |
| UC-10 | Receive and read notifications | 4.12 |
| UC-11 | View dashboard and reports | 4.13 |
| UC-12 | Review the audit trail | 4.14 |

UC-03, UC-04 and UC-05 are the workflows defined in SRS 9.1–9.3; the others are numbered here to cover every requirement.

## Functional requirements

| Requirement | Use case | Frontend | Backend | Test case | Module | Status |
|---|---|---|---|---|---|---|
| FR-AUTH-01 | UC-01 | Sign-in page (`features/auth/LoginPage.tsx`, design screen 1) incl. "Keep me signed in" | `POST /auth/login`, `POST /auth/refresh` | TC-AUTH-01 | 1 auth-users-rbac | ✅ |
| FR-AUTH-02 | UC-01 | `RequireAuth` guard; token refresh + replay in `api/client.ts` | `get_current_user` on every non-public route | TC-AUTH-02 | 1 auth-users-rbac | ✅ |
| FR-AUTH-03 | UC-01 | Permission-filtered sidebar (`components/nav.tsx`), `RequirePermission` (403 page), role matrix on Users & roles | `require_permission()` + seeded 3.2 matrix; `GET /roles` | TC-AUTH-03 | 1 auth-users-rbac | ✅ |
| FR-AUTH-04 | UC-01 | Log out button | `POST /auth/logout` (session revoked, access token rejected at once) | TC-AUTH-04 | 1 auth-users-rbac | ✅ |
| FR-USER-01 | UC-02 | Users & roles (design screen 8) → Add user | `POST /users`; `python -m app.cli create-admin` | TC-USER-01 | 1 auth-users-rbac | ✅ |
| FR-USER-02 | UC-02 | Edit user form (info, roles, password reset) | `PATCH /users/{id}` | TC-USER-02 | 1 auth-users-rbac | ✅ |
| FR-USER-03 | UC-02 | Deactivate on the edit page, Reactivate in the list | `POST /users/{id}/deactivate`, `/activate` (sessions revoked) | TC-USER-03 | 1 auth-users-rbac | ✅ |
| FR-AUD-01 | UC-12 | — | `audit.record()` (`app/modules/audit/service.py`) in the same transaction as each change; module 1 records sign-in, failed sign-in, sign-out, stolen refresh token, user created/registered/updated/password reset/deactivated/activated | TC-AUD-01 | 2 audit-trail | ✅ |
| FR-AUD-02 | UC-12 | Audit log page (`features/audit/AuditLogPage.tsx`): search, action and date filters, expandable changes | `audit_logs` (actor, action, target, timestamp, `{field: [old, new]}` changes, request id, IP); `GET /audit-logs` (`audit:view`) | TC-AUD-02 | 2 audit-trail | ✅ |
| FR-AUD-03 | UC-12 | Read-only page; hidden and blocked without `audit:view` | No write endpoints; triggers reject UPDATE, DELETE and TRUNCATE on `audit_logs` | TC-AUD-03 | 2 audit-trail | ✅ |
| FR-PARTY-01 | UC-06 | Parties list (`features/parties/PartiesPage.tsx`), Party form (`PartyFormPage.tsx`) | `GET/POST /parties`, `GET/PATCH /parties/{id}` (`party:manage` to write); duplicate official numbers → 409; audited | TC-PARTY-01 | 3 parties-properties | ✅ |
| FR-PARTY-02 | UC-06 | Party form: individual / organization switch with each type's fields | `party_type` CHECK + type-only identifier CHECKs; service rejects the other type's fields per field (422); type fixed after creation | TC-PARTY-02 | 3 parties-properties | ✅ |
| FR-PARTY-03 | UC-03 | Contract form section 3 (`features/contracts/PartiesField.tsx`): search parties, role per party, quick-create; details page Parties card | `contract_parties` (party + role); parties in `GET /contracts/{id}`; `GET /contracts?party_id=` | TC-PARTY-03 (`test_TC_CON_01_*`, `test_TC_CON_04_*`, `test_TC_BR_02_*`) | 3 parties-properties / 4 contracts | ✅ |
| FR-PROP-01 | UC-07 | Properties list + form with manager assignment; contract form: properties field | `properties`, `property_assignments`, `/properties`, `/properties/assignable-managers`; `contract_properties` set via `property_ids` on `POST/PATCH /contracts` | TC-PROP-01 | 3 parties-properties / 4 contracts | ✅ |
| FR-PROP-02 | UC-07 | Property page: "Contracts for this property" and "Obligations for this property"; contract page: "All contracts for this property" | `GET /contracts?property_id=`, `GET /obligations?property_id=` | TC-PROP-02 (`test_contract_list_search_and_filters`, `test_TC_OBL_07_*`) | 3 parties-properties / 6 obligations | ✅ |
| FR-CON-01 | UC-03 | New contract (`features/contracts/ContractFormPage.tsx`, design screen 5): suggested number, save as draft | `POST /contracts`, `GET /contracts/defaults` | TC-CON-01 | 4 contracts | ✅ |
| FR-CON-02 | UC-03 | Contract details: key facts, parties, properties (documents in module 5) | `contracts` (7.2 fields incl. renewal date, D-09), `contract_parties`, `contract_properties` | TC-CON-02 (`test_TC_CON_01_contract_manager_creates_*`) | 4 contracts | ✅ |
| FR-CON-03 | UC-03 | Contracts list (screen 3) and details page (screen 4) with activity | `GET /contracts`, `GET /contracts/{id}`, `GET /contracts/{id}/activity` (scoped) | TC-CON-03 | 4 contracts | ✅ |
| FR-CON-04 | UC-03 | Edit contract page; status choices limited to allowed transitions | `PATCH /contracts/{id}`; audited as `contract.updated` / `contract.status_changed` | TC-CON-04 | 4 contracts | ✅ |
| FR-CON-05 | UC-03 | Archive / Restore on the details page and row menu; Archived tab | `POST /contracts/{id}/archive`, `/restore`; archived contracts read-only | TC-CON-05 | 4 contracts | ✅ |
| FR-CON-06 | UC-03 | Type and status selects from the lookup API | `contract_types`, `contract_statuses` (seeded, `is_active`), `GET /contract-types`, `GET /contract-statuses`; D-17 transitions | TC-CON-06 | 4 contracts | ✅ |
| FR-DOC-01 | UC-08 | Documents panel → Upload (`features/documents/DocumentsPanel.tsx`); new contract section 4 (`NewContractFiles.tsx`) | `POST /contracts/{id}/documents` (`document:upload`, contract in scope, not archived) | TC-DOC-01 | 5 documents | ✅ |
| FR-DOC-02 | UC-08 | Download / open the original | Write-once `LocalStorage` (`app/core/storage.py`), SHA-256 recorded; no update or delete endpoint | TC-DOC-02 | 5 documents | ✅ |
| FR-DOC-03 | UC-08 | Click a name to open (PDF/images), download button to save; fetched with the user's token | `GET /documents/{id}/download` (scoped by contract, sandboxed attachment, no-store); downloads audited | TC-DOC-03 | 5 documents | ✅ |
| FR-DOC-04 | UC-08 | Upload dialog: type and size checked before sending; server reason shown | Content detection (PDF/DOCX/PNG/JPG, macro Word refused) → 415; size limit → 413 (middleware + service); empty → 422 | TC-DOC-04 | 5 documents | ✅ |
| FR-DOC-05 | UC-08 | Documents panel: name, type, size, kind, upload date | `contract_documents` metadata; `GET /contracts/{id}/documents`, `GET /documents/{id}` | TC-DOC-05 | 5 documents | ✅ |
| FR-OBL-01 | UC-05 | New obligation (`features/obligations/ObligationFormPage.tsx`), "Add obligation" on the contract page | `POST /obligations` (contract in scope and not archived, else 422) | TC-OBL-01 | 6 obligations | ✅ |
| FR-OBL-02 | UC-05 | Obligation panel and form (title, description, party, owner, dates or ongoing, priority, repeats, penalty, notes) | `obligations` (7.3 fields, D-07, D-08), `GET /obligations/{id}` | TC-OBL-02 | 6 obligations | ✅ |
| FR-OBL-03 | UC-05 | Form: party chosen from the contract's parties, owner from the user directory | Party must belong to the contract; owner must be an active user; `GET /users/directory` | TC-OBL-03 | 6 obligations | ✅ |
| FR-OBL-04 | UC-05 | Panel: Update status + note + Save update (design screen 7) | `POST /obligations/{id}/status`, audited with the note | TC-OBL-04 | 6 obligations | ✅ |
| FR-OBL-05 | UC-05 | Overdue chip, red due dates and "N days overdue", Overdue pills | `effective_status` derived from the due date (BR-04); daily job `mark_overdue` records `overdue_at` + system audit (`python -m app.cli run-daily-jobs`) | TC-OBL-05 / TC-BR-04 | 6 obligations | ✅ |
| FR-OBL-06 | UC-05 | Repeats: weekly, monthly, quarterly, every 6 months, yearly or a custom RRULE | `recurrence_rule` + `series_id`; next occurrence on completion/cancellation and by the daily job (`roll_recurrences`) | TC-OBL-06 | 6 obligations | ✅ |
| FR-OBL-07 | UC-05 | Obligations list: chips, search, contract/owner/priority/due filters, only mine, sort | `GET /obligations` query params, `GET /obligations/counts` | TC-OBL-07 | 6 obligations | ✅ |
| FR-SEARCH-01 | UC-09 | Contracts list search box (number, title, party, property) | `GET /contracts?q=` | TC-SEARCH-01 (`test_contract_list_search_and_filters`) | 4 contracts / 7 search-filtering | ✅ contracts; top-bar search in module 7 |
| FR-SEARCH-02 | UC-09 | Contracts list filter bar: type, party, property, term, tabs, sort | `GET /contracts` filters (`view`, `type_code`, `party_id`, `property_id`, `term_from/to`, `sort`) | TC-SEARCH-02 (`test_contract_list_search_and_filters`, `test_TC_CON_05_list_tabs_and_counts`) | 4 contracts / 7 search-filtering | ✅ |
| FR-SEARCH-03 | UC-09 | Obligations list filter bar | `GET /obligations` filters | TC-SEARCH-03 (`test_TC_OBL_07_*`) | 6 obligations / 7 search-filtering | ✅ |
| FR-SEARCH-04 | UC-09 | Paginated tables (users, audit, parties, properties, contracts) | Shared pagination (`page`, `page_size`, `total`) in `app/core/pagination.py` | TC-SEARCH-04 (list tests per module) | 7 search-filtering | ✅ |
| FR-NOTIF-01 | UC-10 | Notification bell / list | Reminder job (configured rules) | TC-NOTIF-01 | 8 notifications | ⏳ |
| FR-NOTIF-02 | UC-10 | Notification bell / list | Overdue notification on status change | TC-NOTIF-02 | 8 notifications | ⏳ |
| FR-NOTIF-03 | UC-10 | Mark read/unread | `POST /notifications/{id}/read` | TC-NOTIF-03 | 8 notifications | ⏳ |
| FR-NOTIF-04 | UC-10 | Notification preferences | In-app + email channels | TC-NOTIF-04 | 8 notifications | ⏳ |
| FR-EXT-01 | UC-04 | "Extract" action + job status | `POST /extraction-jobs`, worker, provider interface | TC-EXT-01 | 9 extraction | ⏳ |
| FR-EXT-02 | UC-04 | Review page: parties section | Party candidate extraction | TC-EXT-02 | 9 extraction | ⏳ |
| FR-EXT-03 | UC-04 | Review page: dates section | Date/deadline candidate extraction | TC-EXT-03 | 9 extraction | ⏳ |
| FR-EXT-04 | UC-04 | Review page: obligations section | Obligation candidate extraction | TC-EXT-04 | 9 extraction | ⏳ |
| FR-EXT-05 | UC-04 | Extraction Review page | Extraction review/confirm API | TC-EXT-05 | 9 extraction | ⏳ |
| FR-EXT-06 | UC-04 | "Source" link on confirmed data | `source_document_id` on contract/obligation | TC-EXT-06 | 9 extraction | ⏳ |
| FR-REP-01 | UC-11 | Dashboard page | `GET /dashboard` | TC-REP-01 | 10 dashboard-reports | ⏳ |
| FR-REP-02 | UC-11 | Dashboard: obligation status counts | Scoped status counts | TC-REP-02 | 10 dashboard-reports | ⏳ |
| FR-REP-03 | UC-11 | Overdue / upcoming reports | `GET /reports/obligations/overdue`, `/upcoming` | TC-REP-03 | 10 dashboard-reports | ⏳ |
| FR-REP-04 | UC-11 | Contract reports | `GET /reports/contracts?group_by=type,status` | TC-REP-04 | 10 dashboard-reports | ⏳ |
| FR-REP-05 | UC-11 | Export button | CSV export endpoints | TC-REP-05 | 10 dashboard-reports | ⏳ |

## Change requests

| Request | Use case | Frontend | Backend | Test case | Module | Status |
|---|---|---|---|---|---|---|
| CR-01 self sign-up | UC-01 | Sign-up page (`features/auth/SignUpPage.tsx`), "Create an account" link on the login page | `POST /auth/register`, `GET /auth/options` | TC-CR-01 | 1 auth-users-rbac | ✅ |

## Business rules

| Rule | Enforced in | Test case | Module | Status |
|---|---|---|---|---|
| BR-01 | `obligations.contract_id NOT NULL` FK; service requires a contract in scope | TC-BR-01 (`test_TC_OBL_01_*`) | 6 obligations | ✅ |
| BR-02 | Contract service (`_parties`: ≥1, each once, must exist) + schema `min_length=1`; same transaction | TC-BR-02 | 4 contracts | ✅ |
| BR-03 | Service check (field error on `end_date`) + DB `CHECK end_not_before_start`; form validation | TC-BR-03 | 4 contracts | ✅ |
| BR-04 | Derived overdue (`due_date < today` and open) in every query and response; daily job records it | TC-BR-04 | 6 obligations | ✅ |
| BR-05 | Extraction confirm flow (candidates separate) | TC-BR-05 | 9 extraction | ⏳ |
| BR-06 | `require_permission()` on every write endpoint | TC-BR-06 | 1 auth-users-rbac (+ every module) | 🚧 users, parties, properties, contracts, documents and obligations done; each module adds its endpoints |
| BR-07 | `GET /contracts` without `view` excludes archived; Archived tab asks with `view=archived` | TC-BR-07 (`test_TC_CON_05_*`) | 4 contracts | ✅ |
| BR-08 | `recurrence.normalise()`: RFC 5545 RRULE, weekly/monthly/yearly only, must repeat, needs a due date | TC-BR-08 | 6 obligations | ✅ |
| BR-09 | `contract_documents.contract_id NOT NULL` FK; upload only through a contract in scope, not archived; new-contract files uploaded after the contract exists | TC-BR-09 | 5 documents | ✅ |

## Non-functional requirements with automated tests

| Requirement | Test | Status |
|---|---|---|
| NFR-MAIN-01 | `backend/tests/test_errors.py` (error envelope) | ✅ |
| NFR-REL-02 | `backend/tests/test_errors.py::test_unhandled_errors_do_not_leak_implementation_details` | ✅ |
| NFR-UX-02 | `backend/tests/test_errors.py::test_validation_errors_list_every_invalid_field`; `users.test.tsx` (server field errors shown on the form) | 🚧 each new form adds tests |
| NFR-SEC-01 | `test_auth.py::test_TC_AUTH_02_every_non_public_endpoint_rejects_unauthenticated_requests` (walks every route in the OpenAPI document) | ✅ |
| NFR-SEC-02 | `test_rbac.py` (seeded matrix = SRS 3.2, per-role permissions), `test_users.py::test_TC_BR_06_*`; data scope: `test_parties.py::test_party_directory_follows_data_scope`, `test_properties.py::test_property_manager_sees_only_assigned_properties` | ✅ |
| NFR-SEC-03 | `test_auth.py::test_passwords_are_stored_as_argon2_hashes` | ✅ |
| NFR-SEC-04 | `test_security.py` (HSTS + Secure cookies in production, weak JWT secret refused) | ✅ |
| NFR-MAIN-03 | `test_request_context.py` (`X-Request-ID` on every response and in every log line); `test_audit.py` (important actions recorded) | ✅ |
| NFR-SEC-05, NFR-SEC-06 | `test_documents.py` (scope per role, no public path, sandboxed downloads; content-type detection, size limit, file-name cleaning); every form's validation tests | ✅ |
| NFR-PERF-02 | Module 7 tests (page size cap, server-side filters) | ⏳ |
| NFR-PERF-03, NFR-REL-03 | Module 9 tests | ⏳ |
