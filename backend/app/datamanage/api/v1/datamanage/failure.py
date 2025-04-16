#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend
@File    ：__init__.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/25 16:39
'''

from typing import Annotated, List

from fastapi import APIRouter, Query

from backend.app.datamanage.schema.failure import GetFailureDetails
from backend.common.pagination import paging_data, DependsPagination, PageData
from backend.app.datamanage.service.failure_service import failure_service
from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel
from backend.database.db import CurrentSession

router = APIRouter()

"""
接口需求:
1.获取故障数据中所有产品寿命阶段的接口：用于支持前端的下拉框选择
2.获取故障数据中所有的终判故障模式的接口：用于支持前端的下拉选择
3.获取故障数据中所有产品型号的接口：用于支持前端的下拉选择
4.获取故障数据中根据选定的产品型号获取对应的故障部位列表的接口：用于支持前端的级联选择
5.（模糊条件）分页获取所有故障数据
"""


@router.get('/product_lifetime_stage', summary='获取故障数据所有产品寿命阶段')
async def get_failure_product_lifetime_stage() -> ResponseModel:
    models = await failure_service.get_product_lifetime_stage()
    return response_base.success(data=models)


@router.get('/fault_mode', summary='获取故障数据所有终判故障模式')
async def get_failure_fault_mode() -> ResponseModel:
    models = await failure_service.get_fault_mode()
    return response_base.success(data=models)


@router.get('/product_model', summary='获取故障数据所有产品型号')
async def get_failure_product_model() -> ResponseModel:
    models = await failure_service.get_product_model()
    return response_base.success(data=models)


@router.get('/fault_location', summary='根据选定的产品型号获取对应的故障部位')
async def get_failure_fault_location_by_product_model(
        product_model: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    models = await failure_service.get_fault_location_by_product_model(product_model=product_model)
    return response_base.success(data=models)


@router.get('', summary='（模糊条件）分页获取所有故障数据', dependencies=[DependsPagination])
async def get_pagination_failure(
        db: CurrentSession,
        product_model: Annotated[str | None, Query()] = None,
        fault_location: Annotated[str | None, Query()] = None,
        product_lifetime_stage: Annotated[str | None, Query()] = None,
        product_number: Annotated[str | None, Query()] = None,
        fault_mode: Annotated[str | None, Query()] = None,
        time_range: Annotated[list[str] | None, Query()] = None,
        is_zero_distance: Annotated[int | None, Query()] = None,
        fault_material_code: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetFailureDetails]]:
    '''
    param db: 数据库会话
    param product_model: 产品型号
    param fault_location: 故障部位
    param product_lifetime_stage: 产品寿命阶段
    param product_number: 产品编号
    param fault_mode: 故障模式
    param time_range: 时间范围
    param is_zero_distance: 是否为零距离
    param fault_material_code: 终判故障部位物料编码
    return: 故障数据列表
    '''
    failure_select = await failure_service.get_select(
        product_model=product_model,
        fault_location=fault_location,
        product_lifetime_stage=product_lifetime_stage,
        product_number=product_number,
        fault_mode=fault_mode,
        time_range=time_range,
        is_zero_distance=is_zero_distance,
        fault_material_code=fault_material_code
    )
    page_data = await paging_data(db, failure_select)
    return response_base.success(data=page_data)
