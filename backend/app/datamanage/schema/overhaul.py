#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：overhaul.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/26 14:43
"""
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：repair.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/20 09:38
"""

from datetime import date
from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class OverhaulSchemaBase(SchemaBase):
    product_model: Optional[str] = Field(None, description='产品型号')
    product_no: Optional[str] = Field(None, description='产品编号')
    repair_level: Optional[str] = Field(None, description='修造级别')
    repair_time: Optional[date] = Field(None, description='检修时间')
    check_bezier: Optional[str] = Field(None, description='检修项点')
    check_value: Optional[str] = Field(None, description='检修结果')
    beizhu: Optional[str] = Field(None, description='备注')
    shuoming: Optional[str] = Field(None, description='说明')


class CreateRepairParam(OverhaulSchemaBase):
    pass


class GetOverhaulParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_model: str = Field(..., description='产品型号')


class GetRepairDetails(GetOverhaulParam):
    model_config = ConfigDict(from_attributes=True)

    product_no: Optional[str] = Field(None, description='产品编号')
    repair_level: Optional[str] = Field(None, description='修造级别')
    repair_time: Optional[date] = Field(None, description='检修时间')
    check_bezier: Optional[str] = Field(None, description='检修项点')
    check_value: Optional[str] = Field(None, description='检修结果')
    beizhu: Optional[str] = Field(None, description='备注')
    shuoming: Optional[str] = Field(None, description='说明')


class GetOverhaulListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetRepairDetails] = Field(default_factory=list, description='查询结果列表')
    total: int = Field(default=0, ge=0, description='总记录数')
