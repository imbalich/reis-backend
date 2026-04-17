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
    science_warehouse_calculation_v2_task,
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


@router.post("/calculate-v2", summary="科学库存需求计算（新版本）-->后台任务执行")
async def calculate_science_warehouse_requirements_v2(
    request: ScienceWarehouseRequest,
) -> ResponseModel:
    """
    提交科学库存需求计算任务到后台执行（新版本）

    :param request: 计算请求参数
    :return: 任务提交结果（包含任务ID）
    """
    try:
        # 提交新版本后台任务
        task = science_warehouse_calculation_v2_task.delay(
            time_interval_days=request.time_interval_days,
            input_date=request.input_date.isoformat() if request.input_date else None,
            product_model=request.product_model,
            product_config_code=request.product_config_code,
        )

        return response_base.success(
            data={
                "task_id": task.id,
                "task_name": science_warehouse_calculation_v2_task.name,
                "message": "科学库存计算任务（新版本）已提交到后台执行",
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


@router.get("/warehouses", summary="获取库房编码和名称的列表")
async def get_warehouse_code_name_pairs() -> ResponseModel:
    """
    获取库房编码和名称的列表，用于前端下拉框选择
    返回格式: [["库房编码", "库房名称"], ...]

    :return: 库房编码和名称的列表
    """
    try:
        pairs = await science_warehouse_service.get_warehouse_code_name_pairs()
        return response_base.success(data=pairs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取库房列表失败: {str(e)}")


@router.get("/spare-parts", summary="根据库房编码获取备品编码和名称的列表")
async def get_spare_part_code_name_pairs(
    warehouse_code: Annotated[str | None, Query()] = None,
) -> ResponseModel:
    """
    根据库房编码获取备品编码和名称的列表（级联筛选），用于前端下拉框选择
    返回格式: [["备品编码", "备品名称"], ...]

    :param warehouse_code: 库房编码（可选，用于级联筛选）
    :return: 备品编码和名称的列表
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
    获取所有唯一的计算方法，用于前端下拉框选择

    :return: 计算方法列表
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
    product_model: Annotated[str | None, Query()] = None,
    product_config_code: Annotated[str | None, Query()] = None,
    warehouse_code: Annotated[str | None, Query()] = None,
    spare_part_code: Annotated[str | None, Query()] = None,
    calculation_method: Annotated[str | None, Query()] = None,
    time_range: Annotated[list[str] | None, Query()] = None,
) -> ResponseSchemaModel[PageData[ScienceWarehouseListDetails]]:
    """
    分页获取科学库存计算结果列表

    :param db: 数据库会话
    :param calculation_id: 计算批次ID（支持模糊匹配）
    :param warehouse_code: 库房编码（精确匹配）
    :param spare_part_code: 备品编码（精确匹配）
    :param calculation_method: 计算方法（精确匹配）
    :param time_range: 创建时间范围 [开始日期, 结束日期]
    :return: 分页的科学库存计算结果列表
    """
    try:
        science_warehouse_select = await science_warehouse_service.get_select(
            calculation_id=calculation_id,
            product_model=product_model,
            product_config_code=product_config_code,
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
