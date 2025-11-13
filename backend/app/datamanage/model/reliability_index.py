#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：reliability_index.py
@IDE     ：PyCharm
@Author  ：seven
@Date    ：2024/10/15 18:49
"""

from datetime import date

from sqlalchemy import Date, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class ReliabilityIndex(DataClassBase):
    """可靠性指标表"""

    __tablename__ = 'dm_reliability_index'

    id: Mapped[id_key] = mapped_column(init=False)
    model: Mapped[str] = mapped_column(String(100), nullable=True, comment='产品型号')
    model_name: Mapped[str] = mapped_column(String(100), nullable=True, comment='产品名称')
    part: Mapped[str] = mapped_column(String(100), nullable=True, comment='部件物料编码')
    part_name: Mapped[str] = mapped_column(String(100), nullable=True, comment='部件名称')
    index_type: Mapped[str] = mapped_column(String(100), nullable=True, comment='协议指标类型')
    index_value: Mapped[float] = mapped_column(Float, nullable=True, comment='协议指标值')
    index_fpmh: Mapped[float] = mapped_column(Float, nullable=True, comment='协议FPMH值')
    index_fpmh_single: Mapped[float] = mapped_column(Float, nullable=True, comment='协议FPMH值/单台')
    pre_value: Mapped[float] = mapped_column(Float, nullable=True, comment='预计值')
    beizhu: Mapped[str] = mapped_column(String(255), nullable=True, comment='备注')
    shuoming: Mapped[str] = mapped_column(String(255), nullable=True, comment='说明')
