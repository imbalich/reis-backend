#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Optional

from pydantic import ConfigDict, Field

from backend.common.schema import SchemaBase


class FailureSchemaBase(SchemaBase):
    id: Optional[str] = Field(None, description='report id')
    report_id: Optional[str] = Field(None, description='report code')
    product_number: Optional[str] = Field(None, description='product number')
    product_model: Optional[str] = Field(None, description='product model')
    product_config_code: Optional[str] = Field(None, description='product config code')
    fault_location: Optional[str] = Field(None, description='fault location')
    fault_material_code: Optional[str] = Field(None, description='fault material code')
    supplier: Optional[str] = Field(None, description='supplier')
    fault_mode: Optional[str] = Field(None, description='fault mode')
    fault_interval_start: Optional[str] = Field(None, description='fault interval start')
    fault_interval_end: Optional[str] = Field(None, description='fault interval end')
    total_train_milage: Optional[str] = Field(None, description='total train mileage')
    fault_type: Optional[str] = Field(None, description='fault type')
    final_fault_responsibility: Optional[str] = Field(None, description='fault responsibility')
    vehicle_fault_codes: Optional[str] = Field(None, description='vehicle fault codes')
    fault_part_number: Optional[str] = Field(None, description='fault part number')
    fault_part_batch_no: Optional[str] = Field(None, description='fault part batch no')
    fault_part_serial_number: Optional[str] = Field(None, description='fault part serial number')
    replacement_part_number: Optional[str] = Field(None, description='replacement part number')
    repl_part_batch_no: Optional[str] = Field(None, description='replacement part batch no')
    repl_part_serial_number: Optional[str] = Field(None, description='replacement part serial number')
    disposal_end_date: Optional[str] = Field(None, description='disposal end date')
    allotment_status: Optional[str] = Field(None, description='allotment status')
    impact_level: Optional[str] = Field(None, description='impact level')
    is_online: Optional[str] = Field(None, description='is online')
    new_supplier: Optional[str] = Field(None, description='new supplier')
    life_cycle_time_erp: Optional[str] = Field(None, description='life cycle time erp')
    cj_date: Optional[str] = Field(None, description='collection date')
    first_fault_part_name: Optional[str] = Field(None, description='first fault part name')
    first_fault_part_code: Optional[str] = Field(None, description='first fault part code')
    first_failure_mode: Optional[str] = Field(None, description='first failure mode')
    first_fault_type: Optional[str] = Field(None, description='first fault type')
    fault_part_name_old: Optional[str] = Field(None, description='legacy fault part name')
    is_zero_distance: Optional[int] = Field(None, description='zero distance flag')


class CreateFailureParam(FailureSchemaBase):
    pass


class GetFailureParam(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    pk: int
    report_id: str
    product_model: Optional[str] = Field(None, description='product model')
    product_config_code: Optional[str] = Field(None, description='product config code')
    fault_location: Optional[str] = Field(None, description='fault location')
    fault_material_code: Optional[str] = Field(None, description='fault material code')
    product_number: Optional[str] = Field(None, description='product number')
    discovery_date: Optional[str] = Field(None, description='discovery date')
    is_zero_distance: Optional[int] = Field(None, description='zero distance flag')
    product_lifetime_stage: Optional[str] = Field(None, description='product lifetime stage')


class GetFailureDetails(GetFailureParam):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = Field(None, description='report id')
    fault_mode: Optional[str] = Field(None, description='fault mode')
    maintenance_location: Optional[str] = Field(None, description='maintenance location')
    last_maintenance_date: Optional[str] = Field(None, description='last maintenance date')
    manufacturing_date: Optional[str] = Field(None, description='manufacturing date')
    allotment_now: Optional[str] = Field(None, description='current allotment')
    road_subdivision: Optional[str] = Field(None, description='road subdivision')
    discovery_location: Optional[str] = Field(None, description='discovery location')
    allotment_date: Optional[str] = Field(None, description='allotment date')
    train_model_name: Optional[str] = Field(None, description='train model name')
    train_no: Optional[str] = Field(None, description='train number')
    compartment_no: Optional[str] = Field(None, description='compartment no')
    position: Optional[str] = Field(None, description='position')
    train_number: Optional[str] = Field(None, description='train number')
    operational_routing_start: Optional[str] = Field(None, description='routing start')
    operational_routing_end: Optional[str] = Field(None, description='routing end')
    fault_address: Optional[str] = Field(None, description='fault address')
    supplier: Optional[str] = Field(None, description='supplier')
    fault_interval_start: Optional[str] = Field(None, description='fault interval start')
    fault_interval_end: Optional[str] = Field(None, description='fault interval end')
    total_train_milage: Optional[int] = Field(None, description='total train mileage')
    fault_type: Optional[str] = Field(None, description='fault type')
    final_fault_responsibility: Optional[str] = Field(None, description='fault responsibility')
    vehicle_fault_codes: Optional[str] = Field(None, description='vehicle fault codes')
    fault_part_number: Optional[str] = Field(None, description='fault part number')
    fault_part_batch_no: Optional[str] = Field(None, description='fault part batch no')
    fault_part_serial_number: Optional[str] = Field(None, description='fault part serial number')
    replacement_part_number: Optional[str] = Field(None, description='replacement part number')
    repl_part_batch_no: Optional[str] = Field(None, description='replacement part batch no')
    repl_part_serial_number: Optional[str] = Field(None, description='replacement part serial number')
    disposal_end_date: Optional[str] = Field(None, description='disposal end date')
    allotment_status: Optional[str] = Field(None, description='allotment status')
    impact_level: Optional[str] = Field(None, description='impact level')
    is_online: Optional[str] = Field(None, description='is online')
    new_supplier: Optional[str] = Field(None, description='new supplier')
    life_cycle_time_erp: Optional[str] = Field(None, description='life cycle time erp')
    cj_date: Optional[str] = Field(None, description='collection date')
    first_fault_part_name: Optional[str] = Field(None, description='first fault part name')
    first_fault_part_code: Optional[str] = Field(None, description='first fault part code')
    first_failure_mode: Optional[str] = Field(None, description='first failure mode')
    first_fault_type: Optional[str] = Field(None, description='first fault type')
    fault_part_name_old: Optional[str] = Field(None, description='legacy fault part name')


class GetFailureListResponse(SchemaBase):
    model_config = ConfigDict(from_attributes=True)

    items: list[GetFailureDetails] = Field(default_factory=list, description='result list')
    total: int = Field(default=0, ge=0, description='total count')
