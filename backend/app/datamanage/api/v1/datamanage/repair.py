#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：repair.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/20 09:38
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.schema.repair import GetRepairDetails
from backend.app.datamanage.service.repair_service import repair_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession

router = APIRouter()

"""
接口需求:
1. 获取造修阶段数据中所有型号的接口：用于支持前端的下拉框选择
2.（模糊条件）分页获取所有造修阶段数据
"""


@router.get('/models', summary='获取造修阶段数据中所有型号')
async def get_repair_models() -> ResponseModel:
    models = await repair_service.get_models()
    return response_base.success(data=models)


@router.get('', summary='（模糊条件）分页获取所有造修阶段数据', dependencies=[DependsPagination])
async def get_pagination_repair(
    db: CurrentSession, model: Annotated[str | None, Query()] = None, state_now: Annotated[bool | None, Query()] = None
) -> ResponseSchemaModel[PageData[GetRepairDetails]]:
    """
    :param db: 数据库会话
    :param model: 型号
    :param state_now: 当前是否启用
    :return: 造修阶段数据
    """
    repair_select = await repair_service.get_select(model=model, state_now=state_now)
    page_data = await paging_data(db, repair_select)
    return response_base.success(data=page_data)
