# WhatBytes Healthcare Backend

A small Django REST Framework API for user authentication, patient records, doctor records, and patient-doctor assignments. The API uses PostgreSQL and JWT bearer authentication. It has no frontend.

## Stack

- Python 3.12 (the implementation was verified with Python 3.12.3)
- Django 5.2.18
- Django REST Framework 3.18.3
- djangorestframework-simplejwt 5.5.1
- PostgreSQL (verified with PostgreSQL 16)
- psycopg2-binary 2.9.13 and python-decouple 3.8

The direct dependencies are pinned in `requirements.txt`.

## Project structure

```text
accounts/     Custom email-based user, registration, authentication tests
patients/     Patient model, owner-scoped CRUD, tests
doctors/      Doctor model, creator-only mutations, tests
mappings/     Patient-doctor links, shared route, tests
config/       Django settings and root URLs
internal/     Kept outside this repository; engineering log and interview notes
```

## Database design and behavior

- `accounts.User` extends `AbstractUser`, removes `username`, and authenticates by unique email. `name` is a required field.
- A patient belongs to its creator (`created_by`). Patient querysets are filtered by the authenticated user, so another user's patient returns **404** for read, update, and delete.
- A doctor records its creator. Authenticated users can read all doctors; only the creator can update or delete a doctor (others receive **403**).
- A mapping links one patient and one doctor. PostgreSQL enforces unique `(patient, doctor)` pairs. Mapping rows cascade-delete when either related patient or doctor is deleted.
- List routes return unpaginated JSON arrays. `PUT` is supported; `PATCH` is also available on patient and doctor detail routes.
- Registration and login are the only public API endpoints. All other API operations require a JWT access token.

## Setup

### 1. Create the PostgreSQL database

Install and start PostgreSQL if it is not already available. On Ubuntu:

```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-client
sudo service postgresql start
```

Create a login role and database. Set the role password interactively so it does not appear in shell history:

```bash
sudo -u postgres psql
```

At the PostgreSQL prompt:

```sql
CREATE ROLE healthcare_app LOGIN CREATEDB;
\password healthcare_app
CREATE DATABASE healthcare_backend OWNER healthcare_app;
\q
```

The test runner creates a temporary test database, so the role needs `CREATEDB` permission.

### 2. Install Python dependencies

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set a newly generated `SECRET_KEY`, the database password you just set, and the desired hosts. Do not commit `.env`.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django signing key; keep private |
| `DEBUG` | Django debug mode; use `False` outside local development |
| `ALLOWED_HOSTS` | Comma-separated allowed hostnames |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL login role |
| `DB_PASSWORD` | PostgreSQL role password |
| `DB_HOST` | Database hostname, normally `127.0.0.1` locally |
| `DB_PORT` | PostgreSQL port, normally `5432` |

Settings require PostgreSQL configuration; there is no SQLite fallback.

### 4. Migrate, check, test, and run

```bash
python manage.py check
python manage.py migrate
python manage.py test
python manage.py runserver
```

The test command uses Django's test runner and creates/drops a PostgreSQL test database. Tests must be run using the configured PostgreSQL settings.

## Authentication

Register with `POST /api/auth/register/`, then log in with `POST /api/auth/login/`. Login returns an `access` token (60-minute lifetime) and a `refresh` token (1-day lifetime). Send the access token on protected routes as `Authorization: Bearer <access-token>`.

Examples below use these shell variables to avoid embedding credentials or tokens:

```bash
BASE_URL=http://127.0.0.1:8000
TOKEN='<access token returned by login>'
```

## API endpoints (all 16)

### Authentication (public)

**1. `POST /api/auth/register/`** — body fields are `name`, `email`, and `password`. Email is trimmed/lowercased; duplicates and Django password-validator failures return structured 400 responses. Password is write-only.

```bash
curl -X POST "$BASE_URL/api/auth/register/" -H 'Content-Type: application/json' \
  -d '{"name":"<name>","email":"<email>","password":"<new password>"}'
```

201 response:
```json
{"id": 1, "name": "<name>", "email": "<normalized-email>"}
```

**2. `POST /api/auth/login/`** — uses email and password. Invalid credentials return a generic 401.

```bash
curl -X POST "$BASE_URL/api/auth/login/" -H 'Content-Type: application/json' \
  -d '{"email":"<email>","password":"<password>"}'
```

200 response:
```json
{"refresh":"<refresh-token>","access":"<access-token>"}
```

### Patients (JWT required; owner-only)

**3. `POST /api/patients/`** — `name`, `age` (0–130), `gender` (`M`, `F`, or `O`), `phone`, `address`; `medical_history` is optional. Any client-sent `created_by` is ignored.

```bash
curl -X POST "$BASE_URL/api/patients/" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"<patient name>","age":30,"gender":"O","phone":"<phone>","address":"<address>","medical_history":""}'
```

201 response:
```json
{"id":1,"created_by":1,"name":"<patient name>","age":30,"gender":"O","phone":"<phone>","address":"<address>","medical_history":"","created_at":"<timestamp>","updated_at":"<timestamp>"}
```

**4. `GET /api/patients/`** — returns the caller's patients as a plain array.

```bash
curl "$BASE_URL/api/patients/" -H "Authorization: Bearer $TOKEN"
```

