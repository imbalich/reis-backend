#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科学库存计算 API 接口。
"""

from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from backend.app.calcu.schema.science_warehouse import (
    ScienceWarehouseDetailsResponse,
    ScienceWarehouseListDetails,
    ScienceWarehousePushRequest,
    ScienceWarehousePushTaskResponse,
    ScienceWarehouseRequest,
    ScienceWarehouseResultItem,
)
from backend.app.calcu.service.science_warehouse_service import (
    science_warehouse_service,
)
from backend.app.task.tasks.science_warehouse_task.tasks import (
    science_warehouse_calculation_task,
    science_warehouse_push_task,
)
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import (
    ResponseModel,
    ResponseSchemaModel,
    response_base,
)
from backend.database.db import CurrentSession

router = APIRouter()


@router.post("/calculate", summary="科学库存需求计算 -> 后台任务执行")
async def calculate_science_warehouse_requirements(
    request: ScienceWarehouseRequest,
) -> ResponseModel:
    """
    提交科学库存需求计算任务到后台执行。
    """
    try:
        task = science_warehouse_calculation_task.delay(
            time_interval_days=request.time_interval_days,
            input_date=request.input_date.isoformat() if request.input_date else None,
            product_model=request.product_model,
            product_config_code=request.product_config_code,
        )

        return response_base.success(
            data={
                "task_id": task.id,
                "task_name": science_warehouse_calculation_task.name,
                "message": "科学库存计算任务已提交到后台执行",
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"任务提交失败: {str(e)}")


@router.post("/push/{calculation_id}", summary="推送人工审查后的科学库存结果 -> 后台任务执行")
async def push_science_warehouse_results(
    calculation_id: str,
    request: ScienceWarehousePushRequest,
) -> ResponseSchemaModel[ScienceWarehousePushTaskResponse]:
    """
    提交科学库存推送任务到后台执行。
    """
    try:
        task = science_warehouse_push_task.delay(
            calculation_id=calculation_id,
            push_reason=request.push_reason,
        )
        return response_base.success(
            data={
                "task_id": task.id,
                "task_name": science_warehouse_push_task.name,
                "calculation_id": calculation_id,
                "message": "科学库存推送任务已提交",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推送任务提交失败: {str(e)}")


@router.get("/results/{calculation_id}/api", summary="获取 API 格式计算结果")
async def get_calculation_results_for_api(
    calculation_id: str,
) -> ResponseSchemaModel[List[ScienceWarehouseResultItem]]:
    """
    根据计算批次 ID 获取 API 格式的计算结果。
    """
    try:
        api_data = await science_warehouse_service.get_calculation_results_for_api(
            calculation_id
        )
        return response_base.success(data=api_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取结果失败: {str(e)}")


@router.get("/results/{calculation_id}/details", summary="获取详细计算结果")
async def get_calculation_details(
    calculation_id: str,
) -> ResponseSchemaModel[ScienceWarehouseDetailsResponse]:
    """
    根据计算批次 ID 获取详细计算结果。
    """
    try:
        result = await science_warehouse_service.get_calculation_results_by_id(
            calculation_id
        )
        return response_base.success(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取详细结果失败: {str(e)}")


@router.get("/latest-results", summary="获取最新批次计算结果")
async def get_latest_calculation_results() -> (
    ResponseSchemaModel[List[ScienceWarehouseResultItem]]
):
    """
    获取最新一批次的计算结果，用于前端展示。
    """
    try:
        api_data = await science_warehouse_service.get_latest_calculation_results()
        return response_base.success(data=api_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最新结果失败: {str(e)}")


@router.get("/latest-results-detailed", summary="获取最新批次详细计算结果")
async def get_latest_calculation_results_detailed() -> (
    ResponseSchemaModel[List[Dict[str, Any]]]
):
    """
    获取最新一批次的详细计算结果。
    """
    try:
        detailed_data = (
            await science_warehouse_service.get_latest_calculation_results_detailed()
        )
        return response_base.success(data=detailed_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最新详细结果失败: {str(e)}")


@router.get("/latest-statistics", summary="获取最新批次统计信息")
async def get_latest_calculation_statistics() -> ResponseSchemaModel[Dict[str, Any]]:
    """
    获取最新一批次的统计信息。
    """
    try:
        statistics = await science_warehouse_service.get_latest_calculation_statistics()
        return response_base.success(data=statistics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最新统计信息失败: {str(e)}")


@router.get("/warehouses", summary="获取库房编码和名称列表")
async def get_warehouse_code_name_pairs() -> ResponseModel:
    """
    获取库房编码和名称的列表，用于前端下拉选择。
    """
    try:
        pairs = await science_warehouse_service.get_warehouse_code_name_pairs()
        return response_base.success(data=pairs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取库房列表失败: {str(e)}")


@router.get("/spare-parts", summary="根据库房编码获取备品编码和名称列表")
async def get_spare_part_code_name_pairs(
    warehouse_code: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    """
    根据库房编码获取备品编码和名称的列表。
    """
    try:
        pairs = await science_warehouse_service.get_spare_part_code_name_pairs(
            warehouse_code=warehouse_code
        )
        return response_base.success(data=pairs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取备品列表失败: {str(e)}")


@router.get("/calculation-methods", summary="获取所有计算方法")
async def get_calculation_methods() -> ResponseModel:
    """
    获取所有唯一的计算方法，用于前端下拉选择。
    """
    try:
        methods = await science_warehouse_service.get_calculation_methods()
        return response_base.success(data=methods)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取计算方法列表失败: {str(e)}")


@router.get(
    "/list", summary="分页获取科学库存计算结果", dependencies=[DependsPagination]
)
async def get_pagination_science_warehouse_results(
    db: CurrentSession,
    calculation_id: Annotated[str | None, Query()] = None,
    warehouse_code: Annotated[str | None, Query()] = None,
    spare_part_code: Annotated[str | None, Query()] = None,
    calculation_method: Annotated[str | None, Query()] = None,
    time_range: Annotated[list[str] | None, Query()] = None,
) -> ResponseSchemaModel[PageData[ScienceWarehouseListDetails]]:
    """
    分页获取科学库存计算结果列表。
    """
    try:
        science_warehouse_select = await science_warehouse_service.get_select(
            calculation_id=calculation_id,
            warehouse_code=warehouse_code,
            spare_part_code=spare_part_code,
            calculation_method=calculation_method,
            time_range=time_range,
        )
        page_data = await paging_data(db, science_warehouse_select)
        return response_base.success(data=page_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取科学库存结果列表失败: {str(e)}"
        )
