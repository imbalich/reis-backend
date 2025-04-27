#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：reis-backend 
@File    ：sense_sort.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/4/25 10:18 
'''
from datetime import date

from sqlalchemy import String, Date
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key
from backend.utils.timezone import timezone


class SenseSort(DataClassBase):
    """产品级别拟合结果"""

    __tablename__ = 'sense_sort'

    id: Mapped[id_key] = mapped_column(init=False)
    group_id: Mapped[str] = mapped_column(String(50), index=True, comment='分组ID')

    model: Mapped[str] = mapped_column(String(30), index=True, comment='型号')
    part: Mapped[str] = mapped_column(String(30), index=True, comment='零部件物料编码')
    stage: Mapped[str] = mapped_column(String(30), index=True, comment='造修阶段')
    process_name: Mapped[str] = mapped_column(String(50),nullable=True, comment='工序名称')
    check_project: Mapped[str] = mapped_column(String(30),nullable=True, comment='检验区位')
    check_bezier: Mapped[str] = mapped_column(String(30),nullable=True, comment='检验项点')
    start_time: Mapped[date] = mapped_column(Date, nullable=True, comment='计算开始时间')
    end_time: Mapped[date] = mapped_column(Date, nullable=True, comment='计算结束时间')
    extra_material_names: Mapped[str] = mapped_column(String(30),nullable=True, comment='配件/原材料名称')

    model_type: Mapped[str] = mapped_column(String(30), comment='算法类型')
    rela_self_value: Mapped[float | None] = mapped_column(comment='自检结果特征SHAP值')
    check_tools_sign: Mapped[float | None] = mapped_column(comment='检验工具编号特征SHAP值')
    self_create_by: Mapped[float | None] = mapped_column(comment='自检人特征SHAP值')
    extra_source_code: Mapped[float | None] = mapped_column(comment='配件/原材料追溯编号特征SHAP值')
    extra_supplier: Mapped[float | None] = mapped_column(comment='供应商特征SHAP值')
    categorical_analysis: Mapped[str] = mapped_column(LONGTEXT,comment='类别分析结果(json)')
    created_time: Mapped[date] = mapped_column(
        Date, init=False, default_factory=timezone.now_date, sort_order=999, comment='创建时间'
    )