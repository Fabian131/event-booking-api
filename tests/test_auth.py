import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "password": "Password1!"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert data["role"] == "customer"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "password": "Password1!"
        }
    )

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User Two",
            "email": "test@example.com",
            "password": "Password2!"
        }
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "password": "Password1!"
        }
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "Password1!"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["role"] == "customer"


@pytest.mark.asyncio
async def test_login_business_user_success(client: AsyncClient, create_user):
    await create_user(
        email="business@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="User",
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "business@example.com",
            "password": "Password1!"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "business@example.com"
    assert data["user"]["role"] == "business"


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
