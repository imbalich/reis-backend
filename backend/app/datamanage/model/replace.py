#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：replace.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/25 14:24
"""

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class Replace(DataClassBase):
    """必换件表"""

    __tablename__ = 'dm_replace'

    id: Mapped[id_key] = mapped_column(init=False)
    model: Mapped[str] = mapped_column(String(30), nullable=True, comment='型号')
    part_name: Mapped[str] = mapped_column(String(50), nullable=True, comment='零部件名称')
    part_code: Mapped[str] = mapped_column(String(50), nullable=True, comment='零部件物料编码')
    replace_level: Mapped[str] = mapped_column(String(50), nullable=True, comment='修造级别')
    replace_cycle: Mapped[float] = mapped_column(Float, nullable=True, comment='必换周期')
    replace_num: Mapped[int] = mapped_column(Integer, nullable=True, comment='必换数量')
    replace_unit: Mapped[str] = mapped_column(String(50), nullable=True, comment='必换数量单位')
    material_code: Mapped[str] = mapped_column(String(50), nullable=True, comment='材料编码')
    mark: Mapped[str] = mapped_column(String(50), nullable=True, comment='备注预留字段')
    state_now: Mapped[bool] = mapped_column(
        Integer, nullable=True, default=True, comment='当前是否启用，1启用；0未启用,默认为1'
    )
