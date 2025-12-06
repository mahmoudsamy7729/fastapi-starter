# features.md
# Feature Inventory

## Authentication
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| User registration | Create local user, auto-create profile, send verification email | src/auth/router.py -> UserService.register_user | DB users/profiles, fastapi-mail | Checks unique email/username; provider=LOCAL |
| Password login | Email/password auth, issues access & refresh tokens (cookie) | src/auth/router.py:/login -> UserService.login_user | JWT secrets, refresh_tokens table | Fails if inactive; refresh stored hashed |
| Refresh token rotation | Validate refresh cookie, revoke old, issue new tokens | src/auth/router.py:/refresh-token -> UserService.refresh_token | RefreshTokenRepository, hashing, JWT | Requires cookie; rotates by jti |
| Email verification | Verify via validation token; resend verification | /verify, /request/verify | VALIDATION_SECRET_KEY, email templates | Sets is_verified; idempotent |
| Password reset | Request reset email, set new password via token | /forget-password, /new-password | Validation token, hashing | Silent success on unknown email |
| Change password | Authenticated password change | /change-password | Access token, hashing | Verifies old password |
| OTP login | Email one-time code send + login with code | /request/login-code, /login/code | LoginCode table, hashing | Codes expire after 15 min, single-use |
| Account deactivation | Mark current user inactive | /deactivate | Access token | Sets is_active=False |

## OAuth / Social Login
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Google OAuth2 login | Redirect + callback exchange code for user info | /google/login + /auth/social/callback/google | Google OAuth endpoints, src/auth/utils.py | CSRF state cookie; creates user if missing |
| GitHub OAuth2 login | Redirect + callback exchange code for user info/emails | /github/login + /auth/social/callback/github | GitHub OAuth endpoints, src/auth/utils.py | Fallback email username@github.local |

## Token / Session Management
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| JWT generation/verification | Issue access/refresh/validation tokens with jti/exp/iat | src/jwt.py | ALGORITHM, secret keys | HTTP errors on invalid/expired |
| Refresh token storage | Hash + persist refresh tokens, revoke old per user | src/utils.py, src/repository.py | Argon2 hashing, refresh_tokens table | Rotation enforced on login/refresh |
| HTTP bearer guards | Active/not-active/admin user dependencies | src/auth_bearer.py | users table | Admin required for plan management |

## Plans & Billing
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| List plans | Public list of active plans | /billing/plans | PlanRepository | Ordered by price |
| Create plan | Admin-only plan creation, Stripe product/price sync | /billing/plans POST | Stripe API, PlanRepository, StripeGateway.save_plan_to_stripe | Updates plan with Stripe IDs |
| Update plan | Admin plan update + Stripe product/price update | /billing/plans/{id} PATCH | Stripe API | New Stripe price on pricing changes |
| Soft-delete plan | Admin plan deactivation | /billing/plans/{id} DELETE | DB | Marks is_active=False; Stripe soft-delete helper exists |
| Seed plans | Default Free/Pro seed via migration | alembic/versions/7248ef524515_seed_plans.py | Alembic | Runs during migrations |

## Subscriptions
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Get my subscription | Fetch active/current subscription with access window | /billing/subscriptions/me | SubscriptionRepoistory.get_subscription_with_access | Requires non-expired period; statuses active/canceled |
| Start subscription checkout | Initiate Stripe Checkout for plan | /billing/subscriptions/subscribe | Stripe Checkout, user auth, plan lookup | Prevents duplicate active sub |
| Upgrade subscription | Create checkout session to upgrade current plan | /billing/subscriptions/upgrade | Stripe, current subscription | Uses metadata upgrade_from_subscription_id |
| Cancel at period end | Mark subscription to cancel; sync to Stripe | /billing/subscriptions/cancel | Stripe modify subscription | Sets cancel_at_period_end=True |
| Subscription persistence | Create/update/cancel subscriptions in DB | src/billing/repository.py | subscriptions table | Handles provider ids, period calculations |

