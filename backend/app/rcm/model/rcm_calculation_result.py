#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : rcm_calculation_result.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : RCM计算结果表模型
"""

from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.common.model import Base, id_key


class RcmCalculationResult(Base):
    """
    RCM计算结果表 - 存储RCM计算的最终结果
    """

    __tablename__ = "rcm_calculation_result"

    # 主键
    id: Mapped[id_key] = mapped_column(init=False, nullable=False)

    # 关联字段
    base_data_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="关联的RCM基础数据ID"
    )

    # 计算结果字段
    final_result: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="最终计算结果"
    )

    # 计算过程字段
    calculation_process: Mapped[str] = mapped_column(
        Text, nullable=True, comment="计算过程记录"
    )

    # 错误信息字段
    error_message: Mapped[str] = mapped_column(Text, nullable=True, comment="错误信息")

    # 计算状态字段
    calculation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success", comment="计算状态"
    )

    # 计算时间
    calculation_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="计算时间"
    )
