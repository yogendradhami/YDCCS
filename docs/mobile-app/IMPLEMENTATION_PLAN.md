# YD Commercial Cleaning Mobile App — Architecture & Delivery Plan

**Status:** Planning baseline  
**Platforms:** Android and iOS  
**Mobile stack:** React Native + Expo + TypeScript  
**Backend/source of truth:** Existing Django project and its configured database  
**Payments:** Out of scope for the first release; retain current invoice/payment records and add payment processing later.

## 1. Repository inspection summary

Initial inspection of `yogendradhami/YDCCS` (default branch `main`) found:

- A single Django monolith configured through `manage.py` and `ydcleaning/settings.py`.
- Existing business apps for public website/content, quotes, services, reviews, customers, bookings, invoices, employees, induction, portal, notifications, attendance, rosters, leave, expenses, payroll, support, analytics and company documents.
- Django URL routing currently combines the web-facing app URL configurations in `ydcleaning/urls.py`.
- The database is configured through `DATABASE_URL`; the repository settings fall back to SQLite for local development. Production PostgreSQL/Neon should remain the system of record.
- The current `requirements.txt` does **not** include Django REST Framework or a dedicated mobile API authentication package. No established REST API contract was confirmed in this initial pass.
- Existing user/employee/customer relationships and permissions must be mapped from the actual models and views before endpoints are implemented. Do not assume an employee profile is the same thing as a Django user.

This is an initial repository-level inspection, not a full audit of every model, view, migration, deployment setting, or uncommitted local change. The checked GitHub branch may not include the latest work in the developer's local checkout.

## 2. Architecture decision

Use a separate `mobile/` Expo application in this repository, while keeping the Django website and business logic in place.

```text
YDCCS repository
├── existing Django project (preserve)
│   ├── public website and SEO pages (preserve)
│   ├── existing domain apps/models (reuse)
│   └── versioned /api/v1/ endpoints (add after model audit)
└── mobile/ (new Expo + React Native + TypeScript app)
    ├── public/customer experience
    ├── employee experience
    ├── owner/admin experience
    └── shared API client, auth, design system and navigation
```

### Key principles

1. **One source of truth:** all bookings, quotes, job assignments, customers, staff records, invoices and statuses remain in Django/database. The mobile app must not create a parallel business database.
2. **Preserve the website:** no replacement of existing templates, SEO URLs, CSS, web dashboards, models or workflows as part of mobile setup.
3. **API-first integration:** mobile clients call explicit JSON endpoints; do not scrape or reuse HTML views as an API.
4. **Reuse business rules:** extract or call existing service/domain functions where possible. Avoid duplicating booking, assignment, invoice or status-transition logic in API views.
5. **Server-side permissions:** enforce role and object-level access on every request. Hiding a button in the app is not security.
6. **Secure authentication:** evaluate existing login and custom user configuration, then choose a supported token/session strategy. If using bearer tokens, prefer short-lived access tokens and rotating/revocable refresh tokens; store secrets in platform secure storage. Never embed server secrets in the app.
7. **Mobile-safe file access:** private employee/customer documents must use authenticated, authorised endpoints or short-lived signed URLs; never expose raw private storage paths.
8. **Auditable mutations:** job start/finish, assignment, timesheet and document actions should record the acting user and timestamp and should be safe against accidental duplicate submissions.
9. **Accessible and resilient UX:** loading, empty, error, offline and retry states; readable contrast and touch targets; validate all input on the server.
10. **Payments deferred:** first release can show invoice/payment status only if current permissions and workflows support it. Do not enable new payment collection in this phase.

## 3. First-release scope

### Public visitors and customers
- Browse published services and service areas.
- Submit a quote/enquiry using validated server endpoints.
- Register/sign in and manage their own profile where supported by the existing account model.
- Create/view/cancel or reschedule a booking only where the existing business rules permit it.
- View booking status/history, service instructions and permitted invoice details.
- Receive in-app/push notification links where notification events are supported.
- Contact the company and view public reviews/content.

Guest browsing should not require an account. The API must not reveal other customers' bookings or invoices.

