#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：overhaul.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/26 14:39
"""
from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.service.overhaul_service import overhaul_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base

router = APIRouter()

@router.get('/product_model', summary='获取故障数据所有产品型号')
async def get_overhaul_product_model() -> ResponseModel:
    models = await overhaul_service.get_product_model()
    return response_base.success(data=models)

@router.get('/check_bezier', summary='根据选定的产品型号获取对应的检修项点')
async def get_check_bezier_location_by_product_model(
    product_model: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    models = await overhaul_service.get_check_bezier_by_product_model(product_model=product_model)
    return response_base.success(data=models)

@router.get('/product_no', summary='根据选定的产品型号获取对应的产品编号')
async def get_overhaul_product_no_by_product_model(
    product_model: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    models = await overhaul_service.get_product_no_by_product_model(product_model=product_model)
    return response_base.success(data=models)

