# YD Mobile App — Initial Domain Audit

This is a source-level audit of the current `main` branch to inform API design. It is not a substitute for running the application and tests locally.

## Verified model facts

### Authentication and identity
- `customers.models.Customer` links to Django's built-in `django.contrib.auth.models.User` through a nullable, blank `OneToOneField` named `user`.
- `employees.models.Employee` also links to the built-in Django `User` through a nullable, blank `OneToOneField` named `user`.
- Customer and employee profile links can therefore be absent; API code must handle unlinked records explicitly and must not assume a profile exists for every signed-in user.
- The employee model has a role field with `cleaner`, `supervisor`, `manager`, and `admin` choices. That is not by itself sufficient proof of a user's complete company-admin authorization; existing permission/middleware policy must be audited.

### Bookings and job evidence
- `bookings.models.Booking` belongs to a `Customer`, has service/date/time/address/suburb-postcode/quoted-price fields, an optional assigned `Employee`, and statuses `pending`, `confirmed`, `assigned`, `in_progress`, `completed`, and `cancelled`.
- Booking has an optional unique `idempotency_key`. The API should preserve and correctly use this capability rather than blindly creating duplicates.
- `bookings.models.JobPhoto` links a photo to a booking and optionally to an employee, with `before` / `after` photo types, notes, image fields, and employee/customer signature fields. Upload authorization must check that the authenticated employee is assigned/otherwise authorized for that job.

### Employee operations
- `rosters.models.Roster` connects an employee to a booking and includes shift date, start/end times and status.
- `induction.models` includes induction programmes/modules and an `EmployeeInduction` record linked one-to-one to an employee, including status and declaration fields. Mobile induction should reuse this workflow and its existing completion rules.
- `attendance` is a dedicated installed Django app, but its current service/view transitions must be audited before specifying clock-in/clock-out API actions.

### Notifications
- `notifications.models.Notification` is tied to Django User and has title, message, type, link, read status and timestamp. Its current schema represents in-app notifications; push delivery/device-token registration is not established by this model and will need a separate integration design.
- Notification types include bookings, invoices, employees, attendance, payroll, leave, roster and system events.

### URL architecture
- `ydcleaning/urls.py` includes many app URL configurations at the root and includes `core.urls` late because it contains a generic service slug route.
- Add a distinct, explicit `api/v1/` include before the generic website routes. Keep the existing route ordering and website URLs unchanged.

## Design implications

1. Use Django User as the authentication identity unless a full audit reveals a compelling reason to change it. Do not introduce a second mobile-only user table.
2. Implement a single identity endpoint that resolves the signed-in user to allowed customer and/or employee profiles and an explicit permission set. Handle missing/ambiguous profiles safely.
3. Customer list/detail querysets must be filtered by the authenticated user's linked customer profile. A submitted customer ID is never sufficient authorization.
4. Employee job and roster querysets must be filtered to the authenticated user's linked employee profile and allowed supervisory scope.
5. Company administration should be granted through existing Django permissions/groups and audited policy, not merely by trusting the `Employee.role` value or a client-sent role.
6. Keep booking state transitions in shared service functions. Do not let the API accept arbitrary status strings or bypass cancellation/rescheduling rules.
7. Use the booking idempotency mechanism for duplicate-safe creation, after reviewing current form/service behaviour and uniqueness handling.
8. Keep signatures, induction declarations, payroll, contracts and company documents behind explicit authorization. Avoid exposing private storage URLs or internal model fields.
9. Push notifications require an additional device-token model/provider integration and user-controlled permission handling; keep existing in-app notifications working.
10. Do not add database migrations until the endpoint and model audit is complete.

## Next audit items before API implementation

- Inspect `AUTHENTICATION_BACKENDS`, middleware, role helpers, `core.middleware.RoleAccessMiddleware`, login/password-reset views, and existing user/profile provisioning.
- Trace quote creation and booking create/cancel/reschedule code paths, including service functions and tests.
- Trace attendance state transitions and roster assignment permissions.
- Check invoice/payment ownership and file/document storage access patterns.
- Confirm the currently installed dependency versions and add a compatible API/auth stack only after verification.

## Scope boundary

This document records observed repository structure and recommended constraints. It does not claim API endpoints are implemented, does not alter production data, and does not change the website.
