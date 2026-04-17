#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : fastapi-base-backend
@File    : ebom.py
"""

from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class EbomSchemaBase(SchemaBase):
    id: Optional[str] = Field(None, description='primary key id')
    partid: Optional[str] = Field(None, description='parent node id')
    level1: Optional[str] = Field(None, description='level number')
    sync_time: Optional[str] = Field(None, description='sync time')
    prd_no: Optional[str] = Field(None, description='product model')
    product_config_code: Optional[str] = Field(None, description='product config code')
    prd_name: Optional[str] = Field(None, description='product name')
    prd_level: Optional[str] = Field(None, description='product level')
    prd_vision: Optional[str] = Field(None, description='product version')
    y8_matbnum1: Optional[str] = Field(None, description='part code')
    y8_matname: Optional[str] = Field(None, description='part name')
    bl_quantity: Optional[str] = Field(None, description='quantity')
    state_now: Optional[str] = Field(None, description='enabled flag')


class CreateEbomParam(EbomSchemaBase):
    pass


class GetEbomParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description='primary key id')
    partid: Optional[str] = Field(None, description='parent node id')
    level1: Optional[str] = Field(None, description='level number')
    prd_no: Optional[str] = Field(None, description='product model')
    product_config_code: Optional[str] = Field(None, description='product config code')


class GetEbomDetails(GetEbomParam):
    model_config = ConfigDict(from_attributes=True)

    sync_time: Optional[str] = Field(None, description='sync time')
    prd_name: Optional[str] = Field(None, description='product name')
    prd_level: Optional[str] = Field(None, description='product level')
    prd_vision: Optional[str] = Field(None, description='product version')
    y8_matbnum1: Optional[str] = Field(None, description='part code')
    y8_matname: Optional[str] = Field(None, description='part name')
    bl_quantity: Optional[str] = Field(None, description='quantity')
    state_now: Optional[str] = Field(None, description='enabled flag')


class GetEbomListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetEbomDetails] = Field(default_factory=list, description='query result list')
    total: int = Field(default=0, ge=0, description='total count')
