# YD Commercial Cleaning Mobile App — Architecture & Delivery Plan

## Decisions

- Platforms: iOS and Android.
- Audiences: public visitors/customers, employees, and company administrators.
- Backend: reuse the existing YDCCS Django monolith and its PostgreSQL/database configuration; do not create a second business database or duplicate business rules.
- Mobile client: React Native with Expo and TypeScript.
- API: versioned Django REST API under `/api/v1/`; evaluate/install Django REST Framework and a maintained JWT package only after checking dependency compatibility with the project's Django version.
- Existing website: remains operational and is not replaced by the mobile client.
- Work begins on a feature branch; changes should be reviewed and tested before merging/deploying.

## Existing project context

The repository is a Django monolith with apps including `core`, `quotes`, `services`, `reviews`, `customers`, `bookings`, `invoices`, `employees`, `induction`, `portal`, `notifications`, `contracts`, `attendance`, `payroll`, `leave_management`, `rosters`, `expenses`, `support`, `analytics`, `company_documents`, and `dashboard`. Reuse their existing services/models/forms/validation where appropriate rather than duplicating workflow logic in API views.

## Target architecture

```
iOS / Android (Expo + React Native + TypeScript)
  ├── Public services, quote requests, booking journey
  ├── Customer account, bookings, documents/invoices
  ├── Employee workspace, roster, job checklist, induction
  └── Admin workspace, operations summary, approvals
                 │ HTTPS JSON API (/api/v1/)
                 ▼
Existing Django application (ydcleaning)
  ├── API serializers/views/permissions/throttles
  ├── Existing domain apps and business rules
  ├── Existing database and media storage (Cloudinary where configured)
  └── Existing email/SMS/notification integrations
```

The API is a new interface to the existing system, not a parallel backend. Any state-changing API action must call the same domain/service layer used by the website where possible.

## API and authentication principles

- Namespace endpoints under `/api/v1/` and document the contract.
- Use short-lived access tokens and rotating/expiring refresh tokens if JWT is selected; store tokens only in platform secure storage, never ordinary AsyncStorage.
- Confirm the project's custom user model, role definitions, and middleware before implementing authentication.
- Enforce permissions server-side on every endpoint and object: public, authenticated customer, employee, and administrator access are distinct.
- Customers may only read/update their own profile and their own bookings, quotes, invoices, and documents.
- Employees may only access their own roster, assigned jobs, induction and permitted employment records.
- Administrative endpoints require an explicit company-admin permission; never trust a role supplied by the mobile client.
- Rate-limit login, password recovery, public quote submissions and other abuse-prone endpoints. Validate upload type/size and authorization.
- Use HTTPS only in production. Do not embed secrets in the mobile bundle.
- Use idempotency/duplicate-submission protections for booking creation and other sensitive writes where appropriate.
- Keep API responses paginated and avoid exposing internal model fields or unrestricted documents.

## Initial API surface (subject to model/service audit)

### Public
- `GET /api/v1/services/`
- `GET /api/v1/services/{slug}/`
- `POST /api/v1/quotes/`
- `POST /api/v1/auth/register/` (if customer registration policy supports it)
- `POST /api/v1/auth/login/`, `POST /api/v1/auth/refresh/`, `POST /api/v1/auth/password-reset/`

### Customer
- `GET/PATCH /api/v1/me/`
- `GET/POST /api/v1/me/bookings/`
- `GET /api/v1/me/bookings/{id}/`
- `POST /api/v1/me/bookings/{id}/reschedule/` and `/cancel/` only through existing policy/business rules
- `GET /api/v1/me/quotes/`
- `GET /api/v1/me/invoices/` and payment status/details supported by existing integrations
- `GET /api/v1/me/documents/` with authorized, time-limited file access

### Employee
- `GET /api/v1/employee/me/`
- `GET /api/v1/employee/roster/`
- `GET /api/v1/employee/jobs/`
- `POST /api/v1/employee/jobs/{id}/checklist/`
- `POST /api/v1/employee/jobs/{id}/photos/`
- `POST /api/v1/employee/attendance/clock-in/` and `clock-out/` using existing attendance rules
- `GET /api/v1/employee/induction/` and progress updates using existing induction workflows
- `POST /api/v1/device-tokens/` for push-notification registration

### Company administration (phased)
- `GET /api/v1/admin/summary/`
- `GET /api/v1/admin/bookings/` and authorized booking assignment/status actions
- `GET /api/v1/admin/leads/`, `/employees/`, `/invoices/`, `/expenses/` as permissioned, paginated endpoints
- Later phases can expose roster planning, company documents, inventory, reports and marketing controls after their current web workflows have been audited.

