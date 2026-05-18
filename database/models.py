"""Модели базы данных"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Enum as SQLEnum, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class TaskStatusEnum(str, enum.Enum):
    """Статусы задач"""
    NEW = "new"  # Новая
    IN_PROGRESS = "in_progress"  # В работе
    REVIEW = "review"  # На проверке
    DONE = "done"  # Выполнена
    CANCELLED = "cancelled"  # Отменена


class UserRoleEnum(str, enum.Enum):
    """Роли пользователей в системе"""
    PROJECT_MANAGER = "project_manager"  # Проектник - 1 человек, полный доступ
    MAIN_ORGANIZER = "main_organizer"  # Главный организатор - 2 человека
    RESPONSIBLE = "responsible"  # Ответственный - несколько
    WORKER = "worker"  # Обычный работник - много, только через бота


# Связующая таблица для many-to-many связи пользователей и рабочих групп
workgroup_users = Table(
    "workgroup_users",
    Base.metadata,
    Column("workgroup_id", Integer, ForeignKey("workgroups.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

# Связующая таблица для исполнителей задач (many-to-many)
task_assignees = Table(
    "task_assignees",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Роль пользователя
    role: Mapped[UserRoleEnum] = mapped_column(
        SQLEnum(UserRoleEnum),
        default=UserRoleEnum.WORKER,
        nullable=False,
        index=True
    )
    
    # Аутентификация для веб-интерфейса (только для ролей с доступом к сайту)
    login: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Хэшированный пароль
    
    # Иерархия подчинения - кто создал этого пользователя
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Иерархия подчинения - связь с создателем (many-to-one)
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
        remote_side="User.id",
        back_populates="created_users"
    )
    
    # Пользователи, созданные этим пользователем (one-to-many)
    created_users: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="created_by",
        cascade="all"
    )
    
    # Связи с задачами
    created_tasks: Mapped[list["Task"]] = relationship(
        "Task", 
        foreign_keys="Task.created_by_id",
        back_populates="creator",
        cascade="all, delete-orphan"
    )

    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        foreign_keys="Task.assigned_to_id",
        back_populates="assignee"
    )

    # Задачи, где пользователь является исполнителем (через task_assignees)
    tasks_as_assignee: Mapped[list["Task"]] = relationship(
        "Task",
        secondary=task_assignees,
        back_populates="assignees"
    )
    
    # Связи с рабочими группами
    workgroups: Mapped[list["WorkGroup"]] = relationship(
        "WorkGroup",
        secondary=workgroup_users,
        back_populates="members"
    )
    
    # Рабочие группы, где пользователь является ответственным
    responsible_workgroups: Mapped[list["WorkGroup"]] = relationship(
        "WorkGroup",
        foreign_keys="WorkGroup.responsible_id",
        back_populates="responsible"
    )


class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan"
    )


class WorkGroup(Base):
    """Рабочая группа - создается главными организаторами"""
    __tablename__ = "workgroups"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Кто создал группу
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Ответственный за группу (может управлять задачами в группе)
    responsible_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    responsible: Mapped[Optional["User"]] = relationship("User", foreign_keys=[responsible_id], back_populates="responsible_workgroups")
    
    # Участники группы (ответственные и работники)
    members: Mapped[list["User"]] = relationship(
        "User",
        secondary=workgroup_users,
        back_populates="workgroups"
    )
    
    # Задачи группы
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="workgroup",
        cascade="all, delete-orphan"
    )


class Task(Base):
    """Модель задачи"""
    __tablename__ = "tasks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatusEnum] = mapped_column(
        SQLEnum(TaskStatusEnum),
        default=TaskStatusEnum.NEW,
        nullable=False
    )
    
    # Связи
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    workgroup_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workgroups.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    assigned_to_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Опрос о задаче: интервал в днях (0/None = отключено), во сколько спрашивать
    poll_interval_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    poll_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # "HH:MM"
    last_polled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # ID сообщения в Telegram
    telegram_chat_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # ID чата в Telegram


    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="tasks")
    workgroup: Mapped[Optional["WorkGroup"]] = relationship("WorkGroup", back_populates="tasks")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by_id], back_populates="created_tasks")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_tasks")
    # Исполнители задачи (many-to-many)
    assignees: Mapped[list["User"]] = relationship(
        "User",
        secondary=task_assignees,
        back_populates="tasks_as_assignee",
        lazy="selectin"
    )

    @property
    def assignee_ids(self) -> list[int]:
        return [u.id for u in self.assignees]

    status_history: Mapped[list["TaskStatus"]] = relationship(
        "TaskStatus",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskStatus.created_at"
    )

    poll_responses: Mapped[list["TaskPollResponse"]] = relationship(
        "TaskPollResponse",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskPollResponse.polled_at"
    )


class TaskPollResponse(Base):
    """Ответ пользователя на опрос о задаче (когда спрашивали в боте)"""
    __tablename__ = "task_poll_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    polled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Статус задачи в момент отправки опроса (для отображения белой точки на таймлайне)
    status_at_poll: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    task: Mapped["Task"] = relationship("Task", back_populates="poll_responses")
    user: Mapped["User"] = relationship("User")


class TaskStatus(Base):
    """История изменений статусов задач"""
    __tablename__ = "task_statuses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status: Mapped[TaskStatusEnum] = mapped_column(SQLEnum(TaskStatusEnum), nullable=False)
    changed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    task: Mapped["Task"] = relationship("Task", back_populates="status_history")
    changed_by: Mapped[Optional["User"]] = relationship("User")
