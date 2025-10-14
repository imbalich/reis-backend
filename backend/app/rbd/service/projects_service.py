# backend/app/rbd/service/projects_service.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from fastapi import Request
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.rbd.crud.crud_projects import projects_dao
from backend.app.rbd.model.projects import Projects, ProjectStatusType
from backend.app.rbd.schema.projects import CreateProjectsParam, DeleteProjectsParam, UpdateProjectBasicInfoParam, UpdateProjectsParam
from backend.common.exception import errors
from backend.database.db import async_db_session


class ProjectsService:
    """项目服务类"""

    @staticmethod
    async def get(*, pk: int) -> Projects:
        """
        获取项目详情

        :param pk: 项目 ID
        :return:
        """
        async with async_db_session() as db:
            project = await projects_dao.get(db, pk)
            if not project:
                raise errors.NotFoundError(msg='项目不存在')
            return project

    @staticmethod
    async def get_select(
        *, 
        model: str | None, 
        task_type: str | None,
        version: int | None,
        status: ProjectStatusType | None,
        created_by: str | None
    ) -> Select:
        """
        获取项目列表查询条件

        :param model: 产品型号
        :param task_type: 任务类型
        :param version: 版本号
        :param status: 项目状态
        :param created_by: 创建人
        :return:
        """
        return await projects_dao.get_list(
            model=model, 
            task_type=task_type, 
            version=version, 
            status=status, 
            created_by=created_by
        )

    @staticmethod
    async def get_all() -> Sequence[Projects]:
        """获取所有项目"""
        async with async_db_session() as db:
            projects = await projects_dao.get_all(db)
            return projects

    @staticmethod
    async def create(*, request: Request, obj: CreateProjectsParam) -> int:
        """
        创建项目

        :param request: FastAPI 请求对象
        :param obj: 项目创建参数
        :return: 项目ID
        """
        async with async_db_session.begin() as db:
            # 获取下一个版本号
            # TODO:完成版本号管理器的实现
            # next_version = await projects_dao.get_next_version(db, obj.model, obj.task_type)
            
            # 构建完整的项目数据
            project_data = {
                'name': obj.name,
                'description': obj.description,
                'model': obj.model,
                'task_type': obj.task_type,  # 直接使用枚举对象
                'graph_data': {},  # 默认空JSON
                'project_metadata': None,  # 默认None
                'version': 1,
                'status': ProjectStatusType.draft,  # 默认草稿状态
                'created_by': request.user.username,  # 从request获取用户信息
            }
            
            project_id = await projects_dao.create(db, project_data)
            return project_id

    @staticmethod
    async def update(*, pk: str, obj: UpdateProjectsParam) -> int:
        """
        更新项目

        :param pk: 项目 ID
        :param obj: 项目更新参数
        :return:
        """
        async with async_db_session.begin() as db:
            project = await projects_dao.get(db, pk)
            if not project:
                raise errors.NotFoundError(msg='项目不存在')
            count = await projects_dao.update(db, pk, obj)
            return count
        
    @staticmethod
    async def update_basic_info(*, pk: str, obj: UpdateProjectBasicInfoParam) -> int:
        """
        更新项目基本信息（不包含图形数据）

        :param pk: 项目 ID
        :param obj: 项目基本信息更新参数
        :return: 更新的记录数
        """
        async with async_db_session.begin() as db:
            project = await projects_dao.get(db, pk)
            if not project:
                raise errors.NotFoundError(msg='项目不存在')
            
            # 只更新非空字段
            update_data = obj.model_dump(exclude_unset=True)
            if not update_data:
                raise errors.DataValidationError(msg='至少需要提供一个更新字段')
            
            # 校验必填字段（如果提供了值，不能为空字符串）
            if 'name' in update_data and not update_data['name']:
                raise errors.DataValidationError(msg='项目名称不能为空')
            if 'model' in update_data and not update_data['model']:
                raise errors.DataValidationError(msg='产品型号不能为空')
            if 'task_type' in update_data and not update_data['task_type']:
                raise errors.DataValidationError(msg='任务类型不能为空')
            
            count = await projects_dao.update_model(db, pk, update_data)
            return count

    @staticmethod
    async def delete(*, obj: DeleteProjectsParam) -> int:
        """
        批量删除项目

        :param obj: 项目 ID 列表
        :return:
        """
        async with async_db_session.begin() as db:
            count = await projects_dao.delete(db, obj.pks)
            return count


projects_service: ProjectsService = ProjectsService()