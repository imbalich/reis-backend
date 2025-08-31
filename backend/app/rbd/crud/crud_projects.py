# backend/app/rbd/crud/crud_projects.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.rbd.model.projects import ProjectStatusType, Projects, TaskType


class CRUDProjects(CRUDPlus[Projects]):
    """项目数据库操作类"""

    async def get(self, db: AsyncSession, pk: int) -> Projects | None:
        """获取项目详情"""
        return await self.select_model(db, pk)

    async def get_list(
        self,
        model: str | None,
        task_type: TaskType | None,
        version: int | None,
        status: ProjectStatusType | None,
        created_by: str | None,
    ) -> Select:
        """获取项目列表"""
        filters = {}

        if model is not None:
            filters['model__like'] = f'%{model}%'
        if task_type is not None:
            filters['task_type'] = task_type
        if version is not None:
            filters['version'] = version
        if status is not None:
            filters['status'] = status
        if created_by is not None:
            filters['created_by__like'] = f'%{created_by}%'

        return await self.select_order('created_time', 'desc', **filters)  # 改为 created_time

    async def get_all(self, db: AsyncSession) -> Sequence[Projects]:
        """获取所有项目"""
        return await self.select_models(db)

    # async def get_next_version(self, db: AsyncSession, model: str, task_type: TaskType) -> int:
    #     """获取下一个版本号"""
    #     # 查询当前最大版本号
    #     stmt = select(func.max(Projects.version)).where(
    #         Projects.model == model,
    #         Projects.task_type == task_type  # 直接使用枚举对象
    #     )
    #     result = await db.execute(stmt)
    #     max_version = result.scalar()
    #     return max_version + 1 if max_version else 1

    async def create(self, db: AsyncSession, obj: dict) -> int:
        """创建项目"""
        new_project = self.model(**obj)
        db.add(new_project)
        await db.flush()  # 获取ID
        return new_project.id

    async def update(self, db: AsyncSession, pk: str, obj: dict) -> int:
        """更新项目"""
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pks: list[str]) -> int:
        """批量删除项目"""
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pks)


projects_dao: CRUDProjects = CRUDProjects(Projects)