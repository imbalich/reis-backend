#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project 锛歠astapi-base-backend
@File    锛歘_init__.py.py
@IDE     锛歅yCharm
@Author  锛歩mbalich
@Date    锛?024/12/25 16:39
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.schema.failure import GetFailureDetails
from backend.app.datamanage.service.failure_service import failure_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession

router = APIRouter()


@router.get('/product_lifetime_stage', summary='鑾峰彇鏁呴殰鏁版嵁鎵€鏈変骇鍝佸鍛介樁娈?')
async def get_failure_product_lifetime_stage() -> ResponseModel:
    models = await failure_service.get_product_lifetime_stage()
    return response_base.success(data=models)


@router.get('/fault_mode', summary='鑾峰彇鏁呴殰鏁版嵁鎵€鏈夌粓鍒ゆ晠闅滄ā寮?')
async def get_failure_fault_mode() -> ResponseModel:
    models = await failure_service.get_fault_mode()
    return response_base.success(data=models)


@router.get('/product_model', summary='鑾峰彇鏁呴殰鏁版嵁鎵€鏈変骇鍝佸瀷鍙?')
async def get_failure_product_model() -> ResponseModel:
    models = await failure_service.get_product_model()
    return response_base.success(data=models)


@router.get('/dimension-pairs', summary='鑾峰彇鏁呴殰鏁版嵁鐨勪骇鍝佸瀷鍙峰拰閰嶇疆缂栫爜缁勫悎')
async def get_failure_product_dimension_pairs() -> ResponseModel:
    pairs = await failure_service.get_product_dimension_pairs()
    return response_base.success(data=pairs)


@router.get('/fault_location', summary='鏍规嵁閫夊畾鐨勪骇鍝佸瀷鍙疯幏鍙栧搴旂殑鏁呴殰閮ㄤ綅')
async def get_failure_fault_location_by_product_model(
    product_model: Annotated[str | None, Query()] = None,
    product_config_code: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    models = await failure_service.get_fault_location_by_product_model(
        product_model=product_model, product_config_code=product_config_code
    )
    return response_base.success(data=models)


@router.get('/parts', summary='鏍规嵁浜у搧鍨嬪彿鍜岄厤缃紪鐮佽幏鍙栭儴浠朵唬鐮?')
async def get_failure_parts_by_model(
    product_model: Annotated[str | None, Query()] = None,
    product_config_code: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    parts = await failure_service.get_parts_by_model(
        product_model=product_model, product_config_code=product_config_code
    )
    return response_base.success(data=parts)


@router.get('', summary='锛堟ā绯婃潯浠讹級鍒嗛〉鑾峰彇鎵€鏈夋晠闅滄暟鎹?, dependencies=[DependsPagination])
async def get_pagination_failure(
    db: CurrentSession,
    product_model: Annotated[str | None, Query()] = None,
    product_config_code: Annotated[str | None, Query()] = None,
    fault_location: Annotated[str | None, Query()] = None,
    product_lifetime_stage: Annotated[str | None, Query()] = None,
    product_number: Annotated[str | None, Query()] = None,
    fault_mode: Annotated[str | None, Query()] = None,
    time_range: Annotated[list[str] | None, Query()] = None,
    is_zero_distance: Annotated[int | None, Query()] = None,
    is_company: Annotated[int | None, Query()] = None,
    fault_material_code: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetFailureDetails]]:
    failure_select = await failure_service.get_select(
        product_model=product_model,
        product_config_code=product_config_code,
        fault_location=fault_location,
        product_lifetime_stage=product_lifetime_stage,
        product_number=product_number,
        fault_mode=fault_mode,
        time_range=time_range,
        is_zero_distance=is_zero_distance,
        is_company=is_company,
        fault_material_code=fault_material_code,
    )
    page_data = await paging_data(db, failure_select)
    return response_base.success(data=page_data)
