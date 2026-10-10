#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科学库存计算后台任务。
"""

from datetime import date

from backend.app.calcu.schema.science_warehouse import (
    DEFAULT_SCIENCE_WAREHOUSE_INPUT_DATE,
)
from backend.app.calcu.service.science_warehouse_service_change import (
    ScienceWarehouseServiceChange,
)
from backend.app.datamanage.crud.crud_warehouse_inventory import warehouse_inventory_dao
from backend.app.task.celery import celery_app
from backend.app.task.tasks.base import TaskBase
from backend.common.exception.errors import DataValidationError
from backend.database.db import async_db_session


@celery_app.task(name="science_warehouse_calculation_task", base=TaskBase)
async def science_warehouse_calculation_task(
    time_interval_days: int = 180,
    input_date: str = None,
    product_model: str | None = None,
    product_config_code: str | None = None,
) -> str:
    """
    后台任务: 科学库存需求计算。
    """
    try:
        parsed_input_date = (
            date.fromisoformat(input_date)
            if input_date
            else DEFAULT_SCIENCE_WAREHOUSE_INPUT_DATE
        )

        async with async_db_session() as db:
            inventories = await warehouse_inventory_dao.get_all(db)
        warehouse_spare_pairs = []
        seen = set()
        for inventory in inventories:
            pair = (inventory.warehouse_code, inventory.part_code)
            if pair in seen:
                continue
            seen.add(pair)
            warehouse_spare_pairs.append(pair)

        if not warehouse_spare_pairs:
            return "警告：未找到任何库房-备件组合，请检查数据库"

        result = await ScienceWarehouseServiceChange.batch_warehouse_spare_calculate(
            time_interval_days=time_interval_days,
            input_date=parsed_input_date,
            warehouse_spare_pairs=warehouse_spare_pairs,
            save_to_db=True,
        )
        return (
            f"科学库存计算完成 - 计算批次ID: {result.get('calculation_id')}, "
            f"总组合数: {result.get('total_pairs', 0)}, "
            f"成功: {result.get('success_count', 0)}, "
            f"失败: {result.get('failed_count', 0)}"
        )

    except DataValidationError as e:
        return f"数据验证错误: {str(e.msg)}"
    except Exception as e:
        return f"科学库存计算失败: {str(e)}"


@celery_app.task(name="science_warehouse_push_task", base=TaskBase)
async def science_warehouse_push_task(calculation_id: str, push_reason: str) -> str:
    """
    后台任务: 推送人工审查后的科学库存结果到 ESB。
    """
    try:
        from backend.app.calcu.service.science_warehouse_push_service import (
            science_warehouse_push_service,
        )

        result = await science_warehouse_push_service.push_by_calculation_id(
            calculation_id=calculation_id,
            push_reason=push_reason,
        )
        return (
            f"科学库存推送完成 - 计算批次ID: {result['calculation_id']}, "
            f"总记录数: {result['total_records']}, 状态: {result['status']}"
        )
    except Exception as e:
        return f"科学库存推送失败: {str(e)}"
