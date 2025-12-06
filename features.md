
# Feature Inventory

## Authentication
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| User registration & profile seed | Create user with hashed password and empty profile; enforce unique email/username | src/auth/router.py -> UserService.register_user -> UserRepository.create | SQLAlchemy, Argon2 hashing | Provider set to LOCAL; profile created automatically |
| Password login | Verify password, issue access/refresh JWTs, store hashed refresh token, set cookie | src/auth/router.py:/login, src/auth/service.py:login_user | JWT secrets, RefreshTokenRepository, Argon2 | Blocks inactive users |
| Refresh token rotation | Validate refresh cookie, check JTI in DB, revoke/replace old token | /refresh-token -> UserService.refresh_token | refresh_tokens table, hashing, JWT | Old token revoked and linked via `replaced_by_jti` |
| Email verification (request/verify) | Send validation token email and mark user verified | /request/verify, /verify -> UserService.validate_user | FastAPI-Mail, validation_secret_key | Idempotent verify path |
| Password reset | Send reset token and set new password | /forget-password, /new-password | FastAPI-Mail, hashing | Silent success on unknown email |
| Change password | Authenticated password change with old-password check | /change-password -> UserService.change_password | Access token, hashing | 403 on wrong old password |
| OTP login | Issue hashed OTP (15m expiry), email it, and log in with code | /request/login-code, /login/code | LoginCodeRepository, hashing, SMTP | OTP deleted after use; single latest code checked |
| Account deactivation | Mark current user inactive | /deactivate -> UserService.deactivate_user | Access token | Inactive users blocked by auth dependency |

## OAuth / Social Login
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Google OAuth2 | Redirect with state cookie, exchange code, fetch profile, auto-provision user | /google/login, /auth/social/callback/google -> UserService.login_with_google | Google OAuth endpoints, httpx, JWT, refresh_tokens | Sets provider=GOOGLE, marks verified |
| GitHub OAuth2 | Redirect with state cookie, exchange code, fetch emails/profile, auto-provision user | /github/login, /auth/social/callback/github -> UserService.login_with_github | GitHub OAuth endpoints, httpx, JWT, refresh_tokens | Fallback email `${username}@github.local` |

## Token / Session Management
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| JWT issue/verify | Access, refresh, and validation tokens with `jti`, `exp`, `iat` | src/jwt.py | ALGORITHM, secret keys | Raises HTTP errors on invalid/expired |
| Refresh token storage | Hash + persist refresh tokens per user; revoke-all on login | src/utils.py:store_refresh_token_in_db, src/repository.py | Argon2 hashing, refresh_tokens table | Rotation enforced on login/refresh |
| Auth guards | Active/user/admin dependencies | src/auth_bearer.py | users table | Admin required for plan mutations |

## Plans & Pricing
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| List active plans | Public list ordered by price | /billing/plans -> PlanRepository.list_plans | DB | Filters `is_active=True` |
| Create plan | Admin-only create with Stripe product/price sync | /billing/plans POST -> PlanService.create_plan | StripeGateway, PlanRepository | Adds Stripe IDs to plan |
| Update plan | Admin update with new Stripe price if pricing fields change | /billing/plans/{id} PATCH | StripeGateway.update_plan_in_stripe | New price created when amount/currency/period changes |
| Soft-delete plan | Admin mark plan inactive | /billing/plans/{id} DELETE | PlanRepository.soft_delete | Stripe soft-delete helper available |
| Plan tiers | Store tier for gating features | Plan.tier, billing/dependencies.require_plan | Enum PlanTier | Higher number = higher access |
| Seed plans | Migration seeds default plans | alembic/versions/7248ef524515_seed_plans.py | Alembic | Runs during migrations |

## Billing & Subscriptions
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Get current subscription | Fetch active/non-expired sub with plan/user eager loaded | /billing/subscriptions/me -> SubscriptionRepoistory.get_subscription_with_access | DB | Allows canceled subs until period end |
| Start subscription checkout | Create Stripe Checkout session for plan | /billing/subscriptions/subscribe | StripeGateway.create_subscription_checkout_session, auth guard | Blocks if active subscription exists |
| Upgrade subscription | Checkout for new plan; cancel old Stripe sub on completion | /billing/subscriptions/upgrade | StripeGateway.user_subscribe (upgrade path) | Metadata carries `upgrade_from_subscription_id` |
| Cancel at period end | Set subscription to cancel and update Stripe | /billing/subscriptions/cancel | StripeGateway.cancel_subscription_at_period_end | Raises if already canceling |
| Subscription access window | Ensure access only if `current_period_end` > now and status not canceled | SubscriptionRepoistory.get_subscription_with_access | DB | Used across billing deps |

