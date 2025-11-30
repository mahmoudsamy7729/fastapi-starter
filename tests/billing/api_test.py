import pytest
from fastapi import status
from httpx import AsyncClient
from uuid import UUID, uuid4


@pytest.mark.asyncio
async def test_list_plans(client: AsyncClient):
    response = await client.get("/billing/plans")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_create_plan(client: AsyncClient, logged_in_admin):
    headers = {"Authorization": f"Bearer {logged_in_admin['token']}"}
    payload = {
        "name": "test plan",
        "code": "test",
        "price_cents": 0,
        "billing_period": "monthly",
        "currency": "USD",
        "is_active": True
    }

    response = await client.post("/billing/plans", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"]  == "test plan"
    assert data["code"]  == "test"


@pytest.mark.asyncio
async def test_create_plan_exisiting_code(client: AsyncClient, logged_in_admin, test_plan):
    headers = {"Authorization": f"Bearer {logged_in_admin['token']}"}
    payload = {
        "name": "test plan",
        "code": test_plan.code,
        "price_cents": 0,
        "billing_period": "monthly",
        "currency": "USD",
        "is_active": True
    }

    response = await client.post("/billing/plans", json=payload, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Existing Code"


@pytest.mark.asyncio
async def test_create_plan_not_admin(client: AsyncClient, logged_in_user):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    payload = {
        "name": "test plan",
        "code": "test",
        "price_cents": 0,
        "billing_period": "monthly",
        "currency": "USD",
        "is_active": True
    }

    response = await client.post("/billing/plans", json=payload, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "User does not have admin privileges"


@pytest.mark.asyncio
async def test_retrive_non_existing_plan(client: AsyncClient):
    non_existing_id = str(uuid4())  # valid UUID, but not in DB
    response = await client.get(f"/plans/{non_existing_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Not Found"


@pytest.mark.asyncio
async def test_get_plan_by_id(client: AsyncClient, test_plan):
    response = await client.get(f"/billing/plans/{test_plan.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["id"] == str(test_plan.id)
    assert data["name"] == test_plan.name
    assert data["code"] == test_plan.code


@pytest.mark.asyncio
async def test_update_plan(client: AsyncClient, logged_in_admin, test_plan):
    headers = {"Authorization": f"Bearer {logged_in_admin['token']}"}

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
        headers=headers
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "updated"
    assert data["price_cents"] == 999
    assert data["billing_period"] == "yearly"
    assert data["is_active"] is False



@pytest.mark.asyncio
async def test_update_plan_not_admin(client: AsyncClient, logged_in_user, test_plan):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}

    payload = {"name": "hack-change"}

    response = await client.patch(
        f"/billing/plans/{test_plan.id}",
        json=payload,
        headers=headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "User does not have admin privileges"


@pytest.mark.asyncio
async def test_delete_plan(client: AsyncClient, logged_in_admin, test_plan):
    headers = {"Authorization": f"Bearer {logged_in_admin['token']}"}

    response = await client.delete(f"/billing/plans/{test_plan.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # ensure "soft delete" removed it from list
    list_response = await client.get("/billing/plans")
    assert all(plan["id"] != str(test_plan.id) for plan in list_response.json())


@pytest.mark.asyncio
async def test_delete_plan_not_admin(client: AsyncClient, logged_in_user, test_plan):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}

    response = await client.delete(f"/billing/plans/{test_plan.id}", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "User does not have admin privileges"


@pytest.mark.asyncio
async def test_get_my_subscription_none(client: AsyncClient, logged_in_user):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}   

    response = await client.get("/billing/subscriptions/me", headers=headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "No active subscription found for this user."


@pytest.mark.asyncio
async def test_subscribe_to_plan(
    client: AsyncClient, logged_in_user, test_plan
    ):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}

    payload = {"plan_code": test_plan.code}

    response = await client.post(
        "/billing/subscriptions/subscribe",
        json=payload,
        headers=headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["plan_id"] == str(test_plan.id)
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_my_subscription(
    client: AsyncClient, logged_in_user, test_subscription
):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}

    response = await client.get("/billing/subscriptions/me", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(test_subscription.id)
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_cancel_subscription(
    client: AsyncClient, logged_in_user, test_subscription
):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}

    response = await client.post("/billing/subscriptions/cancel", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["cancel_at_period_end"] == True

