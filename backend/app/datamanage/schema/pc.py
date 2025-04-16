#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：pc.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/3/27 15:44
"""

from datetime import date
from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class PCSchemaBase(SchemaBase):
    # model: Optional[str] = Field(None, description='model')
    prod_model: Optional[str] = Field(None, description='产品型号')
    purchase_code: Optional[str] = Field(None, description='订单编号')
    process_name: Optional[str] = Field(None, description='工序名称')
    product_serial_no: Optional[str] = Field(None, description='电机编号/产品编号')
    product_serial_no_2: Optional[str] = Field(None, description='产品编号')
    extra_material_name: Optional[str] = Field(None, description='物料名称/追溯零部件')
    version: Optional[str] = Field(None, description='PC表版本号')
    manufaucture_date: Optional[date] = Field(None, description='出厂日期')
    check_project: Optional[str] = Field(None, description='检验区位')
    check_bezier: Optional[str] = Field(None, description='检验项点')
    check_standard: Optional[str] = Field(None, description='质量标准')
    check_tools: Optional[str] = Field(None, description='检验工具')
    check_tools_sign: Optional[str] = Field(None, description='工具编号')
    unit_name: Optional[str] = Field(None, description='单位')
    rela_self_value: Optional[str] = Field(None, description='自检结果')
    self_create_by: Optional[str] = Field(None, description='自检人/时间')
    rela_self_data: Optional[str] = Field(None, description='自检时间')
    rela_mutual_value: Optional[str] = Field(None, description='互检结果')
    mutual_create_by: Optional[str] = Field(None, description='互检/时间')
    rela_mutual_data: Optional[str] = Field(None, description='互检时间')
    rela_special_test_value: Optional[str] = Field(None, description='专检结果')
    special_create_by: Optional[str] = Field(None, description='专检/时间')
    rela_special_test_data: Optional[str] = Field(None, description='专检时间')
    material_figure_no: Optional[str] = Field(None, description='产品图号')
    extra_type: Optional[str] = Field(None, description='数据类型')
    repair_level: Optional[str] = Field(None, description='寿命阶段')
    cj_date: Optional[date] = Field(None, description='采集时间')


class CreatePCParam(PCSchemaBase):
    pass


class GetPCParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prod_model: str = Field(..., description='产品型号')
    repair_level: str = Field(..., description='寿命阶段')
    manufaucture_date: date = Field(..., description='出厂日期')


class GetPCDetails(GetPCParam):
    model_config = ConfigDict(from_attributes=True)

    purchase_code: Optional[str] = Field(None, description='订单编号')
    process_name: Optional[str] = Field(None, description='工序名称')
    product_serial_no: Optional[str] = Field(None, description='电机编号/产品编号')
    product_serial_no_2: Optional[str] = Field(None, description='产品编号')
    extra_material_name: Optional[str] = Field(None, description='物料名称/追溯零部件')
    version: Optional[str] = Field(None, description='PC表版本号')
    check_project: Optional[str] = Field(None, description='检验区位')
    check_bezier: Optional[str] = Field(None, description='检验项点')
    check_standard: Optional[str] = Field(None, description='质量标准')
    check_tools: Optional[str] = Field(None, description='检验工具')
    check_tools_sign: Optional[str] = Field(None, description='工具编号')
    unit_name: Optional[str] = Field(None, description='单位')
    rela_self_value: Optional[str] = Field(None, description='自检结果')
    self_create_by: Optional[str] = Field(None, description='自检人/时间')
    rela_self_data: Optional[str] = Field(None, description='自检时间')
    rela_mutual_value: Optional[str] = Field(None, description='互检结果')
    mutual_create_by: Optional[str] = Field(None, description='互检/时间')
    rela_mutual_data: Optional[str] = Field(None, description='互检时间')
    rela_special_test_value: Optional[str] = Field(None, description='专检结果')
    special_create_by: Optional[str] = Field(None, description='专检/时间')
    rela_special_test_data: Optional[str] = Field(None, description='专检时间')
    material_figure_no: Optional[str] = Field(None, description='产品图号')
    extra_type: Optional[str] = Field(None, description='数据类型')
    cj_date: Optional[date] = Field(None, description='采集时间')


class GetPCListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetPCDetails] = Field(default_factory=list, description='查询结果列表')
    total: int = Field(default=0, ge=0, description='总记录数')
