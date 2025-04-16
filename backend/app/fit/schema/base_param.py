#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : base_param.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/2/18 下午4:26
"""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import ConfigDict, Field, field_validator

from backend.common.schema import SchemaBase


class DespatchParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str = Field(..., description='产品型号')
    identifier: str = Field(..., description='产品编号')
    repair_level: str = Field(..., description='修理级别')
    life_cycle_time: date = Field(..., description='出厂日期')
    repair_level_num: int = Field(..., description='修级序号')

    @field_validator('life_cycle_time', mode='before')
    @classmethod
    def parse_date(cls, value: Any) -> date:
        if isinstance(value, str):
            # 尝试解析带有时间部分的日期字符串
            try:
                return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').date()
            except ValueError:
                # 如果上面的格式不匹配，尝试其他常见格式
                try:
                    return datetime.strptime(value, '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError(f'无法解析日期: {value}')
        return value


class FailureParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    report_id: str = Field(..., description='报告编号')  # 新表:report_id
    product_lifetime_stage: Optional[str] = Field(default=None, description='产品寿命阶段')  # 新表:repair_level
    discovery_date: date = Field(..., description='发现日期')  # 新表:fault_date
    product_model: Optional[str] = Field(default=None, description='产品型号')  # 新表:product_model
    product_number: Optional[str] = Field(default=None, description='产品编号')  # 新表:product_no
    manufacturing_date: date = Field(..., description='新造出厂日期')  # 新表:life_cycle_time_erp
    fault_location: Optional[str] = Field(default=None, description='终判故障部位')  # 新表:fault_part_name
    fault_material_code: Optional[str] = Field(default=None, description='终判故障部位物料编码')  # 新表:fault_part_code
    fault_part_number: str = Field('#', description='故障部件编号')  # 新表:fault_part_number
    replacement_part_number: str = Field('#', description='更换件编号')  # 新表:replacement_part_number
    final_fault_responsibility: Optional[str] = Field(default=None, description='最终判责')  # 新表:respons
    is_zero_distance: Optional[int] = Field(default=None, description='是否零公里')  # 新表:is_zero

    # is_ours: Optional[str] = Field(default=None, description="是否永济公司产品")  # 新表暂无该字段
    # locomotive_type: Optional[str] = Field(default=None, description="产品类型")  # 新表暂无该字段

    @field_validator('fault_part_number', 'replacement_part_number', mode='before')
    @classmethod
    def check_part_numbers(cls, value: Any) -> str:
        if value in [None, '', '无']:
            return '#'
        return value

    @field_validator('discovery_date', 'manufacturing_date', mode='before')
    @classmethod
    def parse_date(cls, value: Any) -> date:
        if isinstance(value, str):
            # 尝试解析带有时间部分的日期字符串
            try:
                return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').date()
            except ValueError:
                # 如果上面的格式不匹配，尝试其他常见格式
                try:
                    return datetime.strptime(value, '%Y-%m-%d').date()
                except ValueError:
                    raise ValueError(f'无法解析日期: {value}')
        return value

    @field_validator('is_zero_distance', mode='before')
    @classmethod
    def convert_to_int(cls, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, str):
            if value.lower() in ('是', 'yes', 'true', '1'):
                return 1
            elif value.lower() in ('否', 'no', 'false', '0'):
                return 0
            try:
                return int(value)
            except ValueError:
                return None
        return value


class ProductParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description='主键')
    sub_saet: str = Field(..., description='产品系列')
    model: str = Field(..., description='产品型号')
    avg_worktime: int = Field(..., description='日均运行时长（天运行小时）')
    avg_speed: float = Field(..., description='运行时速')
    year_days: int = Field(..., description='年运行天数')
    repair_priod: Optional[str] = Field(default=None, description='维修周期')
    repair_times: Optional[int] = Field(default=None, description='修级间隔天数')


class EbomParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    prd_no: str = Field(..., description='产品型号')
    y8_matbnum1: str = Field(..., description='零部件物料编码')
    y8_matname: str = Field(..., description='零部件名称')
    bl_quantity: str = Field(..., description='物料总数量')  # 查询出来物料编码是str，处理时需要转换将浮点数直接转为1


class ReplaceParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    model: str = Field(..., description='型号')
    part_name: str = Field(..., description='零部件名称')
    part_code: str = Field(..., description='零部件物料编码')
    replace_level: str = Field(..., description='修造级别')
    replace_cycle: float = Field(..., description='必换周期')


class RepairParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    id_repair: int = Field(..., description='修级顺序')
    repair_levels: str = Field(..., description='造修阶段')
    model: str = Field(..., description='型号')
