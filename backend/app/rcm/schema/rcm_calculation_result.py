#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : rcm_calculation_result.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : RCM计算结果Schema定义
"""

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class RcmCalculationListDetails(SchemaBase):
    """RCM计算结果列表详情 - 用于分页查询"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="结果ID")
    base_data_id: int = Field(..., description="RCM基础数据ID")
    product_model: str = Field(..., description="产品型号")
    component_name: str = Field(..., description="部件名称")
    component_material_code: str = Field(..., description="零部件物料编码")
    failure_mode: Optional[str] = Field(None, description="故障模式")
    final_result: str = Field(..., description="最终计算结果")
    calculation_status: str = Field(..., description="计算状态")
    calculation_process: Optional[str] = Field(None, description="计算过程记录")
    error_message: Optional[str] = Field(None, description="错误信息")
    calculation_time: datetime = Field(..., description="计算时间")
    created_time: datetime = Field(..., description="创建时间")
    updated_time: datetime = Field(..., description="更新时间")
