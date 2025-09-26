#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科学库存计算API接口
"""

from fastapi import APIRouter, HTTPException

from backend.app.calcu.schema.science_warehouse import (
    ScienceWarehouseRequest,
    ScienceWarehouseCalculationResponse,
    ScienceWarehouseApiResponse,
    ScienceWarehouseDetailsResponse,
)
from backend.app.calcu.service.science_warehouse_service import (
    science_warehouse_service,
)
from backend.common.response.response_schema import (
    ResponseModel,
    ResponseSchemaModel,
    response_base,
    CustomResponse,
)

router = APIRouter()


@router.post("/calculate", summary="科学库存需求计算")
async def calculate_science_warehouse_requirements(
    request: ScienceWarehouseRequest,
) -> ResponseSchemaModel[ScienceWarehouseCalculationResponse]:
    """
    执行科学库存需求计算

    :param request: 计算请求参数
    :return: 计算结果（包含计算批次ID）
    """
    try:
        # 执行计算并保存到数据库
        result = (
            await science_warehouse_service.calculate_science_warehouse_requirements(
                time_interval_days=request.time_interval_days,
                input_date=request.input_date,
            )
        )

        return response_base.success(data=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")


@router.get("/results/{calculation_id}/api", summary="获取API格式计算结果")
async def get_calculation_results_for_api(
    calculation_id: str,
) -> ResponseSchemaModel[ScienceWarehouseApiResponse]:
    """
    根据计算批次ID获取API格式的计算结果

    :param calculation_id: 计算批次ID
    :return: API格式的计算结果
    """
    try:
        api_data = await science_warehouse_service.get_calculation_results_for_api(
            calculation_id
        )

        response_data = ScienceWarehouseApiResponse(data=api_data)

        return response_base.success(data=response_data)

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


@router.post("/calculate-and-get-api", summary="计算并直接返回API格式结果")
async def calculate_and_get_api_results(
    request: ScienceWarehouseRequest,
) -> ResponseSchemaModel[ScienceWarehouseApiResponse]:
    """
    执行计算并直接返回API格式结果（一次性调用）

    :param request: 计算请求参数
    :return: API格式的计算结果
    """
    try:
        # 1. 执行计算
        result = (
            await science_warehouse_service.calculate_science_warehouse_requirements(
                time_interval_days=request.time_interval_days,
                input_date=request.input_date,
            )
        )

        # 2. 获取API格式数据
        api_data = await science_warehouse_service.get_calculation_results_for_api(
            result.calculation_id
        )

        response_data = ScienceWarehouseApiResponse(data=api_data)

        return response_base.success(data=response_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")
