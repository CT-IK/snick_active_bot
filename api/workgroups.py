"""API endpoints для рабочих групп"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, UserRoleEnum, workgroup_users
from dao.workgroup_dao import WorkGroupDAO
from dao.user_dao import UserDAO
from schemas.workgroup import WorkGroupCreate, WorkGroupUpdate, WorkGroupResponse, WorkGroupWithRelations
from api.dependencies import get_current_user, get_db


def _can_assign_user(creator: User, target: User) -> bool:
    """Проверка: может ли creator назначить target (ГО не может назначить проектника)"""
    if creator.role == UserRoleEnum.PROJECT_MANAGER:
        return True
    if creator.role == UserRoleEnum.MAIN_ORGANIZER:
        return target.role != UserRoleEnum.PROJECT_MANAGER
    return False

router = APIRouter(prefix="/api/workgroups", tags=["workgroups"])


@router.get("/", response_model=List[WorkGroupWithRelations])
async def get_workgroups(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить список рабочих групп"""
    if current_user.role == UserRoleEnum.PROJECT_MANAGER:
        workgroups = await WorkGroupDAO.get_all(db, skip=skip, limit=limit)
    elif current_user.role == UserRoleEnum.MAIN_ORGANIZER:
        workgroups = await WorkGroupDAO.get_by_creator(db, current_user.id)
    elif current_user.role == UserRoleEnum.RESPONSIBLE:
        workgroups = await WorkGroupDAO.get_by_responsible(db, current_user.id)
    else:
        workgroups = []
    
    return [WorkGroupWithRelations.model_validate(wg) for wg in workgroups]


@router.get("/{workgroup_id}", response_model=WorkGroupWithRelations)
async def get_workgroup(
    workgroup_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить рабочую группу по ID"""
    workgroup = await WorkGroupDAO.get_by_id(db, workgroup_id)
    
    if not workgroup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рабочая группа не найдена"
        )
    
    return WorkGroupWithRelations.model_validate(workgroup)


@router.post("/", response_model=WorkGroupResponse)
async def create_workgroup(
    workgroup_data: WorkGroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать рабочую группу"""
    from database.models import WorkGroup
    
    # Только главные организаторы и проектник могут создавать группы
    if current_user.role not in [UserRoleEnum.MAIN_ORGANIZER, UserRoleEnum.PROJECT_MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только главные организаторы могут создавать рабочие группы"
        )
    
    # Валидация: ответственный — по иерархии (ГО не может назначить проектника)
    if workgroup_data.responsible_id:
        responsible = await UserDAO.get_by_id(db, workgroup_data.responsible_id)
        if not responsible:
            raise HTTPException(status_code=400, detail="Ответственный не найден")
        if not _can_assign_user(current_user, responsible):
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав: нельзя назначить пользователя с этой ролью"
            )

    workgroup = WorkGroup(
        name=workgroup_data.name,
        description=workgroup_data.description,
        created_by_id=current_user.id,
        responsible_id=workgroup_data.responsible_id
    )
    
    created_workgroup = await WorkGroupDAO.create(db, workgroup)
    
    # Добавляем участников через таблицу ассоциации (избегаем lazy load в async)
    if workgroup_data.member_ids:
        for member_id in workgroup_data.member_ids:
            member = await UserDAO.get_by_id(db, member_id)
            if member and _can_assign_user(current_user, member):
                await db.execute(
                    insert(workgroup_users).values(workgroup_id=created_workgroup.id, user_id=member_id)
                )
            elif member and not _can_assign_user(current_user, member):
                raise HTTPException(
                    status_code=403,
                    detail=f"Недостаточно прав: нельзя добавить пользователя {member.full_name or member.login}"
                )
        await db.flush()
    
    return WorkGroupResponse.model_validate(created_workgroup)


@router.put("/{workgroup_id}", response_model=WorkGroupResponse)
async def update_workgroup(
    workgroup_id: int,
    workgroup_data: WorkGroupUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновить рабочую группу"""
    workgroup = await WorkGroupDAO.get_by_id(db, workgroup_id)
    
    if not workgroup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рабочая группа не найдена"
        )
    
    # Проверка прав
    if workgroup.created_by_id != current_user.id and current_user.role != UserRoleEnum.PROJECT_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для обновления группы"
        )
    
    # Обновление полей
    if workgroup_data.name is not None:
        workgroup.name = workgroup_data.name
    if workgroup_data.description is not None:
        workgroup.description = workgroup_data.description
    if workgroup_data.responsible_id is not None:
        if workgroup_data.responsible_id == 0:
            workgroup.responsible_id = None
        else:
            responsible = await UserDAO.get_by_id(db, workgroup_data.responsible_id)
            if not responsible:
                raise HTTPException(status_code=400, detail="Ответственный не найден")
            if not _can_assign_user(current_user, responsible):
                raise HTTPException(status_code=403, detail="Недостаточно прав для назначения этого пользователя")
            workgroup.responsible_id = workgroup_data.responsible_id
    
    # Обновление участников через таблицу ассоциации
    if workgroup_data.member_ids is not None:
        await db.execute(delete(workgroup_users).where(workgroup_users.c.workgroup_id == workgroup_id))
        for member_id in workgroup_data.member_ids:
            member = await UserDAO.get_by_id(db, member_id)
            if member and _can_assign_user(current_user, member):
                await db.execute(
                    insert(workgroup_users).values(workgroup_id=workgroup_id, user_id=member_id)
                )
            elif member and not _can_assign_user(current_user, member):
                raise HTTPException(status_code=403, detail="Недостаточно прав для добавления этого пользователя")
        await db.flush()
    
    updated_workgroup = await WorkGroupDAO.update(db, workgroup)
    return WorkGroupResponse.model_validate(updated_workgroup)


@router.delete("/{workgroup_id}")
async def delete_workgroup(
    workgroup_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить рабочую группу"""
    workgroup = await WorkGroupDAO.get_by_id(db, workgroup_id)
    
    if not workgroup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Рабочая группа не найдена"
        )
    
    # Только создатель или проектник может удалять
    if workgroup.created_by_id != current_user.id and current_user.role != UserRoleEnum.PROJECT_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для удаления группы"
        )
    
    await WorkGroupDAO.delete(db, workgroup_id)
    return {"message": "Рабочая группа удалена"}
