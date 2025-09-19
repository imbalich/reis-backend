#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import date
from typing import Optional
from sqlalchemy import Date, String, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class ScienceWarehouseResult(Base):
    """科学库存计算结果"""

    __tablename__ = "calcu_science_warehouse_result"

    id: Mapped[id_key] = mapped_column(init=False)
    calculation_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="计算批次ID"
    )
    warehouse_code: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="库房编码"
    )
    warehouse_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="库房名称"
    )
    spare_part_code: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="备品编码"
    )
    spare_part_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="备品名称"
    )
    required_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="需求数量"
    )
    calculation_method: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="计算方法（fitted/default）"
    )
    time_interval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="时间间隔（天）"
    )
    input_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="计算截止日期"
    )
    created_time: Mapped[date] = mapped_column(Date, nullable=False, comment="创建时间")
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5, comment="置信度"
    )
    coverage_info: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None, comment="覆盖信息（JSON格式）"
    )
    maintenance_analysis: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None, comment="维护责任分析（JSON格式）"
    )
    calculation_details: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None, comment="计算详情（JSON格式）"
    )
