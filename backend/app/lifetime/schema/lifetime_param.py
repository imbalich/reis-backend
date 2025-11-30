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


class CreateEuqalLifetimeInParam(SchemaBase):
    # 创建等寿命优化信息入参
    model: str
    parts: list[str] | None = None
    target_sf: float  = 0.95
    step_start: float = 0.95
    step_end: float = 0.99

class CreateEuqalLifetimeAllPartInParam(SchemaBase):
    # 创建多型号等寿命优化信息入参
    target_sf: float  = 0.95
    step_start: float = 0.95
    step_end: float = 0.99


# class CreateEqualLifetimeParam(SchemaBase):
#     model_config = ConfigDict(from_attributes=True)

#     group_id: str
#     model: str
#     part: str
#     target_sf: float
#     time_point: float
#     step_start: float
#     step_end: float
#     need_optimization: bool
#     # equal_lifetime_point: tuple | None = None
#     equal_lifetime_t: float | None = None
#     equal_lifetime_sf: float | None = None
#     distribution: str| None = None
#     original_sf: float | None = None
#     optimized_sf: float | None = None
#     original_pdf: float | None = None
#     optimized_pdf: float | None = None
#     original_equal_point_pdf: float | None = None
#     optimized_equal_point_pdf: float | None = None
#     alpha: float | None = None
#     beta: float | None = None
#     gamma: float | None = None
#     alpha_1: float | None = None
#     beta_1: float | None = None
#     alpha_2: float | None = None
#     beta_2: float | None = None
#     proportion_1: float | None = None
#     ds: float | None = None
#     mu: float | None = None
#     sigma: float | None = None
#     lambda_: float | None = None

    
class CreateEqualLifetimeParam(SchemaBase):
    """单个分类的等寿命点参数 - 数据库存储参数"""
    model_config = ConfigDict(from_attributes=True)

    group_id: str
    model: str
    parts: str  # JSON 格式字符串
    category: str  # 'A', 'B', 'C'
    part_count: int
    sf_at_time_point: float | None = None
    is_all_parts: bool
    target_sf: float
    time_point: int
    step_start: float
    step_end: float
    equal_lifetime_t: int | None = None
    equal_lifetime_sf: float | None = None
    equal_lifetime_t_year: str | None = None
    status: str = 'completed'
    reason: str | None = None


class EqualLifetimeClassificationResponse(SchemaBase):
    """分类后的等寿命点响应 - API返回参数"""
    model_config = ConfigDict(from_attributes=True)
    
    category: str
    parts: list[str]
    part_count: int
    sf_range_start: float
    sf_range_end: float
    sf_at_time_point: float
    equal_lifetime_t: int | None
    equal_lifetime_sf: float | None
    status: str
    reason: str | None


class LifetimeAnalysisResponse(SchemaBase):
    """完整的分类分析响应"""
    model_config = ConfigDict(from_attributes=True)
    
    model: str
    total_parts: int
    category_a: EqualLifetimeClassificationResponse | None
    category_b: EqualLifetimeClassificationResponse | None
    category_c: EqualLifetimeClassificationResponse | None