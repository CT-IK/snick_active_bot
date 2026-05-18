"""Pydantic схемы для проектов"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from schemas.task import TaskResponse


class ProjectBase(BaseModel):
    """Базовая схема проекта"""
    name: str


class ProjectCreate(ProjectBase):
    """Схема для создания проекта"""
    pass


class ProjectUpdate(BaseModel):
    """Схема для обновления проекта"""
    name: Optional[str] = None


class ProjectResponse(ProjectBase):
    """Схема ответа с данными проекта"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectWithTasks(ProjectResponse):
    """Схема проекта с задачами"""
    tasks: List[TaskResponse] = []
