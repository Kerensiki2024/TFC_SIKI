"""
Point d’entrée FastAPI : création de l’app, CORS, enregistrement des routeurs,
et cycle de vie (démarrage = init DB + seed des comptes / horaires démo).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal, init_db
from app.routers import auth_router, chat, n8n_hooks
from app.seed import ensure_seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Au démarrage : tables SQL + données minimales (utilisateurs L3GIN, agent, événements semaine).
    await init_db()
    async with SessionLocal() as session:
        async with session.begin():
            await ensure_seed(session)
    yield
    # Ici on pourrait fermer des pools ; pour l’instant rien à faire à l’arrêt.


# Instance OpenAPI / Swagger automatique sur /docs.
app = FastAPI(title=settings.app_name, lifespan=lifespan)
# Autorise le front Vite (5173) à appeler l’API avec cookies / Authorization si besoin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router.router)
app.include_router(chat.router)
app.include_router(n8n_hooks.router)


@app.get("/health", tags=["system"])
async def health():
    """Contrôle simple pour Docker / load balancer (pas d’auth)."""
    return {"status": "ok"}
