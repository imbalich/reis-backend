#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : rcm_base_data.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : RCM基础数据表模型
"""

from datetime import date
from sqlalchemy import Date, String, Integer, DECIMAL, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class RcmBaseData(Base):
    """
    RCM基础数据表 - 存储用户上传的Excel数据
    """

    __tablename__ = "rcm_base_data"

    # 主键
    id: Mapped[id_key] = mapped_column(init=False, nullable=False)

    # 基础信息字段
    product_model: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="产品型号"
    )
    derivative_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="派生码"
    )
    component_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="部件名称"
    )
    component_material_code: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="零部件物料编码"
    )
    failure_mode: Mapped[str] = mapped_column(
        String(200), nullable=True, comment="故障模式"
    )

    # 关键信息字段 (黄色背景组)
    source: Mapped[str] = mapped_column(String(100), nullable=True, comment="来源")
    is_key_component: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, comment="是否关键部件"
    )
    # 是否耗损型部件(橙色背景组)
    is_consumable_part: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, comment="是否耗损型部件"
    )

    # 计算参数字段 (绿色背景组)
    estimated_failure_rate: Mapped[float | None] = mapped_column(
        DECIMAL(10, 6), nullable=True, comment="故障率预计值(FPMH)"
    )

    # 预防性维修字段 (红色背景组)
    preventive_maintenance_cost: Mapped[float | None] = mapped_column(
        DECIMAL(12, 2), nullable=True, comment="增加预防性维修的LCC(万元)"
    )

    # LCC成本字段 (浅蓝色背景组)
    lcc_before_improvement: Mapped[float | None] = mapped_column(
        DECIMAL(12, 2), nullable=True, comment="改进前LCC(万元)"
    )
    lcc_after_improvement: Mapped[float | None] = mapped_column(
        DECIMAL(12, 2), nullable=True, comment="改进后LCC(万元)"
    )

    # 系统管理字段
    created_by: Mapped[str] = mapped_column(
        String(255), nullable=True, comment="创建人"
    )
    changed_time: Mapped[date] = mapped_column(
        Date, nullable=True, comment="表格修改时间"
    )
    
    # 故障率变化趋势是否达到预警值
    is_trend_rate_limit:Mapped[bool | None] = mapped_column(
        Boolean, nullable=True,default=False, comment="故障率变化趋势是否达到预警值"
    )
    
    # 状态字段 (灰色背景组) - 有默认值的字段放在最后
    is_online_status: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=False, comment="状态是否可在线"
    )


