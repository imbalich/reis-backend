#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : statistics.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : 备件统计API接口
"""

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Query

from backend.app.calcu.crud.crud_spare_statistics_result import (
    spare_statistics_result_dao,
)
from backend.app.calcu.schema.spare_statistics import (
    FailureCountRequest,
    FilterModelPartRequest,
    FilterModelPartResponse,
    ModelPartItem,
    PredictSpareRequest,
    SpareStatisticsResultDetails,
    TaskResponse,
)
from backend.app.calcu.service.spare_statistics_service import spare_statistics_service
from backend.app.task.tasks.spare_statistics_task.tasks import (
    failure_count_batch_task,
    spare_prediction_batch_task,
)
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.database.db import CurrentSession

router = APIRouter()


@router.post("/filter", summary="筛选符合条件的产品+派生码+零部件组合")
async def filter_model_part_combinations(
    request: FilterModelPartRequest,
) -> ResponseSchemaModel[FilterModelPartResponse]:
    combinations = await spare_statistics_service.filter_model_part_combinations(
        input_date=request.input_date,
        min_failure_count=request.min_failure_count,
    )

    items = [
        ModelPartItem(
            model=model,
            product_config_code=product_config_code,
            part=part,
            failure_count=failure_count,
        )
        for model, product_config_code, part, failure_count in combinations
    ]
    return response_base.success(
        data=FilterModelPartResponse(total=len(items), items=items)
    )


@router.post("/predict", summary="启动预计备件数量批量计算任务")
async def start_prediction_task(
    request: PredictSpareRequest,
) -> ResponseSchemaModel[TaskResponse]:
    model_part_tuples = [
        (item.model, item.product_config_code, item.part)
        for item in request.model_part_list
    ]

    task = spare_prediction_batch_task.delay(
        model_part_list=model_part_tuples,
        input_date=request.input_date.isoformat(),
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
        distribution_type=request.distribution_type,
        method=request.method,
        check=request.check,
        source=request.source,
    )

    return response_base.success(
        data=TaskResponse(
            task_id=task.id,
            message=f"预计备件数量计算任务已启动，共 {len(model_part_tuples)} 个组合",
        )
    )


@router.post("/failure-count", summary="启动实际故障数量批量统计任务")
async def start_failure_count_task(
    request: FailureCountRequest,
) -> ResponseSchemaModel[TaskResponse]:
    model_part_tuples = [
        (item.model, item.product_config_code, item.part)
        for item in request.model_part_list
    ]

    task = failure_count_batch_task.delay(
        model_part_list=model_part_tuples,
        input_date=request.input_date.isoformat(),
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
    )

    return response_base.success(
        data=TaskResponse(
            task_id=task.id,
            message=f"实际故障数量统计任务已启动，共 {len(model_part_tuples)} 个组合",
        )
    )


@router.get("/result", summary="查询备件统计计算结果", dependencies=[DependsPagination])
async def get_statistics_result(
    db: CurrentSession,
    task_id: Annotated[Optional[str], Query(description="任务ID")] = None,
    task_type: Annotated[
        Optional[str], Query(description="任务类型: prediction/failure_count")
    ] = None,
    model: Annotated[Optional[str], Query(description="产品型号")] = None,
    product_config_code: Annotated[Optional[str], Query(description="派生码")] = None,
    part: Annotated[Optional[str], Query(description="零部件物料编码")] = None,
    input_date: Annotated[Optional[date], Query(description="拟合输入日期")] = None,
    start_date: Annotated[Optional[date], Query(description="计算开始日期")] = None,
    end_date: Annotated[Optional[date], Query(description="计算结束日期")] = None,
    calculation_status: Annotated[
        Optional[str], Query(description="计算状态: success/failed")
    ] = None,
) -> ResponseSchemaModel[PageData[SpareStatisticsResultDetails]]:
    select_stmt = await spare_statistics_result_dao.get_select(
        task_id=task_id,
        task_type=task_type,
        model=model,
        product_config_code=product_config_code,
        part=part,
        input_date=input_date,
        start_date=start_date,
        end_date=end_date,
        calculation_status=calculation_status,
    )

    page_data = await paging_data(db, select_stmt)
    return response_base.success(data=page_data)
