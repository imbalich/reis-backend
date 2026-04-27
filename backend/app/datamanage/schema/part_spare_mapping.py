#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, date
from typing import Optional, List

from pydantic import Field

from backend.common.schema import SchemaBase


class PartSpareMappingSchemaBase(SchemaBase):
    """部件与备品对应关系基础模型"""

    product_model: Optional[str] = Field(None, description="产品型号")
    product_config_code: Optional[str] = Field(None, description="产品配置号")
    original_part_name: Optional[str] = Field(None, description="零部件名称（原装）")
    original_part_code: Optional[str] = Field(
        None, description="零部件物料编码（原装）"
    )
    spare_part_name: Optional[str] = Field(None, description="零部件名称（备品）")
    spare_part_code: Optional[str] = Field(None, description="零部件物料编码（备品）")
    created_by: Optional[str] = Field(None, description="创建人")
    changed_time: Optional[date] = Field(None, description="更新时间")


class GetPartSpareMappingDetails(PartSpareMappingSchemaBase):
    """获取部件与备品对应关系详情"""

    id: int = Field(..., description="部件与备品对应关系ID")
    created_time: Optional[datetime] = Field(None, description="创建时间")
    updated_time: Optional[datetime] = Field(None, description="更新时间")


class PartSpareMappingFilterParam(SchemaBase):
    """部件与备品对应关系查询过滤参数"""

    product_model: Optional[str] = Field(None, description="产品型号")
    product_config_code: Optional[str] = Field(None, description="产品配置号")
    original_part_name: Optional[str] = Field(None, description="零部件名称（原装）")
    original_part_code: Optional[str] = Field(
        None, description="零部件物料编码（原装）"
    )
    spare_part_name: Optional[str] = Field(None, description="零部件名称（备品）")
    spare_part_code: Optional[str] = Field(None, description="零部件物料编码（备品）")


class GetPartSpareMappingListResponse(SchemaBase):
    """获取部件与备品对应关系列表响应"""

    total: int = Field(..., description="总数")
    items: List[GetPartSpareMappingDetails] = Field(
        ..., description="部件与备品对应关系列表"
    )


class PartSpareMappingExcelImportRow(SchemaBase):
    """Excel导入行数据"""

    product_model: str = Field(..., description="产品型号")
    product_config_code: Optional[str] = Field(None, description="产品配置号")
    original_part_name: str = Field(..., description="零部件名称（原装）")
    original_part_code: str = Field(..., description="零部件物料编码（原装）")
    spare_part_name: str = Field(..., description="零部件名称（备品）")
    spare_part_code: str = Field(..., description="零部件物料编码（备品）")
    created_by: Optional[str] = Field(None, description="创建人")
    changed_time: Optional[date] = Field(None, description="更新时间")


class PartSpareMappingExcelImportResponse(SchemaBase):
    """Excel导入响应"""

    total_rows: int = Field(..., description="总行数")
    success_rows: int = Field(..., description="成功行数")
    failed_rows: int = Field(..., description="失败行数")
    errors: List[str] = Field(default_factory=list, description="错误信息")
