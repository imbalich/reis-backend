#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.schema.product import GetProductDetails
from backend.app.datamanage.service.product_service import product_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import (
    ResponseModel,
    ResponseSchemaModel,
    response_base,
)
from backend.database.db import CurrentSession

router = APIRouter()


@router.get('/models', summary='获取产品型号列表')
async def get_product_models() -> ResponseModel:
    models = await product_service.get_models()
    return response_base.success(data=models)


@router.get('/dimension-pairs', summary='获取产品型号和派生码组合')
async def get_product_dimension_pairs() -> ResponseModel:
    pairs = await product_service.get_product_dimension_pairs()
    return response_base.success(data=pairs)


@router.get('/by-model/{model}', summary='根据型号和派生码获取产品运行参数')
async def get_product_runtime_params_by_model(
    model: str,
    product_config_code: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    year_days, avg_worktime, avg_speed = await product_service.get_run_time_parameters(
        model=model,
        product_config_code=product_config_code,
    )
    return response_base.success(
        data={
            'year_days': year_days,
            'avg_worktime': avg_worktime,
            'avg_speed': avg_speed,
        }
    )


@router.get('', summary='分页获取产品数据', dependencies=[DependsPagination])
async def get_pagination_product(
    db: CurrentSession,
    model: Annotated[str | None, Query()] = None,
    product_config_code: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetProductDetails]]:
    product_select = await product_service.get_select(
        model=model,
        product_config_code=product_config_code,
    )
    page_data = await paging_data(db, product_select)
    return response_base.success(data=page_data)
