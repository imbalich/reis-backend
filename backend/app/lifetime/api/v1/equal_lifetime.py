#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：equal_lifetime.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/15 14:03
"""

from backend.app.lifetime.schema.lifetime_param import CreateEuqalLifetimeInParam,CreateEuqalLifetimeAllPartInParam
from backend.app.lifetime.service.equal_lifetime_service import equal_lifetime_service
from typing import Annotated
from fastapi import APIRouter, Query

from backend.common.response.response_schema import response_base
from backend.app.task.tasks.lifetime_task.tasks import equal_lifetime_task,equal_lifetime_all_task

router = APIRouter()

@router.post('/swagger', summary='等寿命设计-->仅调试使用')
async def lifetime_optimize(obj: CreateEuqalLifetimeInParam):
    await equal_lifetime_service.create(obj=obj)
    return response_base.success()

@router.post('/swagger_new', summary='等寿命设计-->仅调试使用')
async def lifetime_optimize_new(obj: CreateEuqalLifetimeInParam):
    await equal_lifetime_service.create(obj=obj)
    return response_base.success()


@router.post('', summary='等寿命设计-->后台任务执行')
async def lifetime_optimize_task(obj: CreateEuqalLifetimeInParam):
    # 移除了 await 关键字delay() 方法会立即返回一个 AsyncResult 对象，而不会阻塞当前的异步函数。
    # 任务会在后台异步执行，而 API 会立即返回任务 ID 和其他相关信息
    task = equal_lifetime_task.delay(obj.model, obj.parts, obj.target_sf, obj.step_start, obj.step_end)
    return response_base.success(data={'task_id': task.id, 'task_name': equal_lifetime_task.name, 'message': '任务已提交'})

@router.post('/fit-all', summary='等寿命设计: 创建多型号+全部零部件数据优化-->后台任务执行')
async def lifetime_optimize_all_task(obj: CreateEuqalLifetimeAllPartInParam):
    # 移除了 await 关键字delay() 方法会立即返回一个 AsyncResult 对象，而不会阻塞当前的异步函数。
    # 任务会在后台异步执行，而 API 会立即返回任务 ID 和其他相关信息
    task = equal_lifetime_all_task.delay(obj.target_sf, obj.step_start, obj.step_end)
    return response_base.success(
        data={'task_id': task.id, 'task_name': equal_lifetime_all_task.name, 'message': '任务已提交'}
    )

@router.get('', summary='获取等寿命结果')
async def  get_equal_lifetime_result(
    model: str = Query(..., description='产品型号'),
    # parts: list[str] = Query(..., description='零部件名称'),
    parts: Annotated[list[str] | None, Query(description='零部件名称')] = None,
    target_sf: Annotated[float | None, Query(description='寿命目标值')] = 0.90,
    step_start: Annotated[float | None, Query(description='步长开始值')] = 0.90,
    step_end: Annotated[float | None, Query(description='步长结束值')] = 0.99,
):
    """
    获取单个产品型号的拟合结果
    """
    results = await equal_lifetime_service.get_optimize_result(model, parts,target_sf,step_start,step_end)
    return response_base.success(data=results)


@router.get('/models', summary='获取所有型号')
async def get_all_models_by_fitpart():
    result = await equal_lifetime_service.get_all_models()
    return response_base.success(data=result)

@router.get('/parts', summary='获取所有零部件')
async def get_all_parts_by_fitpart(model: str):
    result = await equal_lifetime_service.get_all_parts(model)
    return response_base.success(data=result)