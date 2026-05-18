"""Pydantic схемы для рабочих групп"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from schemas.user import UserResponse
from schemas.task import TaskResponse


class WorkGroupBase(BaseModel):
    """Базовая схема рабочей группы"""
    name: str
    description: Optional[str] = None


class WorkGroupCreate(WorkGroupBase):
    """Схема для создания рабочей группы"""
    responsible_id: Optional[int] = None
    member_ids: Optional[List[int]] = None


class WorkGroupUpdate(BaseModel):
    """Схема для обновления рабочей группы"""
    name: Optional[str] = None
    description: Optional[str] = None
    responsible_id: Optional[int] = None
    member_ids: Optional[List[int]] = None


class WorkGroupResponse(WorkGroupBase):
    """Схема ответа с данными рабочей группы"""
    id: int
    created_by_id: int
    responsible_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkGroupWithRelations(WorkGroupResponse):
    """Схема рабочей группы с отношениями"""
    created_by: Optional[UserResponse] = None
    responsible: Optional[UserResponse] = None
    members: List[UserResponse] = []
    tasks: List[TaskResponse] = []
