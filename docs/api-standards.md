# API Standards

Applies to every backend endpoint. Source: SRS 10.1 (API areas) and 10.2 (API standards); supports NFR-MAIN-01.

## 1. Basics

| Topic | Standard |
|---|---|
| Transport | HTTPS in production (NFR-SEC-04). |
| Base path | `/api/v1`. A breaking change gets a new version prefix. |
| Format | JSON (`application/json; charset=utf-8`). File upload uses `multipart/form-data`; download streams the file. |
| Documentation | OpenAPI 3 generated from code at `/api/v1/openapi.json`; Swagger UI at `/api/docs`, ReDoc at `/api/redoc`. |
| Naming | Plural, kebab-case resource paths (`/contract-types`); `snake_case` JSON fields; IDs are UUID strings. |
| Dates | `YYYY-MM-DD` for business dates; ISO 8601 UTC with `Z` for timestamps (`2026-10-22T09:30:00Z`). |
| Money | `{"value_amount": "125000.00", "currency": "EGP"}` — amount as a decimal string to avoid float rounding. |
| Language | `Accept-Language: en` or `ar` selects the language of messages and lookup labels. |

## 2. API areas (SRS 10.1)

| Area | Route prefix | Responsibilities |
|---|---|---|
| Authentication | `/auth` | Login, logout, token refresh, current user (`/auth/me`), password operations if enabled. |
| Users/Roles | `/users`, `/roles` | User management and role assignment. |
| Contracts | `/contracts`, `/contract-types`, `/contract-statuses` | CRUD/archive, search, filters, statuses, types. |
| Parties | `/parties`, `/contracts/{id}/parties` | Party CRUD and contract-party relationships. |
| Properties | `/properties`, `/contracts/{id}/properties` | Property CRUD/association. |
| Documents | `/contracts/{id}/documents`, `/documents/{id}` | Upload, metadata, secure retrieval (`/documents/{id}/download`). |
| Extraction | `/extraction-jobs`, `/extraction-results` | Start processing, status, results, review/confirmation. |
| Obligations | `/obligations`, `/contracts/{id}/obligations` | CRUD, assignment, status, due dates, recurrence, filters. |
| Notifications | `/notifications` | List, mark read/unread, delivery tracking. |
| Reports | `/reports`, `/dashboard` | Dashboard KPIs, report queries, exports. |
| Audit | `/audit-logs` | Authorized audit log access (read-only). |
| Health | `/health`, `/health/ready` | Liveness and readiness (database reachable). |

## 3. HTTP methods and status codes

| Operation | Method & path | Success |
|---|---|---|
| List | `GET /contracts` | `200` with a page object |
| Read | `GET /contracts/{id}` | `200` |
| Create | `POST /contracts` | `201` with the created resource and a `Location` header |
| Partial update | `PATCH /contracts/{id}` | `200` with the updated resource |
| Action (state change) | `POST /contracts/{id}/archive`, `POST /contracts/{id}/restore`, `POST /obligations/{id}/status` | `200` |
| Delete (where allowed) | `DELETE /parties/{id}` | `204` |

Errors:

| Status | Code (`error.code`) | When |
|---|---|---|
| 400 | `bad_request` | Malformed request that is not a field validation issue. |
| 401 | `unauthorized` | Missing, invalid or expired credentials (FR-AUTH-02). |
| 403 | `forbidden` | Authenticated but lacks the permission (FR-AUTH-03). |
| 404 | `not_found` | Resource does not exist **or is outside the user's data scope**. |
| 409 | `conflict` | Uniqueness or concurrent-edit conflict (e.g. duplicate contract number). |
| 413 | `payload_too_large` | Upload exceeds the size limit (FR-DOC-04). |
| 415 | `unsupported_media_type` | Upload type not allowed (FR-DOC-04). |
| 422 | `validation_error` | Field validation failed; `details` lists every invalid field (NFR-UX-02). |
| 422 | `business_rule_violation` | Valid input that breaks a business rule (BR-*). |
| 500 | `internal_error` | Unexpected error. Generic message; details only in server logs (NFR-REL-02). |
| 503 | `service_unavailable` | A dependency (e.g. the database) is down. |

## 4. Error envelope

Every error response has the same shape (implemented in `backend/app/core/errors.py`):

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [
      { "field": "body.end_date", "message": "End date must not be earlier than start date.", "type": "value_error" }
    ]
  }
}
```

- `code` is stable and machine-readable; the frontend maps it to a translated message.
- `message` is human-readable and never contains stack traces, SQL or file paths.
- `details` is present only when there is something field-specific to report.

## 5. Pagination, sorting, filtering (FR-SEARCH-*, NFR-PERF-02)

All collection endpoints are paginated **on the server**; there is no "return everything" mode.

Request:

```
GET /api/v1/obligations?page=2&page_size=25&sort=-due_date,title&status=pending,overdue&due_date_from=2026-10-01
```

| Parameter | Rule |
|---|---|
| `page` | 1-based, default `1`. |
| `page_size` | Default `25`, maximum `100`. |
| `sort` | Comma-separated fields; `-` prefix for descending. Only whitelisted fields per resource. |
| `q` | Free-text search over the resource's searchable fields (e.g. contract number, title, party, property). |
| Filters | Named query parameters. Multiple values comma-separated (`status=pending,overdue`). Ranges use `_from` / `_to`. |
| Archived | Archived contracts are excluded unless `include_archived=true` (BR-07). |

Response:

```json
{
  "items": [ { "id": "…" } ],
  "page": 2,
  "page_size": 25,
  "total": 137
}
```

## 6. Authentication and authorization

- `POST /auth/login` returns a short-lived access token in the body and sets a rotating refresh token in an
  `httpOnly`, `Secure`, `SameSite=Strict` cookie.
- Clients send `Authorization: Bearer <access token>`.
- `POST /auth/refresh` exchanges the refresh cookie for a new access token (and rotates the cookie).
- `POST /auth/logout` revokes the refresh token (FR-AUTH-04).
- Authorization is applied by dependencies on each route (`require_permission(...)`) and by data scope in services.
  See [roles-and-permissions.md](./roles-and-permissions.md).

## 7. Validation

- Request bodies are Pydantic models: types, required fields, lengths and formats are validated before any business
  logic runs (NFR-SEC-06).
- Business rules (BR-*) are validated in services and return `422 business_rule_violation`.
- Unknown fields in request bodies are rejected (`extra="forbid"`), so typos do not silently succeed.

## 8. Auditing and logging

- State-changing endpoints write an audit record (FR-AUD-01) through the audit service, in the same transaction as
  the change.
- Every request gets an `X-Request-ID` (generated if absent) that is included in logs and audit records
  (NFR-MAIN-03).
