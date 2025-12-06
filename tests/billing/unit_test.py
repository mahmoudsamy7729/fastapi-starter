import pytest
from uuid import uuid4
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from unittest.mock import AsyncMock, Mock, ANY

from src.billing.service import PlanService, SubscriptionService
from src.billing.schemas import PlanCreate, PlanUpdate
from src.billing.models import BillingPeriod, PaymentProvider
from src.billing.utils import serialize_subscription


pytestmark = pytest.mark.asyncio


def _dummy_request(payload: bytes = b"{}"):
    class DummyRequest:
        def __init__(self, data: bytes):
            self._payload = data

        async def body(self):
            return self._payload
    return DummyRequest(payload)


async def test_retrieve_plans():
    repo = Mock()
    repo.list_plans = AsyncMock(return_value=["p1", "p2"])

    result = await PlanService.retrive_plans(repo)

    assert result == ["p1", "p2"]
    repo.list_plans.assert_awaited_once()


async def test_create_plan_updates_stripe_ids(monkeypatch):
    repo = Mock()
    repo.get_by_code = AsyncMock(return_value=None)
    created_plan = SimpleNamespace(id=uuid4(), stripe_product_id=None, stripe_price_id=None)
    repo.create = AsyncMock(return_value=created_plan)
    updated_plan = SimpleNamespace(id=created_plan.id, stripe_product_id="prod_1", stripe_price_id="price_1")
    repo.update = AsyncMock(return_value=updated_plan)

    stripe_mock = AsyncMock(return_value=SimpleNamespace(stripe_product_id="prod_1", stripe_price_id="price_1"))
    monkeypatch.setattr("src.billing.service.StripeGateway.save_plan_to_stripe", stripe_mock)

    data = PlanCreate(code="BASIC", price_cents=10, name="Basic", billing_period=BillingPeriod.MONTHLY)

    result = await PlanService.create_plan(data, repo)

    assert result == updated_plan
    repo.update.assert_awaited_once_with(created_plan, {"stripe_product_id": "prod_1", "stripe_price_id": "price_1"})


async def test_create_plan_skips_stripe_when_failing(monkeypatch):
    repo = Mock()
    repo.get_by_code = AsyncMock(return_value=None)
    created_plan = SimpleNamespace(id=uuid4())
    repo.create = AsyncMock(return_value=created_plan)
    repo.update = AsyncMock()

    monkeypatch.setattr("src.billing.service.StripeGateway.save_plan_to_stripe", AsyncMock(return_value=None))

    data = PlanCreate(code="BASIC", price_cents=10, name="Basic", billing_period=BillingPeriod.MONTHLY)

    result = await PlanService.create_plan(data, repo)

    assert result == created_plan
    repo.update.assert_not_called()


async def test_create_plan_duplicate_code():
    repo = Mock()
    repo.get_by_code = AsyncMock(return_value=True)

    data = PlanCreate(code="BASIC", price_cents=10, name="Basic", billing_period=BillingPeriod.MONTHLY)

    with pytest.raises(HTTPException) as exc:
        await PlanService.create_plan(data, repo)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Existing Code"


async def test_get_plan_not_found():
    repo = Mock()
    repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException):
        await PlanService.get_plan_by_id(uuid4(), repo)


async def test_update_plan_success(monkeypatch):
    plan = Mock()
    repo = Mock()
    repo.get_by_id = AsyncMock(return_value=plan)
    repo.update = AsyncMock(return_value={"updated": True})

    update_data = {"price_cents": 25}
    monkeypatch.setattr("src.billing.service.StripeGateway.update_plan_in_stripe", AsyncMock(return_value=update_data))

    data = PlanUpdate(price_cents=25)

    result = await PlanService.update_plan(uuid4(), data, repo)

    assert result == {"updated": True}
    repo.update.assert_awaited_once_with(plan, update_data)


async def test_soft_delete_plan_success():
    plan = Mock(is_active=True)
    repo = Mock()
    repo.get_by_id = AsyncMock(return_value=plan)
    repo.soft_delete = AsyncMock()

    await PlanService.soft_delete_plan(uuid4(), repo)

    repo.soft_delete.assert_awaited_once()


async def test_soft_delete_already_deleted():
    plan = Mock(is_active=False)
    repo = Mock()
    repo.get_by_id = AsyncMock(return_value=plan)

    with pytest.raises(HTTPException) as exc:
        await PlanService.soft_delete_plan(uuid4(), repo)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Plan already deleted."


async def test_soft_delete_plan_not_found():
    repo = Mock()
    repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await PlanService.soft_delete_plan(uuid4(), repo)

    assert exc.value.status_code == 404


async def test_get_user_subscription_success():
    repo = Mock()
    repo.get_subscription_with_access = AsyncMock(return_value="subscription")

    user_id = uuid4()
    result = await SubscriptionService.get_user_subscription(user_id, repo)

    assert result == "subscription"
    repo.get_subscription_with_access.assert_awaited_once_with(user_id)


