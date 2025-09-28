#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class ScienceWarehouseRequest(SchemaBase):
    """科学库存计算请求参数"""

    time_interval_days: int = Field(180, description="需求预测时间间隔（天数）")
    input_date: Optional[date] = Field(None, description="计算截止日期")


class ScienceWarehouseResultItem(SchemaBase):
    """科学库存计算结果项"""

    factor: str = Field(..., description="库房编码")
    code: str = Field(..., description="备品编码")
    warehouse: str = Field(..., description="库房名称")
    part: str = Field(..., description="备品编码")
    number: int = Field(..., description="需求数量")


class ScienceWarehouseCalculationResponse(SchemaBase):
    """科学库存计算响应"""

    model_config = ConfigDict(from_attributes=True)

    calculation_id: str = Field(..., description="计算批次ID")
    statistics: Dict[str, Any] = Field(..., description="统计信息")
    calculation_period: Dict[str, Any] = Field(..., description="计算周期信息")


class ScienceWarehouseApiResponse(SchemaBase):
    """科学库存API格式响应"""

    data: List[ScienceWarehouseResultItem] = Field(..., description="计算结果列表")


class ScienceWarehouseDetailsResponse(SchemaBase):
    """科学库存详细结果响应"""

    calculation_id: str = Field(..., description="计算批次ID")
    results: Dict[str, Any] = Field(..., description="详细计算结果")
    statistics: Dict[str, Any] = Field(..., description="统计信息")


class ScienceWarehouseStatistics(SchemaBase):
    """科学库存计算统计信息"""

    total_warehouse_spares: int = Field(..., description="总库房备品数量")
    calculated_spares: int = Field(..., description="成功计算的备品数量")
    default_spares: int = Field(..., description="使用默认数量的备品数量")
    skipped_failures_count: int = Field(..., description="跳过的故障数量")
    mapping_errors_count: int = Field(..., description="映射错误数量")
    time_interval_days: int = Field(..., description="时间间隔（天）")
    input_date: date = Field(..., description="计算截止日期")
    calculation_summary: Optional[Dict[str, Any]] = Field(None, description="计算摘要")
    created_time: date = Field(..., description="创建时间")


class ScienceWarehouseResultDetails(SchemaBase):
    """科学库存计算结果详情"""

    calculation_id: str = Field(..., description="计算批次ID")
    warehouse_code: str = Field(..., description="库房编码")
    warehouse_name: str = Field(..., description="库房名称")
    spare_part_code: str = Field(..., description="备品编码")
    spare_part_name: str = Field(..., description="备品名称")
    required_quantity: int = Field(..., description="需求数量")
    calculation_method: str = Field(..., description="计算方法（fitted/default）")
    time_interval_days: int = Field(..., description="时间间隔（天）")
    input_date: date = Field(..., description="计算截止日期")
    created_time: date = Field(..., description="创建时间")
    confidence: float = Field(..., description="置信度")
    coverage_info: Optional[Dict[str, Any]] = Field(None, description="覆盖信息")
    maintenance_analysis: Optional[Dict[str, Any]] = Field(
        None, description="维护责任分析"
    )
    calculation_details: Optional[Dict[str, Any]] = Field(None, description="计算详情")


class ScienceWarehouseFilterParam(SchemaBase):
    """科学库存查询过滤参数"""

    calculation_id: Optional[str] = Field(None, description="计算批次ID")
    warehouse_code: Optional[str] = Field(None, description="库房编码")
    spare_part_code: Optional[str] = Field(None, description="备品编码")
    calculation_method: Optional[str] = Field(None, description="计算方法")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")


class ScienceWarehouseListResponse(SchemaBase):
    """科学库存列表响应"""

    total: int = Field(..., description="总数")
    items: List[ScienceWarehouseResultDetails] = Field(..., description="结果列表")


class ScienceWarehouseBatchRequest(SchemaBase):
    """科学库存批量计算请求"""

    requests: List[ScienceWarehouseRequest] = Field(..., description="计算请求列表")


class ScienceWarehouseBatchResponse(SchemaBase):
    """科学库存批量计算响应"""

    total_requests: int = Field(..., description="总请求数")
    success_requests: int = Field(..., description="成功请求数")
    failed_requests: int = Field(..., description="失败请求数")
    calculation_ids: List[str] = Field(..., description="计算批次ID列表")
    errors: List[str] = Field(default_factory=list, description="错误信息")


class ScienceWarehouseListDetails(SchemaBase):
    """科学库存列表详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="记录ID")
    calculation_id: str = Field(..., description="计算批次ID")
    warehouse_code: str = Field(..., description="库房编码")
    warehouse_name: str = Field(..., description="库房名称")
    spare_part_code: str = Field(..., description="备品编码")
    spare_part_name: str = Field(..., description="备品名称")
    required_quantity: int = Field(..., description="需求数量")
    calculation_method: str = Field(..., description="计算方法")
    time_interval_days: int = Field(..., description="时间间隔（天）")
    input_date: date = Field(..., description="计算截止日期")
    created_time: date = Field(..., description="创建时间")
