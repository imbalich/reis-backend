#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.fit.schema.fit_param import (
    CreateFitAllPartInParam,
    CreateFitPartInParam,
    FitCheckType,
    FitMethodType,
)
from backend.app.fit_aaron.service.part_fit_service import part_fit_service
from backend.app.fit_aaron.service.part_strategy_service import part_strategy_service
from backend.app.task.tasks.fit_task.tasks import part_fit_all_task, part_fit_aaron_task
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.get("/tag", summary="????: ???????????-Aaron")
async def part_tag_aaron(
    model: str = Query(..., description="????"),
    part: str = Query(..., description="?????"),
    product_config_code: Annotated[str | None, Query(description="???")] = None,
    input_date: Annotated[str | None, Query(description="??????")] = None,
):
    tags = await part_strategy_service.part_tag_process(
        model,
        part,
        input_date,
        product_config_code=product_config_code,
    )
    return response_base.success(data=tags)


@router.post("/fit/swagger", summary="????: ?????????????-Aaron??????")
async def part_create_fit_aaron(obj: CreateFitPartInParam):
    await part_fit_service.create(obj=obj)
    return response_base.success()


@router.post("/fit", summary="????: ?????????????-Aaron???????")
async def part_create_fit_task_aaron(obj: CreateFitPartInParam):
    # Aaron?2026-07-31???Aaron???????Aaron??Celery??
    # ????????????fit.service.part_fit_service????data_result?tags??
    # ???????fit-aaron?? -> part_fit_aaron_task -> fit_aaron.service.part_fit_service
    task = part_fit_aaron_task.delay(
        obj.model,
        obj.part,
        obj.input_date,
        obj.method,
        obj.product_config_code,
    )
    return response_base.success(
        data={
            "task_id": task.id,
            "task_name": part_fit_aaron_task.name,
            "message": "?????",
        }
    )


@router.post("/fit-all", summary="????: ?????????????-Aaron???????")
async def part_create_fit_all_task_aaron(obj: CreateFitAllPartInParam):
    task = part_fit_all_task.delay(obj.input_date, obj.method)
    return response_base.success(
        data={
            "task_id": task.id,
            "task_name": part_fit_all_task.name,
            "message": "?????",
        }
    )


@router.get("/fit", summary="????: ???????????????-Aaron")
async def part_get_fits_aaron(
    model: str = Query(..., description="????"),
    part: str = Query(..., description="?????"),
    product_config_code: Annotated[str | None, Query(description="???")] = None,
    method: Annotated[FitMethodType | None, Query(description="????")] = FitMethodType.MLE,
    input_date: Annotated[str | None, Query(description="??????")] = None,
    check: Annotated[FitCheckType | None, Query(description="??????")] = FitCheckType.BIC,
    source: Annotated[bool, Query(description="?????False ??????True ??????")] = False,
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


@router.get("/fit/best-one", summary="????: ???????????????-Aaron")
async def part_get_best_fit_aaron(
    model: str = Query(..., description="????"),
    part: str = Query(..., description="?????"),
    product_config_code: Annotated[str | None, Query(description="???")] = None,
    input_date: Annotated[str | None, Query(description="??????")] = None,
    method: Annotated[FitMethodType | None, Query(description="????")] = FitMethodType.MLE,
    check: Annotated[FitCheckType | None, Query(description="??????")] = FitCheckType.BIC,
    source: Annotated[bool, Query(description="?????False ??????True ??????")] = False,
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
