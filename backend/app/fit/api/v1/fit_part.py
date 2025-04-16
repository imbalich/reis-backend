#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : fit_part.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/19 17:14
'''
from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.fit.schema.fit_param import CreateFitPartInParam, CreateFitAllPartInParam, FitMethodType, FitCheckType
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.task.celery_task.fit_task.tasks import part_fit_task, part_fit_all_task
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.get('/tag', summary='部件级别:单型号&单零部件 删失数据标签处理')
async def part_tag(
        model: str = Query(..., description="产品型号"),
        part: str = Query(..., description="零部件名称"),
        input_date: Annotated[str | None, Query(description="计算截止日期")] = None
):
    tags = await part_strategy_service.part_tag_process(model, part, input_date)
    return response_base.success(data=tags)


@router.post('/fit/swagger', summary='部件级别:创建单型号&单零部件数据拟合-->仅调试使用')
async def part_create_fit(obj: CreateFitPartInParam):
    await part_fit_service.create(obj=obj)
    return response_base.success()


@router.post('/fit', summary='部件级别:创建单型号+单零部件数据拟合-->后台任务执行')
async def part_create_fit_task(obj: CreateFitPartInParam):
    # 移除了 await 关键字delay() 方法会立即返回一个 AsyncResult 对象，而不会阻塞当前的异步函数。
    # 任务会在后台异步执行，而 API 会立即返回任务 ID 和其他相关信息
    task = part_fit_task.delay(obj.model, obj.part, obj.input_date, obj.method)
    return response_base.success(data={'task_id': task.id, 'task_name': part_fit_task.name, 'message': '任务已提交'})


@router.post('/fit-all', summary='部件级别:创建多型号+全部零部件数据拟合-->后台任务执行')
async def part_create_fit_all_task(obj: CreateFitAllPartInParam):
    # 移除了 await 关键字delay() 方法会立即返回一个 AsyncResult 对象，而不会阻塞当前的异步函数。
    # 任务会在后台异步执行，而 API 会立即返回任务 ID 和其他相关信息
    task = part_fit_all_task.delay(obj.input_date, obj.method)
    return response_base.success(
        data={'task_id': task.id, 'task_name': part_fit_all_task.name, 'message': '任务已提交'})


@router.get('/fit', summary='部件级别:获取单型号+单零部件数据拟合结果')
async def part_get_fits(
        model: str = Query(..., description="产品型号"),
        part: str = Query(..., description="零部件名称"),
        method: Annotated[FitMethodType | None, Query(description="拟合方法")] = FitMethodType.MLE,
        input_date: Annotated[str | None, Query(description="计算截止日期")] = None,
        check: Annotated[FitCheckType | None, Query(description="拟合优度检验")] = FitCheckType.BIC,
        source: Annotated[bool, Query(description="数据来源，False为系统默认，True为用户自定义")] = False
):
    """
    获取单个产品型号的拟合结果
    """
    results = await part_fit_service.get_by_model_and_part(model, part, input_date, method, check, source)
    return response_base.success(data=results)


@router.get('/fit/best-one', summary='部件级别:获取单型号+单零部件最优拟合结果')
async def part_get_best_fit(
        model: str = Query(..., description="产品型号"),
        part: str = Query(..., description="零部件名称"),
        input_date: Annotated[str | None, Query(description="计算截止日期")] = None,
        method: Annotated[FitMethodType | None, Query(description="拟合方法")] = FitMethodType.MLE,
        check: Annotated[FitCheckType | None, Query(description="拟合优度检验")] = FitCheckType.BIC,
        source: Annotated[bool, Query(description="数据来源，False为系统默认，True为用户自定义")] = False
):
    """
    获取单个产品型号的最优拟合结果
    """
    results = await part_fit_service.get_best_by_model_and_part(model, part, input_date, method, check, source)
    return response_base.success(data=results)
