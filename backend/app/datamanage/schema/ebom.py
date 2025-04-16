#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend
@File    ：ebom.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/13 14:56
'''
from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class EbomSchemaBase(SchemaBase):
    id: Optional[str] = Field(None, description='主键id')
    partid: Optional[str] = Field(None, description='父节点')
    level1: Optional[str] = Field(None, description='层级序号')
    sync_time: Optional[str] = Field(None, description='数据解析入库时间')
    prd_no: Optional[str] = Field(None, description='产品型号')
    prd_name: Optional[str] = Field(None, description='产品名称')
    prd_level: Optional[str] = Field(None, description='修造级别')
    y8_knowledgeno: Optional[str] = Field(None, description='结构树编码')
    y8_configurationcode: Optional[str] = Field(None, description='构型编码')
    y8_isbh: Optional[str] = Field(None, description='比偶换件')
    y8_matdescs: Optional[str] = Field(None, description='物料简称')
    item_id: Optional[str] = Field(None, description='产品id')
    state_now: Optional[str] = Field(None, description='当前是否启用，1启用；0未启用,默认为1')


class CreateEbomParam(EbomSchemaBase):
    pass


class GetEbomParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description='主键id')
    partid: str = Field(..., description='父节点')
    level1: int = Field(..., description='层级序号')
    prd_no: str = Field(..., description='产品型号')


class GetEbomDetails(GetEbomParam):
    model_config = ConfigDict(from_attributes=True)

    sync_time: Optional[str] = Field(None, description='数据解析入库时间')
    prd_no: Optional[str] = Field(None, description='产品型号')
    prd_name: Optional[str] = Field(None, description='产品名称')
    prd_level: Optional[str] = Field(None, description='修造级别')
    item_id: Optional[str] = Field(None, description='产品id')
    y8_knowledgeno: Optional[str] = Field(None, description='结构树编码')
    y8_configurationcode: Optional[str] = Field(None, description='构型编码')
    y8_isbh: Optional[str] = Field(None, description='比偶换件')
    y8_matdescs: Optional[str] = Field(None, description='物料简称')
    state_now: Optional[str] = Field(None, description='当前是否启用，1启用；0未启用,默认为1')
    bl_quantity: Optional[str] = Field(None, description='物料总数量')


class GetEbomListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetEbomDetails] = Field(default_factory=list, description="查询结果列表")
    total: int = Field(default=0, ge=0, description="总记录数")
