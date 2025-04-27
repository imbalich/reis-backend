#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：reis-backend 
@File    ：sense_param.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/4/25 10:18 
'''
from datetime import date
from typing import Optional

from backend.common.schema import SchemaBase
from pydantic import ConfigDict, json

class CreateSenseSortInParam(SchemaBase):
    # 创建产品级别拟合信息入参
    model: str
    part: str
    stage: str | None = '新造'
    process_name: str | None = None
    check_project: str | None = None
    check_bezier: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    extra_material_names: str | None = None

class CreateSenseSortParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    group_id: str
    model: str
    part: str
    stage: str
    process_name: str | None  = None
    check_project: str | None  = None
    check_bezier: str | None  = None
    start_time: Optional[date] | None  = None
    end_time: Optional[date] | None = None
    extra_material_names: str | None  = None

    model_type: str

    rela_self_value: float
    check_tools_sign: float
    self_create_by: float
    extra_source_code: float
    extra_supplier: float
    categorical_analysis:str