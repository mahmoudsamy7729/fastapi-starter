import json
import pytest
from fastapi import status
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import ANY, AsyncMock
from src.billing.utils import serialize_subscription


@pytest.mark.asyncio
async def test_list_plans(client: AsyncClient, test_plan):
    response = await client.get("/billing/plans")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert any(plan["id"] == str(test_plan.id) for plan in data)


@pytest.mark.asyncio
async def test_create_plan(client: AsyncClient, admin_headers, plan_payload):
    response = await client.post("/billing/plans", json=plan_payload, headers=admin_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == plan_payload["name"]
    assert data["code"] == plan_payload["code"]
    assert "price_cents" in data
    assert "currency" in data


@pytest.mark.asyncio
async def test_create_plan_exisiting_code(client: AsyncClient, admin_headers, test_plan):
    payload = {
        "name": "duplicate plan",
        "code": test_plan.code,
        "price_cents": 0,
        "billing_period": "monthly",
        "currency": "USD",
        "is_active": True
    }

    response = await client.post("/billing/plans", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Existing Code"


@pytest.mark.asyncio
async def test_create_plan_not_admin(client: AsyncClient, user_headers, plan_payload):
    response = await client.post("/billing/plans", json=plan_payload, headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "User does not have admin privileges"


@pytest.mark.asyncio
async def test_retrive_non_existing_plan(client: AsyncClient):
    non_existing_id = str(uuid4())  # valid UUID, but not in DB
    response = await client.get(f"/billing/plans/{non_existing_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "No plan found for this id"


@pytest.mark.asyncio
async def test_get_plan_by_id(client: AsyncClient, test_plan):
    response = await client.get(f"/billing/plans/{test_plan.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["id"] == str(test_plan.id)
    assert data["name"] == test_plan.name
    assert data["code"] == test_plan.code


@pytest.mark.asyncio
async def test_update_plan(client: AsyncClient, admin_headers, test_plan):
    payload = {
        "name": "updated",
        "price_cents": 999,
        "billing_period": "yearly",
        "currency": "USD",
        "is_active": False
    }

    response = await client.patch(
        f"/billing/plans/{test_plan.id}",
        json=payload,
        headers=admin_headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "updated"
    assert data["price_cents"] == 999
    assert "billing_period" not in data  # PlanOut schema omits billing_period/is_active
    assert "is_active" not in data


@pytest.mark.asyncio
async def test_update_plan_not_admin(client: AsyncClient, user_headers, test_plan):
    payload = {"name": "hack-change"}

    response = await client.patch(
        f"/billing/plans/{test_plan.id}",
        json=payload,
        headers=user_headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "User does not have admin privileges"


@pytest.mark.asyncio
async def test_delete_plan(client: AsyncClient, admin_headers, test_plan):
    response = await client.delete(f"/billing/plans/{test_plan.id}", headers=admin_headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    list_response = await client.get("/billing/plans")
    assert all(plan["id"] != str(test_plan.id) for plan in list_response.json())


@pytest.mark.asyncio
async def test_delete_plan_not_admin(client: AsyncClient, user_headers, test_plan):
    response = await client.delete(f"/billing/plans/{test_plan.id}", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "User does not have admin privileges"


@pytest.mark.asyncio
async def test_get_my_subscription_none(client: AsyncClient, user_headers):
    response = await client.get("/billing/subscriptions/me", headers=user_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "No active subscription found for this user."


@pytest.mark.asyncio
async def test_get_my_subscription(
    client: AsyncClient, user_headers, test_subscription
):
    response = await client.get("/billing/subscriptions/me", headers=user_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(test_subscription.id)
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_cancel_subscription(
    client: AsyncClient, user_headers, test_subscription
):
    response = await client.post("/billing/subscriptions/cancel", headers=user_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["cancel_at_period_end"] is True
    assert data["status"] == "canceled"


@pytest.mark.asyncio
async def test_subscribe_to_plan_starts_checkout(client: AsyncClient, logged_in_user_no_subscription, test_plan, mock_create_checkout):
    headers = {"Authorization": f"Bearer {logged_in_user_no_subscription['token']}"}
    response = await client.post(
        "/billing/subscriptions/subscribe",
        json={"plan_code": test_plan.code},
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"checkout_url": "https://stripe.test/checkout"}
    mock_create_checkout.assert_awaited_once()


@pytest.mark.asyncio
async def test_stripe_webhook_checkout_triggers_email(
    client: AsyncClient,
    mock_user_subscripe,
    fake_subscription,
    mock_send_subscription_email_task,
    monkeypatch,
):
    event_payload = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test", "subscription": "sub_123", "customer": "cus_123"}},
    }
    run_mock = AsyncMock(return_value=event_payload)
    monkeypatch.setattr("src.billing.service.run_in_threadpool", run_mock)

    response = await client.post(
        "/billing/stripe/webhook",
        content=json.dumps(event_payload),
        headers={"stripe-signature": "sig"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Unhandled event"}
    mock_user_subscripe.assert_awaited_once_with(event_payload["data"]["object"], ANY, ANY)
    mock_send_subscription_email_task.assert_called_once_with(serialize_subscription(fake_subscription))
