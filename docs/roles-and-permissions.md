# Roles and Permissions

Source: SRS 2.3 (user classes) and 3.2 (proposed permissions). The SRS marks both as **proposed, subject to business
confirmation** (open decision 1), so they are stored as **seed data** in the database — changing them does not need a
code change.

## Roles (SRS 2.3)

| Code | Role | Responsibilities | Data scope |
|---|---|---|---|
| `admin` | Administrator | Manage users, roles, permissions, and system settings. | All records |
| `contract_manager` | Contract Manager | Manage contracts, parties, documents, and obligations. | All records |
| `legal` | Legal User | Review contract information, extracted data, and obligations. | All records |
| `property_manager` | Property Manager | Manage contracts and obligations related to assigned properties. | Contracts linked to their assigned properties, and those contracts' obligations and documents |
| `employee` | Employee / Responsible User | View and complete assigned obligations and update status. | Obligations assigned to them, and the contracts those obligations belong to |
| `management` | Management | View dashboards, reports, contract status, and obligation summaries. | All records, read-only |

A user can hold more than one role; their permissions are the union of their roles, and their data scope is the
widest scope among their roles.

### Self-registered accounts (CR-01)

Accounts created through **Create an account** get exactly one role, `employee` by default
(`SELF_SIGNUP_ROLE`). The visitor cannot choose or send a role. An administrator can change it later.

## Permission matrix (SRS 3.2)

| Capability | Permission code | Admin | Contract Manager | Legal | Property Manager | Employee | Management |
|---|---|---|---|---|---|---|---|
| View contracts | `contract:view` | Yes | Yes | Yes | Allowed | Allowed | Yes |
| Create/edit contracts | `contract:create`, `contract:edit` | Yes | Yes | Allowed | Allowed | No | No |
| Archive contracts | `contract:archive` | Yes | Allowed | Allowed | Allowed | No | No |
| Upload documents | `document:upload` | Yes | Yes | Yes | Yes | Allowed | No |
| Confirm extracted data | `extraction:confirm` | Yes | Yes | Yes | Allowed | No | No |
| Create obligations | `obligation:create` | Yes | Yes | Yes | Yes | Allowed | No |
| Update assigned obligations | `obligation:update` | Yes | Yes | Yes | Yes | Yes | View |
| Manage users | `user:manage` | Yes | No | No | No | No | No |
| View reports | `report:view` | Yes | Yes | Yes | Yes | Limited | Yes |

### How the cell values are implemented (decision D-01)

| Cell value | Meaning in the system |
|---|---|
| **Yes** | Permission granted. |
| **Allowed** | Permission granted **within the role's data scope**, and flagged for business confirmation. Shown as **Scoped** in the UI (as in the design). Listed in `PENDING_CONFIRMATION` in `users/rbac.py` and returned by `GET /roles` as `scoped_permissions`. |
| **No** | Permission not granted. Requests are rejected with `403 Forbidden`. |
| **View** | Read-only: Management can see obligations but not change them (`obligation:view` only). |
| **Limited** | Granted, restricted to the user's data scope: an Employee's reports only count their own obligations. |

Permissions answer "may this user perform this action?". **Data scope** (last column of the roles table) answers
"on which records?". Both are always checked in the backend.

## Supporting permissions (not in the 3.2 matrix)

These are needed by the SRS functions but are not listed in 3.2. Defaults below; confirm with the business.

| Permission code | Purpose | Granted to |
|---|---|---|
| `obligation:view` | View obligations | All roles (within data scope) |
| `document:view` | View/download documents (FR-DOC-03) | Everyone with `contract:view` on that contract |
| `party:manage` | Create/update parties (FR-PARTY-01) | Admin, Contract Manager, Legal, Property Manager |
| `property:manage` | Create/update properties and assignments (FR-PROP-01) | Admin, Contract Manager |
| `extraction:run` | Start extraction on a document (FR-EXT-01) | Everyone with `document:upload` |
| `report:export` | Export report data (FR-REP-05) | Admin, Contract Manager, Legal, Management |
| `audit:view` | Read the audit log (10.1 Audit) | Admin |
| `role:manage` | Change role → permission mapping | Admin |

## Enforcement

- Every endpoint declares the permission it needs: `Depends(require_permission("contract:create"))`.
  Missing authentication → `401`; missing permission → `403` (FR-AUTH-02, FR-AUTH-03, NFR-SEC-02).
- Data scope by record type (each module adds its own):

  | Records | All-records roles | Property Manager | Employee |
  |---|---|---|---|
  | Contracts | All | Contracts linked to an assigned property (new contracts must link one, T-27), and contracts of obligations assigned to them | Contracts of the obligations assigned to them |
  | Obligations | All | Obligations of their contracts, and obligations assigned to them | Obligations assigned to them; they update the status and add evidence, not the details (T-41) |
  | Parties | All | All (holds `party:manage`; picks parties for contracts) | Parties of the contracts they can see |
  | Properties | All | Assigned properties only | Properties of the contracts they can see |

- Data scope is applied inside services, so list endpoints simply never return out-of-scope records, and fetching an
  out-of-scope record by ID returns `404` (not `403`) to avoid revealing that it exists.
- The frontend receives the current user's permission codes from `GET /api/v1/auth/me` and hides actions the user
  cannot perform. This is for usability only; the backend is the authority (Appendix B).
- Each permission has at least one test proving an allowed role succeeds and a denied role gets `403`.
