#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：degrade_product.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/20 18:08
"""
from typing import Annotated
from fastapi import APIRouter,Query

from backend.app.degrade.service.product_fit_service import product_fit_service
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.get('/degrade', summary='参数退化评估函数')
async def fit_get_degrade(
        product_model: str = Query(..., description="产品型号"),
        check_bezier: str = Query(..., description="检验项点"),
        failure_threshold: Annotated[str | None, Query(description='失效阈值')] = None,
        product_no: Annotated[str | None, Query(description='产品编号')] = None
):
    """
    获取单个产品型号下单个零部件的敏感度排序结果
    """
    results = await product_fit_service.product_fit(product_model, check_bezier,failure_threshold,product_no)
    return response_base.success(data=results)