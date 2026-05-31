import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_event_success(client: AsyncClient):
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
    
    response = await client.post(
        "/api/v1/events",
        json={
            "title": "Test Event",
            "description": "Test Description",
            "location": "Test Location",
            "max_capacity": 100,
            "category": "Test"
        },
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Event"
    assert data["max_capacity"] == 100


@pytest.mark.asyncio
async def test_list_events(client: AsyncClient):
    response = await client.get("/api/v1/events")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data


@pytest.mark.asyncio
async def test_get_event_not_found(client: AsyncClient):
    response = await client.get("/api/v1/events/00000000-0000-0000-0000-000000000000")
    
    assert response.status_code == 404
