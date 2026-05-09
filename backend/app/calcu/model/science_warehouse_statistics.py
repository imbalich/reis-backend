#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import date
from typing import Optional

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class ScienceWarehouseStatistics(Base):
    """科学库存计算统计信息。"""

    __tablename__ = "calcu_science_warehouse_statistics"

    id: Mapped[id_key] = mapped_column(init=False)
    calculation_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="计算批次ID"
    )
    product_model: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True, comment="产品型号"
    )
    product_config_code: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True, comment="派生码"
    )
    total_warehouse_spares: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="总库房备品数量"
    )
    calculated_spares: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="成功计算的备品数量"
    )
    default_spares: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="使用默认数量的备品数量"
    )
    skipped_failures_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="跳过的故障数量"
    )
    mapping_errors_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="映射错误数量"
    )
    time_interval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="时间间隔（天）"
    )
    input_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="计算截止日期"
    )
    calculation_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="计算摘要（JSON格式）"
    )
    created_time: Mapped[date] = mapped_column(Date, nullable=False, comment="创建时间")
