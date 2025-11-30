import pytest
from uuid import uuid4
from fastapi import HTTPException
from unittest.mock import AsyncMock, Mock
from src.billing.service import PlanService, SubscriptionService
from src.billing.schemas import PlanCreate, PlanUpdate
from src.billing.models import BillingPeriod



@pytest.mark.asyncio
class TestPlanService:
    async def test_retrieve_plans(self):
        repo = Mock()
        repo.list_plans = AsyncMock(return_value=["p1", "p2"])

        result = await PlanService.retrive_plans(repo)

        assert result == ["p1", "p2"]
        repo.list_plans.assert_awaited_once()


    async def test_create_plan_success(self):
        repo = Mock()
        repo.get_by_code = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value={"id": 1})

        data = PlanCreate(code="BASIC", price_cents=10, name="Basic", billing_period=BillingPeriod.MONTHLY)

        result = await PlanService.create_plan(data, repo)

        assert result == {"id": 1}
        repo.create.assert_awaited_once()


    async def test_create_plan_duplicate_code(self):
        repo = Mock()
        repo.get_by_code = AsyncMock(return_value=True)

        data = PlanCreate(code="BASIC", price_cents=10, name="Basic", billing_period=BillingPeriod.MONTHLY)

        with pytest.raises(HTTPException) as exc:
            await PlanService.create_plan(data, repo)

        assert exc.value.status_code == 400
        assert exc.value.detail == "Existing Code"


    async def test_get_plan_not_found(self):
        repo = Mock()
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException):
            await PlanService.get_plan_by_id(uuid4(), repo)


    async def test_update_plan_success(self):
        plan = Mock()
        repo = Mock()
        repo.get_by_id = AsyncMock(return_value=plan)
        repo.update = AsyncMock(return_value={"updated": True})

        data = PlanUpdate(price_cents=25)

        result = await PlanService.update_plan(uuid4(), data, repo)

        assert result == {"updated": True}
        repo.update.assert_awaited_once()


    async def test_soft_delete_plan_success(self):
        plan = Mock(is_active=True)
        repo = Mock()
        repo.get_by_id = AsyncMock(return_value=plan)
        repo.soft_delete = AsyncMock()

        await PlanService.soft_delete_plan(uuid4(), repo)

        repo.soft_delete.assert_awaited_once()


    async def test_soft_delete_already_deleted(self):
        plan = Mock(is_active=False)
        repo = Mock()
        repo.get_by_id = AsyncMock(return_value=plan)

        with pytest.raises(HTTPException) as exc:
            await PlanService.soft_delete_plan(uuid4(), repo)

        assert exc.value.status_code == 400



@pytest.mark.asyncio
class TestSubscriptionService:

    async def test_get_user_subscription_success(self):
        repo = Mock()
        repo.get_active_for_user = AsyncMock(return_value="subscription")

        user_id = uuid4()
        result = await SubscriptionService.get_user_subscription(user_id, repo)

        assert result == "subscription"


    async def test_get_user_subscription_not_found(self):
        repo = Mock()
        repo.get_active_for_user = AsyncMock(return_value=None)

        with pytest.raises(HTTPException):
            await SubscriptionService.get_user_subscription(uuid4(), repo)


    async def test_subscribe_user_success(self):
        user_id = uuid4()

        sub_repo = Mock()
        sub_repo.get_active_for_user = AsyncMock(return_value=None)
        sub_repo.create_subscription = AsyncMock(return_value="created_sub")

        plan = Mock()
        plan_repo = Mock()
        plan_repo.get_by_code = AsyncMock(return_value=plan)

        result = await SubscriptionService.subscribe_user_to_plan(
            user_id, "BASIC", sub_repo, plan_repo
        )

        assert result == "created_sub"


    async def test_subscribe_user_already_has_subscription(self):
        sub_repo = Mock()
        sub_repo.get_active_for_user = AsyncMock(return_value="active")

        with pytest.raises(HTTPException):
            await SubscriptionService.subscribe_user_to_plan(
                uuid4(), "BASIC", sub_repo, Mock()
            )


    async def test_subscribe_user_plan_not_found(self):
        sub_repo = Mock()
        sub_repo.get_active_for_user = AsyncMock(return_value=None)

        plan_repo = Mock()
        plan_repo.get_by_code = AsyncMock(return_value=None)

        with pytest.raises(HTTPException):
            await SubscriptionService.subscribe_user_to_plan(
                uuid4(), "UNKNOWN", sub_repo, plan_repo
            )


    async def test_cancel_subscription_success(self):
        subscription = Mock()

        sub_repo = Mock()
        sub_repo.get_active_for_user = AsyncMock(return_value=subscription)
        sub_repo.cancel_at_period_end = AsyncMock()

        result = await SubscriptionService.cancel_subscription(uuid4(), sub_repo)

        assert result == subscription
        sub_repo.cancel_at_period_end.assert_awaited_once()

