#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：repair.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2024/12/25 14:24 
'''
from datetime import date
from sqlalchemy import String, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class Repair(DataClassBase):
    """造修阶段表"""

    __tablename__ = 'dm_repair'

    id: Mapped[id_key] = mapped_column(init=False)

    id_repair: Mapped[int] = mapped_column(Integer, nullable=True, comment='修级顺序')
    repair_levels: Mapped[str] = mapped_column(String(255), nullable=True, comment='造修阶段')
    model: Mapped[str] = mapped_column(String(255), nullable=True, comment='产品型号')
    creator: Mapped[str] = mapped_column(String(255), nullable=True, comment='创建人')
    create_time: Mapped[date] = mapped_column(Date, nullable=True, comment='创建时间')
    state_now: Mapped[bool] = mapped_column(Integer, nullable=True, default=True,
                                            comment='当前是否启用，1启用；0未启用,默认为1')
