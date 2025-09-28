#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科学库存计算API接口
"""

from typing import List, Dict, Any, Annotated
from fastapi import APIRouter, HTTPException, Query

from backend.app.calcu.schema.science_warehouse import (
    ScienceWarehouseRequest,
    ScienceWarehouseCalculationResponse,
    ScienceWarehouseApiResponse,
    ScienceWarehouseDetailsResponse,
    ScienceWarehouseResultItem,
    ScienceWarehouseListDetails,
)
from backend.app.calcu.service.science_warehouse_service import (
    science_warehouse_service,
)
from backend.app.task.tasks.science_warehouse_task.tasks import (
    science_warehouse_calculation_task,
    science_warehouse_calculation_and_api_task,
)
from backend.common.response.response_schema import (
    ResponseModel,
    ResponseSchemaModel,
    response_base,
    CustomResponse,
)
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.database.db import CurrentSession

router = APIRouter()


@router.post("/calculate", summary="科学库存需求计算-->后台任务执行")
async def calculate_science_warehouse_requirements(
    request: ScienceWarehouseRequest,
) -> ResponseModel:
    """
    提交科学库存需求计算任务到后台执行

    :param request: 计算请求参数
    :return: 任务提交结果（包含任务ID）
    """
    try:
        # 提交后台任务
        task = science_warehouse_calculation_task.delay(
            time_interval_days=request.time_interval_days,
            input_date=request.input_date.isoformat() if request.input_date else None,
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


@router.get("/results/{calculation_id}/api", summary="获取API格式计算结果")
async def get_calculation_results_for_api(
    calculation_id: str,
) -> ResponseSchemaModel[List[ScienceWarehouseResultItem]]:
    """
    根据计算批次ID获取API格式的计算结果

    :param calculation_id: 计算批次ID
    :return: API格式的计算结果列表
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
    根据计算批次ID获取详细计算结果（包含统计信息）

    :param calculation_id: 计算批次ID
    :return: 详细计算结果
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
    获取最新一批次的计算结果，用于前端展示

    :return: 最新批次的计算结果列表
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
    获取最新一批次的详细计算结果，包含更多字段信息

    :return: 最新批次的详细计算结果列表
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
    获取最新一批次的统计信息

    :return: 最新批次的统计信息
    """
    try:
        statistics = await science_warehouse_service.get_latest_calculation_statistics()
        return response_base.success(data=statistics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最新统计信息失败: {str(e)}")


@router.get(
    "/list", summary="分页获取科学库存计算结果", dependencies=[DependsPagination]
)
async def get_pagination_science_warehouse_results(
    db: CurrentSession,
    calculation_id: Annotated[str | None, Query()] = None,
    warehouse_code: Annotated[str | None, Query()] = None,
    warehouse_name: Annotated[str | None, Query()] = None,
    spare_part_code: Annotated[str | None, Query()] = None,
    spare_part_name: Annotated[str | None, Query()] = None,
    calculation_method: Annotated[str | None, Query()] = None,
) -> ResponseSchemaModel[PageData[ScienceWarehouseListDetails]]:
    """
    分页获取科学库存计算结果列表

    :param db: 数据库会话
    :param calculation_id: 计算批次ID
    :param warehouse_code: 库房编码
    :param warehouse_name: 库房名称
    :param spare_part_code: 备品编码
    :param spare_part_name: 备品名称
    :param calculation_method: 计算方法
    :return: 分页的科学库存计算结果列表
    """
    try:
        science_warehouse_select = await science_warehouse_service.get_select(
            calculation_id=calculation_id,
            warehouse_code=warehouse_code,
            warehouse_name=warehouse_name,
            spare_part_code=spare_part_code,
            spare_part_name=spare_part_name,
            calculation_method=calculation_method,
        )
        page_data = await paging_data(db, science_warehouse_select)
        return response_base.success(data=page_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取科学库存结果列表失败: {str(e)}"
        )
