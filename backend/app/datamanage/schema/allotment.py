#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import date
from typing import Optional

from pydantic import Field

from backend.common.schema import SchemaBase


class AllotmentSchemaBase(SchemaBase):
    """产品配属基础模型"""

    vehicle_type: Optional[str] = Field(None, description="车型")
    vehicle_number: Optional[str] = Field(None, description="车号")
    product_model: Optional[str] = Field(None, description="产品型号")
    ps_code: Optional[str] = Field(None, description="派生码")
    product_number: Optional[str] = Field(None, description="产品编号")
    allotment_one: Optional[str] = Field(None, description="一级配属")
    allotment_two: Optional[str] = Field(None, description="二级配属")
    allotment_date: Optional[date] = Field(None, description="配属日期")


class GetAllotmentDetails(AllotmentSchemaBase):
    """获取产品配属详情"""

    id: int = Field(..., description="产品配属ID")
    created_time: Optional[date] = Field(None, description="创建时间")
    updated_time: Optional[date] = Field(None, description="更新时间")


class AllotmentFilterParam(SchemaBase):
    """产品配属查询过滤参数"""

    vehicle_type: Optional[str] = Field(None, description="车型")
    vehicle_number: Optional[str] = Field(None, description="车号")
    product_model: Optional[str] = Field(None, description="产品型号")
    ps_code: Optional[str] = Field(None, description="派生码")
    product_number: Optional[str] = Field(None, description="产品编号")
    allotment_one: Optional[str] = Field(None, description="一级配属")
    allotment_two: Optional[str] = Field(None, description="二级配属")


class GetAllotmentListResponse(SchemaBase):
    """获取产品配属列表响应"""

    total: int = Field(..., description="总数")
    items: list[GetAllotmentDetails] = Field(..., description="产品配属列表")
