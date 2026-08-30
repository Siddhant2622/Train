"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    """Safe user representation — never includes password_hash."""
    id: str
    email: EmailStr
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
