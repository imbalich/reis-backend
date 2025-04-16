#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：replace.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/20 09:41
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.schema.replace import GetReplaceDetails
from backend.app.datamanage.service.replace_service import replace_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession

router = APIRouter()

"""
接口需求:
1. 获取必换件数据中所有型号的接口：用于支持前端的下拉框选择
2.（模糊条件）分页获取所有必换件数据
"""


@router.get('/models', summary='获取必换件数据中所有型号的接口：用于支持前端的下拉框选择')
async def get_replace_model() -> ResponseModel:
    models = await replace_service.get_models()
    return response_base.success(data=models)


@router.get('', summary='（模糊条件）分页获取所有必换件数据', dependencies=[DependsPagination])
async def get_pagination_replace(
    db: CurrentSession, model: Annotated[str | None, Query()] = None, state_now: Annotated[bool | None, Query()] = None
) -> ResponseSchemaModel[PageData[GetReplaceDetails]]:
    """
    :param db: 数据库会话
    :param model: 产品型号
    :param state_now: 当前是否启用
    :return: 必换件列表
    """
    replace_select = await replace_service.get_select(model=model, state_now=state_now)
    page_data = await paging_data(db, replace_select)
    return response_base.success(data=page_data)
