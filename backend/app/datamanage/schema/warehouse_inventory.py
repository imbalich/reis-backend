#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, date
from typing import Optional, List

from pydantic import Field

from backend.common.schema import SchemaBase


class WarehouseInventorySchemaBase(SchemaBase):
    """库房备品清单基础模型"""

    warehouse_code: Optional[str] = Field(None, description="库房编号")
    warehouse_name: Optional[str] = Field(None, description="库房名称")
    part_code: Optional[str] = Field(None, description="零部件物料编码")
    part_name: Optional[str] = Field(None, description="零部件名称")
    default_quantity: Optional[int] = Field(1, description="默认数量")
    created_by: Optional[str] = Field(None, description="创建人")
    changed_time: Optional[date] = Field(None, description="更新时间")


class GetWarehouseInventoryDetails(WarehouseInventorySchemaBase):
    """获取库房备品清单详情"""

    id: int = Field(..., description="库房备品清单ID")
    created_time: Optional[datetime] = Field(None, description="创建时间")
    updated_time: Optional[datetime] = Field(None, description="更新时间")


class WarehouseInventoryFilterParam(SchemaBase):
    """库房备品清单查询过滤参数"""

    warehouse_code: Optional[str] = Field(None, description="库房编号")
    warehouse_name: Optional[str] = Field(None, description="库房名称")
    part_code: Optional[str] = Field(None, description="零部件物料编码")
    part_name: Optional[str] = Field(None, description="零部件名称")


class GetWarehouseInventoryListResponse(SchemaBase):
    """获取库房备品清单列表响应"""

    total: int = Field(..., description="总数")
    items: List[GetWarehouseInventoryDetails] = Field(
        ..., description="库房备品清单列表"
    )


class WarehouseInventoryExcelImportRow(SchemaBase):
    """Excel导入行数据"""

    warehouse_code: str = Field(..., description="库房编号")
    warehouse_name: str = Field(..., description="库房名称")
    part_code: str = Field(..., description="零部件物料编码")
    part_name: str = Field(..., description="零部件名称")
    default_quantity: Optional[int] = Field(1, description="默认数量")
    created_by: Optional[str] = Field(None, description="创建人")
    changed_time: Optional[date] = Field(None, description="更新时间")


class WarehouseInventoryExcelImportResponse(SchemaBase):
    """Excel导入响应"""

    total_rows: int = Field(..., description="总行数")
    success_rows: int = Field(..., description="成功行数")
    failed_rows: int = Field(..., description="失败行数")
    errors: List[str] = Field(default_factory=list, description="错误信息")
