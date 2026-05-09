#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : fit_part.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/19 17:14
"""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.fit.schema.fit_param import (
    CreateFitAllPartInParam,
    CreateFitModelAllPartInParam,
    CreateFitPartInParam,
    FitCheckType,
    FitMethodType,
)
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.task.tasks.fit_task.tasks import (
    part_fit_all_task,
    part_fit_model_all_task,
    part_fit_task,
)
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.get("/tag", summary="零部件级别: 单型号单零部件标签处理")
async def part_tag(
    model: str = Query(..., description="产品型号"),
    part: str = Query(..., description="零部件名称"),
    product_config_code: Annotated[str | None, Query(description="派生码")] = None,
    input_date: Annotated[str | None, Query(description="计算截止日期")] = None,
):
    tags = await part_strategy_service.part_tag_process(
        model,
        part,
        input_date,
        product_config_code=product_config_code,
    )
    return response_base.success(data=tags)


@router.post("/fit/swagger", summary="零部件级别: 创建单型号单零部件数据拟合，仅调试使用")
async def part_create_fit(obj: CreateFitPartInParam):
    await part_fit_service.create(obj=obj)
    return response_base.success()


@router.post("/fit", summary="零部件级别: 创建单型号单零部件数据拟合，后台任务执行")
async def part_create_fit_task(obj: CreateFitPartInParam):
    task = part_fit_task.delay(
        obj.model,
        obj.part,
        obj.input_date,
        obj.method,
        obj.product_config_code,
    )
    return response_base.success(
        data={
            "task_id": task.id,
            "task_name": part_fit_task.name,
            "message": "任务已提交",
        }
    )


@router.post("/fit-all", summary="零部件级别: 创建多型号全零部件数据拟合，后台任务执行")
async def part_create_fit_all_task(obj: CreateFitAllPartInParam):
    task = part_fit_all_task.delay(obj.input_date, obj.method)
    return response_base.success(
        data={
            "task_id": task.id,
            "task_name": part_fit_all_task.name,
            "message": "任务已提交",
        }
    )


@router.post("/fit-model-all", summary="零部件级别: 创建单型号全零部件数据拟合，后台任务执行")
async def part_create_fit_model_all_task(obj: CreateFitModelAllPartInParam):
    task = part_fit_model_all_task.delay(
        obj.model,
        obj.input_date,
        obj.method,
        obj.product_config_code,
    )
    return response_base.success(
        data={
            "task_id": task.id,
            "task_name": part_fit_model_all_task.name,
            "message": "任务已提交",
        }
    )


@router.get("/fit", summary="零部件级别: 获取单型号单零部件数据拟合结果")
async def part_get_fits(
    model: str = Query(..., description="产品型号"),
    part: str = Query(..., description="零部件名称"),
    product_config_code: Annotated[str | None, Query(description="派生码")] = None,
    method: Annotated[FitMethodType | None, Query(description="拟合方法")] = FitMethodType.MLE,
    input_date: Annotated[str | None, Query(description="计算截止日期")] = None,
    check: Annotated[FitCheckType | None, Query(description="拟合优度检验")] = FitCheckType.BIC,
    source: Annotated[bool, Query(description="数据来源，False 为系统默认，True 为用户自定义")] = False,
):
    results = await part_fit_service.get_by_model_and_part(
        model,
        part,
        input_date,
        method,
        check,
        source,
        product_config_code=product_config_code,
    )
    return response_base.success(data=results)


@router.get("/fit/best-one", summary="零部件级别: 获取单型号单零部件最优拟合结果")
async def part_get_best_fit(
    model: str = Query(..., description="产品型号"),
    part: str = Query(..., description="零部件名称"),
    product_config_code: Annotated[str | None, Query(description="派生码")] = None,
    input_date: Annotated[str | None, Query(description="计算截止日期")] = None,
    method: Annotated[FitMethodType | None, Query(description="拟合方法")] = FitMethodType.MLE,
    check: Annotated[FitCheckType | None, Query(description="拟合优度检验")] = FitCheckType.BIC,
    source: Annotated[bool, Query(description="数据来源，False 为系统默认，True 为用户自定义")] = False,
):
    results = await part_fit_service.get_best_by_model_and_part(
        model,
        part,
        input_date,
        method,
        check,
        source,
        product_config_code=product_config_code,
    )
    return response_base.success(data=results)


@router.get("/fit/equivalent_lamda", summary="零部件级别: 获取单型号单零部件等效故障率结果")
async def part_get_equivalent_lamda(
    model: str = Query(..., description="产品型号"),
    part: str = Query(..., description="零部件名称"),
    product_config_code: Annotated[str | None, Query(description="派生码")] = None,
    input_time1: str = Query(..., description="输入日期1"),
    input_time2: str = Query(..., description="输入日期2"),
):
    results = await part_fit_service.get_equivalent_lamda(
        model,
        part,
        input_time1,
        input_time2,
        product_config_code=product_config_code,
    )
    return response_base.success(data=results)
