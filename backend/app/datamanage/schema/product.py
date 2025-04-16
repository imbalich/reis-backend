#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend
@File    ：product.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/16 14:56
'''
from datetime import date
from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ProductSchemaBase(SchemaBase):
    large_class: Optional[str] = Field(None, description='产品大类')
    product_type: Optional[str] = Field(None, description='产品类型')
    apply_area: Optional[str] = Field(None, description='应用领域')
    apply_area_desc: Optional[str] = Field(None, description='应用领域（细分）')
    product_sub: Optional[str] = Field(None, description='产品子类')
    sub_name: Optional[str] = Field(None, description='产品名称')
    sub_saet: Optional[str] = Field(None, description='产品系列')
    model: Optional[str] = Field(None, description='产品型号')
    repair_priot: Optional[str] = Field(None, description='维修周期')
    attach_train: Optional[str] = Field(None, description='配属车型')
    repair_times: Optional[int] = Field(None, description='修级间隔天数')
    avg_worktime: Optional[int] = Field(None, description='日均工作小时')
    avg_speed: Optional[float] = Field(None, description='平均时速')
    year_days: Optional[int] = Field(None, description='年运行天数')
    update_time: Optional[date] = Field(None, description='年运行天数')
    mark: Optional[str] = Field(None, description='备注')
    prd_big_type: Optional[str] = Field(None, description='自定义类别')


class CreateProductParam(ProductSchemaBase):
    pass


class GetProductParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    large_class: str = Field(..., description='产品大类')


class GetProductDetails(GetProductParam):
    model_config = ConfigDict(from_attributes=True)

    product_type: Optional[str] = Field(None, description='产品类型')
    apply_area: Optional[str] = Field(None, description='应用领域')
    apply_area_desc: Optional[str] = Field(None, description='应用领域（细分）')
    product_sub: Optional[str] = Field(None, description='产品子类')
    sub_name: Optional[str] = Field(None, description='产品名称')
    sub_saet: Optional[str] = Field(None, description='产品系列')
    model: Optional[str] = Field(None, description='产品型号')
    repair_priod: Optional[str] = Field(None, description='维修周期')
    attach_train: Optional[str] = Field(None, description='配属车型')
    repair_times: Optional[int] = Field(None, description='修级间隔天数')
    avg_worktime: Optional[int] = Field(None, description='日均工作小时')
    avg_speed: Optional[float] = Field(None, description='平均时速')
    year_days: Optional[int] = Field(None, description='年运行天数')
    update_time: Optional[date] = Field(None, description='变更时间')
    mark: Optional[str] = Field(None, description='备注')
    prd_big_type: Optional[str] = Field(None, description='自定义类别')


class GetProductListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetProductDetails] = Field(default_factory=list, description="查询结果列表")
    total: int = Field(default=0, ge=0, description="总记录数")
