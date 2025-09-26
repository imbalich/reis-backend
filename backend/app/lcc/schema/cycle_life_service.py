
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, HttpUrl, model_validator
from typing_extensions import Self

from backend.app.admin.schema.dept import GetDeptDetail
from backend.app.admin.schema.role import GetRoleWithRelationDetail
from backend.common.enums import StatusType
from backend.common.schema import CustomEmailStr, CustomPhoneNumber, SchemaBase


class CycleLifeSchemaBase(SchemaBase):
    """全寿命周期计算单个结果"""
    model: str = Field(None, description='产品型号')
    part: str = Field(description='部件编码')
    part_name: str = Field(description='部件名称')
    part_number: int = Field(None, description='部件数量')
    falut_number: float = Field(None, description='故障次数')
    replace_number: int = Field(None, description='比换件次数')
    build_repair_retio: float = Field(None, description='造修比')
    totle_number: float = Field(None, description='全寿命周期所需部件数量')
    order: int = Field(None, description='排序')

class CycleLifeTotalSchemaBase(SchemaBase):
    result: list[CycleLifeSchemaBase] = Field(description='结果列表')

