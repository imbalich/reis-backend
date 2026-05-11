#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class ScienceWarehousePushLog(Base):
    """科学库存推送日志。"""

    __tablename__ = "calcu_science_warehouse_push_log"

    id: Mapped[id_key] = mapped_column(init=False)
    calculation_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="计算批次ID"
    )
    push_reason: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="推送原因"
    )
    push_status: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True, comment="推送状态"
    )
    chunk_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="分包序号")
    chunk_total: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="分包总数"
    )
    total_records: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="本次分包记录数"
    )
    request_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="ESB消息流水号"
    )
    track_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="ESB链路追踪号"
    )
    service_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="ESB服务名"
    )
    payload_size_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="请求体字节数"
    )
    esb_status_flag: Mapped[str | None] = mapped_column(
        String(10), nullable=True, default=None, comment="ESB状态标识"
    )
    esb_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None, comment="ESB响应码"
    )
    esb_desc: Mapped[str | None] = mapped_column(
        String(500), nullable=True, default=None, comment="ESB响应描述"
    )
    response_body: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None, comment="响应体"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None, comment="异常信息"
    )
    pushed_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None, comment="推送完成时间"
    )
