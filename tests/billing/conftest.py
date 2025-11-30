import pytest
from uuid import uuid4
from sqlalchemy import select, update
from src.hashing import hash_password
from tests.conftest import TestSessionDB
from src.auth.models import User, Provider
from src.billing.models import Plan, BillingPeriod, Subscription, SubscriptionStatus




@pytest.fixture()
async def admin_user():
    async with TestSessionDB() as session:

        result = await session.execute(
            select(User).where(User.email == "admin@test.com")
        )
        user = result.scalar_one_or_none()
        if user:
            return user

        # 2) لو مش موجود، اعمله create
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
            # Reactivate if canceled
            if subscription.status != SubscriptionStatus.ACTIVE:
                await session.execute(
                    update(Subscription)
                    .where(Subscription.id == subscription.id)
                    .values(status=SubscriptionStatus.ACTIVE)
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
            started_at=None,
            expires_at=None,
        )
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
        return subscription
