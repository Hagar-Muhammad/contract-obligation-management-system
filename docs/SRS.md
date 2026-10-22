# Software Requirements Specification (SRS)

## Contract & Obligation Management System

**Version 0.1 – Draft**

> This Markdown file is a faithful conversion of [`Contract_Obligation_SRS_Draft.docx`](./Contract_Obligation_SRS_Draft.docx).
> The `.docx` remains the original; if the two ever disagree, raise it in an issue and fix this file.
> Requirement IDs (`FR-*`, `NFR-*`, `BR-*`) are stable and are referenced by code, tests and [`traceability.md`](./traceability.md).

| Field | Value |
|---|---|
| Document Version | 0.1 |
| Date | 19/09/2026 |
| Prepared By | [ Hagar/ Dev-Aura] |
| Reviewed By | [Magid/Noha / Dev-Aura] |
| Status | Draft – Requirements Validation |

---

## 1. Introduction

### 1.1 Purpose

The purpose of this system is to provide a centralized platform for managing real estate contracts and tracking contractual obligations. Authorized users will be able to create and manage contracts, manage parties, upload and store contract documents, extract important information and potential obligations from existing documents, assign responsibilities, monitor deadlines and statuses, and receive notifications. This SRS is intended for the frontend, backend, QA, and project teams.

### 1.2 Scope

- Create, view, edit, archive, search, and filter contracts.
- Manage parties involved in contracts and associate contracts with properties.
- Upload and manage contract documents.
- Extract important contract information and potential obligations from existing documents.
- Review and confirm extracted information before it becomes official structured data.
- Create, assign, track, and update contractual obligations.
- Track deadlines, recurring obligations, renewals, and overdue items.
- Provide notifications, dashboards, reports, and audit logs.
- Enforce role-based access control.

Out of scope for the initial release: automatic legal decision-making, automatic enforcement of contractual terms, and payment processing unless separately approved.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| Contract | A formal agreement between two or more parties. |
| Obligation | A contractual duty or commitment that a party is required to fulfill. |
| Party | An individual or organization participating in a contract. |
| Responsible User | A system user responsible for monitoring or completing an obligation. |
| Contract Type | The category/classification assigned to a contract. |
| OCR | Optical Character Recognition used to extract text from scanned documents. |
| RBAC | Role-Based Access Control. |
| Audit Trail | A record of important user and system actions. |

### 1.4 References

Project business requirements, real estate contract samples, organizational policies, applicable data protection/security requirements, and technical API/database documentation.

### 1.5 Document Overview

This document defines scope, users, functional requirements, business rules, data requirements, non-functional requirements, interfaces, workflows, acceptance criteria, and open decisions.

---

## 2. Product Overview

### 2.1 Product Perspective

The system will be a web-based contract and obligation management platform. Users may create contracts manually or upload existing contract documents. Uploaded documents may be processed to identify important contract information and potential obligations. Extracted information must be reviewed and confirmed by an authorized user before being treated as official structured data. The frontend will consume secure backend APIs connected to the database, document storage, notification services, and optional OCR/AI extraction services.

### 2.2 Product Functions

- Authentication and authorization
- User and role management
- Contract management
- Party management
- Property association
- Document upload and management
- Contract information extraction
- Obligation management
- Deadline and renewal tracking
- Notifications and reminders
- Dashboard and reporting
- Search, filtering, sorting, and pagination
- Audit logging

### 2.3 User Classes and Characteristics

| Role | Responsibilities |
|---|---|
| Administrator | Manage users, roles, permissions, and system settings. |
| Contract Manager | Manage contracts, parties, documents, and obligations. |
| Legal User | Review contract information, extracted data, and obligations. |
| Property Manager | Manage contracts and obligations related to assigned properties. |
| Employee / Responsible User | View and complete assigned obligations and update status. |
| Management | View dashboards, reports, contract status, and obligation summaries. |

Roles are proposed and require business confirmation.

### 2.4 Operating Environment

- Modern web browsers
- Responsive web frontend
- Secure HTTP(S) APIs
- Database for structured data
- Secure document storage
- Optional OCR/AI extraction service

### 2.5 Design and Implementation Constraints

- Extraction accuracy may vary with document quality.
- Sensitive contract data requires strict access control.
- Extracted data must be reviewed before final confirmation.
- The extraction component should be replaceable without redesigning the core system.
- Final technology stack is to be confirmed.

### 2.6 Assumptions and Dependencies

