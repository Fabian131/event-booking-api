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
async def test_update_event_success_with_business_form_data(client: AsyncClient, create_user):
    await create_user(
        email="business-update@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="Updater",
    )
    headers = await _login_headers(client, "business-update@example.com")
    event_response = await _create_event(client, headers)
    event_id = event_response.json()["id"]

    response = await client.put(
        f"/api/v1/events/{event_id}",
        data={
            "title": "Updated Event",
            "description": "Updated Description",
            "max_capacity": "120",
            "category": "culture",
            "date": "2026-12-16",
            "start_time": "15:00:00",
            "end_time": "19:00:00",
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Event"
    assert data["description"] == "Updated Description"
    assert data["max_capacity"] == 120
    assert data["category"] == "culture"
    assert data["date"] == "2026-12-16"
    assert data["start_time"] == "15:00:00"
    assert data["end_time"] == "19:00:00"


@pytest.mark.asyncio
async def test_update_event_accepts_max_capacity_limit(client: AsyncClient, create_user):
    await create_user(
        email="business-capacity@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="Capacity",
    )
    headers = await _login_headers(client, "business-capacity@example.com")
    event_response = await _create_event(client, headers)
    event_id = event_response.json()["id"]

    response = await client.put(
        f"/api/v1/events/{event_id}",
        data={"max_capacity": "9999999"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["max_capacity"] == 9999999


def _assert_schedule_conflict_response(response):
    assert response.status_code == 409
    data = response.json()
    assert data["error"] == "schedule_conflict"
    assert data["message"] == "An event already occupies this date and time slot"
    assert data["details"] == [
        {"field": "schedule", "message": "An event already occupies this date and time slot"}
    ]


@pytest.mark.asyncio
async def test_create_event_schedule_conflict_response_format(client: AsyncClient, create_user):
    await create_user(
        email="business-create-conflict@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="CreateConflict",
    )
    headers = await _login_headers(client, "business-create-conflict@example.com")
    await _create_event(client, headers, title="Original Event")

    response = await client.post(
        "/api/v1/events",
        data={
            "title": "Overlapping Event",
            "max_capacity": 20,
            "category": "sports",
            "date": "2026-12-15",
            "start_time": "15:00:00",
            "end_time": "17:00:00",
        },
        headers=headers,
    )

    _assert_schedule_conflict_response(response)


@pytest.mark.asyncio
async def test_update_event_schedule_conflict_response_format(client: AsyncClient, create_user):
    await create_user(
        email="business-update-conflict@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="UpdateConflict",
    )
    headers = await _login_headers(client, "business-update-conflict@example.com")
    await _create_event(client, headers, title="Original Event")
    other_event_response = await client.post(
        "/api/v1/events",
        data={
            "title": "Other Event",
            "max_capacity": 20,
            "category": "sports",
            "date": "2026-12-15",
            "start_time": "19:00:00",
            "end_time": "21:00:00",
        },
        headers=headers,
    )
    other_event_id = other_event_response.json()["id"]

    response = await client.put(
        f"/api/v1/events/{other_event_id}",
        data={
            "date": "2026-12-15",
            "start_time": "15:00:00",
            "end_time": "17:00:00",
        },
        headers=headers,
    )

    _assert_schedule_conflict_response(response)


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


# ── Delete Event ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_event_success(client: AsyncClient, create_user):
    await create_user(
        email="business-del@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="Delete",
    )
    headers = await _login_headers(client, "business-del@example.com")
    event_response = await _create_event(client, headers)
    event_id = event_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/events/{event_id}",
        headers=headers,
    )

    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/events/{event_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_event_not_found(client: AsyncClient, create_user):
    await create_user(
        email="business-nf@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="NotFound",
    )
    headers = await _login_headers(client, "business-nf@example.com")

    response = await client.delete(
        "/api/v1/events/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == [{"field": "event_id", "message": "Event not found"}]


@pytest.mark.asyncio
async def test_delete_event_with_reservations(client: AsyncClient, create_user):
    await create_user(
        email="business-wr@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="WithRes",
    )
    business_headers = await _login_headers(client, "business-wr@example.com")
    event_response = await _create_event(client, business_headers)
    event_id = event_response.json()["id"]

    await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Customer",
            "last_name": "One",
            "email": "customer1@example.com",
            "password": "Password1!",
        },
    )
    customer1_headers = await _login_headers(client, "customer1@example.com")
    await client.post(
        "/api/v1/reservations",
        json={"event_id": event_id, "ticket_quantity": 2},
        headers=customer1_headers,
    )

    await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Customer",
            "last_name": "Two",
            "email": "customer2@example.com",
            "password": "Password1!",
        },
    )
    customer2_headers = await _login_headers(client, "customer2@example.com")
    await client.post(
        "/api/v1/reservations",
        json={"event_id": event_id, "ticket_quantity": 1},
        headers=customer2_headers,
    )

    res_list = await client.get(
        f"/api/v1/reservations?event_id={event_id}",
        headers=business_headers,
    )
    assert len(res_list.json()["data"]) == 2

    delete_response = await client.delete(
        f"/api/v1/events/{event_id}",
        headers=business_headers,
    )

    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/events/{event_id}")
    assert get_response.status_code == 404

    res_list_after = await client.get(
        f"/api/v1/reservations?event_id={event_id}",
        headers=business_headers,
    )
    assert len(res_list_after.json()["data"]) == 0


@pytest.mark.asyncio
async def test_delete_event_requires_business_role(client: AsyncClient, create_user):
    await create_user(
        email="business-req@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="Req",
    )
    business_headers = await _login_headers(client, "business-req@example.com")
    event_response = await _create_event(client, business_headers)
    event_id = event_response.json()["id"]

    response = await client.delete(f"/api/v1/events/{event_id}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_delete_event_clears_from_list(client: AsyncClient, create_user):
    await create_user(
        email="business-list@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="List",
    )
    headers = await _login_headers(client, "business-list@example.com")

    e1 = await client.post(
        "/api/v1/events",
        data={
            "title": "Event to delete",
            "max_capacity": 50,
            "category": "music",
            "date": "2026-12-15",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
        },
        headers=headers,
    )
    assert e1.status_code == 201

    e2 = await client.post(
        "/api/v1/events",
        data={
            "title": "Event to keep",
            "max_capacity": 50,
            "category": "sports",
            "date": "2026-12-16",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
        },
        headers=headers,
    )
    assert e2.status_code == 201

    list_before = await client.get("/api/v1/events")
    assert list_before.json()["pagination"]["total"] >= 2

    event_id = e1.json()["id"]

    await client.delete(f"/api/v1/events/{event_id}", headers=headers)

    list_after = await client.get("/api/v1/events")
    assert list_after.json()["pagination"]["total"] == list_before.json()["pagination"]["total"] - 1
    ids_after = [e["id"] for e in list_after.json()["data"]]
    assert event_id not in ids_after


@pytest.mark.asyncio
async def test_delete_event_double_delete_returns_404(client: AsyncClient, create_user):
    await create_user(
        email="business-dd@example.com",
        password="Password1!",
        role="business",
        first_name="Business",
        last_name="DoubleDel",
    )
    headers = await _login_headers(client, "business-dd@example.com")
    event_response = await _create_event(client, headers)
    event_id = event_response.json()["id"]

    first = await client.delete(f"/api/v1/events/{event_id}", headers=headers)
    assert first.status_code == 204

    second = await client.delete(f"/api/v1/events/{event_id}", headers=headers)
    assert second.status_code == 404
    assert second.json()["detail"] == [{"field": "event_id", "message": "Event not found"}]
