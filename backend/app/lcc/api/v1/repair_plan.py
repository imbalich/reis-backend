#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：repair_plan.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/10/10 14:09
"""

from fastapi import APIRouter, Query
from backend.app.lifetime.schema.lifetime_param import CreateEuqalLifetimeInParam,CreateEuqalLifetimeAllPartInParam
from backend.app.lifetime.service.equal_lifetime_service import equal_lifetime_service
from typing import Annotated

from backend.common.response.response_schema import response_base
from backend.app.lcc.service.repair_plan_service import repair_plan_service
from backend.app.task.tasks.lifetime_task.tasks import equal_lifetime_task,equal_lifetime_all_task



router = APIRouter()

@router.get('', summary='维修方案结果')
async def  get_repair_plan_result(
    model: str = Query(..., description='产品型号'),
    # parts: list[str] = Query(..., description='零部件名称'),
    parts: Annotated[list[str] | None, Query(description='零部件名称')] = None,
    life: Annotated[float | None, Query(description='寿命目标值')] = 30,
    is_ai: Annotated[bool | None, Query(description='是否考虑可用度')] = False
):
    """
    获取单个产品型号的拟合结果
    """
    results = await repair_plan_service.get_repair_plan(model, parts,life,is_ai)
    return response_base.success(data=results)

