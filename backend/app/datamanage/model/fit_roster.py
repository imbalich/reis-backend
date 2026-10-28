#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class FitRoster(Base):
    """寿命拟合名单。有记录表示该件当前允许走寿命拟合，没有记录不表示不再计算。"""

    __tablename__ = "dm_fit_roster"
    __table_args__ = (
        UniqueConstraint(
            "product_model",
            "product_config_code",
            "part_code",
            name="uk_fit_roster_model_config_part",
        ),
        {"comment": "寿命拟合名单"},
    )

    id: Mapped[id_key] = mapped_column(init=False)
    product_model: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="产品型号"
    )
    product_config_code: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="派生码，空值存 PS00"
    )
    part_code: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="零部件物料编码"
    )
    part_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", comment="零部件名称"
    )
    family: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None, comment="产品族，如变流器、电机"
    )
    created_by: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None, comment="最近一次写入的人"
    )