- Authorized user accounts will exist.
- Final roles and permissions will be approved by the business owner.
- Supported file types and maximum upload size will be defined.
- Representative real estate contracts will be available for extraction testing.
- Notification delivery depends on selected infrastructure.
- OCR/AI quality depends on the selected service and document quality.

---

## 3. Stakeholders and User Roles

### 3.1 Stakeholders

| Stakeholder | Interest |
|---|---|
| Business Owner / Management | Business objectives, reporting, and adoption. |
| Contract / Legal Team | Contract review, obligations, deadlines, and accuracy. |
| Property Management Team | Property-related contracts and operational obligations. |
| Employees | Execution of assigned obligations. |
| Frontend Developer | User interface and client-side workflows. |
| Backend Developer | APIs, business logic, database, security, documents, integrations. |
| QA Team | Validation of functional and non-functional requirements. |

### 3.2 Proposed Permissions

| Capability | Admin | Contract Manager | Legal | Property Manager | Employee | Management |
|---|---|---|---|---|---|---|
| View contracts | Yes | Yes | Yes | Allowed | Allowed | Yes |
| Create/edit contracts | Yes | Yes | Allowed | Allowed | No | No |
| Archive contracts | Yes | Allowed | Allowed | Allowed | No | No |
| Upload documents | Yes | Yes | Yes | Yes | Allowed | No |
| Confirm extracted data | Yes | Yes | Yes | Allowed | No | No |
| Create obligations | Yes | Yes | Yes | Yes | Allowed | No |
| Update assigned obligations | Yes | Yes | Yes | Yes | Yes | View |
| Manage users | Yes | No | No | No | No | No |
| View reports | Yes | Yes | Yes | Yes | Limited | Yes |

---

## 4. Functional Requirements

### 4.1 Authentication and Authorization

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-AUTH-01 | The system shall allow registered users to log in using valid credentials. | High | Valid credentials create an authenticated session; invalid credentials are rejected. |
| FR-AUTH-02 | The system shall protect authenticated API resources from unauthorized access. | High | Unauthenticated requests are rejected. |
| FR-AUTH-03 | The system shall enforce role-based permissions. | High | Users can perform only permitted actions. |
| FR-AUTH-04 | The system shall allow authenticated users to log out. | Medium | The session/token is invalidated or prevented from continued use. |

### 4.2 User Management

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-USER-01 | The system shall allow authorized administrators to create user accounts. | High | Valid user is created with required role. |
| FR-USER-02 | The system shall allow administrators to update user information and roles. | High | Changes are saved and affect access decisions. |
| FR-USER-03 | The system shall allow administrators to deactivate users. | Medium | Deactivated users cannot authenticate. |

### 4.3 Contract Management

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-CON-01 | The system shall allow authorized users to create contracts. | High | Valid contract is created. |
| FR-CON-02 | The system shall store contract number, title, type, dates, status, value/currency when applicable, parties, property links when applicable, and related documents. | High | Saved data is retrievable accurately. |
| FR-CON-03 | The system shall allow authorized users to view contract details. | High | Permitted users can retrieve contract details. |
| FR-CON-04 | The system shall allow authorized users to edit contract information. | High | Valid changes are saved and audited. |
| FR-CON-05 | The system shall allow authorized users to archive contracts. | Medium | Archived contracts are excluded from active views. |
| FR-CON-06 | The system shall support controlled contract statuses and types. | High | Only approved values are accepted. |

### 4.4 Proposed Contract Types

- Lease
- Sale / Purchase
- Service / Maintenance
- Construction
- Consulting
- Marketing
- Partnership / Joint Venture
- NDA
- License
- Other

Final contract types require business confirmation.

### 4.5 Party Management

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-PARTY-01 | The system shall allow authorized users to create and manage parties. | High | Party records can be created, viewed, and updated. |
| FR-PARTY-02 | The system shall support individual and organization/company parties. | High | The correct party type and fields are stored. |
| FR-PARTY-03 | The system shall associate parties with contracts. | High | Contract-party relationships are retrievable. |

### 4.6 Property Association

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-PROP-01 | The system shall allow contracts to be associated with one or more properties where applicable. | Medium | Authorized users can manage property associations. |
| FR-PROP-02 | The system shall allow users to view contracts and obligations associated with a property. | Medium | Property-level records can be retrieved and filtered. |

