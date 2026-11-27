# AGENTS.md

Guidance for coding agents working in this repository.

## Project Overview

A Django 5.2 web application for an annual supplementary-insurance renewal workflow (`renewals` app, `config` project).
- **Language & Dates:** Persian (`fa`) UI with `Asia/Tehran` timezone. Dates are displayed and entered in Jalali (`jdatetime`) in templates/forms, and stored as Gregorian `DateField`/`DateTimeField` in SQLite (`db.sqlite3`).
- **No external services:** SQLite + Django templates + vanilla JS/CSS in `static/renewals/`.

## Environment & Commands

Use the project virtual environment (`.venv`, Python 3.12–3.14; Django 5.2 does not support Python 3.15):

```bash
# Run tests
.venv/bin/python manage.py test renewals

# Apply migrations and seed demo data
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo

# Start dev server
.venv/bin/python manage.py runserver
```

Demo accounts (also shown on login when `DEBUG=1`):
- Employee: `sara.karimi` / `Renew-Sara-1405`
- Employee (access-control test): `reza.ahmadi` / `Renew-Reza-1405`
- HR: `hr.nazari` / `Renew-HR-1405`

## Code Map

- `config/settings.py`, `config/urls.py`: Django settings and root URL routing.
- `renewals/models.py`: `Employee`, `InsuredPerson`, `RenewalPeriod`, `RenewalRequest`, `CoverageLine`, `Decision`.
- `renewals/services.py`: **All** workflow state transitions (`create_draft`, `add_person`, `include_person`, `update_line`, `remove_line`, `submit`, `return_for_correction`, `approve`).
- `renewals/queries.py`: Read queries for employee/HR lists and reports.
- `renewals/views.py`, `renewals/urls.py`: Employee and HR panels.
- `renewals/access.py`: Role mixins (`EmployeeRequiredMixin`, `HRRequiredMixin`) and ownership helpers (`owned_request`, `owned_line`).
- `renewals/forms.py`: Form validation and Jalali date parsing.
- `renewals/validators.py`: Iranian 10-digit national ID normalization and checksum validation.
- `renewals/dates.py`, `renewals/templatetags/jalali.py`: Jalali conversion and template filters.
- `renewals/management/commands/seed_demo.py`: Idempotent demo data seeder.
- `renewals/tests/`: `test_rules.py`, `test_acceptance.py`, `helpers.py`.

## Architectural Invariants & Conventions

- **Service-layer transitions:** Views must call `renewals/services.py` for any state or roster mutation. Never mutate `RenewalRequest.status` or `CoverageLine` directly in views or templates.
- **Snapshot vs. living roster:** `InsuredPerson` is the employee's current roster; `CoverageLine` is a per-request snapshot. Editing a line in an editable request (`draft` or `needs_correction`) updates both the `CoverageLine` and its linked `InsuredPerson`, leaving historical requests untouched. Removing a line only deletes the `CoverageLine`.
- **Self line:** Every employee has one `Relationship.SELF` `InsuredPerson` and every request must retain its `SELF` `CoverageLine` (cannot be removed; name edits sync to `Employee` and `User`).
- **Uniqueness constraints:** At most one `RenewalPeriod` may have `is_open=True`. At most one `RenewalRequest` per `(employee, period)`.
- **Access control:**
  - Employees (`user.employee`) can only access their own requests; accessing another employee's request ID returns `404` (`renewals/not_found.html`) to avoid leaking existence.
  - HR users belong to the `hr` group (`settings.HR_GROUP_NAME`) and do not have an `Employee` profile. Wrong-role access returns `403` (`renewals/forbidden.html`).
- **Workflow states:**
  - Editable: `draft`, `needs_correction`.
  - Reviewable by HR: `submitted` -> `approved` or `needs_correction` (return requires a reason of at least 3 characters).
  - `approved` requests are locked.
