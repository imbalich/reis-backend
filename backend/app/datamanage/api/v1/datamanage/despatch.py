#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：despatch.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/25 16:40
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.schema.despatch import GetDespatchDetails
from backend.app.datamanage.service.despatch_service import despatch_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession

router = APIRouter()

"""
接口需求:
1.获取发运数据中所有型号的接口：用于支持前端的下拉框选择
2.获取发运数据中所有修理级别的接口：用于支持前端的下拉框选择
3.（模糊条件）分页获取所有发运数据
"""


@router.get('/models', summary='获取发运数据中所有型号')
async def get_despatch_models() -> ResponseModel:
    models = await despatch_service.get_models()
    return response_base.success(data=models)


@router.get('/repair-levels', summary='获取发运数据中所有修理级别')
async def get_despatch_repair_levels() -> ResponseModel:
    repair_levels = await despatch_service.get_repair_levels()
    return response_base.success(data=repair_levels)


@router.get('', summary='（模糊条件）分页获取所有发运数据', dependencies=[DependsPagination])
async def get_pagination_despatch(
    db: CurrentSession,
    model: Annotated[str | None, Query()] = None,
    identifier: Annotated[str | None, Query()] = None,
    repair_level: Annotated[str | None, Query()] = None,
    time_range: Annotated[list[str] | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetDespatchDetails]]:
    despatch_select = await despatch_service.get_select(
        model=model, identifier=identifier, repair_level=repair_level, time_range=time_range
    )
    page_data = await paging_data(db, despatch_select)
    return response_base.success(data=page_data)
