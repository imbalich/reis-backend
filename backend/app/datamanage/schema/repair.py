#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：repair.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/1/20 09:38 
'''
from datetime import date
from typing import Optional

from pydantic import Field, ConfigDict

from backend.common.schema import SchemaBase


class RepairSchemaBase(SchemaBase):
    id_repair: Optional[int] = Field(None, description='修级顺序')
    repair_levels: Optional[str] = Field(None, description='造修阶段')
    model: Optional[str] = Field(None, description='产品型号')
    creator: Optional[str] = Field(None, description='创建人')
    create_time: Optional[date] = Field(None, description='创建时间')
    state_now: bool = Field(default=True, description='当前是否启用，1启用；0未启用,默认为1')


class CreateRepairParam(RepairSchemaBase):
    pass


class GetRepairParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str = Field(..., description='产品型号')


class GetRepairDetails(GetRepairParam):
    model_config = ConfigDict(from_attributes=True)

    id_repair: Optional[int] = Field(None, description='修级顺序')
    repair_levels: Optional[str] = Field(None, description='造修阶段')
    creator: Optional[str] = Field(None, description='创建人')
    create_time: Optional[date] = Field(None, description='创建时间')
    state_now: bool = Field(default=True, description='当前是否启用，1启用；0未启用,默认为1')


class GetRepairListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetRepairDetails] = Field(default_factory=list, description="查询结果列表")
    total: int = Field(default=0, ge=0, description="总记录数")
