#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科学库存计算后台任务
"""

from datetime import date

from backend.app.calcu.service.science_warehouse_service import (
    science_warehouse_service,
)
from backend.app.calcu.service.science_warehouse_service_change import (
    ScienceWarehouseServiceChange,
)
from backend.app.datamanage.crud.crud_warehouse_inventory import warehouse_inventory_dao
from backend.app.task.tasks.base import TaskBase
from backend.common.exception.errors import DataValidationError
from backend.app.task.celery import celery_app
from backend.database.db import async_db_session


@celery_app.task(name="science_warehouse_calculation_task", base=TaskBase)
async def science_warehouse_calculation_task(
    time_interval_days: int = 180,
    input_date: str = None,
    product_model: str | None = None,
    product_config_code: str | None = None,
) -> str:
    """
    Science Warehouse
    后台任务:科学库存需求计算

    :param time_interval_days: 需求预测时间间隔（天数）,默认180天
    :param input_date: 计算截止日期，格式为 YYYY-MM-DD 的字符串，默认为当前日期
    :return: 任务执行结果
    """
    try:
        # 处理 input_date 参数
        parsed_input_date = None
        if input_date:
            parsed_input_date = date.fromisoformat(input_date)

        if product_model is not None or product_config_code is not None:
            result = (
                await science_warehouse_service.calculate_science_warehouse_requirements(
                    time_interval_days=time_interval_days,
                    input_date=parsed_input_date,
                    product_model=product_model,
                    product_config_code=product_config_code,
                )
            )
            return (
                f"科学库存计算完成（新维度过滤走主服务） - "
                f"计算批次ID: {result.calculation_id}, "
                f"总备品数量: {result.statistics.get('total_warehouse_spares', 0)}"
            )

        # 执行科学库存计算
        result = (
            await science_warehouse_service.calculate_science_warehouse_requirements(
                time_interval_days=time_interval_days,
                input_date=parsed_input_date,
                product_model=product_model,
                product_config_code=product_config_code,
            )
        )

        return f"科学库存计算完成 - 计算批次ID: {result.calculation_id}, 总备品数量: {result.statistics.get('total_warehouse_spares', 0)}"

    except DataValidationError as e:
        return f"数据验证错误: {str(e.msg)}"
    except Exception as e:
        return f"科学库存计算失败: {str(e)}"


@celery_app.task(name="science_warehouse_calculation_and_api_task", base=TaskBase)
async def science_warehouse_calculation_and_api_task(
    time_interval_days: int = 180,
    input_date: str = None,
    product_model: str | None = None,
    product_config_code: str | None = None,
) -> str:
    """
    后台任务:科学库存需求计算并返回API格式结果

    :param time_interval_days: 需求预测时间间隔（天数）,默认180天
    :param input_date: 计算截止日期，格式为 YYYY-MM-DD 的字符串，默认为当前日期
    :return: 任务执行结果
    """
    try:
        # 处理 input_date 参数
        parsed_input_date = None
        if input_date:
            parsed_input_date = date.fromisoformat(input_date)

        # 1. 执行科学库存计算
        result = (
            await science_warehouse_service.calculate_science_warehouse_requirements(
                time_interval_days=time_interval_days,
                input_date=parsed_input_date,
                product_model=product_model,
                product_config_code=product_config_code,
            )
        )

        # 2. 获取API格式数据
        api_data = await science_warehouse_service.get_calculation_results_for_api(
            result.calculation_id
        )

        return f"科学库存计算并生成API数据完成 - 计算批次ID: {result.calculation_id}, API数据条数: {len(api_data) if api_data else 0}"

    except DataValidationError as e:
        return f"数据验证错误: {str(e.msg)}"
    except Exception as e:
        return f"科学库存计算失败: {str(e)}"


@celery_app.task(name="science_warehouse_calculation_v2_task", base=TaskBase)
async def science_warehouse_calculation_v2_task(
    time_interval_days: int = 180,
    input_date: str = None,
    product_model: str | None = None,
    product_config_code: str | None = None,
) -> str:
    """
    后台任务:科学库存需求计算（新版本）

    :param time_interval_days: 需求预测时间间隔（天数）,默认180天
    :param input_date: 计算截止日期，格式为 YYYY-MM-DD 的字符串，默认为当前日期
    :return: 任务执行结果
    """
    try:
        # 处理 input_date 参数
        parsed_input_date = None
        if input_date:
            parsed_input_date = date.fromisoformat(input_date)

        # 1. 获取所有库房-备品组合
        async with async_db_session() as db:
            all_inventories = await warehouse_inventory_dao.get_all(db)
            # 提取唯一的库房-备件组合
            warehouse_spare_pairs = []
            seen = set()
            for inventory in all_inventories:
                pair = (inventory.warehouse_code, inventory.part_code)
                if pair not in seen:
                    seen.add(pair)
                    warehouse_spare_pairs.append(pair)

        if not warehouse_spare_pairs:
            return "警告：未找到任何库房-备件组合，请检查数据库"

        # 2. 执行批量科学库存计算
        result = await ScienceWarehouseServiceChange.batch_warehouse_spare_calculate(
            time_interval_days=time_interval_days,
            input_date=parsed_input_date,
            warehouse_spare_pairs=warehouse_spare_pairs,
            save_to_db=True,
        )

        return (
            f"科学库存计算完成（新版本） - "
            f"计算批次ID: {result.get('calculation_id')}, "
            f"总组合数: {result.get('total_pairs', 0)}, "
            f"成功: {result.get('success_count', 0)}, "
            f"失败: {result.get('failed_count', 0)}, "
            f"总备件量: {result.get('total_quantity', 0)}"
        )

    except DataValidationError as e:
        return f"数据验证错误: {str(e.msg)}"
    except Exception as e:
        return f"科学库存计算失败（新版本）: {str(e)}"
