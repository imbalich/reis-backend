#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：ebom.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/1/13 9:10
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.schema.ebom import GetEbomDetails
from backend.app.datamanage.service.ebom_service import ebom_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.database.db import CurrentSession

router = APIRouter()
"""
接口需求:
1. 获取ebom数据中所有型号的接口：用于支持前端的下拉框选择
2.（模糊条件）分页获取所有ebom数据用于前端懒加载树型表
"""


@router.get('/models', summary='获取ebom数据中所有型号')
async def get_ebom_models() -> ResponseModel:
    models = await ebom_service.get_models()
    return response_base.success(data=models)


@router.get('', summary='（模糊条件）分页获取所有ebom数据用于前端懒加载树型表', dependencies=[DependsPagination])
async def get_ebom(
    db: CurrentSession,
    partid: Annotated[str | None, Query()] = None,
    level1: Annotated[int | None, Query()] = None,
    prd_no: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetEbomDetails]]:
    """
    :param db: 数据库会话
    :param partid: 父节点id
    :param level1: 层级序号
    :param prd_no: 产品型号
    :return: ebom数据
    """
    ebom_select = await ebom_service.get_select(partid=partid, level1=level1, prd_no=prd_no)
    page_data = await paging_data(db, ebom_select)
    return response_base.success(data=page_data)
