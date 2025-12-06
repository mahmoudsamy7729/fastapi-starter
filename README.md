
# FastAPI Authentication & Billing Service

A FastAPI backend that provides login/registration, OAuth, OTP, email verification, and Stripe-based subscriptions. It runs async with PostgreSQL, Redis, and Celery so you can plug it into a SaaS dashboard or API-first product.

## Technical Overview
- FastAPI app with per-domain routers (`src/auth/router.py`, `src/billing/router.py`), CORS, structured logging, and slowapi rate limiting.
- Service/repository layers over async SQLAlchemy 2.0 + asyncpg; sync engine for Celery tasks.
- JWT access, refresh, and validation tokens with hashed refresh storage and rotation.
- Stripe Checkout + webhook handling for plans, subscriptions, renewals, and cancellations.
- SMTP email flows (verification, password reset, OTP, subscription notices) via FastAPI-Mail.
- Celery worker and beat for subscription emails and expiry sweeps.

## Main Features
- Local auth: register/login, email verification, password reset/change.
- OTP login (email-delivered, single-use, 15-minute expiry).
- Social auth: Google and GitHub with state validation and auto-provisioning.
- Refresh token rotation with DB-backed JTI tracking and httpOnly cookies.
- Plans: create/update/soft-delete, tiering, and Stripe product/price sync.
- Subscriptions: checkout, upgrade, cancel-at-period-end, and access window enforcement.
- Stripe webhooks: checkout completion, invoice success/failure, subscription deleted.
- Payments recorded on invoice success; subscription emails dispatched via Celery.
- Rate limiting (default 5/min) and request logging for observability.

## Technology Stack
- Python 3.12+, FastAPI, Starlette, Pydantic v2
- Async SQLAlchemy + asyncpg (PostgreSQL), Alembic migrations
- JWT via python-jose; Argon2 hashing (passlib)
- Stripe Python SDK
- Redis broker; Celery worker and beat
- FastAPI-Mail (SMTP + Jinja templates)
- slowapi for rate limiting; loguru for logging

## Requirements
- Python 3.12+
- PostgreSQL (DATABASE_URL) and a sync URL for Celery (SYNC_DATABASE_URL)
- Redis 7+ for rate limiting and Celery broker
- Stripe keys (public, secret, webhook signing)
- SMTP credentials for transactional emails
- Google and GitHub OAuth credentials
- Optional: Docker and docker-compose for local orchestration

## Installation
1. Create and activate a virtualenv:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # on Windows
   # source .venv/bin/activate on Linux/macOS
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements/requirements.txt
   ```
   (For dev-only pins you can also use `requirements/devlopment.txt`.)
3. Copy `.env.example` to `.env` and fill in all values (see Environment Variables below).
4. Create the PostgreSQL databases referenced by `DATABASE_URL`, `SYNC_DATABASE_URL`, and `TEST_DATABASE_URL`.
5. Run migrations:
   ```bash
   alembic upgrade head
   ```

## Environment Variables
Key settings loaded via `src/config.py`:
- App: `APP_NAME`, `APP_ENV`, `APP_DEBUG`, `APP_URL`
- Database: `DATABASE_URL`, `SYNC_DATABASE_URL` (used by Celery), `TEST_DATABASE_URL`
- JWT: `ALGORITHM`, `ACCESS_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE`, `REFRESH_SECRET_KEY`, `REFRESH_TOKEN_EXPIRE`, `VALIDATION_SECRET_KEY`, `VALIDATION_TOKEN_EXPIRE`
- Mail: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- OAuth (Google): `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GOOGLE_AUTH_URL`, `GOOGLE_TOKEN_URL`, `GOOGLE_USERINFO_URL`
- OAuth (GitHub): `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`, `GITHUB_AUTHORIZE_URL`, `GITHUB_TOKEN_URL`, `GITHUB_USER_API`, `GITHUB_EMAILS`
- Infrastructure: `REDIS_URL`, `CELERY_WORKER_URL`, `CELERY_BEAT_URL`
- Stripe: `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`

## Running (Development)
1. Ensure PostgreSQL and Redis are running.
2. Start the API:
   ```bash
   uvicorn src.main:app --reload
   ```
3. Start Celery worker and beat (separate shells):
   ```bash
   celery -A src.celery_app.celery_app worker --loglevel=info
   celery -A src.celery_app.beat_app beat --loglevel=info
   ```
4. Configure your SMTP sandbox so email flows (verification/reset/OTP/subscription) can send.

## Running (Production)
- Set `APP_DEBUG=False`, tighten CORS, and set cookie `secure=True` in the auth router.
- Provide HTTPS termination (e.g., Nginx in front of Uvicorn/Gunicorn workers).
- Run workers with process managers (systemd/supervisor) or containers.
- Validate Stripe webhook signature with `STRIPE_WEBHOOK_SECRET` and expose the webhook URL publicly.
- Docker Compose option:
  ```bash
  docker-compose up --build
  ```
  Services: `api`, `db` (Postgres), `redis`, `celery`, `celery_beat`, and `pgadmin`.

## Tests
- Set `TEST_DATABASE_URL` to a dedicated database.
- Run all tests with:
  ```bash
  pytest
  ```
  Tests spin up schema automatically, disable the rate limiter, and use httpx ASGI client fixtures. Mock Stripe/email in new tests to avoid real calls.

## Short API Overview
- Auth: `/register`, `/login`, `/refresh-token`, `/verify`, `/request/verify`, `/forget-password`, `/new-password`, `/change-password`, `/request/login-code`, `/login/code`, `/google/login` + callback, `/github/login` + callback, `/deactivate`.
- Billing: `/billing/plans` (list/create), `/billing/plans/{id}` (get/update/delete), `/billing/subscriptions/me`, `/billing/subscriptions/subscribe`, `/billing/subscriptions/upgrade`, `/billing/subscriptions/cancel`, `/billing/payments/me`, `/billing/stripe/webhook`.

## Contribution Guidelines
- Fork/branch, keep PRs focused, and update docs when behaviors change.
- Add/adjust tests (pytest) for any new logic; mock external providers.
- Run `alembic upgrade head` and `pytest` before pushing.
- Use clear commit messages and reference relevant modules/paths.

## License
MIT-style licensing (check repository for the full text).
