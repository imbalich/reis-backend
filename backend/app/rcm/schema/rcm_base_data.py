#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime, date
from typing import Optional, List

from pydantic import Field

from backend.common.schema import SchemaBase


class RcmBaseDataSchemaBase(SchemaBase):
    """RCM基础数据基础Schema"""

    # 基础信息字段
    product_model: Optional[str] = Field(None, description="产品型号")
    derivative_code: Optional[str] = Field(None, description="派生码")
    component_name: Optional[str] = Field(None, description="部件名称")
    component_material_code: Optional[str] = Field(None, description="零部件物料编码")
    failure_mode: Optional[str] = Field(None, description="故障模式")

    # 关键信息字段
    source: Optional[str] = Field(None, description="来源")
    is_key_component: Optional[bool] = Field(None, description="是否关键部件")
    is_consumable_part: Optional[bool] = Field(None, description="是否耗损型部件")

    # 计算参数字段
    estimated_failure_rate: Optional[float] = Field(
        None, description="故障率预计值(FPMH)"
    )

    # 预防性维修字段
    preventive_maintenance_cost: Optional[float] = Field(
        None, description="增加预防性维修的(万元)"
    )

    # LCC成本字段
    lcc_before_improvement: Optional[float] = Field(None, description="改进前LCC(万元)")
    lcc_after_improvement: Optional[float] = Field(None, description="改进后LCC(万元)")

    # 状态字段
    is_online_status: Optional[bool] = Field(None, description="状态是否可在线")
    is_trend_rate_limit: Optional[bool] = Field(
        None, description="故障率变化趋势是否达到预警值"
    )

    # 系统管理字段
    created_by: Optional[str] = Field(None, description="创建人")
    changed_time: Optional[date] = Field(None, description="表格修改时间")


class GetRcmBaseDataDetails(RcmBaseDataSchemaBase):
    """获取RCM基础数据详情"""

    id: int = Field(..., description="RCM基础数据ID")
    created_time: Optional[datetime] = Field(None, description="创建时间")
    updated_time: Optional[datetime] = Field(None, description="更新时间")


class RcmBaseDataFilterParam(SchemaBase):
    """RCM基础数据查询过滤参数"""

    product_model: Optional[str] = Field(None, description="产品型号")
    component_name: Optional[str] = Field(None, description="部件名称")
    component_material_code: Optional[str] = Field(None, description="零部件物料编码")
    failure_mode: Optional[str] = Field(None, description="故障模式")
    is_key_component: Optional[bool] = Field(None, description="是否关键部件")
    is_consumable_part: Optional[bool] = Field(None, description="是否耗损型部件")


class GetRcmBaseDataListResponse(SchemaBase):
    """获取RCM基础数据列表响应"""

    total: int = Field(..., description="总数")
    items: List[GetRcmBaseDataDetails] = Field(..., description="RCM基础数据列表")


class RcmExcelImportRow(SchemaBase):
    """RCM Excel导入行数据"""

    product_model: str = Field(..., description="产品型号")
    derivative_code: Optional[str] = Field(None, description="派生码")
    component_name: str = Field(..., description="部件名称")
    component_material_code: str = Field(..., description="零部件物料编码")
    failure_mode: str = Field(..., description="故障模式")
    source: Optional[str] = Field(None, description="来源")
    is_key_component: Optional[bool] = Field(None, description="是否关键部件")
    is_consumable_part: Optional[bool] = Field(None, description="是否耗损型部件")
    estimated_failure_rate: Optional[float] = Field(
        None, description="故障率预计值(FPMH)"
    )
    preventive_maintenance_cost: Optional[float] = Field(
        None, description="增加预防性维修的(万元)"
    )
    lcc_before_improvement: Optional[float] = Field(None, description="改进前LCC(万元)")
    lcc_after_improvement: Optional[float] = Field(None, description="改进后LCC(万元)")
    is_online_status: Optional[bool] = Field(None, description="状态是否可在线")
    is_trend_rate_limit: Optional[bool] = Field(
        None, description="故障率变化趋势是否达到预警值"
    )
    created_by: Optional[str] = Field(None, description="创建人")
    changed_time: Optional[date] = Field(None, description="表格修改时间")


class RcmExcelImportResponse(SchemaBase):
    """RCM Excel导入响应"""

    total_rows: int = Field(..., description="总行数")
    success_rows: int = Field(..., description="成功行数")
    failed_rows: int = Field(..., description="失败行数")
    errors: List[str] = Field(default_factory=list, description="错误信息")
