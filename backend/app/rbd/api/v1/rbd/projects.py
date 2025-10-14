# backend/app/rbd/api/v1/rbd/projects.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.rbd.model.projects import ProjectStatusType
from backend.app.rbd.schema.projects import (
    CreateProjectsParam,
    DeleteProjectsParam,
    GetProjectsDetail,
    UpdateProjectBasicInfoParam,
    UpdateProjectsParam,
)
from backend.app.rbd.service.projects_service import projects_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession

router = APIRouter()

"""
接口需求:
1. 获取项目详情
2. 分页获取项目列表
3. 创建项目（用户只需提供4个字段）
4. 更新项目
5. 发布项目
6. 创建新版本
7. 批量删除项目
"""

@router.get('/{pk}', summary='获取项目详情', dependencies=[DependsJwtAuth])
async def get_project(
    pk: Annotated[int, Path(description='项目 ID')],
) -> ResponseSchemaModel[GetProjectsDetail]:
    data = await projects_service.get(pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取项目列表',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_projects_paged(
    db: CurrentSession,
    model: Annotated[str | None, Query(description='产品型号')] = None,
    task_type: Annotated[str | None, Query(description='任务类型')] = None,  # 改为枚举类型
    version: Annotated[int | None, Query(description='版本号')] = None,
    status: Annotated[ProjectStatusType | None, Query(description='项目状态')] = None,  # 改为枚举类型
    created_by: Annotated[str | None, Query(description='创建人')] = None,
) -> ResponseSchemaModel[PageData[GetProjectsDetail]]:
    project_select = await projects_service.get_select(
        model=model, task_type=task_type, version=version, status=status, created_by=created_by
    )
    page_data = await paging_data(db, project_select)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建项目',
    dependencies=[
        Depends(RequestPermission('rbd:project:add')),
        DependsRBAC,
    ],
)
async def create_project(
    request: Request,
    obj: CreateProjectsParam
) -> ResponseSchemaModel[int]:  # 改为int类型
    """创建项目 - 用户只需提供基本信息，系统自动处理版本和状态"""
    project_id = await projects_service.create(request=request, obj=obj)
    return response_base.success(data=project_id)


@router.put(
    '/{pk}',
    summary='更新项目',
    dependencies=[
        Depends(RequestPermission('rbd:project:edit')),
        DependsRBAC,
    ],
)
async def update_project(
    pk: Annotated[str, Path(description='项目 ID')], 
    obj: UpdateProjectsParam
) -> ResponseModel:  # 这里不需要指定data类型，因为ResponseModel不包含data字段
    count = await projects_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.put(
    '/{pk}/basic-info',
    summary='更新项目基本信息',
    dependencies=[
        Depends(RequestPermission('rbd:project:edit')),
        DependsRBAC,
    ],
)
async def update_project_basic_info(
    pk: Annotated[str, Path(description='项目 ID')], 
    obj: UpdateProjectBasicInfoParam
) -> ResponseModel:
    """更新项目基本信息 - 只修改名称、描述、型号、任务类型，不涉及图形数据"""
    count = await projects_service.update_basic_info(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.put(
    '/{pk}/publish',
    summary='发布项目',
    dependencies=[
        Depends(RequestPermission('rbd:project:publish')),
        DependsRBAC,
    ],
)
async def publish_project(
    pk: Annotated[str, Path(description='项目 ID')]
) -> ResponseModel:  # 这里也不需要指定data类型
    """发布项目 - 将草稿状态改为已发布"""
    count = await projects_service.publish(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post(
    '/{pk}/new-version',
    summary='创建新版本',
    dependencies=[
        Depends(RequestPermission('rbd:project:version')),
        DependsRBAC,
    ],
)
async def create_new_version(
    pk: Annotated[str, Path(description='项目 ID')]
) -> ResponseSchemaModel[str]:
    """基于已发布项目创建新版本 - 原项目归档，创建新草稿"""
    new_project_id = await projects_service.create_new_version(pk=pk)
    return response_base.success(data=new_project_id)


@router.delete(
    '',
    summary='批量删除项目',
    dependencies=[
        Depends(RequestPermission('rbd:project:del')),
        DependsRBAC,
    ],
)
async def delete_projects(obj: DeleteProjectsParam) -> ResponseModel:  # 这里也不需要指定data类型
    count = await projects_service.delete(obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()