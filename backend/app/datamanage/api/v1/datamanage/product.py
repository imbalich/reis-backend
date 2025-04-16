#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend
@File    ：product.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/1/16 16:40
'''
from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.schema.product import GetProductDetails
from backend.app.datamanage.service.product_service import product_service
from backend.common.pagination import paging_data, DependsPagination, PageData
from backend.common.response.response_schema import response_base, ResponseModel, ResponseSchemaModel
from backend.database.db import CurrentSession

router = APIRouter()

"""
接口需求:
1. 获取产品数据中所有型号的接口：用于支持前端的下拉框选择
2.（模糊条件）分页获取所有产品信息数据
"""


@router.get('/models', summary='获取产品数据中所有型号的接口')
async def get_product_models() -> ResponseModel:
    models = await product_service.get_models()
    return response_base.success(data=models)


@router.get('', summary='（模糊条件）分页获取所有产品信息数据', dependencies=[DependsPagination])
async def get_pagination_product(
        db: CurrentSession,
        model: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetProductDetails]]:
    '''
    param db: 数据库会话
    param model: 产品型号
    return: 产品信息列表
    '''
    product_select = await product_service.get_select(model=model)
    page_data = await paging_data(db, product_select)
    return response_base.success(data=page_data)
