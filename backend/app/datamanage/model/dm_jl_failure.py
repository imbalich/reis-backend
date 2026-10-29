#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : dm_jl_failure.py
@Desc    : 故障单-风电(jl) 直连模型(单库架构, 评审定版)
           管道消费字段通过 name=/hybrid_property 对齐铁路 Failure 属性名,
           多来源字段(部位/编码)用 COALESCE 混合属性在 SQL 层完成回退,
           与原视图方案的取数语义完全一致。
"""
from datetime import date

from sqlalchemy import Date, String, case, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key




def cn_yes_no_to_int(value) -> int | None:
    """中文'是/否'转数值: 是→1 否→0 其他→None (与铁路 is_zero/is_company 语义一致)"""
    if value is None:
        return None
    return {'是': 1, '否': 0}.get(str(value))


class FailureJL(DataClassBase):
    """故障单-风电(来源: dm_jl_failure, 风电专属表)"""

    __tablename__ = 'dm_jl_failure'

    pk: Mapped[id_key] = mapped_column(init=False, nullable=False)
    id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment='故障单编号')
    info_no: Mapped[str | None] = mapped_column(String(128), nullable=True, comment='信息编号')
    product_number: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment='产品编号', name='PRODUCT_NO'
    )
    product_model: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment='产品型号', name='PRODUCT_MODEL'
    )
    product_config_code: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment='派生码', name='PRODUCT_CONFIG_CODE'
    )
    manufacturing_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment='生产日期', name='NEW_MANUFACTURING_DATE'
    )
    life_cycle_time_erp: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment='新造发运出场时间', name='LIFE_CYCLE_TIME'
    )
    discovery_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, comment='发生日期', name='OCCUR_DATE'
    )
    part_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='故障部位', name='PART_NAME'
    )
    final_diagnosis: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='终判故障部位', name='FINAL_DIAGNOSIS'
    )
    fault_component: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='终判故障部位物料编码', name='FAULT_COMPONENT'
    )
    fault_material_code: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='原物料编码', name='FAULT_MATERIAL_CODE'
    )
    final_matia_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='故障部位物料编号', name='FINAL_MATIA_ID'
    )
    fault_mode: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='终判故障模式', name='FAULT_MODE'
    )
    fault_type: Mapped[str | None] = mapped_column(
        String(256), nullable=True, comment='故障类型', name='FAULT_TYPE'
    )
    jl_fault_type: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='终判故障类型', name='JL_FAULT_TYPE'
    )
    final_fault_responsibility: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='最终判责', name='FINAL_RESPONSIBILITY'
    )
    serial_number: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='原部件序列号', name='SERIAL_NUMBER'
    )
    new_serial_number: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='更换件序列号', name='NEW_SERIAL_NUMBER'
    )
    is_zero: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment='是否0运行时长(是/否)', name='IS_ZERO'
    )
    is_yj_product: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment='是否永济公司产品(是/否)', name='IS_YJ_PRODUCT'
    )
    park_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment='风场名称', name='PARK_NAME'
    )

    @hybrid_property
    def product_lifetime_stage(self):
        """造修阶段: 风电无此维度, 恒为None"""
        return None

    @product_lifetime_stage.inplace.expression
    @classmethod
    def product_lifetime_stage(cls):
        from sqlalchemy import null

        return null()

    @hybrid_property
    def loss_accounting(self):
        """损失核算: 风电无此字段, 恒为None"""
        return None

    @loss_accounting.inplace.expression
    @classmethod
    def loss_accounting(cls):
        from sqlalchemy import null

        return null()

    @hybrid_property
    def job_duration(self):
        """作业时长: 风电无此字段, 恒为None"""
        return None

    @job_duration.inplace.expression
    @classmethod
    def job_duration(cls):
        from sqlalchemy import null

        return null()

    @hybrid_property
    def report_id(self) -> str:
        """报告编号: 故障单编号兜底, 保证必填字段非空"""
        return self.id or self.info_no or ''

    @hybrid_property
    def fault_location(self):
        """终判故障部位名称, 回退故障部位"""
        return self.final_diagnosis or self.part_name

    @fault_location.inplace.expression
    @classmethod
    def fault_location(cls):
        return func.coalesce(func.nullif(cls.final_diagnosis, ''), cls.part_name)

    @hybrid_property
    def fault_part_code(self):
        """故障部位物料编码: 终判编码回退原物料编码/部位编号"""
        return self.fault_component or self.fault_material_code or self.final_matia_id

    @fault_part_code.inplace.expression
    @classmethod
    def fault_part_code(cls):
        return func.coalesce(
            func.nullif(cls.fault_component, ''),
            func.nullif(cls.fault_material_code, ''),
            cls.final_matia_id,
        )

    @hybrid_property
    def is_zero_distance(self):
        """是否零运行时长: 见 cn_yes_no_to_int 语义说明"""
        return cn_yes_no_to_int(self.is_zero)

    @is_zero_distance.inplace.expression
    @classmethod
    def is_zero_distance(cls):
        return case((cls.is_zero == '是', 1), (cls.is_zero == '否', 0), else_=None)

    @hybrid_property
    def is_company(self):
        """是否本公司产品: 见 cn_yes_no_to_int 语义说明"""
        return cn_yes_no_to_int(self.is_yj_product)

    @is_company.inplace.expression
    @classmethod
    def is_company(cls):
        return case((cls.is_yj_product == '是', 1), (cls.is_yj_product == '否', 0), else_=None)
