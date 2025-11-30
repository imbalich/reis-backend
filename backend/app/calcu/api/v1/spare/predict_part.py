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


@router.get("/predict", summary="部件级别:单型号+单零部件预测")
async def part_spare_predict(
    model: str = Query(..., description="产品型号"),
    part: str = Query(..., description="零部件物料编码"),
    distribution: Annotated[str | None, Query(description="分布类型")] = None,
    method: Annotated[str | None, Query(description="拟合方法")] = None,
    check: Annotated[str | None, Query(description="拟合优度检验")] = None,
    input_date: Annotated[str | None, Query(description="计算截止日期")] = None,
    start_date: Annotated[str | None, Query(description="计算起始日期")] = None,
    end_date: Annotated[str | None, Query(description="计算截止日期")] = None,
    source: Annotated[bool | None, Query(description="拟合来源，默认系统生成")] = False,
):
    # 处理空字符串参数，转换为None或默认值
    if distribution == "" or distribution is None:
        distribution_enum = None
    else:
        try:
            distribution_enum = DistributeType(distribution)
        except ValueError:
            distribution_enum = None

    if method == "" or method is None:
        method_enum = FitMethodType.MLE
    else:
        try:
            method_enum = FitMethodType(method)
        except ValueError:
            method_enum = FitMethodType.MLE

    if check == "" or check is None:
        check_enum = FitCheckType.BIC
    else:
        try:
            check_enum = FitCheckType(check)
        except ValueError:
            check_enum = FitCheckType.BIC

    spare_num = await spare_service.get_part_spare_num(
        model,
        part,
        distribution_enum,
        method_enum,
        check_enum,
        input_date,
        start_date,
        end_date,
        source,
    )
    return response_base.success(data=spare_num)


@router.get("/predict-all", summary="部件级别:单型号+全零部件预测")
async def parts_spare_predict(
    model: str = Query(..., description="产品型号"),
    distribution: Annotated[str | None, Query(description="分布类型")] = None,
    method: Annotated[str | None, Query(description="拟合方法")] = None,
    check: Annotated[str | None, Query(description="拟合优度检验")] = None,
    input_date: Annotated[str | None, Query(description="计算截止日期")] = None,
    start_date: Annotated[str | None, Query(description="计算起始日期")] = None,
    end_date: Annotated[str | None, Query(description="计算截止日期")] = None,
    source: Annotated[bool | None, Query(description="拟合来源，默认系统生成")] = False,
):
    # 处理空字符串参数，转换为None或默认值
    if distribution == "" or distribution is None:
        distribution_enum = None
    else:
        try:
            distribution_enum = DistributeType(distribution)
        except ValueError:
            distribution_enum = None

    if method == "" or method is None:
        method_enum = FitMethodType.MLE
    else:
        try:
            method_enum = FitMethodType(method)
        except ValueError:
            method_enum = FitMethodType.MLE

    if check == "" or check is None:
        check_enum = FitCheckType.BIC
    else:
        try:
            check_enum = FitCheckType(check)
        except ValueError:
            check_enum = FitCheckType.BIC

    results = await spare_service.get_all_parts_spare_num_by_model(
        model,
        distribution_enum,
        method_enum,
        check_enum,
        input_date,
        start_date,
        end_date,
        source,
    )
    return response_base.success(data=results)