### 4.7 Contract Documents

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-DOC-01 | The system shall allow authorized users to upload contract documents. | High | Supported files are stored and linked to the correct contract. |
| FR-DOC-02 | The system shall preserve the original uploaded document. | High | Original file remains retrievable. |
| FR-DOC-03 | The system shall allow authorized users to view/download permitted documents. | High | Unauthorized access is rejected. |
| FR-DOC-04 | The system shall validate supported file types and maximum file size. | High | Invalid files are rejected with a clear error. |
| FR-DOC-05 | The system shall store document metadata such as name, type, size, uploader, and upload date. | Medium | Metadata is retrievable. |

### 4.8 Contract Information Extraction

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-EXT-01 | The system shall support processing uploaded contract documents to extract predefined structured information. | High | Extraction returns results or a clear failure status. |
| FR-EXT-02 | The system shall attempt to identify parties from documents. | High | Candidate parties are presented for review. |
| FR-EXT-03 | The system shall attempt to identify contract dates and relevant deadlines. | High | Candidate dates are presented for review. |
| FR-EXT-04 | The system shall attempt to identify contractual obligations. | High | Candidate obligations are presented for review. |
| FR-EXT-05 | The system shall allow authorized users to review, edit, and confirm extracted information. | High | Unconfirmed data is not treated as final. |
| FR-EXT-06 | The system shall retain the source-document relationship for confirmed extracted data where feasible. | Medium | Source can be traced from confirmed data. |

### 4.9 Obligation Management

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-OBL-01 | The system shall allow authorized users to create an obligation linked to a contract. | High | Obligation cannot be created without a valid contract. |
| FR-OBL-02 | The system shall store title, description, responsible party, responsible user when applicable, due date, priority, status, and frequency when applicable. | High | Data is stored and retrievable. |
| FR-OBL-03 | The system shall allow assignment to a responsible party and/or user. | High | Assignment is saved. |
| FR-OBL-04 | The system shall allow authorized users to update obligation status. | High | Valid status changes are saved and audited. |
| FR-OBL-05 | The system shall identify overdue obligations automatically when the due date has passed and the obligation is not completed. | High | Eligible obligations appear as Overdue. |
| FR-OBL-06 | The system shall support recurring obligations where applicable. | Medium | Approved recurrence rules are stored and processed. |
| FR-OBL-07 | The system shall allow users to search, filter, and sort obligations. | High | Results reflect selected criteria. |

### 4.10 Obligation Status

| Status | Definition |
|---|---|
| Pending | Not completed and not started; due date has not passed. |
| In Progress | Execution has started but is not complete. |
| Completed | Obligation has been fulfilled. |
| Overdue | Due date has passed and obligation is not completed. |
| Cancelled | Obligation has been cancelled by an authorized user or approved rule. |

### 4.11 Search, Filtering, Sorting, Pagination

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-SEARCH-01 | The system shall support contract search by contract number, title, party, and property where applicable. | High | Matching records are returned. |
| FR-SEARCH-02 | The system shall support contract filters by type, status, dates, party, and property. | High | Filters constrain results correctly. |
| FR-SEARCH-03 | The system shall support obligation filters by contract, status, responsible user, priority, and due date. | High | Results reflect filters. |
| FR-SEARCH-04 | The system shall support pagination for large collections. | Medium | Large result sets are paginated. |

### 4.12 Notifications and Reminders

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-NOTIF-01 | The system shall notify responsible users about upcoming obligation deadlines according to configured rules. | High | Notification is generated at the configured time. |
| FR-NOTIF-02 | The system shall notify responsible users when an obligation becomes overdue. | High | Overdue notification is generated. |
| FR-NOTIF-03 | The system shall store notification read/unread status where applicable. | Medium | Notification state is retrievable. |
| FR-NOTIF-04 | The system shall support approved notification channels such as in-app and email. | Medium | Enabled channels deliver notifications. |

### 4.13 Dashboard and Reports

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-REP-01 | The system shall provide dashboard summaries for contracts and obligations. | Medium | Authorized users can view approved KPIs. |
| FR-REP-02 | The system shall display obligation counts by Completed, In Progress, Pending, and Overdue. | High | Counts reflect authorized current data. |
| FR-REP-03 | The system shall provide overdue and upcoming obligation reports. | Medium | Reports return correct records. |
| FR-REP-04 | The system shall provide contract reports by type and status. | Medium | Reports group/filter correctly. |
| FR-REP-05 | The system shall support export of approved report data where required. | Low | Authorized users can export the data. |

