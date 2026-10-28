#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import date

from pydantic import ConfigDict, Field

from backend.app.fit.schema.fit_param import FitMethodType
from backend.common.schema import SchemaBase


class PartFitCurvesParam(SchemaBase):
    """单个零部件拟合入参。input_date 是拟合截止日期，只使用该日之前的故障。"""

    model: str = Field(description="产品型号")
    part: str = Field(description="零部件物料编码")
    product_config_code: str | None = Field(None, description="派生码，空值按 PS00")
    input_date: str = Field(description="拟合截止日期")
    method: FitMethodType = Field(FitMethodType.MLE, description="拟合方法")


class PartCurveResult(SchemaBase):
    """一条候选寿命曲线。一次拟合会返回多条。"""

    model_config = ConfigDict(from_attributes=True)

    group_id: str = Field(description="同一次拟合的分组")
    model: str = Field(description="产品型号")
    product_config_code: str | None = Field(None, description="派生码")
    part: str = Field(description="零部件物料编码")
    input_date: date = Field(description="拟合截止日期")
    method: str = Field(description="拟合方法")
    distribution: str = Field(description="分布名称")
    alpha: float | None = None
    beta: float | None = None
    gamma: float | None = None
    alpha_1: float | None = None
    beta_1: float | None = None
    alpha_2: float | None = None
    beta_2: float | None = None
    proportion_1: float | None = None
    ds: float | None = None
    mu: float | None = None
    sigma: float | None = None
    lambda_: float | None = None
    log_likelihood: float | None = None
    aicc: float | None = None
    bic: float | None = None
    ad: float | None = None
    optimizer: str | None = None
    source: bool = Field(description="False 为系统生成，True 为按指定截止日期拟合")


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
