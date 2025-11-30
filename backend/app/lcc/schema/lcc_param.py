#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : fit_param.py
@IDE     : PyCharm
@Author  : Seven
@Time    : 2025/2/28 下午3:49
"""


from pydantic import ConfigDict

from backend.common.schema import SchemaBase


class CreateRepairPlanInParam(SchemaBase):
    # 创建等寿命优化信息入参
    model: str
    parts: list[str] | None = None
    # parts: list[str] 
    life: int  = 30
    is_ai: bool = False

# class CreateEuqalLifetimeAllPartInParam(SchemaBase):
#     # 创建多型号等寿命优化信息入参
#     target_sf: float  = 0.95
#     step_start: float = 0.95
#     step_end: float = 0.99

    
class CreateRepairPlanParam(SchemaBase):
    """单个分类的等寿命点参数 - 数据库存储参数"""
    model_config = ConfigDict(from_attributes=True)

    group_id: str
    model: str
    life: int
    is_ai: bool
    part: str  # JSON 格式字符串
    part_name: str 
    level_old: str
    year_new: float
    level_new: str
    lcc_min: float
    sf: float
    lcc_old: float
    lcc_result: str | None = None
    lcc_result_tag: str | None = None
    is_all_parts: bool