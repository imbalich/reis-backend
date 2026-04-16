#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import date
from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ProductSchemaBase(SchemaBase):
    large_class: Optional[str] = Field(None, description='product class')
    product_type: Optional[str] = Field(None, description='product type')
    apply_area: Optional[str] = Field(None, description='apply area')
    apply_area_desc: Optional[str] = Field(None, description='apply area desc')
    product_sub: Optional[str] = Field(None, description='product sub type')
    sub_name: Optional[str] = Field(None, description='product name')
    sub_saet: Optional[str] = Field(None, description='product series')
    model: Optional[str] = Field(None, description='product model')
    product_config_code: Optional[str] = Field(None, description='product config code')
    repair_priod: Optional[str] = Field(None, description='repair period')
    attach_train: Optional[str] = Field(None, description='attached train')
    repair_times: Optional[int] = Field(None, description='repair interval days')
    avg_worktime: Optional[int] = Field(None, description='avg work hours')
    avg_speed: Optional[float] = Field(None, description='avg speed')
    year_days: Optional[int] = Field(None, description='year days')
    update_time: Optional[date] = Field(None, description='update time')
    mark: Optional[str] = Field(None, description='remark')
    prd_big_type: Optional[str] = Field(None, description='custom type')


class CreateProductParam(ProductSchemaBase):
    pass


class GetProductParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    large_class: str = Field(..., description='product class')


class GetProductDetails(GetProductParam):
    model_config = ConfigDict(from_attributes=True)

    product_type: Optional[str] = Field(None, description='product type')
    apply_area: Optional[str] = Field(None, description='apply area')
    apply_area_desc: Optional[str] = Field(None, description='apply area desc')
    product_sub: Optional[str] = Field(None, description='product sub type')
    sub_name: Optional[str] = Field(None, description='product name')
    sub_saet: Optional[str] = Field(None, description='product series')
    model: Optional[str] = Field(None, description='product model')
    product_config_code: Optional[str] = Field(None, description='product config code')
    repair_priod: Optional[str] = Field(None, description='repair period')
    attach_train: Optional[str] = Field(None, description='attached train')
    repair_times: Optional[int] = Field(None, description='repair interval days')
    avg_worktime: Optional[int] = Field(None, description='avg work hours')
    avg_speed: Optional[float] = Field(None, description='avg speed')
    year_days: Optional[int] = Field(None, description='year days')
    update_time: Optional[date] = Field(None, description='update time')
    mark: Optional[str] = Field(None, description='remark')
    prd_big_type: Optional[str] = Field(None, description='custom type')


class GetProductListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetProductDetails] = Field(default_factory=list, description='result list')
    total: int = Field(default=0, ge=0, description='total count')
