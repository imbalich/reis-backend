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

from backend.app.calcu.schema.opt_param import OptPartParam
from backend.app.calcu.service.opt_service import opt_service
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.post('', summary='部件最佳维护周期')
async def opt_part(obj: OptPartParam):
    result = await opt_service.get_opt_part_with_plots(obj=obj)
    return response_base.success(data=result)

@router.get('/models', summary='获取所有型号')
async def get_all_models():
    result = await opt_service.get_all_models()
    return response_base.success(data=result)

@router.get('/parts', summary='获取所有零部件')
async def get_all_parts(model: str):
    result = await opt_service.get_all_parts(model)
    return response_base.success(data=result)