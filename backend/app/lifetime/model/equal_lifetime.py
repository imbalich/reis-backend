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

from backend.common.model import DataClassBase, id_key
from backend.utils.timezone import timezone
from sqlalchemy.dialects.mysql import LONGTEXT


class EqualLifetime(DataClassBase):
    """寻找等寿命点结果表"""

    __tablename__ = "equal_lifetime"

    id: Mapped[id_key] = mapped_column(init=False)
    group_id: Mapped[str] = mapped_column(String(50), index=True, comment='分组ID')

    model: Mapped[str] = mapped_column(String(30), index=True, comment='型号')
    parts: Mapped[str] = mapped_column(LONGTEXT,comment='零部件物料编码')
    category: Mapped[str] = mapped_column(String(1), index=True, nullable=True, comment='分类: A(SF>=0.99), B(0.95<=SF<0.99), C(SF<0.95)')
    target_sf: Mapped[float] = mapped_column(comment='目标SF值')
    step_start: Mapped[float] = mapped_column(comment='步长开始值')
    step_end: Mapped[float] = mapped_column(comment='步长结束值')
    time_point: Mapped[int] = mapped_column(comment='计算截止时间点')
    sf_at_time_point: Mapped[float | None] = mapped_column(nullable=True, comment='该分类部件在time_point处的平均SF值')
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True, comment='跳过原因或说明')
    equal_lifetime_t_year: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='等寿命时间对应修程')
    # equal_lifetime_point: Mapped[tuple | None] = mapped_column(comment='等寿命点')
    equal_lifetime_t: Mapped[int | None] = mapped_column(comment='等寿命点t值')
    equal_lifetime_sf: Mapped[float | None] = mapped_column(comment='等寿命点SF值')
    is_all_parts: Mapped[bool] = mapped_column(Integer, default=False, comment='是否所有零部件')
    created_time: Mapped[date] = mapped_column(
        Date, init=False, default_factory=timezone.now_date, sort_order=999, comment='创建时间'
    )
    status: Mapped[str] = mapped_column(String(20), default='completed', comment='状态: skipped(已跳过), completed(已完成), pending(待处理)')
    part_count: Mapped[int] = mapped_column(Integer, default=0, comment='该分类部件数量')
    