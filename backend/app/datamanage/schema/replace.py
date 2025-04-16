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
    material_name: Optional[str] = Field(None, description='零部件名称')
    material_code: Optional[str] = Field(None, description='零部件物料编码')
    replace_level: Optional[str] = Field(None, description='修造级别')
    replace_cycle: Optional[float] = Field(None, description='必换周期')
    state_now: bool = Field(default=True, description='当前是否启用，1启用；0未启用,默认为1')


class CreateReplaceParam(ReplaceSchemaBase):
    pass


class GetReplaceParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str = Field(..., description='型号')


class GetReplaceDetails(GetReplaceParam):
    model_config = ConfigDict(from_attributes=True)

    material_name: Optional[str] = Field(None, description='零部件名称')
    material_code: Optional[str] = Field(None, description='零部件物料编码')
    replace_level: Optional[str] = Field(None, description='修造级别')
    replace_cycle: Optional[float] = Field(None, description='必换周期')
    state_now: bool = Field(default=True, description='当前是否启用，1启用；0未启用,默认为1')
