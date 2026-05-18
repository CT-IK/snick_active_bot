"""Pydantic схемы для задач"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from database.models import TaskStatusEnum
from schemas.user import UserResponse


class TaskPollResponseSchema(BaseModel):
    """Ответ на опрос о задаче"""
    id: int
    task_id: int
    user_id: int
    polled_at: datetime
    response_text: Optional[str] = None
    status_at_poll: Optional[str] = None  # статус задачи в момент опроса (new, in_progress, review, done)
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    """Базовая схема задачи"""
    title: str
    description: Optional[str] = None
    status: TaskStatusEnum = TaskStatusEnum.NEW


class TaskCreate(TaskBase):
    """Схема для создания задачи"""
    project_id: Optional[int] = None
    workgroup_id: Optional[int] = None
    assigned_to_id: Optional[int] = None  # deprecated, используйте assignee_ids
    assignee_ids: List[int] = []
    due_date: Optional[datetime] = None
    poll_interval_days: Optional[int] = None
    poll_time: Optional[str] = None  # "HH:MM"


class TaskUpdate(BaseModel):
    """Схема для обновления задачи"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatusEnum] = None
    project_id: Optional[int] = None
    workgroup_id: Optional[int] = None
    assigned_to_id: Optional[int] = None  # deprecated
    assignee_ids: Optional[List[int]] = None
    due_date: Optional[datetime] = None
    poll_interval_days: Optional[int] = None
    poll_time: Optional[str] = None


class TaskResponse(TaskBase):
    """Схема ответа с данными задачи"""
    id: int
    project_id: Optional[int] = None
    workgroup_id: Optional[int] = None
    created_by_id: int
    assigned_to_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    poll_interval_days: Optional[int] = None
    poll_time: Optional[str] = None
    last_polled_at: Optional[datetime] = None
    
    assignee_ids: List[int] = []
    assignees: List[UserResponse] = []
    poll_responses: List[TaskPollResponseSchema] = []

    class Config:
        from_attributes = True


class TaskWithRelations(TaskResponse):
    """Схема задачи с отношениями"""
    creator: Optional[UserResponse] = None
    assignee: Optional[UserResponse] = None
    assignees: List[UserResponse] = []
