#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import date

from pydantic import Field

from backend.common.schema import SchemaBase


class PartForecastParam(SchemaBase):
    """零部件预测入参。分布和标签由服务按型号、件号、截止日期读取，不在这里传入库存或库房。"""

    model: str = Field(description="产品型号")
    part: str = Field(description="零部件物料编码")
    product_config_code: str | None = Field(None, description="派生码，空值按 PS00")
    input_date: str | None = Field(None, description="窗口开始日，同时作为拟合截止日期")
    end_date: str | None = Field(None, description="窗口结束日")


class PartForecastResult(SchemaBase):
    """零部件预测结果。quantity 是期望故障次数，可以是小数。"""

    model: str = Field(description="产品型号")
    part: str = Field(description="零部件物料编码")
    product_config_code: str = Field(description="派生码")
    input_date: date = Field(description="窗口开始日")
    end_date: date = Field(description="窗口结束日")
    quantity: float = Field(description="期望故障次数")
    unit_count: int = Field(description="参与预测的在役零件位置数")
