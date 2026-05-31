import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_reservation_success(client: AsyncClient):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    event_response = await client.post(
        "/api/v1/events",
        json={
            "title": "Test Event",
            "location": "Test Location",
            "max_capacity": 100,
            "category": "Test"
        },
        headers=headers
    )
    
    event_id = event_response.json()["id"]
    
    schedule_response = await client.post(
        f"/api/v1/events/{event_id}/schedules",
        json={
            "schedule_date": "2026-12-15",
            "start_time": "14:00:00",
            "end_time": "18:00:00",
            "available_slots": 50
        },
        headers=headers
    )
    
    schedule_id = schedule_response.json()["id"]
    
    response = await client.post(
        "/api/v1/reservations",
        json={
            "event_schedule_id": schedule_id,
            "quantity": 2
        },
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["quantity"] == 2
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_create_reservation_insufficient_availability(client: AsyncClient):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    event_response = await client.post(
        "/api/v1/events",
        json={
            "title": "Test Event",
            "location": "Test Location",
            "max_capacity": 10,
            "category": "Test"
        },
        headers=headers
    )
    
    event_id = event_response.json()["id"]
    
    schedule_response = await client.post(
        f"/api/v1/events/{event_id}/schedules",
        json={
            "schedule_date": "2026-12-15",
            "start_time": "14:00:00",
            "end_time": "18:00:00",
            "available_slots": 5
        },
        headers=headers
    )
    
    schedule_id = schedule_response.json()["id"]
    
    response = await client.post(
        "/api/v1/reservations",
        json={
            "event_schedule_id": schedule_id,
            "quantity": 10
        },
        headers=headers
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cancel_reservation(client: AsyncClient):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    event_response = await client.post(
        "/api/v1/events",
        json={
            "title": "Test Event",
            "location": "Test Location",
            "max_capacity": 100,
            "category": "Test"
        },
        headers=headers
    )
    
    event_id = event_response.json()["id"]
    
    schedule_response = await client.post(
        f"/api/v1/events/{event_id}/schedules",
        json={
            "schedule_date": "2026-12-15",
            "start_time": "14:00:00",
            "end_time": "18:00:00",
            "available_slots": 50
        },
        headers=headers
    )
    
    schedule_id = schedule_response.json()["id"]
    
    reservation_response = await client.post(
        "/api/v1/reservations",
        json={
            "event_schedule_id": schedule_id,
            "quantity": 2
        },
        headers=headers
    )
    
    reservation_id = reservation_response.json()["id"]
    
    response = await client.post(
        f"/api/v1/reservations/{reservation_id}/cancel",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"