## Stripe Integration
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Ensure customer | Create Stripe customer when missing | StripeGateway.ensure_customer | Stripe Customers API | Saves `stripe_customer_id` on user |
| Checkout session | Build subscription checkout with metadata | StripeGateway.create_subscription_checkout_session | Stripe Checkout | Success/cancel URLs placeholders; update for prod |
| Invoice success handling | Update sub period, record payment, send emails | StripeGateway.handle_invoice_payment_succeeded, PaymentRepository | Stripe invoices, Celery | Billing reason drives email type |
| Invoice failure handling | Mark subscription past_due | StripeGateway.handle_invoice_payment_failed | Stripe invoices | Sets status PAST_DUE |
| Subscription deleted handling | Cancel local subscription with current period end = now | StripeGateway.handle_subscription_deleted | Stripe subscription object | 400 if missing id |

## Webhooks
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Webhook validation | Verify signature and dispatch by event type | /billing/stripe/webhook -> SubscriptionService.stripe_webhook | STRIPE_WEBHOOK_SECRET, stripe.Webhook.construct_event | Rate-limit exempt |
| Checkout completion | Create/upgrade local subscription from checkout session | StripeGateway.user_subscribe | Stripe subscription retrieval | Cancels old sub on upgrade |
| Payment recording | Persist payments on invoice success | StripeGateway.record_invoice_payment | PaymentRepository | Stores amount/currency/status |

## User Management
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Profile scaffold | Empty profile created alongside user | UserRepository.create | DB | Profile update method stubbed |
| Admin guard | Require `is_admin` for plan mutations | src/auth_bearer.py:get_admin_user | Access token | Returns 403 otherwise |

## Dashboard
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| API-first backend | Backend ready for UI integration; no frontend shipped | n/a | n/a | Build dashboard against documented endpoints |

## Background Tasks / Celery
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Subscription email dispatch | Send confirmation/renewal/update emails via Celery | src/billing/tasks.py, src/billing/emails.py | Celery worker, SMTP | Triggered from webhook handlers |
| Expiry sweep (beat) | Hourly task cancels expired subs | expire_subscriptions_task in src/billing/tasks.py | Celery beat, sync DB engine | Uses `current_period_end` <= now |
| Placeholder task | Legacy expire_subscriptions stub | src/tasks.py | Celery worker | Not scheduled |

## Admin Features
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Plan management | Create/update/delete/list plans | /billing/plans*, PlanService | Admin auth guard | Stripe sync on create/update |
| Subscription oversight | Cancel/upgrade via API | /billing/subscriptions/* | Admin not required, but auth required | Tie into dashboards |

## Utilities / Helpers
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Rate limiting | Default 5/min keying on Authorization or IP | src/rate_limiter.py | slowapi | Webhook exempted |
| Logging | Loguru setup with stdout and file rotation | src/logging.py | loguru | Intercepts standard logging |
| Config management | Pydantic settings loader from .env | src/config.py | pydantic-settings | Supports aliasing (e.g., DATABASE_URL) |
| Email transport | FastAPI-Mail connection config | src/utils.py:conf | SMTP creds, templates/email | Shared by auth/billing emails |
| DB session deps | Async DB dependency for API; sync for Celery | src/database.py | SQLAlchemy | Tests override with `TEST_DATABASE_URL` |

## Partial / Planned
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Profile service implementation | CRUD helpers for profiles | src/auth/service.py:ProfileService, ProfileReposiotry.get_by_user_id | DB | Stubbed for future |
| Payment status coverage | PaymentStatus enum values beyond `succeeded` path | src/billing/models.py | n/a | Not fully wired |
| PAYMOB provider | Extra PaymentProvider enum | src/billing/models.py | n/a | Not implemented |
| Legacy Celery task | expire_subscriptions placeholder | src/tasks.py | Celery | Replace with real logic or remove |
