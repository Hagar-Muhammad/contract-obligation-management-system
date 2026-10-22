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
| FR-AUTH-01 | UC-01 | Login page (`features/auth/LoginPage.tsx`) | `POST /auth/login`, `POST /auth/refresh` | TC-AUTH-01 | 1 auth-users-rbac | ✅ |
| FR-AUTH-02 | UC-01 | `RequireAuth` guard; token refresh + replay in `api/client.ts` | `get_current_user` on every non-public route | TC-AUTH-02 | 1 auth-users-rbac | ✅ |
| FR-AUTH-03 | UC-01 | Permission-filtered menu, `RequirePermission` (403 page) | `require_permission()` + seeded 3.2 matrix | TC-AUTH-03 | 1 auth-users-rbac | ✅ |
| FR-AUTH-04 | UC-01 | Log out button | `POST /auth/logout` (session revoked, access token rejected at once) | TC-AUTH-04 | 1 auth-users-rbac | ✅ |
| FR-USER-01 | UC-02 | Users list → New user form | `POST /users`; `python -m app.cli create-admin` | TC-USER-01 | 1 auth-users-rbac | ✅ |
| FR-USER-02 | UC-02 | Edit user form (info, roles, password reset) | `PATCH /users/{id}` | TC-USER-02 | 1 auth-users-rbac | ✅ |
| FR-USER-03 | UC-02 | Deactivate / Activate actions | `POST /users/{id}/deactivate`, `/activate` (sessions revoked) | TC-USER-03 | 1 auth-users-rbac | ✅ |
| FR-AUD-01 | UC-12 | — | Audit service called by state-changing services | TC-AUD-01 | 2 audit-trail | ⏳ |
| FR-AUD-02 | UC-12 | Audit log page | `audit_logs` schema, `GET /audit-logs` | TC-AUD-02 | 2 audit-trail | ⏳ |
| FR-AUD-03 | UC-12 | — (read-only UI) | No write endpoints + DB trigger blocking UPDATE/DELETE | TC-AUD-03 | 2 audit-trail | ⏳ |
| FR-PARTY-01 | UC-06 | Parties list / Party form | `/parties` CRUD | TC-PARTY-01 | 3 parties-properties | ⏳ |
| FR-PARTY-02 | UC-06 | Party form (type-specific fields) | Party type validation | TC-PARTY-02 | 3 parties-properties | ⏳ |
| FR-PARTY-03 | UC-03 | Contract form: parties section | `contract_parties`, `/contracts/{id}/parties` | TC-PARTY-03 | 3 parties-properties / 4 contracts | ⏳ |
| FR-PROP-01 | UC-07 | Contract form: properties section | `contract_properties`, `/contracts/{id}/properties` | TC-PROP-01 | 3 parties-properties / 4 contracts | ⏳ |
| FR-PROP-02 | UC-07 | Property details: contracts & obligations tabs | `GET /properties/{id}/contracts`, `/obligations?property_id=` | TC-PROP-02 | 3 parties-properties / 6 obligations | ⏳ |
| FR-CON-01 | UC-03 | Create Contract page | `POST /contracts` | TC-CON-01 | 4 contracts | ⏳ |
| FR-CON-02 | UC-03 | Contract details page | Contract model (7.2 fields) | TC-CON-02 | 4 contracts | ⏳ |
| FR-CON-03 | UC-03 | Contract details page | `GET /contracts/{id}` | TC-CON-03 | 4 contracts | ⏳ |
| FR-CON-04 | UC-03 | Edit Contract page | `PATCH /contracts/{id}` + audit | TC-CON-04 | 4 contracts | ⏳ |
| FR-CON-05 | UC-03 | Archive action, "show archived" toggle | `POST /contracts/{id}/archive` | TC-CON-05 | 4 contracts | ⏳ |
| FR-CON-06 | UC-03 | Type/status selects from lookup API | `contract_types`, `contract_statuses` validation | TC-CON-06 | 4 contracts | ⏳ |
| FR-DOC-01 | UC-08 | Document upload on contract page | `POST /contracts/{id}/documents` | TC-DOC-01 | 5 documents | ⏳ |
| FR-DOC-02 | UC-08 | Download original | Write-once storage + SHA-256 | TC-DOC-02 | 5 documents | ⏳ |
| FR-DOC-03 | UC-08 | View/download action | `GET /documents/{id}/download` (permission-checked) | TC-DOC-03 | 5 documents | ⏳ |
| FR-DOC-04 | UC-08 | Upload error messages | Type (content sniffing) + size validation | TC-DOC-04 | 5 documents | ⏳ |
| FR-DOC-05 | UC-08 | Documents table (metadata) | `contract_documents` metadata | TC-DOC-05 | 5 documents | ⏳ |
| FR-OBL-01 | UC-05 | Create Obligation form | `POST /contracts/{id}/obligations` | TC-OBL-01 | 6 obligations | ⏳ |
| FR-OBL-02 | UC-05 | Obligation details | Obligation model (7.3 fields) | TC-OBL-02 | 6 obligations | ⏳ |
| FR-OBL-03 | UC-05 | Assignment fields | Responsible party/user validation | TC-OBL-03 | 6 obligations | ⏳ |
| FR-OBL-04 | UC-05 | Status update action | `POST /obligations/{id}/status` + audit | TC-OBL-04 | 6 obligations | ⏳ |
| FR-OBL-05 | UC-05 | Obligation list/details (Overdue badge) | Overdue status logic + scheduled job | TC-OBL-05 | 6 obligations | ⏳ |
| FR-OBL-06 | UC-05 | Recurrence editor | RRULE storage + occurrence job | TC-OBL-06 | 6 obligations | ⏳ |
| FR-OBL-07 | UC-05 | Obligations list (search/filter/sort) | `GET /obligations` query params | TC-OBL-07 | 6 obligations / 7 search-filtering | ⏳ |
| FR-SEARCH-01 | UC-09 | Contracts list search box | `GET /contracts?q=` | TC-SEARCH-01 | 7 search-filtering | ⏳ |
| FR-SEARCH-02 | UC-09 | Contracts list filter bar | `GET /contracts` filters | TC-SEARCH-02 | 7 search-filtering | ⏳ |
| FR-SEARCH-03 | UC-09 | Obligations list filter bar | `GET /obligations` filters | TC-SEARCH-03 | 7 search-filtering | ⏳ |
| FR-SEARCH-04 | UC-09 | Paginated data table | Shared pagination (`page`, `page_size`, `total`) | TC-SEARCH-04 | 7 search-filtering | ⏳ |
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
| BR-01 | Obligation service + `NOT NULL` FK | TC-BR-01 | 6 obligations | ⏳ |
| BR-02 | Contract service (≥1 party, same transaction) | TC-BR-02 | 4 contracts | ⏳ |
| BR-03 | Pydantic validator + DB `CHECK` | TC-BR-03 | 4 contracts | ⏳ |
| BR-04 | Overdue status logic | TC-BR-04 | 6 obligations | ⏳ |
| BR-05 | Extraction confirm flow (candidates separate) | TC-BR-05 | 9 extraction | ⏳ |
| BR-06 | `require_permission()` on every write endpoint | TC-BR-06 | 1 auth-users-rbac (+ every module) | 🚧 user management done; each module adds its endpoints |
| BR-07 | Contract list default filter | TC-BR-07 | 4 contracts | ⏳ |
| BR-08 | RRULE validation | TC-BR-08 | 6 obligations | ⏳ |
| BR-09 | Document service + `NOT NULL` FK | TC-BR-09 | 5 documents | ⏳ |

