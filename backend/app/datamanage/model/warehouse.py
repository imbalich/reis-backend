#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import date
from typing import Optional
from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class Warehouse(Base):
    __tablename__ = 'dm_warehouse'
    
    id: Mapped[id_key] = mapped_column(init=False)
    area: Mapped[str] = mapped_column(String(255), nullable=True, comment='归属区域')
    code: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment='库房编码')
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment='库房名称')
    allotment_two: Mapped[str] = mapped_column(String(255), nullable=True, index=True, comment='二级配属')
    created_by: Mapped[str] = mapped_column(String(255), nullable=True, comment='创建人')
    changed_time: Mapped[date] = mapped_column(Date, nullable=True, comment='表格修改时间')