async def test_get_user_subscription_not_found():
    repo = Mock()
    repo.get_subscription_with_access = AsyncMock(return_value=None)

    with pytest.raises(HTTPException):
        await SubscriptionService.get_user_subscription(uuid4(), repo)


async def test_subscribe_user_success(monkeypatch):
    user = SimpleNamespace(id=uuid4())

    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value=None)

    plan = SimpleNamespace()
    plan_repo = Mock()
    plan_repo.get_by_code = AsyncMock(return_value=plan)

    user_repo = Mock()

    checkout_mock = AsyncMock(return_value="https://stripe.test/checkout")
    monkeypatch.setattr("src.billing.service.StripeGateway.create_subscription_checkout_session", checkout_mock)

    result = await SubscriptionService.subscribe_user_to_plan(
        user, "BASIC", sub_repo, plan_repo, user_repo
    )

    assert result == "https://stripe.test/checkout"
    checkout_mock.assert_awaited_once_with(user, plan, user_repo)


async def test_subscribe_user_already_has_subscription():
    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value="active")

    with pytest.raises(HTTPException) as exc:
        await SubscriptionService.subscribe_user_to_plan(
            SimpleNamespace(id=uuid4()), "BASIC", sub_repo, Mock(), Mock()
        )

    assert exc.value.detail == "User already has an active subscription."


async def test_subscribe_user_plan_not_found():
    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value=None)

    plan_repo = Mock()
    plan_repo.get_by_code = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await SubscriptionService.subscribe_user_to_plan(
            SimpleNamespace(id=uuid4()), "UNKNOWN", sub_repo, plan_repo, Mock()
        )

    assert exc.value.detail == "No active plan found for this code."


async def test_cancel_subscription_success(monkeypatch):
    subscription = SimpleNamespace(
        cancel_at_period_end=False,
        provider=PaymentProvider.STRIPE,
        provider_subscription_id="sub_test",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=10),
    )

    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value=subscription)
    sub_repo.cancel_subscription = AsyncMock(return_value=SimpleNamespace(cancel_at_period_end=False, status="canceled"))

    monkeypatch.setattr(
        "src.billing.service.StripeGateway.cancel_subscription_at_period_end",
        AsyncMock(return_value=(datetime.now(timezone.utc), subscription.current_period_end)),
    )

    result = await SubscriptionService.cancel_subscription_at_end_of_period(uuid4(), sub_repo)

    assert result.cancel_at_period_end is False
    sub_repo.cancel_subscription.assert_awaited_once_with(
        provider=subscription.provider,
        provider_subscription_id=subscription.provider_subscription_id,
        canceled_at=ANY,
        current_period_end=subscription.current_period_end,
    )


async def test_cancel_subscription_already_marked():
    subscription = SimpleNamespace(cancel_at_period_end=True)
    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value=subscription)

    with pytest.raises(HTTPException) as exc:
        await SubscriptionService.cancel_subscription_at_end_of_period(uuid4(), sub_repo)

    assert exc.value.detail == "Subscription is already set to cancel at the end of the billing period."


async def test_cancel_subscription_not_found():
    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await SubscriptionService.cancel_subscription_at_end_of_period(uuid4(), sub_repo)

    assert exc.value.status_code == 404


async def test_cancel_subscription_missing_local_record(monkeypatch):
    subscription = SimpleNamespace(
        cancel_at_period_end=False,
        provider=PaymentProvider.STRIPE,
        provider_subscription_id="sub_test",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=10),
    )
    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value=subscription)
    sub_repo.cancel_subscription = AsyncMock(return_value=None)

    monkeypatch.setattr(
        "src.billing.service.StripeGateway.cancel_subscription_at_period_end",
        AsyncMock(return_value=(datetime.now(timezone.utc), subscription.current_period_end)),
    )

    with pytest.raises(HTTPException) as exc:
        await SubscriptionService.cancel_subscription_at_end_of_period(uuid4(), sub_repo)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Subscription not found in our database."


async def test_upgrade_subscription_success(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    current_sub = SimpleNamespace(
        provider=PaymentProvider.STRIPE,
        provider_subscription_id="sub_old",
        plan_id=uuid4(),
    )
    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value=current_sub)

    new_plan = SimpleNamespace(id=uuid4(), code="NEW")
    plan_repo = Mock()
    plan_repo.get_by_code = AsyncMock(return_value=new_plan)

    user_repo = Mock()
    checkout_mock = AsyncMock(return_value="https://stripe.test/upgrade")
    monkeypatch.setattr("src.billing.service.StripeGateway.create_subscription_checkout_session", checkout_mock)

    result = await SubscriptionService.upgrade_subscription(user, "NEW", sub_repo, plan_repo, user_repo)

    assert result == "https://stripe.test/upgrade"
    checkout_mock.assert_awaited_once_with(user, new_plan, user_repo, current_sub.provider_subscription_id)


