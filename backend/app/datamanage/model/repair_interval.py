#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：repair.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/25 14:24
"""

from datetime import date

from sqlalchemy import Date, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class RepairInterval(DataClassBase):
    """造修阶段表"""

    __tablename__ = 'dm_repair_interval'

    id: Mapped[id_key] = mapped_column(init=False)
    repair_levels: Mapped[str] = mapped_column(String(255), nullable=True, comment='造修阶段')
    model: Mapped[str] = mapped_column(String(255), nullable=True, comment='产品型号')
    repair_years: Mapped[float] = mapped_column(Float, nullable=True, comment='距离新造时长/年')
    interval_kilo: Mapped[int] = mapped_column(Integer, nullable=True, comment='维修间隔里程/公里')
    document: Mapped[str] = mapped_column(String(255), nullable=True, comment='文件来源')
    version: Mapped[str] = mapped_column(String(255), nullable=True, comment='版本')
    creator: Mapped[str] = mapped_column(String(255), nullable=True, comment='创建人')
    create_time: Mapped[date] = mapped_column(Date, nullable=True, comment='创建时间')
    beizhu: Mapped[str] = mapped_column(String(255), nullable=True, comment='备注')
    shuoming: Mapped[str] = mapped_column(String(255), nullable=True, comment='说明')
