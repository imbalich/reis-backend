#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：replace.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/20 09:39
"""

from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ReplaceSchemaBase(SchemaBase):
    model: Optional[str] = Field(None, description='型号')
    part_name: Optional[str] = Field(None, description='零部件名称')
    part_code: Optional[str] = Field(None, description='零部件物料编码')
    replace_level: Optional[str] = Field(None, description='修造级别')
    replace_cycle: Optional[float] = Field(None, description='必换周期')
    replace_num: Optional[int] = Field(None, description='必换数量')
    replace_unit: Optional[str] = Field(None, description='必换数量单位')
    material_code: Optional[str] = Field(None, description='材料编码')
    state_now: bool = Field(default=True, description='当前是否启用，1启用；0未启用,默认为1')
    mark: Optional[str] = Field(None, description='备注')


class CreateReplaceParam(ReplaceSchemaBase):
    pass


class GetReplaceParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str = Field(..., description='型号')


class GetReplaceDetails(GetReplaceParam):
    model_config = ConfigDict(from_attributes=True)

    part_name: Optional[str] = Field(None, description='零部件名称')
    part_code: Optional[str] = Field(None, description='零部件物料编码')
    replace_level: Optional[str] = Field(None, description='修造级别')
    replace_cycle: Optional[float] = Field(None, description='必换周期')
    replace_num: Optional[int] = Field(None, description='必换数量')
    replace_unit: Optional[str] = Field(None, description='必换数量单位')
    material_code: Optional[str] = Field(None, description='材料编码')
    state_now: bool = Field(default=True, description='当前是否启用，1启用；0未启用,默认为1')
    mark: Optional[str] = Field(None, description='备注')