## Payments / Stripe Integration
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Customer creation/cache | Ensure Stripe customer id on user | StripeGateway.ensure_customer | Stripe Customers | Updates user.stripe_customer_id |
| Checkout session | Create subscription checkout session | StripeGateway.create_subscription_checkout_session | Stripe Checkout | Metadata stores plan/user IDs |
| Webhook handling | Validate signature; handle checkout completion, invoice succeeded, subscription deleted | SubscriptionService.stripe_webhook | stripe.Webhook.construct_event, Stripe events | Returns generic message even after handling |
| Subscription renewals | Update period on invoice payment succeeded | StripeGateway.handle_invoice_payment_succeeded | Stripe API, DB | 400 on missing invoice data |
| Cancellation sync | Handle subscription deletion/cancel | StripeGateway.handle_subscription_deleted | Stripe API, DB | Marks status canceled, updates period end |

## Background Jobs
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Subscription emails | Celery tasks to send confirmation/renewal emails | src/billing/tasks.py, src/billing/emails.py | Celery worker, SMTP | Triggered from webhook handlers |
| Subscription expiry sweep | Celery beat hourly task cancels expired subs | expire_subscriptions_task in src/billing/tasks.py | Sync DB engine | Scheduled in src/celery_app.py |
| Placeholder expiry task | Print-based TODO | src/tasks.py | Celery worker | Not implemented |

## Email & Notifications
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Verification email | Send validation link | src/auth/emails.py:send_verification_email | SMTP, templates/verify_email.html | BackgroundTask |
| Password reset email | Send reset link | src/auth/emails.py:send_password_reset_email | SMTP | BackgroundTask |
| OTP email | Send one-time code | src/auth/emails.py:send_login_code | SMTP | BackgroundTask |
| Subscription emails | Confirmation/updates | src/billing/emails.py | SMTP | Triggered via Celery |

## Access Control & Rate Limiting
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Active/verified checks | Guard routes for active + verified users | src/auth_bearer.py | JWT, DB | Custom HTTP errors |
| Admin check | Require is_admin for plan mutations | src/auth_bearer.py | DB | Used on plan routes |
| Rate limiting | Default 5/min per Authorization or IP | src/rate_limiter.py + middleware in src/main.py | slowapi | Webhook exempted |

## Infrastructure & Utilities
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Logging | Loguru setup, file rotation, intercept std logging | src/logging.py | loguru | Writes stdout + logs/app.log |
| CORS | Allow all origins/headers/methods | src/main.py | FastAPI | Adjust for prod |
| Config management | Pydantic settings from .env | src/config.py | .env file | Defaults provided |
| DB sessions | Async session dependency; sync session for Celery | src/database.py | SQLAlchemy | Test overrides in tests/conftest.py |
| Email config | fastapi-mail connection | src/utils.py | SMTP creds | Templates under templates/email |

## Testing & Quality
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Auth API tests | Register/login/refresh/password/OTP | tests/auth/api_test.py | httpx AsyncClient | Mocks email sending |
| Auth unit tests | Services, JWT, OAuth, OTP logic | tests/auth/unit_test.py | pytest-asyncio | Extensive mocks |
| Billing API tests | Plans CRUD, subscriptions, webhook | tests/billing/api_test.py | httpx, monkeypatch Stripe/Celery | Uses fixtures for admin/user/subscription |
| Test fixtures | Shared DB/session overrides | tests/conftest.py, tests/billing/conftest.py, tests/auth/conftest.py | Async SQLAlchemy | Disables rate limiter in tests |

## Partial / Unfinished Areas
| Feature | Description | Location | Dependencies | Notes |
| --- | --- | --- | --- | --- |
| Profile service/repo gaps | Methods not implemented | src/auth/service.py, src/auth/repository.py | DB | Future work |
| Expiry task TODO | expire_subscriptions placeholder | src/tasks.py | Celery | No logic yet |
| Empty stubs | constants/config/exceptions modules | src/auth/*, src/billing/* | n/a | Placeholder files |
| Unused enum options | PAYMOB, PaymentStatus | src/billing/models.py | n/a | Not wired into flows |
