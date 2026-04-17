#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : spare_statistics.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : 备件统计Schema定义
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class FilterModelPartRequest(SchemaBase):
    """筛选产品+派生码+零部件组合请求参数。"""

    input_date: date = Field(..., description="拟合输入日期")
    min_failure_count: int = Field(10, description="最小故障数量阈值，默认10")


class ModelPartItem(SchemaBase):
    """产品+派生码+零部件组合项。"""

    model: str = Field(..., description="产品型号")
    product_config_code: Optional[str] = Field(None, description="派生码")
    part: str = Field(..., description="零部件物料编码")
    failure_count: int = Field(..., description="故障数量")


class FilterModelPartResponse(SchemaBase):
    """筛选产品+派生码+零部件组合响应。"""

    total: int = Field(..., description="符合条件的组合总数")
    items: List[ModelPartItem] = Field(..., description="组合列表")


class PredictSpareRequest(SchemaBase):
    """预计备件数量批量计算请求参数。"""

    model_part_list: List[ModelPartItem] = Field(
        ..., description="产品+派生码+零部件组合列表"
    )
    input_date: date = Field(..., description="拟合输入日期")
    start_date: date = Field(..., description="计算开始日期")
    end_date: date = Field(..., description="计算结束日期")
    distribution_type: Optional[str] = Field(None, description="分布类型")
    method: Optional[str] = Field(None, description="拟合方法")
    check: Optional[str] = Field(None, description="拟合优度检验")
    source: Optional[bool] = Field(False, description="拟合来源，默认False")


class FailureCountRequest(SchemaBase):
    """实际故障数量批量统计请求参数。"""

    model_part_list: List[ModelPartItem] = Field(
        ..., description="产品+派生码+零部件组合列表"
    )
    input_date: date = Field(..., description="拟合输入日期")
    start_date: date = Field(..., description="统计开始日期")
    end_date: date = Field(..., description="统计结束日期")


class TaskResponse(SchemaBase):
    """任务启动响应。"""

    task_id: str = Field(..., description="Celery任务ID")
    message: str = Field(..., description="提示信息")


class SpareStatisticsResultDetails(SchemaBase):
    """备件统计计算结果详情。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="主键ID")
    task_id: str = Field(..., description="Celery任务ID")
    task_type: str = Field(..., description="任务类型: prediction/failure_count")
    model: str = Field(..., description="产品型号")
    product_config_code: Optional[str] = Field(None, description="派生码")
    part: str = Field(..., description="零部件物料编码")
    part_name: Optional[str] = Field(None, description="零部件名称")
    input_date: date = Field(..., description="拟合输入日期")
    start_date: date = Field(..., description="计算开始日期")
    end_date: date = Field(..., description="计算结束日期")
    predicted_spare_num: Optional[float] = Field(
        None, description="预计备件数量（精确小数）"
    )
    predicted_spare_num_int: Optional[int] = Field(
        None, description="预计备件数量（取整整数）"
    )
    actual_failure_num: Optional[int] = Field(None, description="实际故障数量")
    distribution_type: Optional[str] = Field(None, description="分布类型")
    method: Optional[str] = Field(None, description="拟合方法")
    check: Optional[str] = Field(None, description="拟合优度检验")
    source: Optional[bool] = Field(None, description="拟合来源")
    calculation_status: str = Field(..., description="计算状态: success/failed")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_time: datetime = Field(..., description="创建时间")
    updated_time: Optional[datetime] = Field(None, description="更新时间")


class SpareStatisticsResultFilter(SchemaBase):
    """备件统计结果查询过滤参数。"""

    task_id: Optional[str] = Field(None, description="任务ID")
    task_type: Optional[str] = Field(
        None, description="任务类型: prediction/failure_count"
    )
    model: Optional[str] = Field(None, description="产品型号")
    product_config_code: Optional[str] = Field(None, description="派生码")
    part: Optional[str] = Field(None, description="零部件物料编码")
    input_date: Optional[date] = Field(None, description="拟合输入日期")
    start_date: Optional[date] = Field(None, description="计算开始日期")
    end_date: Optional[date] = Field(None, description="计算结束日期")
    calculation_status: Optional[str] = Field(None, description="计算状态")


class SpareStatisticsResultListResponse(SchemaBase):
    """备件统计结果列表响应。"""

    total: int = Field(..., description="总数")
    items: List[SpareStatisticsResultDetails] = Field(..., description="结果列表")