### Employees
- Secure sign-in and role-aware home screen.
- View only authorised assigned jobs and roster/shift details.
- View job address, timing, customer instructions and checklist.
- Submit job status updates and completion checklist.
- Upload before/after photos where permitted.
- Access authorised induction/training, attendance, leave and announcements.
- View own timesheets/records only where existing workflows support them.

Location tracking is not part of the initial scope. If later requested, obtain explicit consent and define retention/access rules first.

### Company owner/admin
- Role-protected operational overview: bookings, open jobs, quote requests and recent activity.
- Review and manage enquiries/bookings using existing permissions and state transitions.
- Assign staff where supported by current operations workflows.
- View high-level business indicators and invoice statuses the signed-in user is authorised to access.
- View relevant notifications and employee workflow alerts.

The mobile owner area is a focused operational companion, not an attempt to duplicate every desktop dashboard table in v1. Complex admin/configuration screens can remain on the existing web dashboard.

## 4. API and backend workstream

Before implementing endpoints, inspect these areas in order:

1. User model, authentication configuration, account creation, groups/permissions and existing login flows.
2. Booking and quote models, form validation, cancellation/reschedule rules, status transitions and notification hooks.
3. Customer account/profile linkage and ownership checks.
4. Employee model/profile linkage, role mapping, roster/attendance and induction access.
5. Invoice ownership/visibility and document/media access controls.
6. Existing tests, URL namespaces, production CORS/CSRF settings, throttling and error conventions.

Then add a versioned API namespace, ideally `/api/v1/`, and a dedicated API module/app. Select API dependencies only after verifying compatibility with the project's pinned Django version. Proposed endpoint groups (final paths and schemas follow the model audit):

- `/auth/`: login, refresh, logout/revoke, current user.
- `/public/services/`, `/public/service-areas/`: published public data.
- `/quotes/`: create and retrieve a user's own quote requests.
- `/bookings/`: create/list/detail and allowed state actions.
- `/customer/profile/`, `/customer/invoices/`: own records only.
- `/employee/me/`, `/employee/jobs/`, `/employee/roster/`, `/employee/induction/`, `/employee/attendance/`: role and object scoped.
- `/owner/overview/`, `/owner/bookings/`, `/owner/assignments/`, `/owner/quotes/`: administrator-only operations.
- `/notifications/`: authenticated, user-scoped notification listing/read state.
- `/health/`: minimal operational health response without secret/config leakage.

Do not implement endpoints merely to match this illustrative list if equivalent safe workflows already exist. Reuse existing services and permissions wherever possible.

## 5. Mobile app structure

Suggested structure (adapt after Expo version and package manager are confirmed):

```text
mobile/
├── app/                         # Expo Router routes
│   ├── (public)/
│   ├── (auth)/
│   ├── (customer)/
│   ├── (employee)/
│   └── (owner)/
├── src/
│   ├── api/                     # typed API client and error handling
│   ├── auth/                    # session, role gates, secure token storage
│   ├── components/              # shared accessible UI
│   ├── features/
│   │   ├── services/
│   │   ├── quotes/
│   │   ├── bookings/
│   │   ├── employee-jobs/
│   │   ├── rosters/
│   │   ├── induction/
│   │   ├── invoices/
│   │   └── notifications/
│   ├── theme/                   # YD design tokens
│   └── utils/
├── assets/
├── app.json
├── package.json
├── tsconfig.json
└── README.md
```

Use Expo Router for route organisation, TypeScript for safer API contracts, a small shared component/theme layer, and a maintained secure-storage solution for credentials. Add push notifications only after account/device registration and permission handling are designed. Keep dependencies lean.

## 6. Step-by-step delivery plan

### Phase 0 — Audit and safety baseline
- [ ] Confirm the active repository and branch are aligned with the developer's latest local changes.
- [ ] Map models, user/profile relationships, role permissions and existing business workflows.
- [ ] Identify reusable service functions and existing tests.
- [ ] Record API gaps and any blockers; do not alter production data or credentials.

**Exit criteria:** an agreed model-to-feature map and endpoint contract with no assumed foreign-key relationships.