These paths are proposed contracts, not claims that these API routes already exist. Final serializers, fields, statuses, and actions must be mapped to actual models and service functions before implementation.

## Mobile app structure

Suggested independent app directory: `mobile/` (keep the Django project root and deployment configuration intact).

- `src/app/`: navigation and route groups.
- `src/features/public/`: service catalogue and quote flow.
- `src/features/auth/`: login, registration, recovery.
- `src/features/customer/`: profile, bookings, quotes, invoices.
- `src/features/employee/`: roster, assigned jobs, checklists, photos, induction.
- `src/features/admin/`: high-value mobile management and summaries.
- `src/components/`: shared design system and form controls.
- `src/lib/api/`: typed API client, token refresh and error handling.
- `src/lib/storage/`: secure token storage.
- `src/lib/notifications/`: push registration and notification routing.
- `src/theme/`: YD design tokens, typography, spacing, colour and accessibility.

Use a shared sign-in and role-aware navigation, but separate screens and permissions by audience. Public service browsing should work without an account. Avoid trying to copy every dense desktop dashboard table to mobile; prioritize mobile tasks and provide filters/search/pagination for lists.

## Delivery phases

### Phase 0 — Audit and safety baseline
1. Map custom user model, role/permission logic, customer ownership, employee relations and existing auth flows.
2. Trace quote/booking/reschedule/cancellation, invoice, attendance, roster, induction, notifications, document upload and payment workflows.
3. Confirm API dependencies and Django-version compatibility.
4. Add regression tests for the web workflows that the API will reuse.
5. Define API schema, status codes, pagination, error format and permissions matrix.

**Exit criteria:** agreed endpoint-to-model/service map; tests cover core existing website journeys; no production data or current web routes changed.

### Phase 1 — API foundation and customer MVP
- Add API dependencies and versioned routing in an isolated, reviewed change.
- Implement authentication, serializers, object permissions, throttling and API tests.
- Implement service catalogue, quote request, customer profile and booking creation/list/detail using real domain logic.
- Build Expo app shell, branding, accessible navigation, login and public/customer flows.

**Exit criteria:** a quote and booking created in the app appear in the existing website/admin workflow; cross-customer access tests fail safely; website regression suite passes.

### Phase 2 — Employee operations
- Employee identity, roster, assigned jobs, checklists, authorized photo uploads, attendance and induction.
- Push notifications for relevant assignment and schedule events.
- Validate offline/error states and duplicate clock-in/out prevention.

**Exit criteria:** employee can only see permitted records; attendance/checklist actions update existing backend records; notifications route to the correct screen.

### Phase 3 — Owner/admin essentials
- Operations overview, bookings and assignment actions, leads, customer details, staff summaries, invoices/payment status and expenses where current workflows permit.
- Use server-side pagination/filtering and enforce admin-only access.
- Add audit trails for sensitive management actions where missing.

**Exit criteria:** admin actions are permission checked and reflected in the website; employee/customer tokens cannot access admin APIs.

### Phase 4 — Hardening and store release
- Device testing across supported iOS and Android versions.
- API security review, upload tests, accessibility checks, performance and monitoring.
- Configure production API URL, push provider credentials and app-store metadata.
- Prepare privacy policy, data deletion/support contact processes and store submissions.

**Exit criteria:** CI and regression tests pass, no secrets in app bundle, release build tested against staging, and production rollout has a rollback plan.

## Quality gates

- Tests for authentication, object ownership, role permissions, validation, throttling, pagination and state transitions.
- Regression tests for existing website booking/quote/customer/employee flows.
- API contract/schema checks and mobile type checking/linting.
- No destructive schema changes without migrations, backups and a reviewed rollout plan.
- Use staging or a safe test database for integration tests; do not test against live customer records.
- Never expose secrets, private customer data, employee documents or signed file URLs in logs.

## Deployment notes

The current Django service remains the system of record. Deploy API additions to the existing backend only after tests and a reviewed migration plan. Deploy the Expo app separately through iOS and Android release channels. Store API base URLs and public configuration per environment; all privileged credentials remain on the server. Confirm production hosting capacity, database availability, media access and push-notification setup before launch.

## Immediate next implementation task

Audit `ydcleaning/settings.py`, `ydcleaning/urls.py`, the custom user/role model, and the service functions/models for `quotes`, `bookings`, `customers`, `employees`, `attendance`, `rosters`, `induction`, `invoices`, and `notifications`. Then implement only the smallest API foundation and its tests before adding mobile screens.
