#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : fastapi-base-backend
@File    : repair.py
"""

from datetime import date
from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class RepairSchemaBase(SchemaBase):
    id_repair: Optional[int] = Field(None, description='repair order')
    repair_levels: Optional[str] = Field(None, description='repair level')
    model: Optional[str] = Field(None, description='product model')
    product_config_code: Optional[str] = Field(None, description='product config code')
    creator: Optional[str] = Field(None, description='creator')
    create_time: Optional[date] = Field(None, description='create time')
    state_now: bool = Field(default=True, description='enabled flag')


class CreateRepairParam(RepairSchemaBase):
    pass


class GetRepairParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str = Field(..., description='product model')
    product_config_code: Optional[str] = Field(None, description='product config code')


class GetRepairDetails(GetRepairParam):
    model_config = ConfigDict(from_attributes=True)

    id_repair: Optional[int] = Field(None, description='repair order')
    repair_levels: Optional[str] = Field(None, description='repair level')
    creator: Optional[str] = Field(None, description='creator')
    create_time: Optional[date] = Field(None, description='create time')
    state_now: bool = Field(default=True, description='enabled flag')


class GetRepairListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetRepairDetails] = Field(default_factory=list, description='query result list')
    total: int = Field(default=0, ge=0, description='total count')
