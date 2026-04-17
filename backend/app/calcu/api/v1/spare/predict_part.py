#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : predict_part.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/28 14:36
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.calcu.schema.distribute_param import DistributeType
from backend.app.calcu.service.spare_service import spare_service
from backend.app.fit.schema.fit_param import FitCheckType, FitMethodType
from backend.common.response.response_schema import response_base

router = APIRouter()


def _parse_distribution(distribution: str | None) -> DistributeType | None:
    if distribution in ("", None):
        return None
    try:
        return DistributeType(distribution)
    except ValueError:
        return None


def _parse_method(method: str | None) -> FitMethodType:
    if method in ("", None):
        return FitMethodType.MLE
    try:
        return FitMethodType(method)
    except ValueError:
        return FitMethodType.MLE


def _parse_check(check: str | None) -> FitCheckType:
    if check in ("", None):
        return FitCheckType.BIC
    try:
        return FitCheckType(check)
    except ValueError:
        return FitCheckType.BIC


@router.get("/predict", summary="零部件级别: 单型号单零部件预测")
async def part_spare_predict(
    model: str = Query(..., description="产品型号"),
    part: str = Query(..., description="零部件物料编码"),
    product_config_code: Annotated[str | None, Query(description="派生码")] = None,
    distribution: Annotated[str | None, Query(description="分布类型")] = None,
    method: Annotated[str | None, Query(description="拟合方法")] = None,
    check: Annotated[str | None, Query(description="拟合优度检验")] = None,
    input_date: Annotated[str | None, Query(description="计算截止日期")] = None,
    start_date: Annotated[str | None, Query(description="计算起始日期")] = None,
    end_date: Annotated[str | None, Query(description="计算结束日期")] = None,
    source: Annotated[bool | None, Query(description="拟合来源，默认系统生成")] = False,
):
    spare_num = await spare_service.get_part_spare_num(
        model=model,
        part=part,
        product_config_code=product_config_code,
        distribution_type=_parse_distribution(distribution),
        method=_parse_method(method),
        check=_parse_check(check),
        input_date=input_date,
        start_date=start_date,
        end_date=end_date,
        source=source,
    )
    return response_base.success(data=spare_num)


@router.get("/predict-all", summary="零部件级别: 单型号全零部件预测")
async def parts_spare_predict(
    model: str = Query(..., description="产品型号"),
    product_config_code: Annotated[str | None, Query(description="派生码")] = None,
    distribution: Annotated[str | None, Query(description="分布类型")] = None,
    method: Annotated[str | None, Query(description="拟合方法")] = None,
    check: Annotated[str | None, Query(description="拟合优度检验")] = None,
    input_date: Annotated[str | None, Query(description="计算截止日期")] = None,
    start_date: Annotated[str | None, Query(description="计算起始日期")] = None,
    end_date: Annotated[str | None, Query(description="计算结束日期")] = None,
    source: Annotated[bool | None, Query(description="拟合来源，默认系统生成")] = False,
):
    results = await spare_service.get_all_parts_spare_num_by_model(
        model=model,
        product_config_code=product_config_code,
        distribution_type=_parse_distribution(distribution),
        method=_parse_method(method),
        check=_parse_check(check),
        input_date=input_date,
        start_date=start_date,
        end_date=end_date,
        source=source,
    )
    return response_base.success(data=results)
