#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：despatch.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/24 10:48
"""

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class Despatch(DataClassBase):
    """发运表表:只查不增改删"""

    __tablename__ = 'dm_despatch'

    id: Mapped[id_key] = mapped_column(init=False)
    model: Mapped[str] = mapped_column(String(255), nullable=True, comment='model')
    identifier: Mapped[str] = mapped_column(String(255), nullable=True, comment='identifier')
    attach_company: Mapped[str] = mapped_column(String(255), nullable=True, comment='配属路局')
    attach_dept: Mapped[str] = mapped_column(String(255), nullable=True, comment='配属路段')
    cust_name: Mapped[str] = mapped_column(String(255), nullable=True, comment='客户名称')
    dopt_name: Mapped[str] = mapped_column(String(255), nullable=True, comment='库房名称')
    factory_name: Mapped[str] = mapped_column(String(255), nullable=True, comment='工厂名称')
    repair_level: Mapped[str] = mapped_column(String(255), nullable=True, comment='修理级别')
    life_cycle_time: Mapped[date] = mapped_column(Date, nullable=True, comment='出厂日期')
    repair_level_num: Mapped[int] = mapped_column(nullable=True, comment='修级序号')
    date_source: Mapped[str] = mapped_column(String(255), nullable=True, comment='数据来源')
    sync_time: Mapped[date] = mapped_column(Date, nullable=True, comment='生成时间')