async def test_upgrade_subscription_same_plan():
    plan_id = uuid4()
    current_sub = SimpleNamespace(plan_id=plan_id)
    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value=current_sub)

    plan_repo = Mock()
    plan_repo.get_by_code = AsyncMock(return_value=SimpleNamespace(id=plan_id))

    with pytest.raises(HTTPException) as exc:
        await SubscriptionService.upgrade_subscription(SimpleNamespace(id=uuid4()), "CODE", sub_repo, plan_repo, Mock())

    assert exc.value.detail == "You are already on this plan."


async def test_upgrade_subscription_plan_not_found():
    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value=SimpleNamespace(plan_id=uuid4()))

    plan_repo = Mock()
    plan_repo.get_by_code = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await SubscriptionService.upgrade_subscription(SimpleNamespace(id=uuid4()), "CODE", sub_repo, plan_repo, Mock())

    assert exc.value.detail == "Plan not found."


async def test_upgrade_subscription_no_active():
    sub_repo = Mock()
    sub_repo.get_subscription_with_access = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc:
        await SubscriptionService.upgrade_subscription(SimpleNamespace(id=uuid4()), "CODE", sub_repo, Mock(), Mock())

    assert exc.value.detail == "No active subscription to upgrade."


async def test_stripe_webhook_checkout_creates_subscription(monkeypatch, mock_user_subscribe):
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test", "subscription": "sub_123", "customer": "cus_123"}},
    }
    run_mock = AsyncMock(return_value=event)
    monkeypatch.setattr("src.billing.service.run_in_threadpool", run_mock)

    request = _dummy_request(b"{}")
    sub_repo = Mock()
    plan_repo = Mock()
    payment_repo = Mock()

    result = await SubscriptionService.stripe_webhook(request, "sig", sub_repo, plan_repo, payment_repo)

    assert result is None
    mock_user_subscribe.assert_awaited_once_with(event["data"]["object"], sub_repo, plan_repo)


async def test_stripe_webhook_invoice_payment(monkeypatch, mock_send_update_subscription_email_task):
    invoice = {
        "lines": {
            "data": [
                {"parent": {"subscription_item_details": {"subscription": "sub_123"}}}
            ]
        },
        "billing_reason": "subscription_cycle",
        "id": "in_test",
        "amount_paid": 5000,
        "currency": "usd",
    }
    event = {"type": "invoice.payment_succeeded", "data": {"object": invoice}}
    run_mock = AsyncMock(return_value=event)
    monkeypatch.setattr("src.billing.service.run_in_threadpool", run_mock)

    updated_sub = SimpleNamespace(
        id=uuid4(),
        user=SimpleNamespace(email="e", username="u"),
        plan=SimpleNamespace(name="Plan", price_cents=5000),
        started_at=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    handle_payment_mock = AsyncMock(return_value=updated_sub)
    monkeypatch.setattr(
        "src.billing.service.StripeGateway.handle_invoice_payment_succeeded",
        handle_payment_mock,
    )
    record_payment_mock = AsyncMock()
    monkeypatch.setattr(
        "src.billing.service.StripeGateway.record_invoice_payment",
        record_payment_mock,
    )

    request = _dummy_request(b"{}")
    sub_repo = Mock()
    payment_repo = Mock()

    result = await SubscriptionService.stripe_webhook(request, "sig", sub_repo, Mock(), payment_repo)

    assert result is None
    handle_payment_mock.assert_awaited_once_with(invoice, sub_repo)
    mock_send_update_subscription_email_task.assert_called_once_with(serialize_subscription(updated_sub))
    record_payment_mock.assert_awaited_once_with(invoice, updated_sub, payment_repo)


async def test_stripe_webhook_subscription_deleted(monkeypatch):
    event = {"type": "customer.subscription.deleted", "data": {"object": {"id": "sub_123"}}}
    run_mock = AsyncMock(return_value=event)
    monkeypatch.setattr("src.billing.service.run_in_threadpool", run_mock)

    handler = AsyncMock()
    monkeypatch.setattr("src.billing.service.StripeGateway.handle_subscription_deleted", handler)

    request = _dummy_request(b"{}")
    sub_repo = Mock()
    payment_repo = Mock()

    result = await SubscriptionService.stripe_webhook(request, "sig", sub_repo, Mock(), payment_repo)

    assert result is None
    handler.assert_awaited_once_with(event["data"]["object"], sub_repo)


async def test_stripe_webhook_invalid_signature(monkeypatch):
    error = Exception("bad signature")
    run_mock = AsyncMock(side_effect=error)
    monkeypatch.setattr("src.billing.service.run_in_threadpool", run_mock)

    request = _dummy_request(b"{}")
    response = await SubscriptionService.stripe_webhook(request, "sig", Mock(), Mock(), Mock())

    assert response == {"error": "bad signature"}
