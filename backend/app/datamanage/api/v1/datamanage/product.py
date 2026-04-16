#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project 锛歠astapi-base-backend
@File    锛歱roduct.py
@IDE     锛歅yCharm
@Author  锛歩mbalich
@Date    锛?024/1/16 14:40
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.schema.product import GetProductDetails
from backend.app.datamanage.service.product_service import product_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession

router = APIRouter()


@router.get('/models', summary='鑾峰彇浜у搧鏁版嵁涓墍鏈夊瀷鍙风殑鎺ュ彛')
async def get_product_models() -> ResponseModel:
    models = await product_service.get_models()
    return response_base.success(data=models)


@router.get('/dimension-pairs', summary='鑾峰彇浜у搧鍨嬪彿鍜岄厤缃紪鐮佺粍鍚?')
async def get_product_dimension_pairs() -> ResponseModel:
    pairs = await product_service.get_product_dimension_pairs()
    return response_base.success(data=pairs)


@router.get('', summary='锛堟ā绯婃潯浠讹級鍒嗛〉鑾峰彇鎵€鏈変骇鍝佷俊鎭暟鎹?, dependencies=[DependsPagination])
async def get_pagination_product(
    db: CurrentSession,
    model: Annotated[str | None, Query()] = None,
    product_config_code: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetProductDetails]]:
    product_select = await product_service.get_select(
        model=model, product_config_code=product_config_code
    )
    page_data = await paging_data(db, product_select)
    return response_base.success(data=page_data)
