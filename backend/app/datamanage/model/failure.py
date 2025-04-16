#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : failure.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/25 13:45
'''
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import DataClassBase, id_key


class Failure(DataClassBase):
    """
    故障提报-产品基础信息-国铁
    DWD.DWD_SER_MRO_FAULT_GT_INFO_D
    """

    __tablename__ = 'dm_failure'

    pk: Mapped[id_key] = mapped_column(init=False, nullable=False)
    id: Mapped[str] = mapped_column(String(128), nullable=True, comment='故障基本信息表中的报告ID')
    report_id: Mapped[str] = mapped_column(String(128), nullable=True, comment='报告编号')
    product_number: Mapped[str] = mapped_column(String(128), nullable=True, comment='产品编号', name="product_no")
    product_model: Mapped[str] = mapped_column(String(128), nullable=True, comment='产品型号')
    product_lifetime_stage: Mapped[str] = mapped_column(String(128), nullable=True, comment='修造级别',
                                                        name="repair_level")
    maintenance_location: Mapped[str] = mapped_column(String(128), nullable=True, comment='检修地点',
                                                      name="overhaul_location")
    last_maintenance_date: Mapped[str] = mapped_column(String(30), nullable=True, comment='检修出厂日期',
                                                       name="overhaul_factory_date")
    manufacturing_date: Mapped[str] = mapped_column(String(30), nullable=True, comment='新造日期',
                                                    name="production_data")
    allotment_now: Mapped[str] = mapped_column(String(128), nullable=True, comment='目前配属')
    road_subdivision: Mapped[str] = mapped_column(String(128), nullable=True, comment='一级配属', name="allotment_one")
    discovery_location: Mapped[str] = mapped_column(String(128), nullable=True, comment='二级配属',
                                                    name="allotment_two")
    allotment_date: Mapped[str] = mapped_column(String(128), nullable=True, comment='配属日期')
    train_model_name: Mapped[str] = mapped_column(String(128), nullable=True, comment='车型名称')
    train_no: Mapped[str] = mapped_column(String(128), nullable=True, comment='车辆编号')
    compartment_no: Mapped[str] = mapped_column(String(128), nullable=True, comment='装车位置/车厢编号')
    position: Mapped[str] = mapped_column(String(128), nullable=True, comment='轴位')
    train_number: Mapped[str] = mapped_column(String(128), nullable=True, comment='担当车次')
    operational_routing_start: Mapped[str] = mapped_column(String(128), nullable=True, comment='运行交路开始')
    operational_routing_end: Mapped[str] = mapped_column(String(128), nullable=True, comment='运行交路结束')
    discovery_date: Mapped[str] = mapped_column(String(30), nullable=True, comment='故障时间', name="fault_date")
    fault_address: Mapped[str] = mapped_column(String(128), nullable=True, comment='故障地点')
    fault_location: Mapped[str] = mapped_column(String(128), nullable=True, comment='终判故障部位名称',
                                                name="fault_part_name")
    fault_material_code: Mapped[str] = mapped_column(String(128), nullable=True, comment='终判故障部位物料代号',
                                                     name="fault_part_code")
    supplier: Mapped[str] = mapped_column(String(128), nullable=True, comment='供应商/供方名称')
    fault_mode: Mapped[str] = mapped_column(String(128), nullable=True, comment='终判故障模式', name="failure_mode")
    fault_interval_start: Mapped[str] = mapped_column(String(128), nullable=True, comment='故障区间起始')
    fault_interval_end: Mapped[str] = mapped_column(String(128), nullable=True, comment='故障区间结束')
    total_train_milage: Mapped[int] = mapped_column(nullable=True, comment='车组运行里程')
    fault_type: Mapped[str] = mapped_column(String(128), nullable=True, comment='终判故障类型')
    final_fault_responsibility: Mapped[str] = mapped_column(String(128), nullable=True, comment='责任用户',
                                                            name="respons")
    vehicle_fault_codes: Mapped[str] = mapped_column(String(128), nullable=True, comment='车载故障代码')
    fault_part_number: Mapped[str] = mapped_column(String(255), nullable=True, comment='故障件编号')
    fault_part_batch_no: Mapped[str] = mapped_column(String(128), nullable=True, comment='故障件批次号')
    fault_part_serial_number: Mapped[str] = mapped_column(String(128), nullable=True, comment='故障件序列号')
    replacement_part_number: Mapped[str] = mapped_column(String(255), nullable=True, comment='更换件编号')
    repl_part_batch_no: Mapped[str] = mapped_column(String(128), nullable=True, comment='更换件批次号')
    repl_part_serial_number: Mapped[str] = mapped_column(String(128), nullable=True, comment='更换件序列号')
    disposal_end_date: Mapped[str] = mapped_column(String(30), nullable=True, comment='处置完成日期')
    allotment_status: Mapped[str] = mapped_column(String(128), nullable=True, comment='配属状态')
    impact_level: Mapped[str] = mapped_column(String(128), nullable=True, comment='影响级别')
    is_online: Mapped[str] = mapped_column(String(128), nullable=True, comment='在线/返修')
    new_supplier: Mapped[str] = mapped_column(String(128), nullable=True, comment='更换件的供应商')
    life_cycle_time_erp: Mapped[str] = mapped_column(String(30), nullable=True, comment='新造日期ERP')
    cj_date: Mapped[str] = mapped_column(String(128), nullable=True, comment='采集时间')
    first_fault_part_name: Mapped[str] = mapped_column(String(128), nullable=True, comment='初判故障部位名称')
    first_fault_part_code: Mapped[str] = mapped_column(String(128), nullable=True, comment='初判故障部位物料代号')
    first_failure_mode: Mapped[str] = mapped_column(String(128), nullable=True, comment='初判故障模式')
    first_fault_type: Mapped[str] = mapped_column(String(128), nullable=True, comment='初判故障类型')
    fault_part_name_old: Mapped[str] = mapped_column(String(128), nullable=True, comment='终判故障部位名称_未改')
    is_zero_distance: Mapped[int] = mapped_column(nullable=True, comment='是否为零公里 1:是,0:否', name="is_zero")
