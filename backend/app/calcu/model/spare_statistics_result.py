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

from datetime import date, datetime
from sqlalchemy import Date, String, Integer, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class SpareStatisticsResult(Base):
    """
    备件统计计算结果表 - 存储预计备件数量和实际故障数量的计算结果
    """

    __tablename__ = "calcu_spare_statistics_result"

    # 主键
    id: Mapped[id_key] = mapped_column(init=False, nullable=False)

    # 任务信息字段（必填字段，无默认值）
    task_id: Mapped[str] = mapped_column(
        String(155), nullable=False, index=True, comment="Celery任务ID"
    )
    task_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="任务类型: prediction/failure_count",
    )

    # 业务字段（必填字段，无默认值）
    model: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True, comment="产品型号"
    )
    part: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True, comment="零部件物料编码"
    )
    input_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="拟合输入日期"
    )
    start_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="计算开始日期"
    )
    end_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="计算结束日期"
    )
    
    # 可选字段（有默认值，必须放在必填字段之后）
    # 注意：part_name 使用 init=False，因为预测任务不需要设置，只在故障统计任务中设置
    part_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, default=None, init=False, comment="零部件名称"
    )

    # 计算结果字段（可选字段，有默认值）
    predicted_spare_num: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None, comment="预计备件数量"
    )
    actual_failure_num: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None, comment="实际故障数量"
    )

    # 计算参数字段（可选字段，有默认值）
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

    # 错误信息字段（可选字段，有默认值）
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None, comment="错误信息"
    )

    # 状态字段（有默认值）
    calculation_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        comment="计算状态: success/failed",
    )

    # 注意：created_time 和 updated_time 已从 Base 继承（DateTimeMixin），无需重新定义

    # 定义索引
    __table_args__ = (
        Index(
            "idx_model_part_dates",
            "model",
            "part",
            "input_date",
            "start_date",
            "end_date",
        ),
    )
