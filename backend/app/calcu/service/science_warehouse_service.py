#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 科学库存服务,支援国铁售后需求
import math
import json
import time
from collections import defaultdict
from datetime import date, timedelta, datetime
from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.calcu.schema.science_warehouse import (
        ScienceWarehouseCalculationResponse,
        ScienceWarehouseDetailsResponse,
    )

from backend.app.datamanage.crud.crud_warehouse import warehouse_dao
from backend.app.datamanage.crud.crud_warehouse_inventory import warehouse_inventory_dao
from backend.app.datamanage.crud.crud_part_spare_mapping import part_spare_mapping_dao
from backend.app.datamanage.crud.crud_allotment import allotment_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.calcu.crud.crud_science_warehouse_result import (
    science_warehouse_result_dao,
)
from typing import Sequence

# 统计表相关逻辑已移除，不再导入
# from backend.app.calcu.crud.crud_science_warehouse_statistics import (
#     science_warehouse_statistics_dao,
# )
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.utils.time_utils import dateutils
from backend.database.db import async_db_session
from backend.utils.snowflake import snowflake


def parse_discovery_date(discovery_date_str: str) -> Optional[date]:
    """
    解析故障发现日期字符串为date对象

    :param discovery_date_str: 日期字符串
    :return: 解析后的date对象，解析失败返回None
    """
    if not discovery_date_str or not isinstance(discovery_date_str, str):
        return None

    # 去除前后空格
    discovery_date_str = discovery_date_str.strip()

    if not discovery_date_str:
        return None

    # 尝试多种日期格式
    date_formats = [
        "%Y-%m-%d",  # 2023-12-25
        "%Y/%m/%d",  # 2023/12/25
        "%Y%m%d",  # 20231225
        "%Y-%m-%d %H:%M:%S",  # 2023-12-25 10:30:00
        "%Y/%m/%d %H:%M:%S",  # 2023/12/25 10:30:00
        "%Y-%m-%d %H:%M",  # 2023-12-25 10:30
        "%Y/%m/%d %H:%M",  # 2023/12/25 10:30
    ]

    for fmt in date_formats:
        try:
            parsed_datetime = datetime.strptime(discovery_date_str, fmt)
            return parsed_datetime.date()
        except ValueError:
            continue

    # 如果所有格式都失败，尝试pandas的自动解析
    try:
        import pandas as pd

        parsed_datetime = pd.to_datetime(discovery_date_str)
        return parsed_datetime.date()
    except:
        pass

    return None


def is_failure_date_valid(failure_date_str: str, cutoff_date: date) -> bool:
    """
    检查故障日期是否在截止日期之前或等于截止日期

    :param failure_date_str: 故障日期字符串
    :param cutoff_date: 截止日期
    :return: 是否有效
    """
    parsed_date = parse_discovery_date(failure_date_str)
    if parsed_date is None:
        return False

    return parsed_date <= cutoff_date


