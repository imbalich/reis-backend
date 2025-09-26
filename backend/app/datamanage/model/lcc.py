#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：overhaul.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/19 17:52
"""
from datetime import date
from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class LCC(DataClassBase):
    """检修数据表"""

    __tablename__ = 'dm_lcc'

    id: Mapped[id_key] = mapped_column(init=False)
    model: Mapped[str] = mapped_column(String(100), nullable=True, comment='产品型号')
    material_code: Mapped[str] = mapped_column(String(100), nullable=True, comment='物料编码')
    part_name: Mapped[str] = mapped_column(String(100), nullable=True, comment='零部件名称')
    basic_number: Mapped[float] = mapped_column(Float,nullable=True, comment='基本数量')
    level: Mapped[str] = mapped_column(String(100), nullable=True, comment='层级')
    project_code: Mapped[str] = mapped_column(String(100), nullable=True, comment='项目编号')
    cost: Mapped[date] = mapped_column(String(100), nullable=True, comment='价格')
    cost_unit: Mapped[float] = mapped_column(Float, nullable=True, comment='价格单位')
    number: Mapped[str] = mapped_column(String(100), nullable=True, comment='数量')
    total_cost: Mapped[float] = mapped_column(Float, nullable=True, comment='总价')
    unit: Mapped[str] = mapped_column(String(100), nullable=True, comment='单位')
    mark: Mapped[str] = mapped_column(String(255), nullable=True, comment='备注预留字段')
