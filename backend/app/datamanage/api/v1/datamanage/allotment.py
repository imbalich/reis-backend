#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.datamanage.schema.allotment import GetAllotmentDetails
from backend.app.datamanage.service.allotment_service import allotment_service
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import (
    ResponseModel,
    ResponseSchemaModel,
    response_base,
)
from backend.database.db import CurrentSession

router = APIRouter()

"""
接口需求:
1. 分页获取所有产品配属数据（支持车型、车号、产品型号、派生码、产品编号、一级配属、二级配属模糊查询）
"""


@router.get(
    "",
    summary="分页获取所有产品配属数据",
    dependencies=[DependsPagination],
)
async def get_pagination_allotment(
    db: CurrentSession,
    vehicle_type: Annotated[str | None, Query()] = None,
    vehicle_number: Annotated[str | None, Query()] = None,
    product_model: Annotated[str | None, Query()] = None,
    ps_code: Annotated[str | None, Query()] = None,
    product_number: Annotated[str | None, Query()] = None,
    allotment_one: Annotated[str | None, Query()] = None,
    allotment_two: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[GetAllotmentDetails]]:
    """
    分页获取所有产品配属数据

    :param db: 数据库会话
    :param vehicle_type: 车型
    :param vehicle_number: 车号
    :param product_model: 产品型号
    :param ps_code: 派生码
    :param product_number: 产品编号
    :param allotment_one: 一级配属
    :param allotment_two: 二级配属
    :return: 产品配属数据列表
    """
    allotment_select = await allotment_service.get_select(
        vehicle_type=vehicle_type,
        vehicle_number=vehicle_number,
        product_model=product_model,
        ps_code=ps_code,
        product_number=product_number,
        allotment_one=allotment_one,
        allotment_two=allotment_two,
    )
    page_data = await paging_data(db, allotment_select)
    return response_base.success(data=page_data)
