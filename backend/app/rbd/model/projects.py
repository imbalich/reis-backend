#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import JSON

from backend.common.enums import StrEnum
from backend.common.model import id_key
from backend.common.model import Base


class ProjectStatusType(StrEnum):
    """项目状态类型"""
    
    draft = 'draft'           # 草稿
    published = 'published'   # 已发布
    archived = 'archived'     # 已归档


class TaskType(StrEnum):
    """任务类型"""
    
    jp = 'jp'     # 机破
    lx = 'lx'     # 临修


class Projects(Base):
    """rbd_projects 表"""
    
    __tablename__ = 'rbd_projects'
    
    # 联合唯一索引：版本+型号+任务类型
    __table_args__ = (
        UniqueConstraint('model', 'task_type', 'version', name='uk_model_task_version'),
    )

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment='项目名称')
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment='项目描述')
    model: Mapped[str] = mapped_column(String(100), nullable=False, comment='产品型号')
    graph_data: Mapped[dict] = mapped_column(
        JSON, 
        nullable=False, 
        comment='完整的图形数据'
    )
    project_metadata: Mapped[dict | None] = mapped_column(
        JSON, 
        nullable=True, 
        comment='项目元数据'
    )
    created_by: Mapped[str | None] = mapped_column(
        String(50), 
        nullable=True, 
        comment='创建人'
    )
    task_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default=TaskType.jp.value,
        comment='任务类型（jp:击破 lx:临修）'
    )
    version: Mapped[int] = mapped_column(
        Integer, 
        default=1, 
        comment='版本号'
    )
    status: Mapped[str] = mapped_column(
        String(20), 
        default=ProjectStatusType.draft.value, 
        comment='项目状态（draft:草稿 published:已发布 archived:已归档）'
    )