#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : reis-backend
@File    : opt_param.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/5/8 16:50
'''
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from backend.common.schema import SchemaBase


class OptPartParam(SchemaBase):
    """部件最佳更换周期模型"""

    model: str = Field(description='产品型号')
    part: str = Field(description='零部件物料编码')
    cm_price: float = Field(description='修复性维修CM价格')
    pm_price: float = Field(description='预防性维修PM价格')

    @model_validator(mode='after')
    def check_cm_gt_pm(self) -> 'OptPartParam':
        if self.cm_price <= self.pm_price:
            raise ValueError('cm_price必须大于pm_price')
        return self

    @field_validator('pm_price', 'cm_price', mode='before')
    @classmethod
    def prices_must_be_non_negative(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('价格必须大于等于0')
        return v