### Phase 1 — Backend API foundation
- [ ] Add API dependencies with compatible pinned versions.
- [ ] Add `/api/v1/` routing and standard response/error conventions.
- [ ] Implement authentication/current-user and role/object permissions.
- [ ] Add schema/OpenAPI documentation if supported by the chosen packages.
- [ ] Add API tests for anonymous access, role boundaries, object ownership, invalid input and state transitions.

**Exit criteria:** API tests prove a customer cannot access another customer's data, an employee cannot access unassigned jobs or another employee's private records, and only authorised admins can perform management actions.

### Phase 2 — Expo foundation
- [ ] Create the `mobile/` app without changing existing Django files.
- [ ] Configure TypeScript, navigation, environment-based API base URL and dev setup.
- [ ] Establish YD branding, reusable inputs/buttons/cards, loading/error/empty states.
- [ ] Implement auth/session restoration and role-aware navigation.
- [ ] Add unit/component tests and API-client tests.

**Exit criteria:** app runs in Expo development builds on iOS and Android and signs in against a development API.

### Phase 3 — Customer journeys
- [ ] Public service catalogue and service details.
- [ ] Quote/enquiry submission.
- [ ] Sign-in/account and customer profile.
- [ ] Booking creation and booking list/detail.
- [ ] Booking status, allowed cancellation/reschedule actions, and invoice status where authorised.

**Exit criteria:** customer journeys are tested end-to-end against the same database as the website.

### Phase 4 — Employee journeys
- [ ] Assigned jobs and roster.
- [ ] Job detail, checklist, allowed status updates.
- [ ] Completion notes and photo uploads.
- [ ] Induction/training and own attendance/leave views where current models support them.

**Exit criteria:** employees see only authorised records and repeated network submissions do not duplicate job actions.

### Phase 5 — Owner/admin journeys
- [ ] Operational overview.
- [ ] Booking/quote review and permitted management actions.
- [ ] Staff assignment and progress visibility.
- [ ] Notifications and key invoice/financial status summaries.

**Exit criteria:** admin actions are permission-checked, audited where appropriate, and do not bypass current business rules.

### Phase 6 — Hardening and release
- [ ] Verify production HTTPS, allowed hosts, CORS policy, throttling, token rotation/revocation and secure storage.
- [ ] Verify private media/document access and upload limits.
- [ ] Test on physical iOS/Android devices and small/large screens.
- [ ] Add crash/error monitoring without collecting unnecessary personal data.
- [ ] Configure Expo EAS build profiles, app icons/splash, privacy disclosures and store metadata.
- [ ] Prepare internal testing tracks before public release.

**Exit criteria:** release checklist passed, API security tests green, backup/rollback plan documented, and app-store builds tested.

### Deferred phase — Payments
- Integrate an approved payment flow only after the booking/invoice workflow is stable, with server-side payment verification and idempotent webhooks. Never store card details in the app or Django models.

## 7. Testing and acceptance criteria

- All existing Django website tests and key booking/quote tests remain green.
- API tests cover unauthenticated, customer, employee, supervisor and owner/admin permissions as applicable to the actual roles.
- Customer data isolation is enforced server-side for bookings, quotes, invoices and files.
- Employees cannot access jobs or HR documents outside their authorised scope.
- Invalid transitions (e.g. completing an unassigned job) are rejected server-side.
- Repeated requests do not duplicate quote/booking creation or job status events.
- Mobile UI includes loading, empty, error and retry states for networked screens.
- App works against staging without hardcoded production credentials or URLs.
- Existing website SEO pages, URLs, templates and desktop dashboard workflows are unchanged by the mobile project.

## 8. Immediate next actions

1. Finish the detailed model/view/permission audit of bookings, quotes, customers, employees, invoices, notifications and induction.
2. Draft the concrete API schemas from the actual model relationships.
3. Implement and test the API foundation on a feature branch.
4. Scaffold the Expo app in `mobile/` and connect it to the development API.
5. Deliver customer journeys first, then employee, then owner operations, validating each against existing workflows.

**Important:** do not run production migrations, overwrite existing app models, or commit environment secrets as part of the initial mobile setup.
