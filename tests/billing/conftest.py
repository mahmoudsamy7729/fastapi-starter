import pytest
from uuid import uuid4
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select, update, delete
from src.hashing import hash_password
from tests.conftest import TestSessionDB
from src.auth.models import User, Provider
from src.billing.models import Plan, BillingPeriod, Subscription, SubscriptionStatus, PaymentProvider


@pytest.fixture(autouse=True)
def mock_save_stripe_plan(monkeypatch):
    """Prevent real Stripe product/price creation in tests."""
    mock = AsyncMock(return_value=None)
    monkeypatch.setattr("src.billing.service.StripeUtils.save_stripe_plan", mock)
    return mock


@pytest.fixture(autouse=True)
def mock_send_subscription_email_task(monkeypatch):
    """Stub Celery task to avoid hitting a broker and allow assertions."""
    delay_mock = MagicMock()
    task_mock = MagicMock(delay=delay_mock)
    monkeypatch.setattr("src.billing.service.send_subscription_email_task", task_mock)
    return delay_mock


@pytest.fixture()
def mock_checkout_url(monkeypatch):
    mock = AsyncMock(return_value="https://stripe.test/checkout")
    monkeypatch.setattr("src.billing.service.StripeUtils.stripe_subscripe_checkout_url", mock)
    return mock


@pytest.fixture()
async def fake_subscription(normal_user, test_plan):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        user=normal_user,
        plan=test_plan,
        started_at=now,
        current_period_end=now,
        cancel_at_period_end=False,
    )


@pytest.fixture()
async def mock_user_subscripe(monkeypatch, fake_subscription):
    mock = AsyncMock(return_value=fake_subscription)
    monkeypatch.setattr("src.billing.service.StripeUtils.user_subscripe", mock)
    return mock


@pytest.fixture()
async def admin_user():
    async with TestSessionDB() as session:

        result = await session.execute(
            select(User).where(User.email == "admin@test.com")
        )
        user = result.scalar_one_or_none()
        if user:
            return user

        hashed = await hash_password("123456")

        user = User(
            id=uuid4(),
            email="admin@test.com",
            username="admin_user",
            password=hashed,          
            is_active=True,
            is_verified=True,
            is_admin=True,
            provider=Provider.LOCAL,        
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture()
async def normal_user():
    async with TestSessionDB() as session:

        result = await session.execute(
            select(User).where(User.email == "normal@test.com")
        )
        user = result.scalar_one_or_none()
        if user:
            return user

        hashed = await hash_password("123456")

        user = User(
            id=uuid4(),
            email="normal@test.com",
            username="normal",
            password=hashed,          
            is_active=True,
            is_verified=True,
            provider=Provider.LOCAL,        
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    


@pytest.fixture
async def logged_in_admin(client, admin_user):
    response = await client.post("/login", json={
        "email": admin_user.email,
        "password": "123456"
    })
    assert response.status_code == 200
    token = response.json()["token"]
    refresh_token = response.cookies.get("refresh_token")

    return {"user": admin_user, "token": token, "refresh_token": refresh_token}


@pytest.fixture
async def logged_in_user(client, normal_user):
    response = await client.post("/login", json={
        "email": normal_user.email,
        "password": "123456"
    })
    assert response.status_code == 200
    token = response.json()["token"]
    refresh_token = response.cookies.get("refresh_token")

    return {"user": normal_user, "token": token, "refresh_token": refresh_token}


@pytest.fixture
async def admin_headers(logged_in_admin):
    return {"Authorization": f"Bearer {logged_in_admin['token']}"}


@pytest.fixture
async def user_headers(logged_in_user):
    return {"Authorization": f"Bearer {logged_in_user['token']}"}


@pytest.fixture
def plan_payload():
    return {
        "name": "test plan",
        "code": f"test-{uuid4().hex[:6]}",
        "price_cents": 0,
        "billing_period": "monthly",
        "currency": "USD",
        "is_active": True
    }


@pytest.fixture
async def test_plan():
    async with TestSessionDB() as session:
        # Check if the plan exists
        result = await session.execute(select(Plan).where(Plan.code == "test-plan"))
        plan = result.scalar_one_or_none()

        if plan:
            # Reactivate if soft-deleted
            if not plan.is_active:
                await session.execute(
                    update(Plan).where(Plan.id == plan.id).values(is_active=True)
                )
                await session.commit()
                await session.refresh(plan)
            return plan

        # Create plan if it does not exist
        plan = Plan(
            id=uuid4(),
            name="Test Plan",
            code="test-plan",
            price_cents=1000,
            billing_period=BillingPeriod.MONTHLY,
            currency="USD",
            is_active=True,
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        return plan



@pytest.fixture
async def test_subscription(normal_user, test_plan):
    async with TestSessionDB() as session:
        # Check if subscription exists for this user and plan
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == normal_user.id,
                Subscription.plan_id == test_plan.id
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            # Reactivate if canceled and reset cancel flag; ensure provider is set
            update_values = {"status": SubscriptionStatus.ACTIVE, "cancel_at_period_end": False}
            if subscription.provider is None:
                update_values["provider"] = PaymentProvider.MANUAL
            await session.execute(
                update(Subscription)
                .where(Subscription.id == subscription.id)
                .values(**update_values)
            )
            await session.commit()
            await session.refresh(subscription)
            return subscription

        # Create new subscription
        subscription = Subscription(
            id=uuid4(),
            user_id=normal_user.id,
            plan_id=test_plan.id,
            status=SubscriptionStatus.ACTIVE,
            cancel_at_period_end=False,
            provider=PaymentProvider.MANUAL,
        )
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
        return subscription


@pytest.fixture()
async def clear_user_subscriptions(normal_user):
    async with TestSessionDB() as session:
        await session.execute(
            delete(Subscription).where(Subscription.user_id == normal_user.id)
        )
        await session.commit()
    return normal_user


@pytest.fixture()
async def logged_in_user_no_subscription(client, clear_user_subscriptions):
    response = await client.post("/login", json={
        "email": clear_user_subscriptions.email,
        "password": "123456"
    })
    assert response.status_code == 200
    token = response.json()["token"]
    refresh_token = response.cookies.get("refresh_token")

    return {"user": clear_user_subscriptions, "token": token, "refresh_token": refresh_token}
