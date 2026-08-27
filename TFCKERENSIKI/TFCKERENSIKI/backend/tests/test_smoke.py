import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_etudiant(client: AsyncClient):
    r = await client.post(
        "/auth/login",
        json={"email": "kerensiki@gmail.com", "password": "Makula@123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["email"] == "kerensiki@gmail.com"
    assert data["role"] == "ETUDIANT"


@pytest.mark.asyncio
async def test_chat_sans_token_refuse(client: AsyncClient):
    r = await client.post("/chat", json={"message": "Bonjour"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_chat_prochain_cours(client: AsyncClient):
    login = await client.post(
        "/auth/login",
        json={"email": "kerensiki@gmail.com", "password": "Makula@123"},
    )
    token = login.json()["access_token"]
    r = await client.post(
        "/chat",
        json={"message": "Quel est mon prochain cours ?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "prochain_cours"
    assert "reply" in body
    assert len(body["reply"]) > 10


@pytest.mark.asyncio
async def test_pending_confirmation_persistee(client: AsyncClient):
    login = await client.post(
        "/auth/login",
        json={"email": "bob.agent@univ.demo", "password": "bob123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    r1 = await client.post(
        "/chat",
        json={"message": "Annule le cours de Travaux de Programmation groupe L3GIN"},
        headers=h,
    )
    assert r1.status_code == 200
    assert r1.json().get("needs_confirmation") is True
    r2 = await client.post(
        "/chat",
        json={"message": "non"},
        headers=h,
    )
    assert r2.status_code == 200
    assert r2.json()["intent"] == "confirm_no"
