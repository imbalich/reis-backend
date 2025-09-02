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
from sqlalchemy import String, Date
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class Overhaul(DataClassBase):
    """检修数据表"""

    __tablename__ = 'dm_overhaul'

    id: Mapped[id_key] = mapped_column(init=False)
    product_model: Mapped[str] = mapped_column(String(100), nullable=True, comment='产品型号')
    product_no: Mapped[str] = mapped_column(String(100), nullable=True, comment='产品编号')
    repair_level: Mapped[str] = mapped_column(String(100), nullable=True, comment='修造级别')
    repair_time: Mapped[date] = mapped_column(Date, nullable=True, comment='检修时间')
    check_bezier: Mapped[str] = mapped_column(String(255), nullable=True, comment='检修项点')
    check_value: Mapped[str] = mapped_column(String(100), nullable=True, comment='检修结果')
    beizhu: Mapped[str] = mapped_column(String(255), nullable=True, comment='备注')
    shuoming: Mapped[str] = mapped_column(String(255), nullable=True, comment='说明')