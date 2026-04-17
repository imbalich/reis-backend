#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : fastapi-base-backend
@File    : despatch.py
"""

from datetime import date
from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class DespatchSchemaBase(SchemaBase):
    model: Optional[str] = Field(None, description='model')
    product_config_code: Optional[str] = Field(None, description='product config code')
    identifier: Optional[str] = Field(None, description='identifier')
    attach_company: Optional[str] = Field(None, description='attach company')
    attach_dept: Optional[str] = Field(None, description='attach dept')
    cust_name: Optional[str] = Field(None, description='customer name')
    dopt_name: Optional[str] = Field(None, description='depot name')
    factory_name: Optional[str] = Field(None, description='factory name')
    repair_level: Optional[str] = Field(None, description='repair level')
    life_cycle_time: Optional[date] = Field(None, description='life cycle time')
    repair_level_num: Optional[int] = Field(None, description='repair level number')
    date_source: Optional[str] = Field(None, description='data source')
    sync_time: Optional[date] = Field(None, description='sync time')


class CreateDespatchParam(DespatchSchemaBase):
    pass


class GetDespatchParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str = Field(..., description='product model')
    product_config_code: Optional[str] = Field(None, description='product config code')
    identifier: str = Field(..., description='product identifier')
    repair_level: str = Field(..., description='repair level')
    life_cycle_time: date = Field(..., description='life cycle time')
    repair_level_num: Optional[int] = Field(None, description='repair level number')


class GetDespatchDetails(GetDespatchParam):
    model_config = ConfigDict(from_attributes=True)

    attach_company: Optional[str] = Field(None, description='attach company')
    attach_dept: Optional[str] = Field(None, description='attach dept')
    cust_name: Optional[str] = Field(None, description='customer name')
    dopt_name: Optional[str] = Field(None, description='depot name')
    factory_name: Optional[str] = Field(None, description='factory name')
    date_source: Optional[str] = Field(None, description='data source')
    sync_time: Optional[date] = Field(None, description='sync time')


class GetDespatchListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetDespatchDetails] = Field(default_factory=list, description='query result list')
    total: int = Field(default=0, ge=0, description='total count')
