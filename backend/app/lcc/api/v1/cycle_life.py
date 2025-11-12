#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：cycle_life.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/10 09:48
"""

from typing import Annotated
import json
from fastapi import APIRouter, Query

from backend.common.response.response_schema import response_base
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.app.lcc.schema.cycle_life_service import CycleLifeTotalSchemaBase
from backend.app.lcc.service.cycle_life_service import cycle_life_service

router = APIRouter()

@router.get('', summary='获取产品生命周期计算结果')
async def get_cycle_life_result(
    items: str = Query(..., description='产品生命周期数据，JSON格式的列表字符串'),
    life : Annotated[int | None, Query(description='计算截止日期')] = 30,
) -> ResponseSchemaModel[CycleLifeTotalSchemaBase]:
    # 将字符串转换为 list[dict] 类型
    items_list = json.loads(items)
    data = await cycle_life_service.get_cycle_life_result(items_list, life)
    return response_base.success(data=data)


@router.get('/get_parts', summary='获取所有部件')
async def get_cycle_life_parts(model: str):
    result = await cycle_life_service.get_parts_by_model(model=model)
    return response_base.success(data=result)