## Non-functional requirements with automated tests

| Requirement | Test | Status |
|---|---|---|
| NFR-MAIN-01 | `backend/tests/test_errors.py` (error envelope) | ✅ |
| NFR-REL-02 | `backend/tests/test_errors.py::test_unhandled_errors_do_not_leak_implementation_details` | ✅ |
| NFR-UX-02 | `backend/tests/test_errors.py::test_validation_errors_list_every_invalid_field`; `users.test.tsx` (server field errors shown on the form) | 🚧 each new form adds tests |
| NFR-SEC-01 | `test_auth.py::test_TC_AUTH_02_every_non_public_endpoint_rejects_unauthenticated_requests` (walks every route in the OpenAPI document) | ✅ |
| NFR-SEC-02 | `test_rbac.py` (seeded matrix = SRS 3.2, per-role permissions), `test_users.py::test_TC_BR_06_*` | ✅ |
| NFR-SEC-03 | `test_auth.py::test_passwords_are_stored_as_argon2_hashes` | ✅ |
| NFR-SEC-04 | `test_security.py` (HSTS + Secure cookies in production, weak JWT secret refused) | ✅ |
| NFR-SEC-05, NFR-SEC-06 | Module 5 tests | ⏳ |
| NFR-PERF-02 | Module 7 tests (page size cap, server-side filters) | ⏳ |
| NFR-PERF-03, NFR-REL-03 | Module 9 tests | ⏳ |
