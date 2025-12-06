# docs.md
# Project Documentation

## Overview
FastAPI-based authentication and billing service with JWT access/refresh tokens, OAuth (Google/GitHub), OTP login, email flows, plan/subscription management, and Stripe billing integration. Async-first architecture uses SQLAlchemy 2.0 async ORM, Celery for background jobs, Redis as broker, and PostgreSQL as the primary datastore.

## Architecture
- API layer: FastAPI app (`src/main.py`) with routers per domain (`src/auth/router.py`, `src/billing/router.py`).
- Services: Business logic in `src/auth/service.py` and `src/billing/service.py`.
- Repositories: Data access layer for each aggregate (`src/repository.py`, `src/auth/repository.py`, `src/billing/repository.py`).
- Models: SQLAlchemy models (`src/auth/models.py`, `src/billing/models.py`, `src/models.py`).
- Utilities: JWT, hashing, email, rate limiting, logging, and Stripe gateway helpers.
- Background workers: Celery app (`src/celery_app.py`) with worker and beat; beat schedules subscription expiry checks.
- Tests: Pytest + httpx ASGI client with DB overrides in `tests/`.

## Folder Structure (key paths)
- `src/main.py` – FastAPI app wiring, middleware, routers.
- `src/config.py` – Pydantic settings loader from `.env`.
- `src/database.py` – Async engine/session + sync engine for Celery tasks.
- `src/auth/*` – Auth domain (models, schemas, service, router, OAuth/OTP utils, emails).
- `src/billing/*` – Billing domain (models, schemas, service, router, Stripe gateway, Celery tasks/emails).
- `src/tasks.py` – Placeholder Celery task (subscription expiry TODO).
- `src/celery_app.py` – Celery worker/beat setup.
- `templates/email/` – Jinja email templates (verify, reset, OTP, subscription).
- `alembic/` – Migration scripts (schema + seeds).
- `tests/` – API + unit tests for auth and billing with fixtures.
- `requirements/` – Runtime and dev dependency pins.
- `docker-compose.yml`, `Dockerfile` – Container orchestration for API, Postgres, Redis, Celery, pgAdmin.

## Technology Stack
- Framework: FastAPI, Starlette, Pydantic v2.
- ORM/DB: SQLAlchemy 2.0 async, asyncpg, PostgreSQL; Alembic migrations.
- Auth: python-jose JWT, HTTPBearer security, Argon2 hashing (passlib).
- Async/Concurrency: run_in_threadpool for CPU-bound/hash/Stripe calls.
- Background jobs: Celery worker/beat, Redis broker.
- Rate limiting: slowapi (5/min default, key = Authorization header or IP).
- Email: fastapi-mail with SMTP + Jinja templates.
- Payments: Stripe SDK.
- Testing: pytest, pytest-asyncio, httpx AsyncClient.

## Configuration & Environment
Loaded via `src/config.py` (`.env` or env vars). Key variables (see `.env.example`):
- App: `APP_NAME`, `APP_ENV`, `APP_DEBUG`, `APP_URL`
- DB: `DATABASE_URL`, `SYNC_DATABASE_URL`, `TEST_DATABASE_URL`
- JWT: `ALGORITHM`, `ACCESS_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE`, `REFRESH_SECRET_KEY`, `REFRESH_TOKEN_EXPIRE`, `VALIDATION_SECRET_KEY`, `VALIDATION_TOKEN_EXPIRE`
- Mail: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- OAuth Google: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GOOGLE_AUTH_URL`, `GOOGLE_TOKEN_URL`, `GOOGLE_USERINFO_URL`
- OAuth GitHub: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`, `GITHUB_AUTHORIZE_URL`, `GITHUB_TOKEN_URL`, `GITHUB_USER_API`, `GITHUB_EMAILS`
- Infra: `REDIS_URL`, `CELERY_WORKER_URL`, `CELERY_BEAT_URL`
- Stripe: `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`

## Database Models
- User (`users`): id (UUID), email, username, password (nullable for social), is_admin, is_active, is_verified, stripe_customer_id, provider enum, timestamps; relations: profile, subscriptions, refresh_tokens.
- Profile (`profiles`): user_id unique FK, first/last name, profile_img, timestamps.
- LoginCode (`login_codes`): user_id FK cascade, code_hash, created_at, expires_at.
- RefreshToken (`refresh_tokens`): user_id FK, jti unique, token_hash, created_at, expires_at, revoked, revoked_at, replaced_by_jti.
- Plan (`plans`): name, code unique, price_cents, currency, billing_period, is_active, stripe_product_id, stripe_price_id, timestamps.
- Subscription (`subscriptions`): user_id, plan_id, status, provider, provider_subscription_id unique, provider_customer_id, started_at, current_period_end, canceled_at, cancel_at_period_end.
- Enums: Provider (google/github/local), SubscriptionStatus, BillingPeriod, PaymentStatus (unused), PaymentProvider (stripe/paymob/manual).

