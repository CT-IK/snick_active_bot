"""API endpoints для пользователей"""
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, UserRoleEnum
from dao.user_dao import UserDAO
from schemas.user import UserCreate, UserUpdate, UserResponse, UserWithHierarchy
from api.dependencies import get_current_user, require_role, get_db
from utils.auth import get_password_hash
from services.bot import notify_role_assigned, ROLE_NAMES

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return UserResponse.model_validate(current_user)


@router.post("/me/test-telegram")
async def test_telegram(current_user: User = Depends(get_current_user)):
    """Тест: отправить пробное сообщение в Telegram (для проверки настройки)"""
    if not current_user.telegram_id:
        raise HTTPException(
            status_code=400,
            detail="У вас не указан Telegram ID. Отредактируйте профиль и добавьте его."
        )
    from services.bot import send_message
    ok = await send_message(
        current_user.telegram_id,
        "🔔 <b>Тест</b>\n\nСообщение от Task Tracker. Если вы это видите — уведомления настроены верно!"
    )
    if ok:
        return {"ok": True, "message": "Сообщение отправлено"}
    raise HTTPException(status_code=502, detail="Не удалось отправить. Проверьте логи сервера и что вы писали боту /start.")


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить список пользователей"""
    # Проектник и главные организаторы видят всех
    if current_user.role in [UserRoleEnum.PROJECT_MANAGER, UserRoleEnum.MAIN_ORGANIZER]:
        users = await UserDAO.get_all(db, skip=skip, limit=limit)
    # Ответственные видят только своих подчиненных
    elif current_user.role == UserRoleEnum.RESPONSIBLE:
        users = await UserDAO.get_created_by(db, current_user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    
    return [UserResponse.model_validate(u) for u in users]


@router.get("/assignable", response_model=List[UserResponse])
async def get_assignable_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Пользователи, которых можно назначить в рабочую группу (с учётом иерархии: ГО не может добавить проектника)"""
    if current_user.role == UserRoleEnum.PROJECT_MANAGER:
        users = await UserDAO.get_all(db, skip=0, limit=500)
    elif current_user.role == UserRoleEnum.MAIN_ORGANIZER:
        all_users = await UserDAO.get_all(db, skip=0, limit=500)
        users = [u for u in all_users if u.role != UserRoleEnum.PROJECT_MANAGER]
    else:
        users = []
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить пользователя по ID"""
    user = await UserDAO.get_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Проверка прав доступа
    if current_user.role == UserRoleEnum.RESPONSIBLE:
        # Ответственный видит только своих подчиненных
        if user.created_by_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав"
            )
    
    return UserResponse.model_validate(user)


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать пользователя"""
    # Проверка прав на создание
    if current_user.role == UserRoleEnum.WORKER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Работники не могут создавать пользователей"
        )
    
    # Для ролей с доступом к веб-интерфейсу — обязательны логин и пароль
    web_access_roles = [UserRoleEnum.PROJECT_MANAGER, UserRoleEnum.MAIN_ORGANIZER, UserRoleEnum.RESPONSIBLE]
    if user_data.role in web_access_roles:
        if not (user_data.login and user_data.login.strip()):
            raise HTTPException(status_code=400, detail="Для этой роли обязательно указать логин")
        if not (user_data.password and user_data.password.strip()):
            raise HTTPException(status_code=400, detail="Для этой роли обязательно указать пароль")

    # Проверка уникальности логина
    if user_data.login and user_data.login.strip():
        login_clean = user_data.login.strip()
        existing = await UserDAO.get_by_login(db, login_clean)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким логином уже существует"
            )
    
    # Создание пользователя
    login_val = user_data.login.strip() if user_data.login else None
    user = User(
        username=user_data.username,
        full_name=user_data.full_name,
        role=user_data.role,
        telegram_id=user_data.telegram_id,
        login=login_val,
        password_hash=get_password_hash(user_data.password.strip()) if (user_data.password and user_data.password.strip()) else None,
        created_by_id=current_user.id
    )
    
    created_user = await UserDAO.create(db, user)
    if created_user.telegram_id:
        role_name = ROLE_NAMES.get(created_user.role, str(created_user.role))
        has_web = created_user.role in (UserRoleEnum.PROJECT_MANAGER, UserRoleEnum.MAIN_ORGANIZER, UserRoleEnum.RESPONSIBLE)
        background_tasks.add_task(notify_role_assigned, created_user.telegram_id, role_name, True, has_web)
    return UserResponse.model_validate(created_user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновить пользователя"""
    user = await UserDAO.get_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Проверка прав
    if current_user.role == UserRoleEnum.RESPONSIBLE:
        if user.created_by_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Можно обновлять только своих подчиненных"
            )
    
    # Обновление полей
    old_role = user.role
    if user_data.username is not None:
        user.username = user_data.username
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.login is not None:
        login_clean = user_data.login.strip() if user_data.login else None
        if login_clean:
            existing = await UserDAO.get_by_login(db, login_clean)
            if existing and existing.id != user_id:
                raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
        user.login = login_clean
    if user_data.password is not None and user_data.password.strip():
        user.password_hash = get_password_hash(user_data.password.strip())
    if user_data.telegram_id is not None:
        user.telegram_id = user_data.telegram_id if user_data.telegram_id else None
    
    # Уведомление при смене роли (если есть telegram_id)
    role_changed = user_data.role is not None and user_data.role != old_role
    if role_changed and user.telegram_id:
        role_name = ROLE_NAMES.get(user.role, str(user.role))
        has_web = user.role in (UserRoleEnum.PROJECT_MANAGER, UserRoleEnum.MAIN_ORGANIZER, UserRoleEnum.RESPONSIBLE)
        background_tasks.add_task(notify_role_assigned, user.telegram_id, role_name, False, has_web)
    
    updated_user = await UserDAO.update(db, user)
    return UserResponse.model_validate(updated_user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить пользователя"""
    user = await UserDAO.get_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Только проектник может удалять
    if current_user.role != UserRoleEnum.PROJECT_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только проектник может удалять пользователей"
        )
    
    await UserDAO.delete(db, user_id)
    return {"message": "Пользователь удален"}
