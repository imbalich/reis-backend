#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, date
from typing import Optional, List

from pydantic import Field

from backend.common.schema import SchemaBase


class WarehouseSchemaBase(SchemaBase):
    """仓库基础模型"""

    area: Optional[str] = Field(None, description="归属区域")
    code: Optional[str] = Field(None, description="库房编码")
    name: Optional[str] = Field(None, description="库房名称")
    allotment_two: Optional[str] = Field(None, description="二级配属")
    created_by: Optional[str] = Field(None, description="创建人")
    changed_time: Optional[date] = Field(None, description="更新时间")


class GetWarehouseDetails(WarehouseSchemaBase):
    """获取仓库详情"""

    id: int = Field(..., description="仓库ID")
    created_time: Optional[datetime] = Field(None, description="创建时间")
    updated_time: Optional[datetime] = Field(None, description="更新时间")


class WarehouseFilterParam(SchemaBase):
    """仓库查询过滤参数"""

    area: Optional[str] = Field(None, description="归属区域")
    name: Optional[str] = Field(None, description="库房名称")
    code: Optional[str] = Field(None, description="库房编码")


class GetWarehouseListResponse(SchemaBase):
    """获取仓库列表响应"""

    total: int = Field(..., description="总数")
    items: List[GetWarehouseDetails] = Field(..., description="仓库列表")


class WarehouseImportRow(SchemaBase):
    """CSV导入行数据"""

    area: str = Field(..., description="归属区域")
    name: str = Field(..., description="库存地")
    actual_warehouse: Optional[str] = Field(None, description="实际库存地")


class WarehouseImportResponse(SchemaBase):
    """导入响应"""

    total_rows: int = Field(..., description="总行数")
    success_rows: int = Field(..., description="成功行数")
    failed_rows: int = Field(..., description="失败行数")
    errors: List[str] = Field(default_factory=list, description="错误信息")


class WarehouseExcelImportRow(SchemaBase):
    """Excel导入行数据"""

    area: Optional[str] = Field(None, description="区域")
    code: str = Field(..., description="库房编号")
    name: str = Field(..., description="库房名称")
    allotment_two: str = Field(..., description="二级配属")
    created_by: Optional[str] = Field(None, description="创建人")
    changed_time: Optional[date] = Field(None, description="更新时间")


class WarehouseExcelImportResponse(SchemaBase):
    """Excel导入响应"""

    total_rows: int = Field(..., description="总行数")
    success_rows: int = Field(..., description="成功行数")
    failed_rows: int = Field(..., description="失败行数")
    errors: List[str] = Field(default_factory=list, description="错误信息")
