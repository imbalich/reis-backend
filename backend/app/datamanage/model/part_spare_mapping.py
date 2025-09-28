#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import date
from typing import Optional
from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class PartSpareMapping(Base):
    __tablename__ = "dm_part_spare_mapping"

    id: Mapped[id_key] = mapped_column(init=False)
    product_model: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="产品型号"
    )
    derived_code: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True, comment="派生码"
    )
    original_part_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="零部件名称（原装）"
    )
    original_part_code: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="零部件物料编码（原装）"
    )
    spare_part_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="零部件名称（备品）"
    )
    spare_part_code: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="零部件物料编码（备品）"
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="创建人"
    )
    changed_time: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="更新时间"
    )
