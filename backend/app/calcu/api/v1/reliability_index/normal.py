#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
@Project : reis-backend
@File    : normal.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/4/22 14:52
'''

from fastapi import APIRouter, Query

from backend.app.calcu.service.reliability_index_service import reliability_index_service
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.get('/fpmh', summary='产品故障率')
async def fpmh(
        model: str = Query(..., description='产品型号'),
        part: str | None = Query(None, description='零部件物料编码'),
        t: float | None = Query(None, description='时间'),
):
    # 先获取分布
    result = await reliability_index_service.get_fpmh(model, part, t)
    return response_base.success(data=result)
