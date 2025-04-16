#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：configuration.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/3/27 15:37
"""

from datetime import date, datetime
from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ConfigurationSchemaBase(SchemaBase):
    # model: Optional[str] = Field(None, description='model')
    prod_model: Optional[str] = Field(None, description='产品型号')
    product_no: Optional[str] = Field(None, description='电机编号/产品编号')
    product_serial_no: Optional[str] = Field(None, description='产品编号')
    process_name: Optional[str] = Field(None, description='工序名称')
    extra_material_code: Optional[str] = Field(None, description='物料代码')
    extra_material_name: Optional[str] = Field(None, description='物料名称')
    extra_product_batch_no: Optional[str] = Field(None, description='产品序列号/批次号')
    extra_supplier: Optional[str] = Field(None, description='供应商')
    extra2_file_version: Optional[str] = Field(None, description='图号版本')
    extra2_material_state: Optional[str] = Field(None, description='状态')
    extra_source_code: Optional[str] = Field(None, description='配件/原材料追溯编号')
    repair_level: Optional[str] = Field(None, description='寿命阶段')
    life_cycle_time: Optional[date] = Field(None, description='出厂日期')
    rela_self_value: Optional[str] = Field(None, description='自检结果')
    self_create_by: Optional[str] = Field(None, description='自检人/时间')
    rela_self_data: Optional[str] = Field(None, description='自检时间')
    rela_mutual_value: Optional[str] = Field(None, description='互检结果')
    mutual_create_by: Optional[str] = Field(None, description='互检/时间')
    rela_mutual_data: Optional[str] = Field(None, description='互检时间')
    rela_special_test_value: Optional[str] = Field(None, description='专检结果')
    special_create_by: Optional[str] = Field(None, description='专检/时间')
    rela_special_test_data: Optional[str] = Field(None, description='专检时间')
    version: Optional[str] = Field(None, description='PC版本')
    check_project: Optional[str] = Field(None, description='检修区位')
    check_bezier: Optional[str] = Field(None, description='检修项点')
    cj_date: Optional[date] = Field(None, description='采集时间')
    create_time: Optional[datetime] = Field(None, description='操作日期')
    create_by_name: Optional[str] = Field(None, description='操作人')


class CreateConfigurationParam(ConfigurationSchemaBase):
    pass


class GetConfigurationParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prod_model: str = Field(..., description='产品型号')
    extra_material_code: str = Field(..., description='物料代码')
    repair_level: str = Field(..., description='寿命阶段')
    life_cycle_time: date = Field(..., description='出厂日期')


class GetConfigurationDetails(GetConfigurationParam):
    model_config = ConfigDict(from_attributes=True)

    product_no: Optional[str] = Field(None, description='电机编号/产品编号')
    product_serial_no: Optional[str] = Field(None, description='产品编号')
    process_name: Optional[str] = Field(None, description='工序名称')
    extra_material_name: Optional[str] = Field(None, description='物料名称')
    extra_product_batch_no: Optional[str] = Field(None, description='产品序列号/批次号')
    extra_supplier: Optional[str] = Field(None, description='供应商')
    extra2_file_version: Optional[str] = Field(None, description='图号版本')
    extra2_material_state: Optional[str] = Field(None, description='状态')
    extra_source_code: Optional[str] = Field(None, description='配件/原材料追溯编号')
    rela_self_value: Optional[str] = Field(None, description='自检结果')
    self_create_by: Optional[str] = Field(None, description='自检人/时间')
    rela_self_data: Optional[str] = Field(None, description='自检时间')
    rela_mutual_value: Optional[str] = Field(None, description='互检结果')
    mutual_create_by: Optional[str] = Field(None, description='互检/时间')
    rela_mutual_data: Optional[str] = Field(None, description='互检时间')
    rela_special_test_value: Optional[str] = Field(None, description='专检结果')
    special_create_by: Optional[str] = Field(None, description='专检/时间')
    rela_special_test_data: Optional[str] = Field(None, description='专检时间')
    version: Optional[str] = Field(None, description='PC版本')
    check_project: Optional[str] = Field(None, description='检修区位')
    check_bezier: Optional[str] = Field(None, description='检修项点')
    cj_date: Optional[date] = Field(None, description='采集时间')
    create_time: Optional[datetime] = Field(None, description='操作日期')
    create_by_name: Optional[str] = Field(None, description='操作人')


class GetConfigurationListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetConfigurationDetails] = Field(default_factory=list, description='查询结果列表')
    total: int = Field(default=0, ge=0, description='总记录数')
