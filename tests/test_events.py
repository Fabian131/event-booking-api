import pytest
from httpx import AsyncClient


async def _login_headers(client: AsyncClient, email: str, password: str = "Password1!") -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_event(client: AsyncClient, headers: dict, title: str = "Test Event"):
    return await client.post(
        "/api/v1/events",
        data={
            "title": title,
            "description": "Test Description",
            "max_capacity": 100,
            "category": "sports",
            "date": "2026-12-15",
            "start_time": "14:00:00",
            "end_time": "18:00:00",
        },
        headers=headers,
    )


@pytest.mark.asyncio
async def test_create_event_success(client: AsyncClient, create_user):
    await create_user(
        email="business@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="User",
    )
    headers = await _login_headers(client, "business@example.com")

    response = await _create_event(client, headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Event"
    assert data["max_capacity"] == 100
    assert data["remaining_capacity"] == 100
    assert data["date"] == "2026-12-15"


@pytest.mark.asyncio
async def test_create_event_forbidden_for_customer(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "password": "Password1!"
        }
    )
    headers = await _login_headers(client, "test@example.com")

    response = await _create_event(client, headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Business user access required"


@pytest.mark.asyncio
async def test_update_and_delete_event_forbidden_for_customer(client: AsyncClient, create_user):
    await create_user(
        email="business@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="User",
    )
    business_headers = await _login_headers(client, "business@example.com")
    event_response = await _create_event(client, business_headers)
    event_id = event_response.json()["id"]

    await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "password": "Password1!"
        }
    )
    customer_headers = await _login_headers(client, "test@example.com")

    update_response = await client.put(
        f"/api/v1/events/{event_id}",
        data={"title": "Updated Event"},
        headers=customer_headers,
    )
    delete_response = await client.delete(
        f"/api/v1/events/{event_id}",
        headers=customer_headers,
    )

    assert update_response.status_code == 403
    assert update_response.json()["detail"] == "Business user access required"
    assert delete_response.status_code == 403
    assert delete_response.json()["detail"] == "Business user access required"


@pytest.mark.asyncio
async def test_list_events(client: AsyncClient):
    response = await client.get("/api/v1/events")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert "has_next_page" in data["pagination"]


@pytest.mark.asyncio
async def test_calendar_dates_empty_month(client: AsyncClient):
    response = await client.get("/api/v1/events/calendar?year=2027&month=1")

    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["year"] == 2027
    assert data["month"] == 1


@pytest.mark.asyncio
async def test_calendar_dates_with_events(client: AsyncClient, create_user):
    await create_user(
        email="biz@example.com",
        password="Password1!",
        role="business",
        first_name="Biz",
        last_name="User",
    )
    headers = await _login_headers(client, "biz@example.com")

    await client.post(
        "/api/v1/events",
        data={
            "title": "Event A",
            "max_capacity": 50,
            "category": "music",
            "date": "2026-12-15",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
        },
        headers=headers,
    )
    await client.post(
        "/api/v1/events",
        data={
            "title": "Event B",
            "max_capacity": 30,
            "category": "sports",
            "date": "2026-12-15",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
        },
        headers=headers,
    )
    await client.post(
        "/api/v1/events",
        data={
            "title": "Event C",
            "max_capacity": 20,
            "category": "culture",
            "date": "2026-12-20",
            "start_time": "09:00:00",
            "end_time": "11:00:00",
        },
        headers=headers,
    )

    response = await client.get("/api/v1/events/calendar?year=2026&month=12")

    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2026
    assert data["month"] == 12

    dates = {item["date"]: item["count"] for item in data["data"]}
    assert dates["2026-12-15"] == 2
    assert dates["2026-12-20"] == 1
    assert "2026-12-01" not in dates


@pytest.mark.asyncio
async def test_calendar_dates_invalid_month(client: AsyncClient):
    response = await client.get("/api/v1/events/calendar?year=2026&month=13")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_calendar_dates_excludes_inactive(client: AsyncClient, create_user):
    await create_user(
        email="biz2@example.com",
        password="Password1!",
        role="business",
        first_name="Biz",
        last_name="User",
    )
    headers = await _login_headers(client, "biz2@example.com")

    create_resp = await client.post(
        "/api/v1/events",
        data={
            "title": "Active Event",
            "max_capacity": 50,
            "category": "gastronomy",
            "date": "2026-11-10",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
        },
        headers=headers,
    )
    event_id = create_resp.json()["id"]

    await client.put(
        f"/api/v1/events/{event_id}",
        data={"is_active": False},
        headers=headers,
    )

    response = await client.get("/api/v1/events/calendar?year=2026&month=11")

    assert response.status_code == 200
    dates = [item["date"] for item in response.json()["data"]]
    assert "2026-11-10" not in dates
