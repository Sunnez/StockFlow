# StockFlow — Local setup

This guide describes local development and safe test execution. For features and architecture, see the [main README](../README.md).

## Prerequisites

- Python 3.13 and pip
- Node.js 22.12+ and npm
- Docker Engine / Docker Desktop with Docker Compose

## 1. Python environment

From the repository root, create and activate a virtual environment if you do not already have one:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Environment configuration

Copy `.env.example` to `.env` **only if you do not already have a configured `.env`**. Set the PostgreSQL development and test credentials, database URLs, and independent secrets.

Generate two different random secrets, one for `JWT_SECRET_KEY` and one for `CSRF_SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Run that command twice. Keep `.env` out of version control. For SQLAlchemy URLs, percent-encode special characters in usernames and passwords; the plain PostgreSQL environment variables use their unencoded values.

For the browser running on `http://localhost:5173`:

- Add `http://localhost:5173` to `AUTH_ALLOWED_ORIGINS` using the JSON array format expected by the backend settings.
- Set `AUTH_COOKIE_SECURE=false` **only for local HTTP**. Use HTTPS with Secure cookies in production.
- Use `http://localhost:8000` for the API, not `127.0.0.1`, when the frontend is opened on `localhost`. Browser cookies depend on the hostname.
- Keep development and test PostgreSQL credentials separate. The test database must be named `stockflow_test`, and its role name must end in `_test` and differ from the development role.

## 3. PostgreSQL and migrations

Start PostgreSQL:

```powershell
docker compose up -d --wait
```

For a **new, empty database**, apply the migration chain:

```powershell
alembic upgrade head
alembic current
```

The expected migration head is `1f2a3b4c5d61`. Some older revisions and the tenant migration require empty tables; do not apply the clean-install path to a populated legacy database without reviewing data migration requirements. Do not use `docker compose down -v` unless you intentionally want to delete the Compose volumes.

## 4. Backend and frontend

In the repository root, start FastAPI:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start React:

```powershell
cd frontend
npm ci
npm run dev
```

Open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

The frontend sends cookies with `credentials: "include"`. The access and refresh tokens are HttpOnly; the readable CSRF cookie is mirrored into the `X-CSRF-Token` header for relevant requests.

## 5. Checks

Backend unit tests (do not connect to PostgreSQL):

```powershell
python -m pytest tests/unit -q
```

Frontend checks (run from `frontend/`):

```powershell
npm run typecheck
npm run lint
npm test
npm run build
```

### PostgreSQL integration tests — destructive test data

Integration fixtures can drop/recreate tables and delete records in the designated **test database**. Before running them:

1. Confirm `TEST_DATABASE_URL` points to a disposable local `stockflow_test` database, on the expected loopback host/port, with a test role different from the main role.
2. Confirm `DATABASE_URL` still points to your development database; it must **not** equal `TEST_DATABASE_URL`.
3. Verify the test data can be discarded. Never use a production or development database as the integration target.
4. Run the suite in a separate process with its explicit reset marker:

   ```powershell
   $env:STOCKFLOW_ALLOW_TEST_DB_RESET = "stockflow_test"
   try {
       python -m pytest tests/integration -q
   } finally {
       Remove-Item Env:STOCKFLOW_ALLOW_TEST_DB_RESET -ErrorAction SilentlyContinue
   }
   ```

Do not run unit and integration suites together in a single process. The integration fixtures generate ORM tables directly, so this test suite does **not** verify Alembic's full upgrade path. Test migrations separately using another disposable database when needed.
