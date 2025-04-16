#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from datetime import date, datetime
from sqlalchemy import String, Date
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class Configuration(DataClassBase):
    __tablename__ = 'dm_configuration'

    id: Mapped[id_key] = mapped_column(init=False)
    prod_model: Mapped[str] = mapped_column(String(255), nullable=True, comment='产品型号')
    product_no: Mapped[str] = mapped_column(String(255), nullable=True, comment='电机编号/产品编号')
    product_serial_no: Mapped[str] = mapped_column(String(255), nullable=True, comment='产品编号')
    process_name: Mapped[str] = mapped_column(String(255), nullable=True, comment='工序名称')
    extra_material_code: Mapped[str] = mapped_column(String(255), nullable=True, comment='物料代码')
    extra_material_name: Mapped[str] = mapped_column(LONGTEXT, nullable=True, comment='物料名称')
    extra_product_batch_no: Mapped[str] = mapped_column(String(255), nullable=True, comment='产品序列号/批次号')
    extra_supplier: Mapped[str] = mapped_column(String(255), nullable=True, comment='供应商')
    extra2_file_version: Mapped[str] = mapped_column(String(255), nullable=True, comment='图号版本')
    extra2_material_state: Mapped[str] = mapped_column(String(255), nullable=True, comment='状态')
    extra_source_code: Mapped[str] = mapped_column(String(255), nullable=True, comment='配件/原材料追溯编号')
    repair_level: Mapped[str] = mapped_column(String(255), nullable=True, comment='寿命阶段')
    life_cycle_time: Mapped[date] = mapped_column(Date, nullable=True, comment='出厂日期')
    rela_self_value: Mapped[str] = mapped_column(String(255), nullable=True, comment='自检结果')
    self_create_by: Mapped[str] = mapped_column(String(255), nullable=True, comment='自检人/时间')
    rela_self_data: Mapped[str] = mapped_column(String(255), nullable=True, comment='自检时间')
    rela_mutual_value: Mapped[str] = mapped_column(String(255), nullable=True, comment='互检结果')
    mutual_create_by: Mapped[str] = mapped_column(String(255), nullable=True, comment='互检/时间')
    rela_mutual_data: Mapped[str] = mapped_column(String(255), nullable=True, comment='互检时间')
    rela_special_test_value: Mapped[str] = mapped_column(String(255), nullable=True, comment='专检结果')
    special_create_by: Mapped[str] = mapped_column(String(255), nullable=True, comment='专检/时间')
    rela_special_test_data: Mapped[str] = mapped_column(String(255), nullable=True, comment='专检时间')
    version: Mapped[str] = mapped_column(String(128), nullable=True, comment='PC版本')
    check_project: Mapped[str] = mapped_column(String(255), nullable=True, comment='检修区位')
    check_bezier: Mapped[str] = mapped_column(String(255), nullable=True, comment='检修项点')
    cj_date: Mapped[date] = mapped_column(Date, nullable=True, comment='采集时间')
    create_time: Mapped[datetime] = mapped_column(Date, nullable=True, comment='操作日期')
    create_by_name: Mapped[str] = mapped_column(String(255), nullable=True, comment='操作人')
