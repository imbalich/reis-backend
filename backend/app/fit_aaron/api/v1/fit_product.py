#!/usr/bin/env python
# -*- coding: UTF-8 -*-

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
from backend.app.task.tasks.fit_task.tasks import product_fit_all_task, product_fit_task
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.get("/tag", summary="????: ???????-Aaron")
async def product_tag_aaron(
    model: str = Query(..., description="????"),
    product_config_code: Annotated[str | None, Query(description="???")] = None,
    input_date: Annotated[str | None, Query(description="??????")] = None,
):
    tags = await product_strategy_service.model_tag_process(
        model,
        input_date,
        product_config_code=product_config_code,
    )
    return response_base.success(data=tags)


@router.post("/fit/swagger", summary="????: ?????????-Aaron??????")
async def product_create_fit_aaron(obj: CreateFitProductInParam):
    await product_fit_service.create(obj=obj)
    return response_base.success()


@router.post("/fit", summary="????: ?????????-Aaron???????")
async def product_create_fit_task_aaron(obj: CreateFitProductInParam):
    task = product_fit_task.delay(
        obj.model,
        obj.input_date,
        obj.method,
        obj.product_config_code,
    )
    return response_base.success(
        data={
            "task_id": task.id,
            "task_name": product_fit_task.name,
            "message": "?????",
        }
    )


@router.post("/fit-all", summary="????: ?????????-Aaron???????")
async def product_create_fit_all_task_aaron(obj: CreateFitAllProductInParam):
    task = product_fit_all_task.delay(obj.input_date, obj.method)
    return response_base.success(
        data={
            "task_id": task.id,
            "task_name": product_fit_all_task.name,
            "message": "?????",
        }
    )


@router.get("/fit", summary="????: ???????????-Aaron")
async def product_get_fits_aaron(
    model: str = Query(..., description="????"),
    product_config_code: Annotated[str | None, Query(description="???")] = None,
    method: Annotated[FitMethodType | None, Query(description="????")] = FitMethodType.MLE,
    input_date: Annotated[str | None, Query(description="??????")] = None,
    check: Annotated[FitCheckType | None, Query(description="??????")] = FitCheckType.BIC,
    source: Annotated[bool, Query(description="?????False ??????True ??????")] = False,
):
    results = await product_fit_service.get_by_model(
        model,
        input_date,
        method,
        check,
        source,
        product_config_code=product_config_code,
    )
    return response_base.success(data=results)


@router.get("/fit/best-one", summary="????: ???????????-Aaron")
async def product_get_best_fit_aaron(
    model: str = Query(..., description="????"),
    product_config_code: Annotated[str | None, Query(description="???")] = None,
    input_date: Annotated[str | None, Query(description="??????")] = None,
    method: Annotated[FitMethodType | None, Query(description="????")] = FitMethodType.MLE,
    check: Annotated[FitCheckType | None, Query(description="??????")] = FitCheckType.BIC,
    source: Annotated[bool, Query(description="?????False ??????True ??????")] = False,
):
    results = await product_fit_service.get_best_by_model(
        model,
        input_date,
        method,
        check,
        source,
        product_config_code=product_config_code,
    )
    return response_base.success(data=results)
