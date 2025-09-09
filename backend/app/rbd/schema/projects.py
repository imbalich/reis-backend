# backend/app/rbd/schema/projects.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from backend.app.rbd.model.projects import ProjectStatusType
from backend.common.schema import SchemaBase


class ProjectsSchemaBase(SchemaBase):
    """项目基础模型"""

    name: str = Field(description='项目名称')
    description: str | None = Field(None, description='项目描述')
    model: str = Field(description='产品型号')
    graph_data: dict[str, Any] = Field(description='完整的图形数据')
    project_metadata: dict[str, Any] | None = Field(None, description='项目元数据')
    task_type: str = Field(description='任务类型')  # 直接使用枚举类型
    status: ProjectStatusType = Field(description='项目状态')  # 直接使用枚举类型


class CreateProjectsParam(SchemaBase):
    """创建项目参数"""
    
    name: str = Field(description='项目名称')
    description: str | None = Field(None, description='项目描述')
    model: str = Field(description='产品型号')
    task_type: str = Field(description='任务类型')  # 直接使用枚举类型


class UpdateProjectsParam(ProjectsSchemaBase):
    """更新项目参数"""


class DeleteProjectsParam(SchemaBase):
    """删除项目参数"""

    pks: list[int] = Field(description='项目 ID 列表')


class GetProjectsDetail(ProjectsSchemaBase):
    """项目详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='项目 ID')
    version: int = Field(description='版本号')
    created_by: str | None = Field(None, description='创建人')
    created_time: datetime = Field(description='创建时间')  # 改为 created_time
    updated_time: datetime | None = Field(None, description='更新时间')  # 改为 updated_time