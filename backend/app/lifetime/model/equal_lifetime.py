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

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key
from backend.utils.timezone import timezone


class EqualLifetime(DataClassBase):
    """等寿命点优化结果表"""

    __tablename__ = "equal_lifetime"

    id: Mapped[id_key] = mapped_column(init=False)
    group_id: Mapped[str] = mapped_column(String(50), index=True, comment='分组ID')

    model: Mapped[str] = mapped_column(String(30), index=True, comment='型号')
    part: Mapped[str] = mapped_column(String(30), index=True, comment='零部件物料编码')
    target_sf: Mapped[float] = mapped_column(comment='目标SF值')
    step_start: Mapped[float] = mapped_column(comment='步长开始值')
    step_end: Mapped[float] = mapped_column(comment='步长结束值')
    time_point: Mapped[float] = mapped_column(comment='计算截止时间点')
    # equal_lifetime_point: Mapped[tuple | None] = mapped_column(comment='等寿命点')
    equal_lifetime_t: Mapped[float | None] = mapped_column(comment='等寿命点t值')
    equal_lifetime_sf: Mapped[float | None] = mapped_column(comment='等寿命点SF值')
    distribution: Mapped[str | None] = mapped_column(String(50), comment='分布类型')
    original_sf: Mapped[float | None] = mapped_column(comment='原始time_point时刻SF值')
    optimized_sf: Mapped[float | None] = mapped_column(comment='优化后time_point时刻的SF值')
    original_pdf: Mapped[float | None] = mapped_column(comment='原始time_point时刻的PDF值')
    optimized_pdf: Mapped[float | None] = mapped_column(comment='优化后time_point时刻的PDF值')
    original_equal_point_pdf: Mapped[float | None] = mapped_column(comment='原始等寿命点PDF值')
    optimized_equal_point_pdf: Mapped[float | None] = mapped_column(comment='优化后等寿命点PDF值')
    alpha: Mapped[float | None] = mapped_column(comment='alpha')
    beta: Mapped[float | None] = mapped_column(comment='beta')
    gamma: Mapped[float | None] = mapped_column(comment='gamma')
    alpha_1: Mapped[float | None] = mapped_column(comment='alpha_1')
    beta_1: Mapped[float | None] = mapped_column(comment='beta_1')
    alpha_2: Mapped[float | None] = mapped_column(comment='alpha_2')
    beta_2: Mapped[float | None] = mapped_column(comment='beta_2')
    proportion_1: Mapped[float | None] = mapped_column(comment='proportion_1')
    ds: Mapped[float | None] = mapped_column(comment='ds')
    mu: Mapped[float | None] = mapped_column(comment='mu')
    sigma: Mapped[float | None] = mapped_column(comment='sigma')
    lambda_: Mapped[float | None] = mapped_column(comment='lambda_')


    created_time: Mapped[date] = mapped_column(
        Date, init=False, default_factory=timezone.now_date, sort_order=999, comment='创建时间'
    )
    need_optimization: Mapped[bool] = mapped_column(Integer, default=False, comment='数据来源,0为没有优化,1为进行优化')