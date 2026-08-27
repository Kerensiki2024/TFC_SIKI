from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — metadata complète
from app.database import Base, get_session
from app.routers import auth_router, chat, n8n_hooks
from app.seed import ensure_seed

# StaticPool : une seule base « :memory: » partagée entre toutes les connexions.
TEST_DB = "sqlite+aiosqlite://"


def _build_test_app(factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    """Sans lifespan : le schéma et le seed sont appliqués dans la fixture (fiable avec httpx)."""
    application = FastAPI()

    async def override_get_session():
        async with factory() as session:
            yield session

    application.dependency_overrides[get_session] = override_get_session
    application.include_router(auth_router.router)
    application.include_router(chat.router)
    application.include_router(n8n_hooks.router)

    @application.get("/health")
    async def health():
        return {"status": "ok"}

    return application


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        TEST_DB,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with factory() as s:
        async with s.begin():
            await ensure_seed(s)

    test_app = _build_test_app(factory)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()
    test_app.dependency_overrides.clear()