## API Overview
Auth (`src/auth/router.py`):
- POST `/register` – create user, send verification email (BackgroundTask); returns user.
- POST `/login` – password login; sets `refresh_token` cookie; returns access token + user.
- POST `/refresh-token` – rotate refresh; sets new cookie; returns access token.
- GET `/verify` – verify email via validation token.
- POST `/request/verify` – resend verification email.
- POST `/forget-password` – send reset link (silent on unknown email).
- POST `/new-password` – set new password via token.
- POST `/change-password` – change password (auth required).
- POST `/request/login-code` – send OTP code to email.
- POST `/login/code` – OTP login; sets refresh cookie; returns tokens + user.
- GET `/google/login` + `/auth/social/callback/google` – Google OAuth.
- GET `/github/login` + `/auth/social/callback/github` – GitHub OAuth.
- POST `/deactivate` – deactivate current user.

Billing (`src/billing/router.py`):
- GET `/billing/plans` – list active plans.
- POST `/billing/plans` – create plan (admin).
- GET `/billing/plans/{plan_id}` – retrieve plan.
- PATCH `/billing/plans/{plan_id}` – update plan (admin).
- DELETE `/billing/plans/{plan_id}` – soft-delete plan (admin).
- GET `/billing/subscriptions/me` – current subscription for user.
- POST `/billing/subscriptions/subscribe` – start Stripe checkout for plan.
- POST `/billing/subscriptions/cancel` – cancel at period end.
- POST `/billing/subscriptions/upgrade` – upgrade via Stripe checkout.
- POST `/billing/stripe/webhook` – Stripe webhook (rate-limit exempt).

## Auth & Token Flow
- Passwords hashed with Argon2 (`src/hashing.py`).
- JWTs include `jti`, `exp`, `iat`; access/refresh/validation tokens via `src/jwt.py`.
- Refresh tokens stored hashed; rotation revokes previous tokens (`src/utils.py`, `src/repository.py`).
- Validation tokens for email verification/password reset (`VALIDATION_SECRET_KEY`).
- Guards: active/non-active/admin dependencies in `src/auth_bearer.py`.
- OAuth: state cookie protection; user auto-provision on first login.
- OTP: hashed code stored with expiry; single-use delete on success.

## Billing/Subscription Flow
- Plan CRUD via `PlanService`/`PlanRepository`; Stripe product/price created/updated when available.
- Subscribe/upgrade: Stripe Checkout session; metadata stores plan/user/upgrade info; webhook creates/cancels/renews local subs.
- Cancel: Stripe modify subscription when provider is Stripe; local sub marked cancel_at_period_end.
- Renewals: `invoice.payment_succeeded` updates period; `customer.subscription.deleted` marks canceled.

## Payments (Stripe)
- API key from `STRIPE_SECRET_KEY`; webhook signature `STRIPE_WEBHOOK_SECRET`.
- Customer creation on-demand; stored in `User.stripe_customer_id`.
- Product/price IDs cached on Plan; new price created on pricing changes.
- Operations run in threadpool to avoid blocking event loop.

## Background Tasks / Workers
- FastAPI BackgroundTasks for auth emails.
- Celery worker: subscription email tasks (`send_subscription_email_task`, `send_update_subscription_email_task`).
- Celery beat: hourly `expire_subscriptions_task` to cancel expired subs.
- Placeholder `src/tasks.py:expire_subscriptions` remains TODO.

## Error Handling
- Custom validation handler returns `{errors: {field: msg}}` (422).
- Consistent `HTTPException` usage with meaningful codes for auth/billing flows.
- Refresh validation checks presence, revocation, jti, expiry.

## Deployment Notes
- Docker Compose: API (8000), Postgres (5432), Redis (6379), Celery worker/beat, pgAdmin (5050); project volume mounted.
- Dockerfile: Python 3.12-slim, installs requirements, runs `uvicorn src.main:app --reload`.
- Run migrations: `alembic upgrade head`.
- CORS open; tighten for production.
- Cookies `httponly`, `samesite=lax`; set `secure=True` in production.

## Testing
- Pytest + pytest-asyncio; httpx AsyncClient with ASGITransport.
- DB overrides to `TEST_DATABASE_URL`; rate limiter disabled in tests.
- Auth tests cover register/login/refresh/password/OTP/OAuth; billing tests cover plans/subscriptions/webhooks.

## Conventions / Gaps
- Service + repository layering; blocking calls offloaded to threadpool.
- Refresh tokens hashed + rotated per login/refresh.
- Unimplemented: `ProfileService`, `ProfileReposiotry.get_by_user_id`, `src/tasks.expire_subscriptions` logic.
- Empty stubs: `src/auth/constants.py`, `src/auth/config.py`, `src/auth/exceptions.py`, `src/billing/constants.py`, `src/billing/config.py`, `src/billing/exceptions.py`.
- Unused enum entries: `PaymentStatus`, `PAYMOB` provider option.
