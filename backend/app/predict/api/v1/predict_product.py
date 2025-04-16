#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : predict_product.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/28 14:33
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.fit.schema.fit_param import FitCheckType, FitMethodType
from backend.app.predict.schema.distribute_param import DistributeType
from backend.app.predict.service.distribute_service import distribute_service
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.get('/spare-predict', summary='整机级别:预测')
async def product_spare_predict(
    model: str = Query(..., description='产品型号'),
    distribution: Annotated[DistributeType | None, Query(description='分布类型')] = None,
    method: Annotated[FitMethodType | None, Query(description='拟合方法')] = FitMethodType.MLE,
    check: Annotated[FitCheckType | None, Query(description='拟合优度检验')] = FitCheckType.BIC,
    input_date: Annotated[str | None, Query(description='计算截止日期')] = None,
    start_date: Annotated[str | None, Query(description='计算起始日期')] = None,
    end_date: Annotated[str | None, Query(description='计算截止日期')] = None,
):
    spare_num = await distribute_service.get_product_spare_num(
        model, distribution, method, check, input_date, start_date, end_date
    )
    return response_base.success(data=spare_num)