### 4.14 Audit Trail

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
| FR-AUD-01 | The system shall record important user and system actions. | Medium | Configured actions create audit records. |
| FR-AUD-02 | Audit records shall include actor, action, target, timestamp, and relevant change information where applicable. | Medium | Required metadata is stored. |
| FR-AUD-03 | Audit records shall be protected from unauthorized modification. | High | Regular users cannot alter/delete audit records. |

---

## 5. Business Rules

| ID | Rule |
|---|---|
| BR-01 | Every obligation must be associated with a valid contract. |
| BR-02 | Every contract must have at least one participating party; final minimum is subject to confirmation. |
| BR-03 | Contract end date must not be earlier than start date. |
| BR-04 | An obligation is Overdue when its due date has passed and its status is not Completed or Cancelled. |
| BR-05 | Extracted information must be reviewed and confirmed before becoming official structured data. |
| BR-06 | Only authorized roles may create, edit, archive, confirm, or delete/restore records. |
| BR-07 | Archived contracts should not appear in standard active lists unless explicitly requested. |
| BR-08 | A recurring obligation must have a valid recurrence rule. |
| BR-09 | A contract document must be associated with a contract. |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| ID | Requirement | Target | Priority |
|---|---|---|---|
| NFR-PERF-01 | Standard API requests should return within an acceptable response time under normal load. | Target to be agreed during performance testing. | High |
| NFR-PERF-02 | Large lists shall use pagination and server-side filtering where appropriate. | No unnecessary full-table retrieval. | High |
| NFR-PERF-03 | Long-running extraction should not block normal application requests. | Use background/asynchronous processing where appropriate. | Medium |

### 6.2 Security

| ID | Requirement | Target | Priority |
|---|---|---|---|
| NFR-SEC-01 | Protected resources shall require authentication. | 100% of protected endpoints. | High |
| NFR-SEC-02 | The system shall enforce RBAC. | Unauthorized actions rejected. | High |
| NFR-SEC-03 | Passwords shall not be stored in plain text. | Secure password hashing. | High |
| NFR-SEC-04 | Production client-server communication shall use HTTPS. | HTTPS. | High |
| NFR-SEC-05 | Contract documents shall be accessible only to authorized users. | Permission-controlled access. | High |
| NFR-SEC-06 | The system shall validate uploaded files and user input. | Security validation applied. | High |

### 6.3 Reliability and Availability

| ID | Requirement | Target | Priority |
|---|---|---|---|
| NFR-REL-01 | The system should remain available during defined business periods. | Target to be agreed. | Medium |
| NFR-REL-02 | Application errors shall not expose sensitive implementation details. | Safe client errors + server logging. | High |
| NFR-REL-03 | Extraction failures shall be recorded with a visible processing status. | Clear failure state. | Medium |

### 6.4 Usability and Accessibility

| ID | Requirement | Target | Priority |
|---|---|---|---|
| NFR-UX-01 | Frontend shall provide consistent navigation and terminology. | Approved UI/UX system. | High |
| NFR-UX-02 | Forms shall provide clear validation and error messages. | All invalid/required fields identified. | High |
| NFR-UX-03 | Frontend should support agreed responsive screen sizes. | Desktop required; mobile/tablet TBD. | Medium |

### 6.5 Scalability

| ID | Requirement | Target | Priority |
|---|---|---|---|
| NFR-SCALE-01 | Backend shall support growth in contracts, obligations, and documents without redesigning core business logic. | Target volumes TBD. | Medium |
| NFR-SCALE-02 | Extraction processing should be independently scalable or replaceable. | Isolated extraction component. | Medium |

### 6.6 Maintainability

| ID | Requirement | Target | Priority |
|---|---|---|---|
| NFR-MAIN-01 | Backend APIs shall use consistent naming, validation, error, and response conventions. | Documented API standard. | High |
| NFR-MAIN-02 | Frontend shall use reusable components and consistent state/form patterns. | Approved frontend architecture. | Medium |
| NFR-MAIN-03 | Important actions and errors shall be logged. | Application logging. | High |

### 6.7 Backup and Recovery

| ID | Requirement | Target | Priority |
|---|---|---|---|
| NFR-BACK-01 | Critical structured data shall be backed up. | Frequency/retention TBD. | High |
| NFR-BACK-02 | Contract documents shall be included in backup/recovery. | Recovery policy TBD. | High |

---

## 7. Data Requirements

