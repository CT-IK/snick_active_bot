"""Pydantic схемы для пользователей"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
from database.models import UserRoleEnum


class UserBase(BaseModel):
    """Базовая схема пользователя"""
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRoleEnum = UserRoleEnum.WORKER
    telegram_id: Optional[int] = None


class UserCreate(UserBase):
    """Схема для создания пользователя"""
    login: Optional[str] = None
    password: Optional[str] = None
    created_by_id: Optional[int] = None


class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    login: Optional[str] = None
    password: Optional[str] = None
    telegram_id: Optional[int] = None


class UserResponse(UserBase):
    """Схема ответа с данными пользователя"""
    id: int
    login: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserWithHierarchy(UserResponse):
    """Схема пользователя с иерархией"""
    created_users: list[UserResponse] = []


class LoginRequest(BaseModel):
    """Схема для входа"""
    login: str
    password: str

    @field_validator("login", "password", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        return v.strip() if isinstance(v, str) else v


class TokenResponse(BaseModel):
    """Схема ответа с токеном"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
