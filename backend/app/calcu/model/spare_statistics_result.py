#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : spare_statistics_result.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : 备件统计计算结果表模型
"""

from datetime import date

from sqlalchemy import Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class SpareStatisticsResult(Base):
    """存储预计备件数量和实际故障数量的计算结果。"""

    __tablename__ = "calcu_spare_statistics_result"

    id: Mapped[id_key] = mapped_column(init=False, nullable=False)

    task_id: Mapped[str] = mapped_column(
        String(155), nullable=False, index=True, comment="Celery任务ID"
    )
    task_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="任务类型: prediction/failure_count",
    )

    model: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True, comment="产品型号"
    )
    product_config_code: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True, comment="派生码"
    )
    part: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True, comment="零部件物料编码"
    )
    input_date: Mapped[date] = mapped_column(
        nullable=False, index=True, comment="拟合输入日期"
    )
    start_date: Mapped[date] = mapped_column(
        nullable=False, index=True, comment="计算开始日期"
    )
    end_date: Mapped[date] = mapped_column(
        nullable=False, index=True, comment="计算结束日期"
    )

    part_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, default=None, init=False, comment="零部件名称"
    )

    predicted_spare_num: Mapped[float | None] = mapped_column(
        Numeric(precision=15, scale=8),
        nullable=True,
        default=None,
        comment="预计备件数量（精确小数）",
    )
    predicted_spare_num_int: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None, comment="预计备件数量（取整整数）"
    )
    actual_failure_num: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None, comment="实际故障数量"
    )

    distribution_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None, comment="分布类型"
    )
    method: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None, comment="拟合方法"
    )
    check: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None, comment="拟合优度检验"
    )
    source: Mapped[bool | None] = mapped_column(
        nullable=True, default=None, comment="拟合来源"
    )

    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None, comment="错误信息"
    )

    calculation_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        comment="计算状态: success/failed",
    )

    __table_args__ = (
        Index(
            "idx_model_config_part_dates",
            "model",
            "product_config_code",
            "part",
            "input_date",
            "start_date",
            "end_date",
        ),
    )
