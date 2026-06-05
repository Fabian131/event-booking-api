import pytest
from httpx import AsyncClient


async def _create_authenticated_user(client: AsyncClient) -> tuple[str, dict]:
    """Helper: register + login, return (token, headers)."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "password": "Password1",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "Password1"},
    )
    token = login.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


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
async def test_create_reservation_success(client: AsyncClient):
    token, headers = await _create_authenticated_user(client)
    event_id = await _create_event(client, headers)

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
    assert data["status"] == "PENDING"
    assert data["event_id"] == event_id
    assert "user" in data
    assert data["user"]["user_email"] == "test@example.com"


@pytest.mark.asyncio
async def test_create_reservation_insufficient_availability(client: AsyncClient):
    token, headers = await _create_authenticated_user(client)
    event_id = await _create_event(client, headers, max_capacity=5)

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
async def test_cancel_reservation(client: AsyncClient):
    token, headers = await _create_authenticated_user(client)
    event_id = await _create_event(client, headers)

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