class ScienceWarehouseService:
    @staticmethod
    async def calculate_science_warehouse_requirements(
        time_interval_days: int = 180,
        input_date: date = None,
        product_model: str | None = None,
        product_config_code: str | None = None,
    ) -> "ScienceWarehouseCalculationResponse":
        """
        科学库存需求计算主流程

        :param time_interval_days: 需求预测时间间隔（天数）,默认180天
        :param input_date: 计算截止日期（用于拟合）
        :return: 计算结果和统计信息
        """
        start_time = time.time()

        if not input_date:
            input_date = date.today()

        # 1. 获取所有库房备品清单
        warehouse_spares = await ScienceWarehouseService.get_all_warehouse_spare_list()

        # 统计总备品数量
        total_spares = sum(len(spares) for spares in warehouse_spares.values())

        # 2. 初始化结果和统计
        results = {}
        statistics = {
            "total_warehouse_spares": 0,
            "calculated_spares": 0,
            "default_spares": 0,
            "insufficient_failure_data_spares": 0,  # 新增：故障数据不足的备品数量
            "exponential_fit_success_spares": 0,  # 新增：指数分布拟合成功的备品数量
            "exponential_fit_fail_spares": 0,  # 新增：指数分布拟合失败的备品数量
            "skipped_failures": [],
            "mapping_errors": [],
            "maintenance_responsibility_analysis": {},
        }

        # 3. 按库房-备品维度计算
        calculation_start = time.time()
        processed_warehouses = 0
        processed_spares = 0

        for warehouse_code, spare_parts in warehouse_spares.items():
            processed_warehouses += 1
            results[warehouse_code] = {}
            statistics["maintenance_responsibility_analysis"][warehouse_code] = {
                "total_spares": len(spare_parts),
                "calculated": 0,
                "default": 0,
                "responsible_products": 0,
                "non_responsible_products": 0,
            }

            for spare_part in spare_parts:
                processed_spares += 1
                statistics["total_warehouse_spares"] += 1

                # 计算该库房该备品的需求
                spare_start = time.time()
                requirement_result = await ScienceWarehouseService.calculate_spare_requirement_with_coverage(
                    warehouse_code,
                    spare_part,
                    time_interval_days,
                    input_date,
                    product_model=product_model,
                    product_config_code=product_config_code,
                )
                spare_duration = time.time() - spare_start

                if requirement_result["calculated"]:
                    # 检查是否使用了指数分布拟合
                    maintenance_analysis = requirement_result.get(
                        "maintenance_analysis", {}
                    )
                    exponential_success = maintenance_analysis.get(
                        "exponential_fit_success_count", 0
                    )

                    if exponential_success > 0:
                        # 使用了指数分布拟合
                        calculation_method = "exponential_fit"
                        confidence = 0.5  # 指数分布拟合的置信度较低
                        statistics["exponential_fit_success_spares"] += 1
                    else:
                        # 使用正常拟合
                        calculation_method = "fitted"
                        confidence = requirement_result.get("confidence", 0.8)
                        statistics["calculated_spares"] += 1

                    results[warehouse_code][spare_part["part_code"]] = {
                        "part_name": spare_part["part_name"],
                        "required_quantity": requirement_result["quantity"],
                        "calculation_method": calculation_method,
                        "confidence": confidence,
                    }
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "calculated"
                    ] += 1
                elif requirement_result.get("insufficient_failure_data", False):
                    # 检查是否尝试了指数分布拟合但失败
                    maintenance_analysis = requirement_result.get(
                        "maintenance_analysis", {}
                    )
                    exponential_fail = maintenance_analysis.get(
                        "exponential_fit_fail_count", 0
                    )

                    if exponential_fail > 0:
                        # 指数分布拟合失败，使用默认数量
                        calculation_method = "exponential_fit_failed"
                        statistics["exponential_fit_fail_spares"] += 1
                    else:
                        # 直接使用默认数量（没有尝试指数分布拟合）
                        calculation_method = "insufficient_data"
                        statistics["insufficient_failure_data_spares"] += 1

                    results[warehouse_code][spare_part["part_code"]] = {
                        "part_name": spare_part["part_name"],
                        "required_quantity": spare_part["default_quantity"],
                        "calculation_method": calculation_method,
                        "confidence": 0.3,
                    }
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "default"
                    ] += 1
                else:
                    # 其他原因使用默认数量
                    results[warehouse_code][spare_part["part_code"]] = {
                        "part_name": spare_part["part_name"],
                        "required_quantity": spare_part["default_quantity"],
                        "calculation_method": "default",
                        "confidence": 0.5,
                    }
                    statistics["default_spares"] += 1
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "default"
                    ] += 1

                # 只记录错误数量，不保存详细错误信息（减少内存使用）
                statistics["skipped_failures"].extend(
                    requirement_result.get("skipped_failures", [])
                )
                statistics["mapping_errors"].extend(
                    requirement_result.get("mapping_errors", [])
                )

                # 简化维护责任分析统计
                if requirement_result.get("maintenance_analysis"):
                    maintenance_analysis = requirement_result["maintenance_analysis"]
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "responsible_products"
                    ] += maintenance_analysis.get("responsible_products", 0)
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "non_responsible_products"
                    ] += maintenance_analysis.get("non_responsible_products", 0)

        calculation_duration = time.time() - calculation_start

        # 4. 生成计算批次ID
        calculation_id = f"SW_{snowflake.generate()}"

        # 5. 保存计算结果到数据库
        await ScienceWarehouseService.save_calculation_results(
            calculation_id,
            results,
            statistics,
            time_interval_days,
            input_date,
            product_model=product_model,
            product_config_code=product_config_code,
        )

        # 导入Schema类
        from backend.app.calcu.schema.science_warehouse import (
            ScienceWarehouseCalculationResponse,
        )

        total_duration = time.time() - start_time

        return ScienceWarehouseCalculationResponse(
            calculation_id=calculation_id,
            statistics=statistics,
            calculation_period={
                "time_interval_days": time_interval_days,
                "input_date": input_date.isoformat() if input_date else None,
            },
        )

    @staticmethod
    def build_failure_dimension_key(failure: Any) -> str:
        return "_".join(
            [
                getattr(failure, "product_model", "") or "",
                getattr(failure, "product_config_code", "") or "",
                getattr(failure, "fault_material_code", "") or "",
            ]
        )

    @staticmethod
    def group_failures_by_dimension(failures: List[Any]) -> dict[str, list[Any]]:
        grouped: dict[str, list[Any]] = defaultdict(list)
        for failure in failures:
            grouped[ScienceWarehouseService.build_failure_dimension_key(failure)].append(
                failure
            )
        return grouped

    @staticmethod
    async def get_all_warehouse_spare_list() -> Dict[str, List[Dict[str, Any]]]:
        """
        获取所有库房备品清单

        :return: 按库房分组的备品清单 {库房编码: [备品信息列表]}
        """
        async with async_db_session() as db:
            # 获取所有库房备品清单
            warehouse_inventories = await warehouse_inventory_dao.get_all(db)

            # 按库房分组
            warehouse_spares = defaultdict(list)
            for inventory in warehouse_inventories:
                warehouse_spares[inventory.warehouse_code].append(
                    {
                        "part_code": inventory.part_code,
                        "part_name": inventory.part_name,
                        "default_quantity": inventory.default_quantity,
                    }
                )

            return dict(warehouse_spares)

    @staticmethod
    async def calculate_spare_requirement_with_coverage(
        warehouse_code: str,
        spare_part: dict,
        time_interval_days: int,
        input_date: date,
        product_model: str | None = None,
        product_config_code: str | None = None,
    ) -> Dict[str, Any]:
        """
        计算单个库房单个备品的需求数量（考虑库房-路局-产品关系）
        """

        result = {
            "calculated": False,
            "quantity": 0,
            "skipped_failures": [],
            "mapping_errors": [],
            "maintenance_analysis": {},
        }

        try:
            # 1. 获取库房支持的二级配属（路局）
            warehouse_allotments = (
                await ScienceWarehouseService.get_warehouse_allotments(warehouse_code)
            )

            if not warehouse_allotments:
                result["mapping_errors"].append(
                    {
                        "type": "no_warehouse_allotments",
                        "warehouse_code": warehouse_code,
                        "message": f"库房 {warehouse_code} 未找到支持的二级配属",
                    }
                )
                return result

            # 2. 获取使用此备品的产品型号（通过映射表）
            related_models = await ScienceWarehouseService.get_models_using_spare(
                spare_part["part_code"]
            )
            if product_model is not None:
                related_models = [model for model in related_models if model == product_model]

            if not related_models:
                result["mapping_errors"].append(
                    {
                        "type": "no_related_models",
                        "spare_part_code": spare_part["part_code"],
                        "message": f"备品 {spare_part['part_code']} 未找到相关产品型号",
                    }
                )
                return result

            # 3. 获取运行在库房覆盖路局上且型号匹配的产品编号（优化版本）
            filtered_products = []
            for allotment_two in warehouse_allotments:
                products_in_allotment = await ScienceWarehouseService.get_products_by_allotment_two_and_models(
                    allotment_two, related_models
                )
                filtered_products.extend(products_in_allotment)

            # 去重
            filtered_products = list(set(filtered_products))

            if not filtered_products:
                result["mapping_errors"].append(
                    {
                        "type": "no_relevant_products",
                        "spare_part_code": spare_part["part_code"],
                        "warehouse_code": warehouse_code,
                        "message": f"备品 {spare_part['part_code']} 在库房 {warehouse_code} 覆盖的路局上无相关产品",
                    }
                )
                return result

            # 5. 获取相关产品的故障数据
            all_failures = []
            skipped_failures = []

            for product_number in filtered_products:
                product_failures = (
                    await ScienceWarehouseService.get_failures_by_product_number(
                        product_number
                    )
                )

                # 过滤时间范围
                time_filtered_failures = []
                date_parse_errors = []

                for f in product_failures:
                    if is_failure_date_valid(f.discovery_date, input_date):
                        time_filtered_failures.append(f)
                    else:
                        # 记录日期解析失败的情况
                        parsed_date = parse_discovery_date(f.discovery_date)
                        if parsed_date is None:
                            date_parse_errors.append(
                                {
                                    "failure_id": f.id,
                                    "product_number": f.product_number,
                                    "discovery_date": f.discovery_date,
                                    "reason": "invalid_date_format",
                                }
                            )
                        else:
                            # 日期格式正确但超出时间范围
                            date_parse_errors.append(
                                {
                                    "failure_id": f.id,
                                    "product_number": f.product_number,
                                    "discovery_date": f.discovery_date,
                                    "parsed_date": str(parsed_date),
                                    "cutoff_date": str(input_date),
                                    "reason": "date_out_of_range",
                                }
                            )

                # 记录时间过滤结果

                # 将日期解析错误添加到跳过的故障中
                skipped_failures.extend(date_parse_errors)

                # 检查故障部件是否能映射到目标备品
                for failure in time_filtered_failures:
                    if product_model is not None and failure.product_model != product_model:
                        continue
                    if (
                        product_config_code is not None
                        and getattr(failure, "product_config_code", None) != product_config_code
                    ):
                        continue
                    mapping = await ScienceWarehouseService.get_part_spare_mapping(
                        failure.product_model,
                        getattr(failure, "product_config_code", None),
                        failure.fault_material_code,
                    )

                    if mapping and mapping.spare_part_code == spare_part["part_code"]:
                        all_failures.append(failure)
                    else:
                        skipped_failures.append(
                            {
                                "failure_id": failure.id,
                                "product_number": failure.product_number,
                                "product_model": failure.product_model,
                                "fault_material_code": failure.fault_material_code,
                                "reason": (
                                    "no_mapping_to_target_spare"
                                    if not mapping
                                    else "mapped_to_different_spare"
                                ),
                            }
                        )

            result["skipped_failures"] = skipped_failures

            if not all_failures:
                result["mapping_errors"].append(
                    {
                        "type": "no_relevant_failures",
                        "spare_part_code": spare_part["part_code"],
                        "warehouse_code": warehouse_code,
                        "message": f"备品 {spare_part['part_code']} 在库房 {warehouse_code} 未找到相关故障数据",
                    }
                )
                return result

            # 6. 进行寿命拟合和备件量计算
            calculation_result = (
                await ScienceWarehouseService.perform_spare_calculation_with_fit(
                    all_failures,
                    time_interval_days,
                    input_date,
                    warehouse_code,
                    spare_part["part_code"],
                )
            )

            if calculation_result["success"]:
                # 检查是否有故障数据不足的情况
                maintenance_analysis = calculation_result.get(
                    "maintenance_analysis", {}
                )
                if (
                    maintenance_analysis.get(
                        "insufficient_failure_data_combinations", 0
                    )
                    > 0
                ):
                    result["insufficient_failure_data"] = True
                    result["calculated"] = False
                    result["quantity"] = 0
                    result["confidence"] = 0.3
                else:
                    result["calculated"] = True
                    result["quantity"] = calculation_result["quantity"]
                    result["confidence"] = calculation_result.get("confidence", 0.8)
                    result["maintenance_analysis"] = maintenance_analysis
            else:
                result["mapping_errors"].append(
                    {
                        "type": "calculation_failed",
                        "spare_part_code": spare_part["part_code"],
                        "warehouse_code": warehouse_code,
                        "error": calculation_result.get("error", "未知错误"),
                    }
                )

        except Exception as e:
            result["mapping_errors"].append(
                {
                    "type": "exception",
                    "spare_part_code": spare_part["part_code"],
                    "warehouse_code": warehouse_code,
                    "error": str(e),
                }
            )

        return result

    @staticmethod
    async def perform_spare_calculation_with_fit(
        failures: List,
        time_interval_days: int,
        input_date: date,
        warehouse_code: str,
        spare_part_code: str,
    ) -> Dict[str, Any]:
        """
        基于故障数据进行寿命拟合和备件量计算（考虑库房维护责任）
        """

        try:
            # 1. 按产品型号+派生码+零部件编码分组故障数据
            failures_by_model_part = ScienceWarehouseService.group_failures_by_dimension(
                failures
            )

            # 2. 对每个型号+零部件组合进行备件量计算
            total_requirement = 0.0
            responsible_products = 0
            non_responsible_products = 0
            insufficient_failure_data_combinations = 0
            exponential_fit_success_count = 0
            exponential_fit_fail_count = 0

            for model_part_key, model_part_failures in failures_by_model_part.items():
                # 解析型号、派生码和零部件编码
                product_model, product_config_code, part_code = model_part_key.split("_", 2)
                product_numbers = list(
                    set([f.product_number for f in model_part_failures])
                )

                # 检查故障数量是否足够（需要 > 4 个）
                if len(model_part_failures) <= 4:

                    # 尝试使用指数分布拟合
                    try:
                        model_part_spare_quantity = await ScienceWarehouseService.exponential_fit_for_insufficient_data(
                            model_part_failures,
                            product_model,
                            product_config_code,
                            part_code,
                            time_interval_days,
                            input_date,
                        )

                        if model_part_spare_quantity > 0:
                            group_has_responsible_product = False

                            for product_number in product_numbers:
                                maintenance_responsibility = (
                                    await ScienceWarehouseService.check_maintenance_responsibility(
                                        product_number, warehouse_code, spare_part_code
                                    )
                                )

                                if maintenance_responsibility["responsible"]:
                                    group_has_responsible_product = True
                                    responsible_products += 1
                                else:
                                    non_responsible_products += 1

                            if group_has_responsible_product:
                                total_requirement += model_part_spare_quantity
                                exponential_fit_success_count += 1
                            else:
                                insufficient_failure_data_combinations += 1
                                exponential_fit_fail_count += 1
                        else:
                            # 指数分布拟合失败，使用默认值
                            insufficient_failure_data_combinations += 1
                            non_responsible_products += len(product_numbers)
                            exponential_fit_fail_count += 1

                    except Exception as e:
                        # 指数分布拟合异常，使用默认值
                        insufficient_failure_data_combinations += 1
                        non_responsible_products += len(product_numbers)
                        exponential_fit_fail_count += 1

                    continue

                # 使用已过滤的故障数据进行打标处理
                tags = await part_strategy_service.part_tag_process_with_failures(
                    product_model,
                    part_code,
                    input_date,
                    model_part_failures,
                    product_config_code=product_config_code,
                )

                # 进行拟合
                fit_result = await part_fit_service.tag_fit(tags)

                # 获取最佳分布
                best_distribution = fit_result.best_distribution

                # 计算该型号+零部件的备件量
                model_part_spare_quantity = (
                    await ScienceWarehouseService.calculate_spare_quantity_by_interval(
                        best_distribution,
                        time_interval_days,
                        model_part_failures,
                        input_date,
                    )
                )

                group_has_responsible_product = False

                # 检查每个产品是否由该库房负责维护
                for product_number in product_numbers:
                    maintenance_responsibility = (
                        await ScienceWarehouseService.check_maintenance_responsibility(
                            product_number, warehouse_code, spare_part_code
                        )
                    )

                    if maintenance_responsibility["responsible"]:
                        group_has_responsible_product = True
                        responsible_products += 1
                    else:
                        # 该库房不负责维护，不计入总需求
                        non_responsible_products += 1

                if group_has_responsible_product:
                    total_requirement += model_part_spare_quantity

            return {
                "success": True,
                "quantity": max(1, math.ceil(total_requirement)),  # 向上取整且最小为1
                "confidence": 0.8,
                "maintenance_analysis": {
                    "total_model_part_combinations": len(failures_by_model_part),
                    "responsible_products": responsible_products,
                    "non_responsible_products": non_responsible_products,
                    "insufficient_failure_data_combinations": insufficient_failure_data_combinations,
                    "exponential_fit_success_count": exponential_fit_success_count,
                    "exponential_fit_fail_count": exponential_fit_fail_count,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def calculate_spare_quantity_by_interval(
        best_distribution,
        time_interval_days: int,
        product_failures: List,
        input_date: date,
    ) -> float:
        """
        基于时间间隔计算备件量（CDF差值计算）
        参考 spare_service.py 中的计算逻辑
        """

        try:
            # 1. 获取产品信息（从第一个故障记录中获取产品型号）
            if not product_failures:
                return 0.0

            product_model = product_failures[0].product_model
            product_config_code = getattr(product_failures[0], "product_config_code", None)

            # 2. 获取产品运行参数
            async with async_db_session() as db:
                from backend.app.fit.schema.base_param import ProductParam
                from backend.app.fit.utils.convert_model import (
                    convert_to_pydantic_model,
                )
                from backend.app.datamanage.crud.crud_product import product_dao

                product_data = convert_to_pydantic_model(
                    await product_dao.get_by_model(
                        db, product_model, product_config_code=product_config_code
                    ),
                    ProductParam,
                )

            # 3. 计算每个产品的备件量
            result = 0.0
            product_list = {}

            # 4. 从 despatch 数据中获取产品发运日期信息
            # 获取所有产品编号
            product_numbers = list(set([f.product_number for f in product_failures]))

            # 从 despatch 表中获取发运日期
            async with async_db_session() as db:
                from backend.app.datamanage.crud.crud_despatch import despatch_dao

                # 获取所有相关的 despatch 数据
                despatch_data = await despatch_dao.select_models(
                    db, identifier__in=product_numbers, repair_level__eq="新造"
                )

                # 构建产品编号到发运日期的映射
                product_despatch_map = {}
                for despatch in despatch_data:
                    if despatch.identifier and despatch.life_cycle_time:
                        product_despatch_map[despatch.identifier] = (
                            despatch.life_cycle_time
                        )

                # 为每个产品编号设置发运日期
                for product_number in product_numbers:
                    if product_number not in product_list:
                        despatch_date = product_despatch_map.get(product_number)
                        if despatch_date:
                            product_list[product_number] = {"despatch": despatch_date}
                        else:
                            # 如果没有找到发运日期，使用故障发现日期作为近似
                            # 这种情况应该记录警告
                            first_failure = next(
                                (
                                    f
                                    for f in product_failures
                                    if f.product_number == product_number
                                ),
                                None,
                            )
                            if first_failure and first_failure.discovery_date:
                                parsed_date = parse_discovery_date(
                                    first_failure.discovery_date
                                )
                                if parsed_date:
                                    product_list[product_number] = {
                                        "despatch": parsed_date
                                    }
                                else:
                                    product_list[product_number] = {
                                        "despatch": input_date
                                    }
                            else:
                                product_list[product_number] = {"despatch": input_date}

            # 5. 计算每个产品的备件量
            for product_number, product_info in product_list.items():
                # 获取发运日期（已经是 date 对象）
                despatch_date = product_info["despatch"]

                # 计算时间间隔
                start_date = input_date
                end_date = input_date + timedelta(days=time_interval_days)

                # 转换为运行时间（参考 spare_service.py 的逻辑）
                xvals = [
                    (start_date - despatch_date).days
                    * product_data.year_days
                    * product_data.avg_worktime
                    / 365,
                    (end_date - despatch_date).days
                    * product_data.year_days
                    * product_data.avg_worktime
                    / 365,
                ]

                # 确保运行时间为正数
                xvals = [max(0, x) for x in xvals]

                # 计算CDF差值
                yvals = best_distribution.CDF(xvals=xvals, show_plot=False)
                calcu = yvals[1] - yvals[0]

                result += max(0.0, calcu)  # 确保不为负数

            return result

        except Exception as e:
            # 如果计算失败，返回0
            return 0.0

    @staticmethod
    async def check_maintenance_responsibility(
        product_number: str, warehouse_code: str, spare_part_code: str
    ) -> Dict[str, Any]:
        """
        检查该库房是否负责维护指定产品的指定备品
        """

        try:
            # 1. 获取产品的配属信息
            allotment = await ScienceWarehouseService.get_allotment_by_product_number(
                product_number
            )
            if not allotment:
                return {
                    "responsible": False,
                    "reason": f"产品编号 {product_number} 未找到配属信息",
                }

            # 2. 检查库房是否支持该产品的二级配属
            warehouse_allotments = (
                await ScienceWarehouseService.get_warehouse_allotments(warehouse_code)
            )
            if allotment.allotment_two not in warehouse_allotments:
                return {
                    "responsible": False,
                    "reason": f"库房 {warehouse_code} 不支持产品 {product_number} 的二级配属 {allotment.allotment_two}",
                }

            # 3. 检查库房备品清单中是否包含该备品
            warehouse_spare = await ScienceWarehouseService.get_warehouse_spare(
                warehouse_code, spare_part_code
            )
            if not warehouse_spare:
                return {
                    "responsible": False,
                    "reason": f"库房 {warehouse_code} 的备品清单中不包含备品 {spare_part_code}",
                }

            return {
                "responsible": True,
                "reason": f"库房 {warehouse_code} 负责维护产品 {product_number} 的备品 {spare_part_code}",
                "allotment_info": {
                    "allotment_two": allotment.allotment_two,
                    "product_model": allotment.product_model,
                },
            }

        except Exception as e:
            return {"responsible": False, "reason": f"检查维护责任时发生错误: {str(e)}"}

    # 辅助方法
    @staticmethod
    async def get_warehouse_allotments(warehouse_code: str) -> List[str]:
        """获取库房支持的二级配属列表"""
        async with async_db_session() as db:
            warehouses = await warehouse_dao.get_by_code(db, warehouse_code)
            if warehouses:
                # 收集所有库房的二级配属，去重
                allotments = set()
                for w in warehouses:
                    if w.allotment_two:
                        allotments.add(w.allotment_two)
                return list(allotments)
            return []

    @staticmethod
    async def get_models_using_spare(spare_part_code: str) -> List[str]:
        """获取使用指定备品的产品型号列表"""
        async with async_db_session() as db:
            mappings = await part_spare_mapping_dao.get_by_spare_part_code(
                db, spare_part_code
            )
            return list(set([mapping.product_model for mapping in mappings]))

    @staticmethod
    async def get_products_by_allotment_two(allotment_two: str) -> List[str]:
        """获取指定二级配属下的所有产品编号"""
        async with async_db_session() as db:
            allotments = await allotment_dao.get_by_allotment_two(db, allotment_two)
            return [a.product_number for a in allotments]

    @staticmethod
    async def get_products_by_allotment_two_and_models(
        allotment_two: str, target_models: List[str]
    ) -> List[str]:
        """获取指定二级配属下且型号在目标列表中的产品编号（优化版本）"""
        async with async_db_session() as db:
            allotments = await allotment_dao.get_by_allotment_two_and_models(
                db, allotment_two, target_models
            )
            return [a.product_number for a in allotments]

    @staticmethod
    async def get_model_by_product_number(product_number: str) -> str:
        """根据产品编号获取产品型号"""
        async with async_db_session() as db:
            allotment = await allotment_dao.get_by_product_number(db, product_number)
            return allotment.product_model if allotment else None

    @staticmethod
    async def calculate_total_run_time_for_products(
        product_numbers: List[str], product_model: str, product_config_code: str | None = None
    ) -> float:
        """计算特定产品编号列表的总运行时间"""
        async with async_db_session() as db:
            # 获取产品运行参数
            product = await product_dao.get_by_model(
                db, product_model, product_config_code=product_config_code
            )
            if not product:
                return 0.0

            # 获取这些产品编号的发运数据
            despatchs = await despatch_dao.select_models(
                db, identifier__in=product_numbers, repair_level__eq="新造"
            )

            if not despatchs:
                return 0.0

            # 计算总运行时间
            now = date.today()
            total_hours = 0
            for despatch in despatchs:
                dispatch_date = despatch.life_cycle_time
                if isinstance(dispatch_date, str):
                    dispatch_date = dateutils.validate_and_parse_date(dispatch_date)
                # 计算日期差
                date_diff = (now - dispatch_date).days
                hours = dateutils.run_time(
                    date_diff, product.year_days, product.avg_worktime
                )
                total_hours += hours

            return total_hours

    @staticmethod
    async def exponential_fit_for_insufficient_data(
        model_part_failures: List,
        product_model: str,
        product_config_code: str | None,
        part_code: str,
        time_interval_days: int,
        input_date: date,
    ) -> float:
        """
        当故障数据不足4个时，使用指数分布拟合计算备件量
        参考 part_fit_service.py 中的 none_tag_fit 方法
        """
        try:
            # 获取该型号+零部件的所有产品编号
            product_numbers = list(set([f.product_number for f in model_part_failures]))

            # 计算这些产品的总运行时间
            total_run_time = (
                await ScienceWarehouseService.calculate_total_run_time_for_products(
                    product_numbers, product_model, product_config_code
                )
            )

            if total_run_time == 0:
                return 0.0

            # 计算故障数量
            failure_count = len(model_part_failures)

            # 计算指数分布的lambda参数
            if failure_count > 0:
                # 存在故障，计算指数分布公式: λ = n / T
                lambda_param = failure_count / total_run_time
            else:
                # 不存在故障，计算指数分布公式: λ = t/-ln(1/e)
                lambda_param = -(math.log(1 / math.e)) / total_run_time

            # 计算备件量（使用指数分布的CDF）
            # 获取产品运行参数用于时间转换
            async with async_db_session() as db:
                product = await product_dao.get_by_model(
                    db, product_model, product_config_code=product_config_code
                )
                if not product:
                    return 0.0

                # 计算时间间隔的运行时间
                start_date = input_date
                end_date = input_date + timedelta(days=time_interval_days)

                # 转换为运行时间
                start_run_time = 0  # 从当前时间开始
                end_run_time = (
                    time_interval_days * product.year_days * product.avg_worktime / 365
                )

                # 计算指数分布的CDF差值
                # P(X <= end) - P(X <= start)
                cdf_end = 1 - math.exp(-lambda_param * end_run_time)
                cdf_start = 1 - math.exp(-lambda_param * start_run_time)
                spare_quantity = cdf_end - cdf_start

                return max(0.0, spare_quantity)

        except Exception as e:
            return 0.0

    @staticmethod
    async def get_failures_by_product_number(product_number: str) -> List:
        """根据产品编号获取故障数据"""
        async with async_db_session() as db:
            return await failure_dao.get_by_product_number(db, product_number)

    @staticmethod
    async def get_part_spare_mapping(
        product_model: str, product_config_code: str, original_part_code: str
    ):
        """获取部件与备品映射关系"""
        async with async_db_session() as db:
            return await part_spare_mapping_dao.get_by_original_part_code(
                db, product_model, product_config_code, original_part_code
            )

    @staticmethod
    async def get_allotment_by_product_number(product_number: str):
        """根据产品编号获取配属信息"""
        async with async_db_session() as db:
            return await allotment_dao.get_by_product_number(db, product_number)

    @staticmethod
    async def get_warehouse_spare(warehouse_code: str, spare_part_code: str):
        """获取库房备品信息"""
        async with async_db_session() as db:
            return await warehouse_inventory_dao.get_by_warehouse_and_part(
                db, warehouse_code, spare_part_code
            )

    @staticmethod
    async def save_calculation_results(
        calculation_id: str,
        results: Dict[str, Any],
        statistics: Dict[str, Any],
        time_interval_days: int,
        input_date: date,
        product_model: str | None = None,
        product_config_code: str | None = None,
    ):
        """
        保存计算结果到数据库
        """
        async with async_db_session() as db:
            # 1. 清空该批次的历史数据
            await science_warehouse_result_dao.clear_by_calculation_id(
                db, calculation_id
            )
            # 统计表相关逻辑已移除
            # await science_warehouse_statistics_dao.clear_by_calculation_id(
            #     db, calculation_id
            # )

            # 2. 准备结果数据
            result_data = []
            for warehouse_code, spare_parts in results.items():
                # 获取库房名称
                warehouse_name = await ScienceWarehouseService.get_warehouse_name(
                    warehouse_code
                )

                for spare_part_code, spare_info in spare_parts.items():
                    result_data.append(
                        {
                            "calculation_id": calculation_id,
                            "product_model": product_model,
                            "product_config_code": product_config_code,
                            "warehouse_code": warehouse_code,
                            "warehouse_name": warehouse_name or warehouse_code,
                            "spare_part_code": spare_part_code,
                            "spare_part_name": spare_info["part_name"],
                            "required_quantity": spare_info["required_quantity"],
                            "calculation_method": spare_info["calculation_method"],
                            "time_interval_days": time_interval_days,
                            "input_date": input_date,
                            "created_time": date.today(),
                            "confidence": spare_info["confidence"],
                            "max_failure_count": 0,  # 旧版本服务不计算此字段，设为0
                        }
                    )

            # 3. 批量保存结果数据
            if result_data:
                await science_warehouse_result_dao.bulk_create(db, result_data)

            # 统计表相关逻辑已移除，只保留核心计算结果
            # # 4. 保存统计信息
            # from backend.app.calcu.model.science_warehouse_statistics import (
            #     ScienceWarehouseStatistics,
            # )
            # ... (统计表创建逻辑已注释)

    @staticmethod
    async def get_warehouse_name(warehouse_code: str) -> str:
        """获取库房名称"""
        async with async_db_session() as db:
            warehouses = await warehouse_dao.get_by_code(db, warehouse_code)
            if warehouses:
                # 如果有多个库房，返回第一个的名称
                return warehouses[0].name
            return None

    @staticmethod
    async def convert_to_api_format(results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        将内部计算结果转换为API输出格式

        :param results: 内部计算结果
        :return: API格式的数据列表
        """
        api_data = []

        for warehouse_code, spare_parts in results.items():
            # 获取库房名称
            warehouse_name = await ScienceWarehouseService.get_warehouse_name(
                warehouse_code
            )

            for spare_part_code, spare_info in spare_parts.items():
                # 根据你的API格式要求
                api_item = {
                    "factor": "G002",  # 工厂编码固定为G002
                    "code": warehouse_code,  # 库房编码作为code
                    "warehouse": warehouse_name
                    or warehouse_code,  # 库房名称，如果没有则使用编码
                    "part": spare_part_code,  # 备品编码作为part
                    "number": spare_info["required_quantity"],  # 需求数量
                }
                api_data.append(api_item)

        return api_data

    @staticmethod
    async def get_calculation_results_by_id(
        calculation_id: str,
    ) -> "ScienceWarehouseDetailsResponse":
        """
        根据计算批次ID获取详细计算结果（包含统计信息）
        """
        async with async_db_session() as db:
            # 获取结果数据
            results = await science_warehouse_result_dao.select_models(
                db, calculation_id__eq=calculation_id
            )

            # 统计表相关逻辑已移除
            # statistics = await science_warehouse_statistics_dao.select_model(
            #     db, calculation_id__eq=calculation_id
            # )
            statistics = None

            # 转换为内部格式
            results_dict = {}
            for result in results:
                if result.warehouse_code not in results_dict:
                    results_dict[result.warehouse_code] = {}

                results_dict[result.warehouse_code][result.spare_part_code] = {
                    "part_name": result.spare_part_name,
                    "required_quantity": result.required_quantity,
                    "calculation_method": result.calculation_method,
                    "confidence": result.confidence,
                    "max_failure_count": getattr(result, "max_failure_count", 0),
                }

            # 导入Schema类
            from backend.app.calcu.schema.science_warehouse import (
                ScienceWarehouseDetailsResponse,
            )

            return ScienceWarehouseDetailsResponse(
                calculation_id=calculation_id,
                results=results_dict,
                statistics={},  # 统计表已移除，返回空字典
            )

    @staticmethod
    async def get_calculation_results_for_api(
        calculation_id: str,
    ) -> List[Dict[str, Any]]:
        """
        根据计算批次ID获取API格式的计算结果

        :param calculation_id: 计算批次ID
        :return: API格式的数据列表
        """
        async with async_db_session() as db:
            # 获取结果数据
            results = await science_warehouse_result_dao.select_models(
                db, calculation_id__eq=calculation_id
            )

            if not results:
                return []

            # 转换为内部格式
            results_dict = {}
            for result in results:
                if result.warehouse_code not in results_dict:
                    results_dict[result.warehouse_code] = {}

                results_dict[result.warehouse_code][result.spare_part_code] = {
                    "part_name": result.spare_part_name,
                    "required_quantity": result.required_quantity,
                    "calculation_method": result.calculation_method,
                    "confidence": result.confidence,
                }

            # 转换为API格式
            api_data = await ScienceWarehouseService.convert_to_api_format(results_dict)
            return api_data

    @staticmethod
    async def get_latest_calculation_results() -> List[Dict[str, Any]]:
        """
        获取最新一批次的计算结果，用于前端展示

        :return: 最新批次的计算结果列表
        """
        async with async_db_session() as db:
            # 统计表已移除，改为从结果表获取最新的calculation_id
            # 1. 获取最新的结果记录（按自增ID倒序，确保唯一性）
            latest_result = await science_warehouse_result_dao.select_model(
                db, order_by="id", desc=True
            )

            if not latest_result:
                return []

            # 2. 根据最新结果记录的calculation_id获取结果数据
            return await ScienceWarehouseService.get_calculation_results_for_api(
                latest_result.calculation_id
            )

    @staticmethod
    async def get_latest_calculation_results_detailed() -> List[Dict[str, Any]]:
        """
        获取最新一批次的详细计算结果，包含更多字段信息

        :return: 最新批次的详细计算结果列表
        """
        async with async_db_session() as db:
            # 统计表已移除，改为从结果表获取最新的calculation_id
            # 1. 获取最新的结果记录（按自增ID倒序，确保唯一性）
            latest_result = await science_warehouse_result_dao.select_model(
                db, order_by="id", desc=True
            )

            if not latest_result:
                return []

            # 2. 获取详细的结果数据
            results = await science_warehouse_result_dao.select_models(
                db, calculation_id__eq=latest_result.calculation_id
            )

            if not results:
                return []

            # 3. 转换为详细格式
            detailed_results = []
            for result in results:
                detailed_item = {
                    "calculation_id": result.calculation_id,
                    "product_model": getattr(result, "product_model", None),
                    "product_config_code": getattr(result, "product_config_code", None),
                    "warehouse_code": result.warehouse_code,
                    "warehouse_name": result.warehouse_name,
                    "spare_part_code": result.spare_part_code,
                    "spare_part_name": result.spare_part_name,
                    "required_quantity": result.required_quantity,
                    "calculation_method": result.calculation_method,
                    "confidence": result.confidence,
                    "time_interval_days": result.time_interval_days,
                    "input_date": (
                        result.input_date.isoformat() if result.input_date else None
                    ),
                    "created_time": (
                        result.created_time.isoformat() if result.created_time else None
                    ),
                    "max_failure_count": getattr(result, "max_failure_count", 0),
                }
                detailed_results.append(detailed_item)

            return detailed_results

    @staticmethod
    async def get_select(
        calculation_id: Optional[str] = None,
        product_model: Optional[str] = None,
        product_config_code: Optional[str] = None,
        warehouse_code: Optional[str] = None,
        spare_part_code: Optional[str] = None,
        calculation_method: Optional[str] = None,
        time_range: Optional[list[str]] = None,
    ):
        """
        获取科学库存计算结果的查询条件

        :param calculation_id: 计算批次ID（支持模糊匹配）
        :param warehouse_code: 库房编码（精确匹配）
        :param spare_part_code: 备品编码（精确匹配）
        :param calculation_method: 计算方法（精确匹配）
        :param time_range: 创建时间范围 [开始日期, 结束日期]
        :return: 查询条件
        """
        from sqlalchemy import and_, or_, select
        from backend.app.calcu.model.science_warehouse_result import (
            ScienceWarehouseResult,
        )

        conditions = []

        # 固定条件：required_quantity必须大于0
        conditions.append(ScienceWarehouseResult.required_quantity > 0)
        conditions.append(ScienceWarehouseResult.required_quantity >= ScienceWarehouseResult.max_failure_count)

        if calculation_id:
            # 计算批次ID支持模糊匹配（因为用户手动输入）
            conditions.append(
                ScienceWarehouseResult.calculation_id.like(f"%{calculation_id}%")
            )

        if product_model:
            conditions.append(ScienceWarehouseResult.product_model == product_model)

        if product_config_code is not None:
            conditions.append(
                ScienceWarehouseResult.product_config_code == product_config_code
            )

        if warehouse_code:
            # 库房编码精确匹配（下拉框选择）
            conditions.append(ScienceWarehouseResult.warehouse_code == warehouse_code)

        if spare_part_code:
            # 备品编码精确匹配（下拉框选择）
            conditions.append(ScienceWarehouseResult.spare_part_code == spare_part_code)

        if calculation_method:
            # 计算方法精确匹配（下拉框选择）
            conditions.append(
                ScienceWarehouseResult.calculation_method == calculation_method
            )

        if time_range:
            conditions.append(
                ScienceWarehouseResult.created_time.between(
                    time_range[0], time_range[1]
                )
            )

        return (
            select(ScienceWarehouseResult)
            .where(and_(*conditions))
            .order_by(ScienceWarehouseResult.required_quantity.desc())
        )

    @staticmethod
    async def get_warehouse_code_name_pairs() -> Sequence[List[str]]:
        """
        获取库房编码和名称的列表（去重）

        :return: [[库房编码, 库房名称], ...] 的列表
        """
        async with async_db_session() as db:
            return await science_warehouse_result_dao.get_warehouse_code_name_pairs(db)

    @staticmethod
    async def get_spare_part_code_name_pairs(
        warehouse_code: str | None = None,
    ) -> Sequence[List[str]]:
        """
        根据库房编码获取备品编码和名称的列表（级联筛选）

        :param warehouse_code: 库房编码（可选，用于级联筛选）
        :return: [[备品编码, 备品名称], ...] 的列表
        """
        async with async_db_session() as db:
            return await science_warehouse_result_dao.get_spare_part_code_name_pairs(
                db, warehouse_code
            )

    @staticmethod
    async def get_calculation_methods() -> Sequence[str]:
        """
        获取所有唯一的计算方法

        :return: 计算方法列表
        """
        async with async_db_session() as db:
            return await science_warehouse_result_dao.get_distinct_calculation_methods(
                db
            )

    @staticmethod
    async def get_latest_calculation_statistics() -> Dict[str, Any]:
        """
        获取最新一批次的统计信息（统计表已移除，返回空字典）

        :return: 最新批次的统计信息
        """
        # 统计表已移除，返回空字典
        return {}


science_warehouse_service: ScienceWarehouseService = ScienceWarehouseService()
