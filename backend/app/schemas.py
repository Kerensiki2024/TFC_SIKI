"""
Schémas Pydantic = contrat JSON des requêtes / réponses (validation + doc OpenAPI).
Séparés des modèles SQLAlchemy pour ne pas mélanger persistance et API.
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    intent: str
    needs_confirmation: bool = False


class HealthResponse(BaseModel):
    status: str


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=3, max_length=255)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str
    groupe: str | None = None


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=255)
    groupe: str = Field(..., min_length=2, max_length=64)
