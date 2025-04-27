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

from backend.app.calcu.schema.distribute_param import DistributeType
from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.calcu.service.reliability_index_service import reliability_index_service
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.get('/fpmh', summary='产品故障率')
async def fpmh(
        model: str = Query(..., description='产品型号'),
        part: str | None = Query(None, description='零部件物料编码'),
        t: float | None = Query(None, description='时间'),
        distribution: DistributeType | None = Query(None, description='分布类型'),
):
    if distribution:
        distribution_obj = await distribute_service.get_distribution(model, part, distribution)
        if distribution_obj:
            result = await reliability_index_service.get_fpmh(model, part, t, distribution_obj)
            return response_base.success(data=result)
    result = await reliability_index_service.get_fpmh(model, part, t)
    return response_base.success(data=result)