### 7.1 Core Entities

| Entity | Purpose |
|---|---|
| User | Account, identity, status, and role. |
| Role | Role and permission mapping. |
| Contract | Contract metadata, dates, type, status, value, and relationships. |
| Party | Individual or organization participating in a contract. |
| ContractParty | Relationship between contract and party. |
| Property | Real estate asset associated with contracts. |
| ContractDocument | Uploaded contract file and metadata. |
| ExtractedContractData | Machine-extracted candidate data awaiting/linked to confirmation. |
| Obligation | Contractual duty linked to a contract and responsible party/user. |
| Notification | Reminder/alert and delivery/read status. |
| AuditLog | Record of important system/user actions. |

### 7.2 Proposed Contract Fields

| Field | Required | Notes |
|---|---|---|
| Contract ID | System | Unique identifier. |
| Contract Number | Yes | Business/reference number. |
| Contract Name/Title | Yes | Human-readable title. |
| Contract Type | Yes | Controlled list. |
| Description | Optional | Contract summary. |
| Start Date | Yes | Start date. |
| End Date | Conditional | Required for time-bound contracts. |
| Status | Yes | Controlled list. |
| Contract Value | Conditional | When applicable. |
| Currency | Conditional | When value is present. |
| Parties | Yes | Participating parties. |
| Property | Conditional | When contract relates to property. |
| Document | Conditional | Original file when available. |
| Created/Updated Metadata | System | Audit metadata. |

### 7.3 Proposed Obligation Fields

| Field | Required | Notes |
|---|---|---|
| Obligation ID | System | Unique identifier. |
| Contract ID | Yes | Parent contract. |
| Title | Yes | Short obligation name. |
| Description | Yes | Obligation details. |
| Responsible Party | Yes | Party responsible for the duty. |
| Responsible User | Conditional | Internal user responsible for monitoring/completion. |
| Start Date | Optional | If applicable. |
| Due Date | Conditional | For deadline-driven obligations. |
| Priority | Yes | Low/Medium/High/Critical – subject to confirmation. |
| Status | Yes | Pending/In Progress/Completed/Overdue/Cancelled. |
| Frequency | Optional | For recurring obligations. |
| Evidence/Attachment | Optional | Supporting evidence. |
| Notes | Optional | Additional information. |

---

## 8. Document and Contract Processing

### 8.1 Proposed Workflow

- Upload supported contract document.
- Validate and store the original file.
- Run OCR/AI extraction when enabled.
- Extract candidate contract information, parties, dates, and obligations.
- Store extraction results separately from confirmed business data.
- Allow an authorized user to review and edit results.
- Allow the user to confirm results.
- Create/update official contract and obligation records.
- Keep the original document as the source.

### 8.2 Information to Extract – Proposed

- Contract number/reference
- Contract title/type
- Parties
- Property information
- Start/end dates
- Contract value/currency
- Renewal date/terms
- Termination conditions
- Obligations
- Due dates/deadlines
- Responsible parties
- Penalties where identifiable
- Important clauses where explicitly included in the approved extraction scope

The final extraction schema requires business confirmation.

---

## 9. Main Use Cases and Workflows

### 9.1 Manual Contract Creation

- Authorized user opens Create Contract.
- User enters required data.
- User selects type and parties and optionally properties.
- User uploads the document if available.
- System validates input and creates the record.
- Audit entry is created.

### 9.2 Contract Creation from Existing Document

- User uploads document.
- System stores original.
- Extraction starts.
- Candidate data and obligations are presented.
- User reviews/edits.
- User confirms.
- System saves official structured data.
- Audit entry records confirmation.

### 9.3 Obligation Tracking

- User opens a contract.
- System displays associated obligations.
- User reviews owner, priority, due date, and status.
- Responsible user updates progress.
- System identifies overdue items.
- Configured reminders are sent.
- User marks obligation Completed when fulfilled.

---

## 10. External Interfaces and API Requirements

### 10.1 API Areas

| Area | Responsibilities |
|---|---|
| Authentication | Login, logout, token/session validation, password operations if enabled. |
| Users/Roles | User management and role assignment. |
| Contracts | CRUD/archive, search, filters, statuses, types. |
| Parties | Party CRUD and contract-party relationships. |
| Properties | Property CRUD/association if enabled. |
| Documents | Upload, metadata, secure retrieval. |
| Extraction | Start processing, status, results, review/confirmation. |
| Obligations | CRUD, assignment, status, due dates, recurrence, filters. |
| Notifications | Create/list/read and delivery tracking. |
| Reports | Dashboard KPIs, report queries, exports. |
| Audit | Authorized audit log access. |

