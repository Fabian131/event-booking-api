import pytest
from httpx import AsyncClient
from uuid import uuid4


async def _create_authenticated_user(client: AsyncClient, email: str = "test@example.com") -> tuple[str, dict]:
    """Helper: register + login, return (token, headers)."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": "Password1!",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password1!"},
    )
    token = login.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


async def _login_headers(client: AsyncClient, email: str, password: str = "Password1!") -> dict:
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_business_headers(client: AsyncClient, create_user) -> dict:
    await create_user(
        email="business@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="User",
    )
    return await _login_headers(client, "business@example.com")


async def _create_event(client: AsyncClient, headers: dict, max_capacity: int = 100) -> str:
    """Helper: create an event via form-data, return event_id."""
    resp = await client.post(
        "/api/v1/events",
        data={
            "title": "Test Event",
            "max_capacity": max_capacity,
            "category": "sports",
            "date": "2026-12-15",
            "start_time": "14:00:00",
            "end_time": "18:00:00",
        },
        headers=headers,
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_reservation_success(client: AsyncClient, create_user):
    _, headers = await _create_authenticated_user(client)
    business_headers = await _create_business_headers(client, create_user)
    event_id = await _create_event(client, business_headers)

    response = await client.post(
        "/api/v1/reservations",
        json={
            "event_id": event_id,
            "ticket_quantity": 2,
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["ticket_quantity"] == 2
    assert data["status"] == "CONFIRMED"
    assert data["event_id"] == event_id
    assert "user" in data
    assert data["user"]["user_email"] == "test@example.com"


@pytest.mark.asyncio
async def test_create_reservation_insufficient_availability(client: AsyncClient, create_user):
    _, headers = await _create_authenticated_user(client)
    business_headers = await _create_business_headers(client, create_user)
    event_id = await _create_event(client, business_headers, max_capacity=5)

    response = await client.post(
        "/api/v1/reservations",
        json={
            "event_id": event_id,
            "ticket_quantity": 10,
        },
        headers=headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_cancel_reservation(client: AsyncClient, create_user):
    _, headers = await _create_authenticated_user(client)
    business_headers = await _create_business_headers(client, create_user)
    event_id = await _create_event(client, business_headers)

    reservation_response = await client.post(
        "/api/v1/reservations",
        json={
            "event_id": event_id,
            "ticket_quantity": 2,
        },
        headers=headers,
    )

    reservation_id = reservation_response.json()["id"]

    response = await client.patch(
        f"/api/v1/reservations/{reservation_id}/cancel",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_reservation_updates_event_capacity(client: AsyncClient, create_user):
    _, headers = await _create_authenticated_user(client)
    business_headers = await _create_business_headers(client, create_user)
    event_id = await _create_event(client, business_headers, max_capacity=10)

    reservation_response = await client.post(
        "/api/v1/reservations",
        json={
            "event_id": event_id,
            "ticket_quantity": 3,
        },
        headers=headers,
    )
    reservation_id = reservation_response.json()["id"]

    event_before = await client.get(f"/api/v1/events/{event_id}")
    assert event_before.json()["remaining_capacity"] == 7

    await client.patch(
        f"/api/v1/reservations/{reservation_id}/cancel",
        headers=headers,
    )

    event_after = await client.get(f"/api/v1/events/{event_id}")
    assert event_after.json()["remaining_capacity"] == 10


@pytest.mark.asyncio
async def test_cancel_already_cancelled_reservation(client: AsyncClient, create_user):
    _, headers = await _create_authenticated_user(client)
    business_headers = await _create_business_headers(client, create_user)
    event_id = await _create_event(client, business_headers)

    reservation_resp = await client.post(
        "/api/v1/reservations",
        json={"event_id": event_id, "ticket_quantity": 2},
        headers=headers,
    )
    reservation_id = reservation_resp.json()["id"]

    await client.patch(f"/api/v1/reservations/{reservation_id}/cancel", headers=headers)

    response = await client.patch(f"/api/v1/reservations/{reservation_id}/cancel", headers=headers)

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "already_cancelled"
    assert "already been cancelled" in data["message"]
    assert "details" in data


@pytest.mark.asyncio
async def test_cancel_nonexistent_reservation(client: AsyncClient, create_user):
    _, headers = await _create_authenticated_user(client)

    fake_id = str(uuid4())
    response = await client.patch(f"/api/v1/reservations/{fake_id}/cancel", headers=headers)

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "not_found"
    assert "details" in data


@pytest.mark.asyncio
async def test_cancel_other_users_reservation(client: AsyncClient, create_user):
    _, user1_headers = await _create_authenticated_user(client, "user1@example.com")
    _, user2_headers = await _create_authenticated_user(client, "user2@example.com")
    business_headers = await _create_business_headers(client, create_user)
    event_id = await _create_event(client, business_headers)

    reservation_resp = await client.post(
        "/api/v1/reservations",
        json={"event_id": event_id, "ticket_quantity": 1},
        headers=user1_headers,
    )
    reservation_id = reservation_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/reservations/{reservation_id}/cancel",
        headers=user2_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_business_cancels_customer_reservation(client: AsyncClient, create_user):
    _, customer_headers = await _create_authenticated_user(client, "customer@example.com")
    business_headers = await _create_business_headers(client, create_user)
    event_id = await _create_event(client, business_headers)

    reservation_resp = await client.post(
        "/api/v1/reservations",
        json={"event_id": event_id, "ticket_quantity": 2},
        headers=customer_headers,
    )
    reservation_id = reservation_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/reservations/{reservation_id}/cancel",
        headers=business_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"
    assert data["user"]["user_email"] == "customer@example.com"


@pytest.mark.asyncio
async def test_cancel_creates_notification(client: AsyncClient, create_user):
    _, headers = await _create_authenticated_user(client)
    business_headers = await _create_business_headers(client, create_user)
    event_id = await _create_event(client, business_headers)

    reservation_resp = await client.post(
        "/api/v1/reservations",
        json={"event_id": event_id, "ticket_quantity": 2},
        headers=headers,
    )
    reservation_id = reservation_resp.json()["id"]

    await client.patch(f"/api/v1/reservations/{reservation_id}/cancel", headers=headers)

    notif_resp = await client.get("/api/v1/notifications", headers=headers)
    notifications = notif_resp.json()["data"]
    cancel_notifs = [n for n in notifications if n["type"] == "reservation_cancelled"]
    assert len(cancel_notifs) == 1
    assert "cancelled" in cancel_notifs[0]["title"].lower()


@pytest.mark.asyncio
async def test_cancel_reservation_response_matches_contract(client: AsyncClient, create_user):
    _, headers = await _create_authenticated_user(client)
    business_headers = await _create_business_headers(client, create_user)
    event_id = await _create_event(client, business_headers)

    reservation_resp = await client.post(
        "/api/v1/reservations",
        json={"event_id": event_id, "ticket_quantity": 3, "notes": "Please cancel"},
        headers=headers,
    )
    reservation_id = reservation_resp.json()["id"]

    response = await client.patch(f"/api/v1/reservations/{reservation_id}/cancel", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "user_id" in data
    assert "event_id" in data
    assert data["event_id"] == event_id
    assert "event_title" in data
    assert "event_date" in data
    assert "event_start_time" in data
    assert "event_end_time" in data
    assert data["ticket_quantity"] == 3
    assert data["status"] == "CANCELLED"
    assert data["notes"] == "Please cancel"
    assert "user" in data
    assert "user_id" in data["user"]
    assert "user_name" in data["user"]
    assert "user_email" in data["user"]
    assert data["user"]["user_email"] == "test@example.com"
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_cancel_unauthenticated(client: AsyncClient, create_user):
    business_headers = await _create_business_headers(client, create_user)
    event_id = await _create_event(client, business_headers)

    _, headers = await _create_authenticated_user(client)
    reservation_resp = await client.post(
        "/api/v1/reservations",
        json={"event_id": event_id, "ticket_quantity": 1},
        headers=headers,
    )
    reservation_id = reservation_resp.json()["id"]

    response = await client.patch(f"/api/v1/reservations/{reservation_id}/cancel")

    assert response.status_code == 401
