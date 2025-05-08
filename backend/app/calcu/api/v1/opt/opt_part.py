#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : reis-backend
@File    : opt_part.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/5/8 15:42
'''
from fastapi import APIRouter, Query

from backend.common.response.response_schema import response_base

router = APIRouter()


@router.get('', summary='部件最佳维护周期')
async def opt_part(
        model: str = Query(..., description='产品型号'),
        part: str = Query(..., description='零部件物料编码'),
        cm_price: float = Query(..., description='CM价格'),
        pm_price: float = Query(..., description='PM价格'),
):
    data = f"model: {model}, part: {part}, cm_price: {cm_price}, pm_price: {pm_price}"
    return response_base.success(data=data)
