import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User 2",
            "email": "test@example.com",
            "password": "password456"
        }
    )
    
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
