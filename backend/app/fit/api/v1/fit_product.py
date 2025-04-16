#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：fit_product.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/6 14:34
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.fit.schema.fit_param import (
    CreateFitAllProductInParam,
    CreateFitProductInParam,
    FitCheckType,
    FitMethodType,
)
from backend.app.fit.service.product_fit_service import product_fit_service
from backend.app.fit.service.product_strategy_service import product_strategy_service
from backend.app.task.celery_task.fit_task.tasks import product_fit_all_task, product_fit_task
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.get('/tag', summary='整机级别:单型号删失数据标签处理')
async def product_tag(
    model: str = Query(..., description='产品型号'),
    input_date: Annotated[str | None, Query(description='计算截止日期')] = None,
):
    tags = await product_strategy_service.model_tag_process(model, input_date)
    return response_base.success(data=tags)


@router.post('/fit/swagger', summary='整机级别:创建单型号数据拟合-->仅调试使用')
async def product_create_fit(obj: CreateFitProductInParam):
    await product_fit_service.create(obj=obj)
    return response_base.success()


@router.post('/fit', summary='整机级别:创建单型号数据拟合-->后台任务执行')
async def product_create_fit_task(obj: CreateFitProductInParam):
    # 移除了 await 关键字delay() 方法会立即返回一个 AsyncResult 对象，而不会阻塞当前的异步函数。
    # 任务会在后台异步执行，而 API 会立即返回任务 ID 和其他相关信息
    task = product_fit_task.delay(obj.model, obj.input_date, obj.method)
    return response_base.success(data={'task_id': task.id, 'task_name': product_fit_task.name, 'message': '任务已提交'})


@router.post('/fit-all', summary='整机级别:创建多型号数据拟合-->后台任务执行')
async def product_create_fit_all_task(obj: CreateFitAllProductInParam):
    # 移除了 await 关键字delay() 方法会立即返回一个 AsyncResult 对象，而不会阻塞当前的异步函数。
    # 任务会在后台异步执行，而 API 会立即返回任务 ID 和其他相关信息
    task = product_fit_all_task.delay(obj.input_date, obj.method)
    return response_base.success(
        data={'task_id': task.id, 'task_name': product_fit_all_task.name, 'message': '任务已提交'}
    )


@router.get('/fit', summary='整机级别:获取单型号数据拟合结果')
async def product_get_fits(
    model: str = Query(..., description='产品型号'),
    method: Annotated[FitMethodType | None, Query(description='拟合方法')] = FitMethodType.MLE,
    input_date: Annotated[str | None, Query(description='计算截止日期')] = None,
    check: Annotated[FitCheckType | None, Query(description='拟合优度检验')] = FitCheckType.BIC,
    source: Annotated[bool, Query(description='数据来源，False为系统默认，True为用户自定义')] = False,
):
    """
    获取单个产品型号的拟合结果
    """
    results = await product_fit_service.get_by_model(model, input_date, method, check, source)
    return response_base.success(data=results)


@router.get('/fit/best-one', summary='整机级别:获取单型号最优拟合结果')
async def product_get_best_fit(
    model: str = Query(..., description='产品型号'),
    input_date: Annotated[str | None, Query(description='计算截止日期')] = None,
    method: Annotated[FitMethodType | None, Query(description='拟合方法')] = FitMethodType.MLE,
    check: Annotated[FitCheckType | None, Query(description='拟合优度检验')] = FitCheckType.BIC,
    source: Annotated[bool, Query(description='数据来源，False为系统默认，True为用户自定义')] = False,
):
    """
    获取单个产品型号的最优拟合结果
    """
    results = await product_fit_service.get_best_by_model(model, input_date, method, check, source)
    return response_base.success(data=results)
