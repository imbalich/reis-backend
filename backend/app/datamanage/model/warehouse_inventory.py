#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import date
from typing import Optional
from sqlalchemy import Date, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class WarehouseInventory(Base):
    __tablename__ = "dm_warehouse_inventory"

    id: Mapped[id_key] = mapped_column(init=False)
    warehouse_code: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="库房编号"
    )
    warehouse_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="库房名称"
    )
    part_code: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="零部件物料编码"
    )
    part_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="零部件名称"
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="创建人"
    )
    changed_time: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="表格修改时间"
    )
    default_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="默认数量"
    )
