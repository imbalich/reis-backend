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
    input_date: str | None = Field(None, description="窗口开始日 A，同时作为拟合截止日期")
    end_date: str | None = Field(None, description="窗口结束日 B")


class PartForecastUnit(SchemaBase):
    """一台产品在这次预测里的情况。差值为空表示这台产品被跳过。"""

    product_number: str = Field(description="产品编号")
    online_date: date = Field(description="上线日，发运日与生产日期较早者再加 90 天")
    situation: str = Field(description="窗口前已上线、窗口内上线，或上线晚于窗口结束")
    hours_at_start: float | None = Field(None, description="A 点运行小时。被跳过时为空")
    hours_at_end: float | None = Field(None, description="B 点运行小时。被跳过时为空")
    contribution: float | None = Field(None, description="这台产品乘 BOM 之前的 CDF 差值。被跳过时为空")


class PartForecastTrace(SchemaBase):
    """预测汇总和卡点。调用方可以不使用这些字段，不影响 quantity。"""

    distribution: str = Field(description="选定的分布名称")
    hours_per_day: float = Field(description="每天平均运行小时")
    bom_quantity: int = Field(description="一台产品上该物料的 BOM 用量")
    product_quantity: float = Field(description="乘 BOM 之前，按产品加总的期望次数")
    in_service_count: int = Field(description="窗口前已上线的产品台数")
    entered_during_window_count: int = Field(description="窗口内上线的产品台数")
    skipped_count: int = Field(description="上线晚于窗口结束、被跳过的产品台数")
    notes: list[str] = Field(description="改变结果含义的卡点说明")


class PartForecastResult(SchemaBase):
    """零部件预测结果。quantity 是乘过 BOM 的期望故障次数，可以是小数。"""

    model: str = Field(description="产品型号")
    part: str = Field(description="零部件物料编码")
    product_config_code: str = Field(description="派生码")
    input_date: date = Field(description="窗口开始日")
    end_date: date = Field(description="窗口结束日")
    quantity: float = Field(description="期望故障次数，已乘 BOM 用量")
    unit_count: int = Field(description="参与预测的产品台数，上线日晚于窗口结束日的不计入")
    trace: PartForecastTrace = Field(description="汇总和卡点")
    units: list[PartForecastUnit] = Field(description="每台产品的分类和乘 BOM 前的差值")