### 10.2 API Standards

- HTTPS in production.
- Consistent HTTP methods and status codes.
- Consistent request/response schemas.
- Structured validation and error responses.
- Authentication and authorization middleware.
- Pagination for large collections.
- OpenAPI/Swagger documentation or an agreed equivalent.

---

## 11. Acceptance Criteria

| Scenario | Given | When | Then |
|---|---|---|---|
| Create Contract | User is authorized and data is valid. | User submits contract. | Contract is created and success is returned. |
| Invalid Contract | Required data is missing/invalid. | User submits. | Request is rejected with validation errors. |
| Overdue Obligation | Obligation is not completed and due date has passed. | System evaluates status. | Obligation is identified as Overdue. |
| Extraction Review | Document extraction has completed. | Authorized user reviews and confirms. | Confirmed information is stored as official data. |

---

## 12. Traceability

Each requirement shall have a unique ID and should be mapped to use cases, frontend work items, backend work items, and test cases.

| Requirement | Use Case | Frontend | Backend | Test Case |
|---|---|---|---|---|
| FR-CON-01 | Create Contract | Create Contract Page | POST /contracts | TC-CON-01 |
| FR-OBL-05 | Obligation Tracking | Obligation List/Details | Overdue status logic | TC-OBL-05 |
| FR-EXT-05 | Extraction Review | Extraction Review Page | Extraction review/confirm API | TC-EXT-05 |

The full, maintained matrix lives in [`traceability.md`](./traceability.md).

---

## 13. Risks, Open Issues, and Future Enhancements

### 13.1 Risks

- OCR/AI may produce incorrect or incomplete information.
- Contract terminology and obligation structures vary between documents.
- Sensitive contract data requires strong access control.
- Incorrect extracted dates/obligations may cause operational issues without human review.

### 13.2 Open Questions – Required Business Decisions

1. Confirm final user roles and permissions.
2. Is the system for one company or multi-company/multi-tenant?
3. Confirm final contract types.
4. Can a contract be linked to multiple properties?
5. What fields are required for individual and company parties?
6. Confirm mandatory contract fields.
7. Confirm mandatory obligation fields.
8. Are penalties required as structured obligation data?
9. Are contract renewal dates and renewal reminders required?
10. What reminder schedule is required (for example 7/3/1 days)?
11. Which notification channels are required: in-app, email, or both?
12. What document formats and maximum file sizes are supported?
13. Is OCR/AI extraction mandatory for Release 1?
14. Exactly which contract information must be extracted?
15. Must every extracted result be reviewed and approved before saving?
16. Must Arabic contracts/documents be supported?
17. What are the final contract statuses and allowed transitions?
18. What are the expected numbers of users, contracts, obligations, and documents?
19. What are the backup and document-retention requirements?

The defaults adopted until the business decides are recorded in [`decisions.md`](./decisions.md).

### 13.3 Future Enhancements

- Advanced AI clause classification.
- Automatic penalty and renewal/termination clause detection.
- Advanced contract risk analysis.
- Electronic signature integration.
- ERP/CRM/accounting/property-management integrations.
- Mobile application.
- Advanced analytics and forecasting.

---

## Appendix A – Requirement ID Convention

| Prefix | Meaning | Example |
|---|---|---|
| FR-AUTH | Functional – Authentication | FR-AUTH-01 |
| FR-CON | Functional – Contracts | FR-CON-01 |
| FR-OBL | Functional – Obligations | FR-OBL-01 |
| FR-EXT | Functional – Extraction | FR-EXT-01 |
| NFR | Non-functional | NFR-SEC-01 |
| BR | Business Rule | BR-01 |
| UC | Use Case | UC-01 |
| TC | Test Case | TC-CON-01 |

## Appendix B – Development Notes

- Frontend and backend teams should implement against the approved requirements baseline.
- Changes to requirements should be tracked and their impact on frontend, backend, database, API, and testing reviewed.
- The backend must enforce critical authorization and business validation; frontend validation alone is not sufficient.
- The frontend should consume documented APIs rather than duplicate backend business logic.
- The database should support relationships between contracts, parties, properties, documents, and obligations.
- Extraction should be isolated from core contract management logic so the OCR/AI technology can be replaced later.
