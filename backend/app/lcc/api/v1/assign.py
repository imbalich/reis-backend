#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：assign.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/10 09:48
"""

from typing import Annotated
import json
from fastapi import APIRouter, Query

from backend.common.response.response_schema import response_base
from backend.app.lcc.service.assign_service import assign_service
from backend.app.lcc.service.assign_compare_service import assign_compare_service

router = APIRouter()

@router.get('', summary='可靠性经济性分配结果')
async def get_assgin_result(
    items: str = Query(..., description='可靠性指标分配数据，JSON格式的列表字符串'),
    fpmh_user : Annotated[float, Query(description='用户要求的FPMH值')]= None,
    yan_cost : Annotated[float, Query(description='研发费')]= None,
    shou_cost : Annotated[float, Query(description='整机售价')]= None,
    lirun_ratio : Annotated[float, Query(description='利润率')]= 10,
    reserved_value : Annotated[float | None, Query(description='预留值')] = 0.2, 
):
    # 将字符串转换为 list[dict] 类型
    items_list = json.loads(items)
    # 调用服务层方法获取结果
    result = await assign_service.get_assign_result(
        items=items_list,
        fpmh_user=fpmh_user,
        yan_cost=yan_cost,
        shou_cost=shou_cost,
        lirun_ratio=lirun_ratio,
        reserved_value=reserved_value
    )
    return response_base.success(data=result)


@router.get('/assign_compare', summary='可靠性经济性分配结果')
async def get_assgin_commpare(
    items1: str = Query(..., description='可靠性指标分配数据，JSON格式的列表字符串'),
    items2: str = Query(..., description='可靠性指标分配数据，JSON格式的列表字符串'),
    fpmh_user : Annotated[float, Query(description='用户要求的FPMH值')]= None,
    yan_cost : Annotated[float, Query(description='研发费')]= None,
    shou_cost : Annotated[float, Query(description='整机售价')]= None,
    lirun_ratio : Annotated[float, Query(description='利润率')]= 10,
    order: Annotated[int, Query(description='订单数量')]= None,
    reserved_value : Annotated[float | None, Query(description='预留值')] = 0.2, 
):
    # 将字符串转换为 list[dict] 类型
    items_list1 = json.loads(items1)
    items_list2 = json.loads(items2)
    # 调用服务层方法获取结果
    result = await assign_compare_service.get_assign_compare(
        items1=items_list1,
        items2=items_list2,
        fpmh_user=fpmh_user,
        yan_cost=yan_cost,
        shou_cost=shou_cost,
        lirun_ratio=lirun_ratio,
        order=order,
        reserved_value=reserved_value
    )
    return response_base.success(data=result)