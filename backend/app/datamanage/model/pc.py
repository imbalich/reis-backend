#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：pc.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/3/24 10:35 
'''
from datetime import date

from sqlalchemy import String, Date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import LONGTEXT

from backend.common.model import DataClassBase, id_key


class PC(DataClassBase):
    __tablename__ = "dm_pc"

    id: Mapped[id_key] = mapped_column(init=False)
    prod_model: Mapped[str] = mapped_column(String(255), nullable=True, comment='产品型号')
    purchase_code: Mapped[str] = mapped_column(String(128), nullable=True, comment='订单编号')
    process_name: Mapped[str] = mapped_column(String(255), nullable=True, comment='工序名称')
    product_serial_no: Mapped[str] = mapped_column(String(255), nullable=True, comment='电机编号/产品编号')
    product_serial_no_2: Mapped[str] = mapped_column(String(255), nullable=True, comment='产品编号')
    extra_material_name: Mapped[str] = mapped_column(String(255), nullable=True, comment='物料名称/追溯零部件')
    version: Mapped[str] = mapped_column(String(255), nullable=True, comment='PC表版本号')
    manufaucture_date: Mapped[date] = mapped_column(Date, nullable=True, comment='出厂日期')
    check_project: Mapped[str] = mapped_column(String(255), nullable=True, comment='检验区位')
    check_bezier: Mapped[str] = mapped_column(String(255), nullable=True, comment='检验项点')
    check_standard: Mapped[str] = mapped_column(LONGTEXT, nullable=True, comment='质量标准')
    check_tools: Mapped[str] = mapped_column(String(255), nullable=True, comment='检验工具')
    check_tools_sign: Mapped[str] = mapped_column(String(255), nullable=True, comment='工具编号')
    unit_name: Mapped[str] = mapped_column(String(255), nullable=True, comment='单位')
    rela_self_value: Mapped[str] = mapped_column(String(255), nullable=True, comment='自检结果')
    self_create_by: Mapped[str] = mapped_column(String(255), nullable=True, comment='自检人/时间')
    rela_self_data: Mapped[str] = mapped_column(String(255), nullable=True, comment='自检时间')
    rela_mutual_value: Mapped[str] = mapped_column(String(255), nullable=True, comment='互检结果')
    mutual_create_by: Mapped[str] = mapped_column(String(255), nullable=True, comment='互检/时间')
    rela_mutual_data: Mapped[str] = mapped_column(String(255), nullable=True, comment='互检时间')
    rela_special_test_value: Mapped[str] = mapped_column(String(255), nullable=True, comment='专检结果')
    special_create_by: Mapped[str] = mapped_column(String(255), nullable=True, comment='专检/时间')
    rela_special_test_data: Mapped[str] = mapped_column(String(255), nullable=True, comment='专检时间')
    material_figure_no: Mapped[str] = mapped_column(String(255), nullable=True, comment='产品图号')
    extra_type: Mapped[str] = mapped_column(String(255), nullable=True, comment='数据类型')
    repair_level: Mapped[str] = mapped_column(String(255), nullable=True, comment='寿命阶段')
    cj_date: Mapped[date] = mapped_column(Date, nullable=True, comment='采集时间')
