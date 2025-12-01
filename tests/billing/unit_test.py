import pytest
from uuid import uuid4
from types import SimpleNamespace
from fastapi import HTTPException
from unittest.mock import AsyncMock, Mock
from src.billing.service import PlanService, SubscriptionService
from src.billing.schemas import PlanCreate, PlanUpdate
from src.billing.models import BillingPeriod
from src.billing.utils import serialize_subscription


@pytest.mark.asyncio
class TestPlanService:
    async def test_retrieve_plans(self):
        repo = Mock()
        repo.list_plans = AsyncMock(return_value=["p1", "p2"])

        result = await PlanService.retrive_plans(repo)

        assert result == ["p1", "p2"]
        repo.list_plans.assert_awaited_once()

    async def test_create_plan_updates_stripe_ids(self, mock_save_stripe_plan):
        repo = Mock()
        repo.get_by_code = AsyncMock(return_value=None)
        created_plan = SimpleNamespace(id=uuid4(), stripe_product_id=None, stripe_price_id=None)
        repo.create = AsyncMock(return_value=created_plan)
        updated_plan = SimpleNamespace(id=created_plan.id, stripe_product_id="prod_1", stripe_price_id="price_1")
        repo.update = AsyncMock(return_value=updated_plan)
        mock_save_stripe_plan.return_value = SimpleNamespace(stripe_product_id="prod_1", stripe_price_id="price_1")

        data = PlanCreate(code="BASIC", price_cents=10, name="Basic", billing_period=BillingPeriod.MONTHLY)

        result = await PlanService.create_plan(data, repo)

        assert result == updated_plan
        repo.update.assert_awaited_once_with(created_plan, {"stripe_product_id": "prod_1", "stripe_price_id": "price_1"})

    async def test_create_plan_skips_stripe_when_failing(self, mock_save_stripe_plan):
        repo = Mock()
        repo.get_by_code = AsyncMock(return_value=None)
        created_plan = SimpleNamespace(id=uuid4())
        repo.create = AsyncMock(return_value=created_plan)
        mock_save_stripe_plan.return_value = None

        data = PlanCreate(code="BASIC", price_cents=10, name="Basic", billing_period=BillingPeriod.MONTHLY)

        result = await PlanService.create_plan(data, repo)

        assert result == created_plan
        repo.update.assert_not_called()

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

    async def test_soft_delete_plan_not_found(self):
        repo = Mock()
        repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await PlanService.soft_delete_plan(uuid4(), repo)

        assert exc.value.status_code == 404


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

    async def test_subscribe_user_success(self, mock_checkout_url):
        user = SimpleNamespace(id=uuid4())

        sub_repo = Mock()
        sub_repo.get_active_for_user = AsyncMock(return_value=None)

        plan = SimpleNamespace()
        plan_repo = Mock()
        plan_repo.get_by_code = AsyncMock(return_value=plan)

        user_repo = Mock()

        result = await SubscriptionService.subscribe_user_to_plan(
            user, "BASIC", sub_repo, plan_repo, user_repo
        )

        assert result == "https://stripe.test/checkout"
        mock_checkout_url.assert_awaited_once_with(user, plan, user_repo)

    async def test_subscribe_user_already_has_subscription(self):
        sub_repo = Mock()
        sub_repo.get_active_for_user = AsyncMock(return_value="active")

        with pytest.raises(HTTPException) as exc:
            await SubscriptionService.subscribe_user_to_plan(
                SimpleNamespace(id=uuid4()), "BASIC", sub_repo, Mock(), Mock()
            )

        assert exc.value.detail == "User already has an active subscription."

    async def test_subscribe_user_plan_not_found(self):
        sub_repo = Mock()
        sub_repo.get_active_for_user = AsyncMock(return_value=None)

        plan_repo = Mock()
        plan_repo.get_by_code = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await SubscriptionService.subscribe_user_to_plan(
                SimpleNamespace(id=uuid4()), "UNKNOWN", sub_repo, plan_repo, Mock()
            )

        assert exc.value.detail == "No active plan found for this code."

    async def test_cancel_subscription_success(self):
        subscription = SimpleNamespace(cancel_at_period_end=False)

        sub_repo = Mock()
        sub_repo.get_active_for_user = AsyncMock(return_value=subscription)
        sub_repo.cancel_at_period_end = AsyncMock(return_value=subscription)

        result = await SubscriptionService.cancel_subscription_at_end_of_period(uuid4(), sub_repo)

        assert result == subscription
        sub_repo.cancel_at_period_end.assert_awaited_once_with(subscription)

    async def test_cancel_subscription_already_marked(self):
        subscription = SimpleNamespace(cancel_at_period_end=True)
        sub_repo = Mock()
        sub_repo.get_active_for_user = AsyncMock(return_value=subscription)

        with pytest.raises(HTTPException) as exc:
            await SubscriptionService.cancel_subscription_at_end_of_period(uuid4(), sub_repo)

        assert exc.value.detail == "No active subscription found for this user."

    async def test_cancel_subscription_not_found(self):
        sub_repo = Mock()
        sub_repo.get_active_for_user = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await SubscriptionService.cancel_subscription_at_end_of_period(uuid4(), sub_repo)

        assert exc.value.status_code == 404

    async def test_stripe_webhook_checkout_sends_email(self, monkeypatch, mock_user_subscripe, fake_subscription, mock_send_subscription_email_task):
        event = {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test", "subscription": "sub_123", "customer": "cus_123"}},
        }
        run_mock = AsyncMock(return_value=event)
        monkeypatch.setattr("src.billing.service.run_in_threadpool", run_mock)

        class DummyRequest:
            def __init__(self, payload: bytes):
                self._payload = payload

            async def body(self):
                return self._payload

        request = DummyRequest(b"{}")
        sub_repo = Mock()
        plan_repo = Mock()

        result = await SubscriptionService.stripe_webhook(request, "sig", sub_repo, plan_repo)

        assert result is None
        mock_user_subscripe.assert_awaited_once_with(event["data"]["object"], sub_repo, plan_repo)
        mock_send_subscription_email_task.assert_called_once_with(serialize_subscription(fake_subscription))

    async def test_stripe_webhook_invalid_signature(self, monkeypatch):
        error = Exception("bad signature")
        run_mock = AsyncMock(side_effect=error)
        monkeypatch.setattr("src.billing.service.run_in_threadpool", run_mock)

        class DummyRequest:
            def __init__(self, payload: bytes):
                self._payload = payload

            async def body(self):
                return self._payload

        request = DummyRequest(b"{}")
        response = await SubscriptionService.stripe_webhook(request, "sig", Mock(), Mock())

        assert response == {"error": "bad signature"}
