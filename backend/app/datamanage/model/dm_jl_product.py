#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : dm_jl_product.py
@Desc    : 产品信息-风电(jl) 直连模型(单库架构, 评审定版)
           管道消费字段通过 name=/property 对齐铁路 Product 属性名:
           - 派生码: 物理列即 PS_CODE, 属性名与铁路一致
           - 修级间隔: 风电无修级体系, 以产品寿命折算天数作为删失阈值
             (repair_times 属性 = PROD_REPAIR 年 × 365)
           - 运行时速: 风电无此概念, 恒为 None(管道不校验时速)
"""
from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key




def calc_repair_times_days(prod_repair_years) -> int | None:
    """删失阈值口径(评审PR#3意见#6, 业务确认后固化):
    修级间隔天数 = 产品寿命(年) × 365 (风电无修级体系, 以设计寿命为界)
    """
    if prod_repair_years is None:
        return None
    return int(round(float(prod_repair_years) * 365))


class ProductJL(DataClassBase):
    """产品信息-风电(来源: dm_jl_product, 风电专属表)"""

    __tablename__ = 'dm_jl_product'

    pk: Mapped[id_key] = mapped_column(init=False, nullable=False)
    id: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='主键ID')
    large_class: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='产品大类', name='LARGE_CLASS'
    )
    product_type: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='产品类型', name='PRODUCT_TYPE'
    )
    apply_area: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='应用领域', name='APPLY_AREA'
    )
    apply_area_desc: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='应用领域（细分）', name='APPLY_AREA_DESC'
    )
    product_sub: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='产品子类', name='PRODUCT_SUB'
    )
    belong_platform: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='所属产品平台', name='BELONG_PLATFORM'
    )
    sub_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='产品名称', name='SUB_NAME'
    )
    sub_saet: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='产品系列', name='SUB_SAET'
    )
    model: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='产品型号', name='MODEL'
    )
    product_config_code: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment='派生码', name='PS_CODE'
    )
    industry_unit: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='产业单元', name='INDUSTRY_UNIT'
    )
    cooling_mode: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='冷却方式', name='COOLING_MODE'
    )
    voltage_level: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='电压等级', name='VOLTAGE_LEVEL'
    )
    structure: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment='轴承结构', name='STRUCTURE'
    )
    avg_worktime: Mapped[int | None] = mapped_column(
        Numeric(20, 6, asdecimal=False), nullable=True, comment='日均工作小时', name='AVG_WORKTIME'
    )
    avg_power_generation: Mapped[float | None] = mapped_column(
        nullable=True, comment='年均发电量', name='AVG_POWER_GENERATION'
    )
    year_days: Mapped[int | None] = mapped_column(
        nullable=True, comment='年运行天数', name='YEAR_DAYS'
    )
    prod_repair: Mapped[float | None] = mapped_column(
        nullable=True, comment='产品寿命(年)', name='PROD_REPAIR'
    )
    update_time: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment='变更时间', name='UPDATE_TIME'
    )
    prd_big_type: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment='自定义类别', name='PRD_BIG_TYPE'
    )

    @property
    def avg_speed(self) -> float | None:
        """运行时速: 风电无此概念, 恒为None(管道不校验时速)"""
        return None

    @property
    def repair_priod(self) -> str | None:
        """维修周期: 风电无修级概念"""
        return None

    @property
    def repair_times(self) -> int | None:
        """修级间隔天数(删失阈值): 见 calc_repair_times_days 口径说明"""
        return calc_repair_times_days(self.prod_repair)
