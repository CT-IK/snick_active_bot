"""API endpoints для аутентификации"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_db
from dao.user_dao import UserDAO
from schemas.user import LoginRequest, TokenResponse, UserResponse
from utils.auth import verify_password, create_access_token
from database.models import UserRoleEnum

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Вход в систему"""
    user = await UserDAO.get_by_login(db, login_data.login)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пароль не установлен. Обратитесь к проектнику для установки пароля."
        )
    
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    
    # Проверяем, что у пользователя есть доступ к веб-интерфейсу
    if user.role == UserRoleEnum.WORKER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Работники не имеют доступа к веб-интерфейсу"
        )
    
    # sub должен быть строкой для совместимости с JWT
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )
