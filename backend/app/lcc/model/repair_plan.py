#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：equal_lifetime_optimization.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/15 14:03
"""
from datetime import date

from sqlalchemy import Date, String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from backend.utils.timezone import timezone

from backend.common.model import DataClassBase, id_key


class RepairPlan(DataClassBase):
    """维修方案制定结果表"""

    __tablename__ = "repair_plan"

    id: Mapped[id_key] = mapped_column(init=False)
    group_id: Mapped[str] = mapped_column(String(50), index=True, comment='分组ID')

    model: Mapped[str] = mapped_column(String(30), index=True, comment='型号')
    part: Mapped[str] = mapped_column(String(30), index=True, comment='零部件物料编码')
    part_name: Mapped[str] = mapped_column(String(255), index=True, comment='零部件名称')
    life: Mapped[int] = mapped_column(nullable=True,comment='寿命终点')
    level_old: Mapped[str] = mapped_column(String(30), nullable=True, comment='原来修程')
    level_new: Mapped[str] = mapped_column(String(30), nullable=True, comment='推荐修程')
    year_new: Mapped[float] = mapped_column(nullable=True, comment='推荐修程周期')
    lcc_old: Mapped[float] = mapped_column(nullable=True, comment='原LCC')
    lcc_min: Mapped[float] = mapped_column(nullable=True, comment='最小LCC')
    sf: Mapped[float] = mapped_column(nullable=True, comment='推荐修程周期SF值')
    lcc_result: Mapped[str | None] = mapped_column(String(30), nullable=True, comment='分析结果-保持-延长-缩短')
    lcc_result_tag: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='分析结果标签')
    is_ai: Mapped[bool] = mapped_column(Integer, default=False, comment='是否考虑可用度')
    is_all_parts: Mapped[bool] = mapped_column(Integer, default=False, comment='是否所有零部件')
    created_time: Mapped[date] = mapped_column(
        Date, init=False, default_factory=timezone.now_date, sort_order=999, comment='创建时间'
    )