#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : fit_product.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/3 上午11:35
'''
from datetime import date

from sqlalchemy import String, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key
from backend.utils.timezone import timezone


class FitProduct(DataClassBase):
    """产品级别拟合结果"""

    __tablename__ = 'fit_product'

    id: Mapped[id_key] = mapped_column(init=False)
    group_id: Mapped[str] = mapped_column(String(50), index=True, comment='分组ID')

    model: Mapped[str] = mapped_column(String(30), index=True, comment='型号')
    input_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment='输入日期')
    method: Mapped[str] = mapped_column(String(30), comment='拟合方法')

    distribution: Mapped[str] = mapped_column(String(30), comment='分布类型')
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
    lambda_: Mapped[float | None] = mapped_column(comment='lambda')
    log_likelihood: Mapped[float | None] = mapped_column(comment='log_likelihood')
    aicc: Mapped[float | None] = mapped_column(comment='aicc')
    bic: Mapped[float | None] = mapped_column(comment='bic')
    ad: Mapped[float | None] = mapped_column(comment='ad')
    optimizer: Mapped[str | None] = mapped_column(String(30), comment='optimizer')

    source: Mapped[bool] = mapped_column(Integer, default=False, comment='数据来源,0为系统生成,1为用户输入')
    created_time: Mapped[date] = mapped_column(
        Date, init=False, default_factory=timezone.now_date, sort_order=999, comment='创建时间'
    )
