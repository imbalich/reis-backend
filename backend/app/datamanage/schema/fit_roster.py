#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import Field

from backend.common.schema import SchemaBase


class FitRosterSchemaBase(SchemaBase):
    """寿命拟合名单基础字段。"""

    product_model: str = Field(description="产品型号")
    product_config_code: str = Field(description="派生码")
    part_code: str = Field(description="零部件物料编码")
    part_name: str = Field("", description="零部件名称")
    family: str | None = Field(None, description="产品族")
    created_by: str | None = Field(None, description="最近一次写入的人")


class CreateFitRosterParam(SchemaBase):
    """新增寿命拟合名单。"""

    product_model: str = Field(description="产品型号")
    product_config_code: str | None = Field(None, description="派生码，空值按 PS00")
    part_code: str = Field(description="零部件物料编码")
    part_name: str = Field("", description="零部件名称")
    family: str | None = Field(None, description="产品族")
    created_by: str | None = Field(None, description="写入人")


class UpdateFitRosterParam(SchemaBase):
    """修改名称和族。型号、派生码、件号不变。"""

    part_name: str = Field("", description="零部件名称")
    family: str | None = Field(None, description="产品族")
    created_by: str | None = Field(None, description="写入人")


class DeleteFitRosterParam(SchemaBase):
    """批量删除。"""

    ids: list[int] = Field(description="名单 ID 列表")


class GetFitRosterDetail(FitRosterSchemaBase):
    """寿命拟合名单详情。"""

    id: int = Field(description="名单 ID")
    created_time: datetime | None = Field(None, description="创建时间")
    updated_time: datetime | None = Field(None, description="更新时间")


class FitRosterChangeItem(SchemaBase):
    """导入差异中的一行。"""

    product_model: str = Field(description="产品型号")
    product_config_code: str = Field(description="派生码")
    part_code: str = Field(description="零部件物料编码")
    part_name: str = Field("", description="导入后的零部件名称")
    family: str | None = Field(None, description="导入后的产品族")
    current_part_name: str | None = Field(None, description="当前零部件名称")
    current_family: str | None = Field(None, description="当前产品族")


class FitRosterImportPreview(SchemaBase):
    """导入更换前的差异。确认前不写库。"""

    can_replace: bool = Field(description="是否允许按该文件更换")
    total_rows: int = Field(description="文件数据行数")
    errors: list[str] = Field(default_factory=list, description="错误信息")
    to_add: list[FitRosterChangeItem] = Field(default_factory=list, description="将加入")
    to_remove: list[FitRosterChangeItem] = Field(default_factory=list, description="将移除")
    to_update: list[FitRosterChangeItem] = Field(default_factory=list, description="将更新")
    unchanged: int = Field(0, description="保持不变的件数")