200 response: `[{"id":1,"created_by":1,"name":"<patient name>","age":30,"gender":"O","phone":"<phone>","address":"<address>","medical_history":"","created_at":"<timestamp>","updated_at":"<timestamp>"}]`

**5. `GET /api/patients/{id}/`** — retrieve an owned patient. Missing and other-user IDs return 404.

```bash
curl "$BASE_URL/api/patients/{{patientId}}/" -H "Authorization: Bearer $TOKEN"
```

200 response: the patient object shown for endpoint 3.

**6. `PUT /api/patients/{id}/`** — replace an owned patient's editable fields; all required fields must be present. `PATCH` is also supported.

```bash
curl -X PUT "$BASE_URL/api/patients/{{patientId}}/" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"<updated name>","age":31,"gender":"F","phone":"<phone>","address":"<address>","medical_history":"<history>"}'
```

200 response: updated patient object.

**7. `DELETE /api/patients/{id}/`** — delete an owned patient; mapping rows cascade-delete.

```bash
curl -X DELETE "$BASE_URL/api/patients/{{patientId}}/" -H "Authorization: Bearer $TOKEN"
```

204 response: empty body.

### Doctors (JWT required; readable by all authenticated users)

**8. `POST /api/doctors/`** — `name`, `specialization`, `email`, `phone`, and `experience_years` (0–80). Creator is assigned server-side.

```bash
curl -X POST "$BASE_URL/api/doctors/" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"<doctor name>","specialization":"<specialization>","email":"<doctor email>","phone":"<phone>","experience_years":8}'
```

201 response:
```json
{"id":1,"created_by":1,"name":"<doctor name>","specialization":"<specialization>","email":"<normalized-email>","phone":"<phone>","experience_years":8,"created_at":"<timestamp>","updated_at":"<timestamp>"}
```

**9. `GET /api/doctors/`** — list all doctors as a plain array.

```bash
curl "$BASE_URL/api/doctors/" -H "Authorization: Bearer $TOKEN"
```

200 response: `[<doctor object>]`.

**10. `GET /api/doctors/{id}/`** — any authenticated user may retrieve an existing doctor.

```bash
curl "$BASE_URL/api/doctors/{{doctorId}}/" -H "Authorization: Bearer $TOKEN"
```

200 response: the doctor object shown for endpoint 8.

**11. `PUT /api/doctors/{id}/`** — creator only; non-creators receive 403. `PATCH` is also supported.

```bash
curl -X PUT "$BASE_URL/api/doctors/{{doctorId}}/" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"<updated doctor>","specialization":"<specialization>","email":"<doctor email>","phone":"<phone>","experience_years":9}'
```

200 response: updated doctor object.

**12. `DELETE /api/doctors/{id}/`** — creator only; mapping rows cascade-delete.

```bash
curl -X DELETE "$BASE_URL/api/doctors/{{doctorId}}/" -H "Authorization: Bearer $TOKEN"
```

204 response: empty body.

### Patient-doctor mappings (JWT required)

**13. `POST /api/mappings/`** — body contains `patient_id` and `doctor_id`. Patient must belong to caller; missing and foreign patient IDs produce the same 400 validation message. Duplicate pairs return 400.

```bash
curl -X POST "$BASE_URL/api/mappings/" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"patient_id":{{patientId}},"doctor_id":{{doctorId}}}'
```

201 response:
```json
{"id":1,"patient":1,"doctor":1,"created_at":"<timestamp>"}
```

**14. `GET /api/mappings/`** — list only the caller's patient mappings as a plain array.

```bash
curl "$BASE_URL/api/mappings/" -H "Authorization: Bearer $TOKEN"
```

200 response: `[{"id":1,"patient":1,"doctor":1,"created_at":"<timestamp>"}]`.

**15. `GET /api/mappings/{patient_id}/`** — on the shared mapping-ID route, GET treats the path number as a patient ID and returns its assigned doctors. Patient must be owned by caller.

```bash
curl "$BASE_URL/api/mappings/{{patientId}}/" -H "Authorization: Bearer $TOKEN"
```

200 response: `[<doctor object>]`.

**16. `DELETE /api/mappings/{id}/`** — on that same route, DELETE treats the path number as a mapping ID. Mapping must belong to a patient owned by caller; otherwise 404.

```bash
curl -X DELETE "$BASE_URL/api/mappings/{{mappingId}}/" -H "Authorization: Bearer $TOKEN"
```

204 response: empty body.

## Error behavior and assumptions

- Invalid JSON/field values, missing required fields, weak passwords, invalid/duplicate emails, invalid relationships, and duplicate mappings return 4xx validation responses rather than application tracebacks.
- Missing records return 404. Patient ownership is intentionally hidden as 404. An unowned patient submitted to mapping creation returns a non-disclosing 400. Non-creator doctor mutation returns 403.
- Patient gender choices are `M`, `F`, `O`; patient age is capped at 130. Doctor experience is capped at 80 years. These bounds are input-validation choices, not clinical rules.
- Mapping deletion is a database-level cascade when a patient or doctor is deleted.
- There is no pagination, refresh-token URL, frontend, deployment configuration, or healthcare regulatory-compliance claim. The API implements the requested assignment scope only.
