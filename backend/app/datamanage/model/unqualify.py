#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：unqualify.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/10/11 16:17
"""
from datetime import date
from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class Unqualify(DataClassBase):
    """检修数据表"""

    __tablename__ = 'dm_unqualify'

    id: Mapped[id_key] = mapped_column(init=False)
    product_model: Mapped[str] = mapped_column(String(100), nullable=True, comment='产品型号')
    product_no: Mapped[str] = mapped_column(String(100), nullable=True, comment='产品编号')
    ncr_code: Mapped[str] = mapped_column(String(100), nullable=True, comment='不合格编码')
    ncr_name: Mapped[str] = mapped_column(String(255), nullable=True, comment='零部件名称')
    ncr_material_code: Mapped[str] = mapped_column(String(100), nullable=True, comment='物料编码')
    is_new: Mapped[str] = mapped_column(String(100), nullable=True, comment='是否新造')
    repair_levels: Mapped[str] = mapped_column(String(100), nullable=True, comment='检修级别')
    derive_code: Mapped[str] = mapped_column(String(100), nullable=True, comment='派生编码')
    occurrence_rate: Mapped[float] = mapped_column(Float, nullable=True, comment='偶换率')
    mark: Mapped[str] = mapped_column(String(255), nullable=True, comment='备注预留字段')
    shuoming: Mapped[str] = mapped_column(String(255), nullable=True, comment='说明')
