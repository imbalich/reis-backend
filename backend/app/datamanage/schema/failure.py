#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend
@File    ：base_param.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/25 14:56
'''
from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class FailureSchemaBase(SchemaBase):
    id: Optional[str] = Field(None, description='故障基本信息表中的报告ID')
    report_id: Optional[str] = Field(None, description='报告编号')
    product_number: Optional[str] = Field(None, description='产品编号')
    product_model: Optional[str] = Field(None, description='产品型号')
    product_lifetime_stage: Optional[str] = Field(None, description='修造级别')
    maintenance_location: Optional[str] = Field(None, description='检修地点')
    last_maintenance_date: Optional[str] = Field(None, description='检修出厂日期')
    manufacturing_date: Optional[str] = Field(None, description='新造日期')
    allotment_now: Optional[str] = Field(None, description='目前配属')
    road_subdivision: Optional[str] = Field(None, description='一级配属')
    discovery_location: Optional[str] = Field(None, description='二级配属')
    allotment_date: Optional[str] = Field(None, description='配属日期')
    train_model_name: Optional[str] = Field(None, description='车型名称')
    train_no: Optional[str] = Field(None, description='车辆编号')
    compartment_no: Optional[str] = Field(None, description='装车位置/车厢编号')
    position: Optional[str] = Field(None, description='轴位')
    train_number: Optional[str] = Field(None, description='担当车次')
    operational_routing_start: Optional[str] = Field(None, description='运行交路开始')
    operational_routing_end: Optional[str] = Field(None, description='运行交路结束')
    discovery_date: Optional[str] = Field(None, description='故障时间')
    fault_address: Optional[str] = Field(None, description='故障地点')
    fault_location: Optional[str] = Field(None, description='终判故障部位名称')
    fault_material_code: Optional[str] = Field(None, description='终判故障部位物料代号')
    supplier: Optional[str] = Field(None, description='供应商/供方名称')
    fault_mode: Optional[str] = Field(None, description='终判故障模式')
    fault_interval_start: Optional[str] = Field(None, description='故障区间起始')
    fault_interval_end: Optional[str] = Field(None, description='故障区间结束')
    total_train_milage: Optional[str] = Field(None, description='车组运行里程')
    fault_type: Optional[str] = Field(None, description='终判故障类型')
    final_fault_responsibility: Optional[str] = Field(None, description='责任用户')
    vehicle_fault_codes: Optional[str] = Field(None, description='车载故障代码')
    fault_part_number: Optional[str] = Field(None, description='故障件编号')
    fault_part_batch_no: Optional[str] = Field(None, description='故障件批次号')
    fault_part_serial_number: Optional[str] = Field(None, description='故障件序列号')
    replacement_part_number: Optional[str] = Field(None, description='更换件编号')
    repl_part_batch_no: Optional[str] = Field(None, description='更换件批次号')
    repl_part_serial_number: Optional[str] = Field(None, description='更换件序列号')
    disposal_end_date: Optional[str] = Field(None, description='处置完成日期')
    allotment_status: Optional[str] = Field(None, description='配属状态')
    impact_level: Optional[str] = Field(None, description='影响级别')
    is_online: Optional[str] = Field(None, description='在线/返修')
    new_supplier: Optional[str] = Field(None, description='更换件的供应商')
    life_cycle_time_erp: Optional[str] = Field(None, description='新造日期ERP')
    cj_date: Optional[str] = Field(None, description='采集时间')
    first_fault_part_name: Optional[str] = Field(None, description='初判故障部位名称')
    first_fault_part_code: Optional[str] = Field(None, description='初判故障部位物料代号')
    first_failure_mode: Optional[str] = Field(None, description='初判故障模式')
    first_fault_type: Optional[str] = Field(None, description='初判故障类型')
    fault_part_name_old: Optional[str] = Field(None, description='终判故障部位名称_未改')
    is_zero_distance: Optional[int] = Field(None, description='是否为零公里 1:是,0:否')

class CreateFailureParam(FailureSchemaBase):
    pass


class GetFailureParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    pk: int
    report_id: str
    product_model: str = Field(..., description='产品型号')
    fault_location: str = Field(..., description='终判故障部位')
    fault_material_code: str = Field(..., description='终判故障部位物料编码')
    product_lifetime_stage: str = Field(..., description='产品寿命阶段')
    product_number: str = Field(..., description='产品编号')
    fault_mode: str = Field(..., description='终判故障模式')
    discovery_date: str = Field(..., description='发现时间（日期）')
    is_zero_distance: int = Field(..., description='是否零公里(是/否)')

class GetFailureDetails(GetFailureParam):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = Field(None, description='故障基本信息表中的报告ID')
    maintenance_location: Optional[str] = Field(None, description='检修地点')
    last_maintenance_date: Optional[str] = Field(None, description='检修出厂日期')
    manufacturing_date: Optional[str] = Field(None, description='新造日期')
    allotment_now: Optional[str] = Field(None, description='目前配属')
    road_subdivision: Optional[str] = Field(None, description='一级配属')
    discovery_location: Optional[str] = Field(None, description='二级配属')
    allotment_date: Optional[str] = Field(None, description='配属日期')
    train_model_name: Optional[str] = Field(None, description='车型名称')
    train_no: Optional[str] = Field(None, description='车辆编号')
    compartment_no: Optional[str] = Field(None, description='装车位置/车厢编号')
    position: Optional[str] = Field(None, description='轴位')
    train_number: Optional[str] = Field(None, description='担当车次')
    operational_routing_start: Optional[str] = Field(None, description='运行交路开始')
    operational_routing_end: Optional[str] = Field(None, description='运行交路结束')
    fault_address: Optional[str] = Field(None, description='故障地点')
    supplier: Optional[str] = Field(None, description='供应商/供方名称')
    fault_interval_start: Optional[str] = Field(None, description='故障区间起始')
    fault_interval_end: Optional[str] = Field(None, description='故障区间结束')
    total_train_milage: Optional[int] = Field(None, description='车组运行里程')
    fault_type: Optional[str] = Field(None, description='终判故障类型')
    final_fault_responsibility: Optional[str] = Field(None, description='责任用户')
    vehicle_fault_codes: Optional[str] = Field(None, description='车载故障代码')
    fault_part_number: Optional[str] = Field(None, description='故障件编号')
    fault_part_batch_no: Optional[str] = Field(None, description='故障件批次号')
    fault_part_serial_number: Optional[str] = Field(None, description='故障件序列号')
    replacement_part_number: Optional[str] = Field(None, description='更换件编号')
    repl_part_batch_no: Optional[str] = Field(None, description='更换件批次号')
    repl_part_serial_number: Optional[str] = Field(None, description='更换件序列号')
    disposal_end_date: Optional[str] = Field(None, description='处置完成日期')
    allotment_status: Optional[str] = Field(None, description='配属状态')
    impact_level: Optional[str] = Field(None, description='影响级别')
    is_online: Optional[str] = Field(None, description='在线/返修')
    new_supplier: Optional[str] = Field(None, description='更换件的供应商')
    life_cycle_time_erp: Optional[str] = Field(None, description='新造日期ERP')
    cj_date: Optional[str] = Field(None, description='采集时间')
    first_fault_part_name: Optional[str] = Field(None, description='初判故障部位名称')
    first_fault_part_code: Optional[str] = Field(None, description='初判故障部位物料代号')
    first_failure_mode: Optional[str] = Field(None, description='初判故障模式')
    first_fault_type: Optional[str] = Field(None, description='初判故障类型')
    fault_part_name_old: Optional[str] = Field(None, description='终判故障部位名称_未改')


class GetFailureListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetFailureDetails] = Field(default_factory=list, description="查询结果列表")
    total: int = Field(default=0, ge=0, description="总记录数")


    












