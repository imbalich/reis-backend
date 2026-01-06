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

from typing import Annotated, Optional
from datetime import date

from fastapi import APIRouter, Query, Depends
from pydantic import Field

from backend.app.calcu.schema.spare_statistics import (
    FilterModelPartRequest,
    FilterModelPartResponse,
    ModelPartItem,
    PredictSpareRequest,
    FailureCountRequest,
    TaskResponse,
    SpareStatisticsResultFilter,
    SpareStatisticsResultListResponse,
    SpareStatisticsResultDetails,
)
from backend.app.calcu.service.spare_statistics_service import spare_statistics_service
from backend.app.calcu.crud.crud_spare_statistics_result import (
    spare_statistics_result_dao,
)
from backend.app.task.tasks.spare_statistics_task.tasks import (
    spare_prediction_batch_task,
    failure_count_batch_task,
)
from backend.common.response.response_schema import (
    ResponseModel,
    ResponseSchemaModel,
    response_base,
)
from backend.common.pagination import DependsPagination, PageData, paging_data
from backend.database.db import CurrentSession

router = APIRouter()


@router.post("/filter", summary="筛选符合条件的型号+零部件组合")
async def filter_model_part_combinations(
    request: FilterModelPartRequest,
) -> ResponseSchemaModel[FilterModelPartResponse]:
    """
    筛选符合条件的型号+零部件组合
    条件：input_date之前故障个数 >= min_failure_count

    :param request: 筛选请求参数
    :return: 符合条件的组合列表
    """
    combinations = await spare_statistics_service.filter_model_part_combinations(
        input_date=request.input_date, min_failure_count=request.min_failure_count
    )

    items = [
        ModelPartItem(model=model, part=part, failure_count=failure_count)
        for model, part, failure_count in combinations
    ]

    response = FilterModelPartResponse(total=len(items), items=items)
    return response_base.success(data=response)


@router.post("/predict", summary="启动预计备件数量批量计算任务")
async def start_prediction_task(
    request: PredictSpareRequest,
) -> ResponseSchemaModel[TaskResponse]:
    """
    启动预计备件数量批量计算任务
    每次计算都新增记录（保留历史），按 task_id 区分批次

    :param request: 计算请求参数
    :return: 任务ID
    """
    # 转换 model_part_list 为元组列表
    model_part_tuples = [(item.model, item.part) for item in request.model_part_list]

    # 启动后台任务
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

    response = TaskResponse(
        task_id=task.id,
        message=f"预计备件数量计算任务已启动，共 {len(model_part_tuples)} 个组合",
    )
    return response_base.success(data=response)


@router.post("/failure-count", summary="启动实际故障数量批量统计任务")
async def start_failure_count_task(
    request: FailureCountRequest,
) -> ResponseSchemaModel[TaskResponse]:
    """
    启动实际故障数量批量统计任务
    相同条件覆盖更新

    :param request: 统计请求参数
    :return: 任务ID
    """
    # 转换 model_part_list 为元组列表
    model_part_tuples = [(item.model, item.part) for item in request.model_part_list]

    # 启动后台任务
    task = failure_count_batch_task.delay(
        model_part_list=model_part_tuples,
        input_date=request.input_date.isoformat(),
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
    )

    response = TaskResponse(
        task_id=task.id,
        message=f"实际故障数量统计任务已启动，共 {len(model_part_tuples)} 个组合",
    )
    return response_base.success(data=response)


@router.get("/result", summary="查询备件统计计算结果", dependencies=[DependsPagination])
async def get_statistics_result(
    db: CurrentSession,
    task_id: Annotated[Optional[str], Query(description="任务ID")] = None,
    task_type: Annotated[
        Optional[str], Query(description="任务类型: prediction/failure_count")
    ] = None,
    model: Annotated[Optional[str], Query(description="产品型号")] = None,
    part: Annotated[Optional[str], Query(description="零部件物料编码")] = None,
    input_date: Annotated[Optional[date], Query(description="拟合输入日期")] = None,
    start_date: Annotated[Optional[date], Query(description="计算开始日期")] = None,
    end_date: Annotated[Optional[date], Query(description="计算结束日期")] = None,
    calculation_status: Annotated[
        Optional[str], Query(description="计算状态: success/failed")
    ] = None,
) -> ResponseSchemaModel[PageData[SpareStatisticsResultDetails]]:
    """
    查询备件统计计算结果
    支持分页和多条件筛选

    :param db: 数据库会话
    :param task_id: 任务ID
    :param task_type: 任务类型
    :param model: 产品型号
    :param part: 零部件物料编码
    :param input_date: 拟合输入日期
    :param start_date: 计算开始日期
    :param end_date: 计算结束日期
    :param calculation_status: 计算状态
    :return: 分页结果列表
    """
    select_stmt = await spare_statistics_result_dao.get_select(
        task_id=task_id,
        task_type=task_type,
        model=model,
        part=part,
        input_date=input_date,
        start_date=start_date,
        end_date=end_date,
        calculation_status=calculation_status,
    )

    page_data = await paging_data(db, select_stmt)
    return response_base.success(data=page_data)
