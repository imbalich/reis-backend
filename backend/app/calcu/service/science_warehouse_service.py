#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 科学库存服务,支援国铁售后需求
import math
import json
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
from backend.app.calcu.crud.crud_science_warehouse_result import (
    science_warehouse_result_dao,
)
from backend.app.calcu.crud.crud_science_warehouse_statistics import (
    science_warehouse_statistics_dao,
)
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.service.part_fit_service import part_fit_service
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
        time_interval_days: int = 180, input_date: date = None
    ) -> "ScienceWarehouseCalculationResponse":
        """
        科学库存需求计算主流程

        :param time_interval_days: 需求预测时间间隔（天数）,默认180天
        :param input_date: 计算截止日期（用于拟合）
        :return: 计算结果和统计信息
        """

        if not input_date:
            input_date = date.today()

        # 1. 获取所有库房备品清单
        warehouse_spares = await ScienceWarehouseService.get_all_warehouse_spare_list()

        # 2. 初始化结果和统计
        results = {}
        statistics = {
            "total_warehouse_spares": 0,
            "calculated_spares": 0,
            "default_spares": 0,
            "skipped_failures": [],
            "mapping_errors": [],
            "maintenance_responsibility_analysis": {},
        }

        # 3. 按库房-备品维度计算
        for warehouse_code, spare_parts in warehouse_spares.items():
            results[warehouse_code] = {}
            statistics["maintenance_responsibility_analysis"][warehouse_code] = {
                "total_spares": len(spare_parts),
                "calculated": 0,
                "default": 0,
                "responsible_products": 0,
                "non_responsible_products": 0,
            }

            for spare_part in spare_parts:
                statistics["total_warehouse_spares"] += 1

                # 计算该库房该备品的需求
                requirement_result = await ScienceWarehouseService.calculate_spare_requirement_with_coverage(
                    warehouse_code, spare_part, time_interval_days, input_date
                )

                if requirement_result["calculated"]:
                    results[warehouse_code][spare_part["part_code"]] = {
                        "part_name": spare_part["part_name"],
                        "required_quantity": requirement_result["quantity"],
                        "calculation_method": "fitted",
                        "confidence": requirement_result.get("confidence", 0.8),
                        "coverage_info": requirement_result.get("coverage_info", {}),
                        "maintenance_analysis": requirement_result.get(
                            "maintenance_analysis", {}
                        ),
                    }
                    statistics["calculated_spares"] += 1
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "calculated"
                    ] += 1
                else:
                    # 使用默认数量
                    results[warehouse_code][spare_part["part_code"]] = {
                        "part_name": spare_part["part_name"],
                        "required_quantity": spare_part["default_quantity"],
                        "calculation_method": "default",
                        "confidence": 0.5,
                        "coverage_info": requirement_result.get("coverage_info", {}),
                        "maintenance_analysis": requirement_result.get(
                            "maintenance_analysis", {}
                        ),
                    }
                    statistics["default_spares"] += 1
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "default"
                    ] += 1

                # 记录跳过的故障和映射错误
                statistics["skipped_failures"].extend(
                    requirement_result.get("skipped_failures", [])
                )
                statistics["mapping_errors"].extend(
                    requirement_result.get("mapping_errors", [])
                )

                # 记录维护责任分析
                if requirement_result.get("maintenance_analysis"):
                    maintenance_analysis = requirement_result["maintenance_analysis"]
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "responsible_products"
                    ] += maintenance_analysis.get("responsible_products", 0)
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "non_responsible_products"
                    ] += maintenance_analysis.get("non_responsible_products", 0)

        # 4. 生成计算批次ID
        calculation_id = f"SW_{snowflake.generate()}"

        # 5. 保存计算结果到数据库
        await ScienceWarehouseService.save_calculation_results(
            calculation_id, results, statistics, time_interval_days, input_date
        )

        # 导入Schema类
        from backend.app.calcu.schema.science_warehouse import (
            ScienceWarehouseCalculationResponse,
        )

        return ScienceWarehouseCalculationResponse(
            calculation_id=calculation_id,
            statistics=statistics,
            calculation_period={
                "time_interval_days": time_interval_days,
                "input_date": input_date.isoformat() if input_date else None,
            },
        )

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
        warehouse_code: str, spare_part: dict, time_interval_days: int, input_date: date
    ) -> Dict[str, Any]:
        """
        计算单个库房单个备品的需求数量（考虑库房-路局-产品关系）
        """

        result = {
            "calculated": False,
            "quantity": 0,
            "skipped_failures": [],
            "mapping_errors": [],
            "coverage_info": {},
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

            result["coverage_info"]["warehouse_allotments"] = warehouse_allotments

            # 2. 获取使用此备品的产品型号（通过映射表）
            related_models = await ScienceWarehouseService.get_models_using_spare(
                spare_part["part_code"]
            )

            if not related_models:
                result["mapping_errors"].append(
                    {
                        "type": "no_related_models",
                        "spare_part_code": spare_part["part_code"],
                        "message": f"备品 {spare_part['part_code']} 未找到相关产品型号",
                    }
                )
                return result

            result["coverage_info"]["related_models"] = related_models

            # 3. 获取运行在库房覆盖路局上的产品编号
            relevant_products = []
            for allotment_two in warehouse_allotments:
                products_in_allotment = (
                    await ScienceWarehouseService.get_products_by_allotment_two(
                        allotment_two
                    )
                )
                relevant_products.extend(products_in_allotment)

            # 去重
            relevant_products = list(set(relevant_products))

            # 4. 过滤出相关型号的产品编号
            filtered_products = []
            for product_number in relevant_products:
                product_model = (
                    await ScienceWarehouseService.get_model_by_product_number(
                        product_number
                    )
                )
                if product_model in related_models:
                    filtered_products.append(product_number)

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

            result["coverage_info"]["relevant_products_count"] = len(filtered_products)

            # 5. 获取相关产品的故障数据
            all_failures = []
            skipped_failures = []

            for product_number in filtered_products:
                product_failures = (
                    await ScienceWarehouseService.get_failures_by_product_number(
                        product_number
                    )
                )

                # 记录原始故障数量
                result["coverage_info"][f"product_{product_number}_total_failures"] = (
                    len(product_failures)
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
                result["coverage_info"][
                    f"product_{product_number}_time_filtered_failures"
                ] = len(time_filtered_failures)
                result["coverage_info"][
                    f"product_{product_number}_date_parse_errors"
                ] = len(date_parse_errors)

                # 将日期解析错误添加到跳过的故障中
                skipped_failures.extend(date_parse_errors)

                # 检查故障部件是否能映射到目标备品
                for failure in time_filtered_failures:
                    mapping = await ScienceWarehouseService.get_part_spare_mapping(
                        failure.product_model, failure.fault_material_code
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
            result["coverage_info"]["total_failures"] = len(all_failures)
            result["coverage_info"]["skipped_failures_count"] = len(skipped_failures)

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
                result["calculated"] = True
                result["quantity"] = calculation_result["quantity"]
                result["confidence"] = calculation_result.get("confidence", 0.8)
                result["maintenance_analysis"] = calculation_result.get(
                    "maintenance_analysis", {}
                )
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
            # 1. 按产品型号+零部件编码分组故障数据
            failures_by_model_part = defaultdict(list)
            for failure in failures:
                key = f"{failure.product_model}_{failure.fault_material_code}"
                failures_by_model_part[key].append(failure)

            # 2. 对每个型号+零部件组合进行备件量计算
            total_requirement = 0.0
            calculation_details = []
            responsible_products = 0
            non_responsible_products = 0

            for model_part_key, model_part_failures in failures_by_model_part.items():
                # 解析型号和零部件编码
                product_model, part_code = model_part_key.split("_", 1)

                # 获取该型号+零部件的所有产品编号
                product_numbers = list(
                    set([f.product_number for f in model_part_failures])
                )

                # 使用已过滤的故障数据进行打标处理
                tags = await part_strategy_service.part_tag_process_with_failures(
                    product_model, part_code, input_date, model_part_failures
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

                # 检查每个产品是否由该库房负责维护
                for product_number in product_numbers:
                    maintenance_responsibility = (
                        await ScienceWarehouseService.check_maintenance_responsibility(
                            product_number, warehouse_code, spare_part_code
                        )
                    )

                    if maintenance_responsibility["responsible"]:
                        # 该库房负责维护，计入总需求
                        total_requirement += model_part_spare_quantity
                        responsible_products += 1

                        calculation_details.append(
                            {
                                "product_number": product_number,
                                "product_model": product_model,
                                "part_code": part_code,
                                "failures_count": len(model_part_failures),
                                "spare_quantity": model_part_spare_quantity,
                                "distribution": best_distribution.distribution,
                                "maintenance_responsible": True,
                                "responsibility_reason": maintenance_responsibility[
                                    "reason"
                                ],
                            }
                        )
                    else:
                        # 该库房不负责维护，不计入总需求
                        non_responsible_products += 1

                        calculation_details.append(
                            {
                                "product_number": product_number,
                                "product_model": product_model,
                                "part_code": part_code,
                                "failures_count": len(model_part_failures),
                                "spare_quantity": model_part_spare_quantity,
                                "distribution": best_distribution.distribution,
                                "maintenance_responsible": False,
                                "responsibility_reason": maintenance_responsibility[
                                    "reason"
                                ],
                            }
                        )

            return {
                "success": True,
                "quantity": math.ceil(total_requirement),  # 先相加再取整
                "confidence": 0.8,
                "calculation_details": calculation_details,
                "maintenance_analysis": {
                    "total_model_part_combinations": len(failures_by_model_part),
                    "responsible_products": responsible_products,
                    "non_responsible_products": non_responsible_products,
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

            # 2. 获取产品运行参数
            async with async_db_session() as db:
                from backend.app.fit.schema.base_param import ProductParam
                from backend.app.fit.utils.convert_model import (
                    convert_to_pydantic_model,
                )
                from backend.app.datamanage.crud.crud_product import product_dao

                product_data = convert_to_pydantic_model(
                    await product_dao.get_by_model(db, product_model), ProductParam
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
    async def get_model_by_product_number(product_number: str) -> str:
        """根据产品编号获取产品型号"""
        async with async_db_session() as db:
            allotment = await allotment_dao.get_by_product_number(db, product_number)
            return allotment.product_model if allotment else None

    @staticmethod
    async def get_failures_by_product_number(product_number: str) -> List:
        """根据产品编号获取故障数据"""
        async with async_db_session() as db:
            return await failure_dao.get_by_product_number(db, product_number)

    @staticmethod
    async def get_part_spare_mapping(product_model: str, original_part_code: str):
        """获取部件与备品映射关系"""
        async with async_db_session() as db:
            return await part_spare_mapping_dao.get_by_original_part_code(
                db, product_model, original_part_code
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
    ):
        """
        保存计算结果到数据库
        """
        async with async_db_session() as db:
            # 1. 清空该批次的历史数据
            await science_warehouse_result_dao.clear_by_calculation_id(
                db, calculation_id
            )
            await science_warehouse_statistics_dao.clear_by_calculation_id(
                db, calculation_id
            )

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
                            "coverage_info": json.dumps(
                                spare_info.get("coverage_info", {}), ensure_ascii=False
                            ),
                            "maintenance_analysis": json.dumps(
                                spare_info.get("maintenance_analysis", {}),
                                ensure_ascii=False,
                            ),
                            "calculation_details": json.dumps(
                                spare_info.get("calculation_details", {}),
                                ensure_ascii=False,
                            ),
                        }
                    )

            # 3. 批量保存结果数据
            if result_data:
                await science_warehouse_result_dao.bulk_create(db, result_data)

            # 4. 保存统计信息
            from backend.app.calcu.model.science_warehouse_statistics import (
                ScienceWarehouseStatistics,
            )

            statistics_data = {
                "calculation_id": calculation_id,
                "total_warehouse_spares": statistics["total_warehouse_spares"],
                "calculated_spares": statistics["calculated_spares"],
                "default_spares": statistics["default_spares"],
                "skipped_failures_count": len(statistics.get("skipped_failures", [])),
                "mapping_errors_count": len(statistics.get("mapping_errors", [])),
                "time_interval_days": time_interval_days,
                "input_date": input_date,
                "calculation_summary": json.dumps(statistics, ensure_ascii=False),
                "created_time": date.today(),
            }

            # 直接使用字典创建统计信息
            statistics_obj = ScienceWarehouseStatistics(**statistics_data)
            db.add(statistics_obj)
            await db.commit()
            await db.refresh(statistics_obj)

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
                    "factor": warehouse_code,  # 库房编码作为factor
                    "code": spare_part_code,  # 备品编码作为code
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

            # 获取统计信息
            statistics = await science_warehouse_statistics_dao.select_model(
                db, calculation_id__eq=calculation_id
            )

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
                    "coverage_info": (
                        json.loads(result.coverage_info) if result.coverage_info else {}
                    ),
                    "maintenance_analysis": (
                        json.loads(result.maintenance_analysis)
                        if result.maintenance_analysis
                        else {}
                    ),
                    "calculation_details": (
                        json.loads(result.calculation_details)
                        if result.calculation_details
                        else {}
                    ),
                }

            # 导入Schema类
            from backend.app.calcu.schema.science_warehouse import (
                ScienceWarehouseDetailsResponse,
            )

            return ScienceWarehouseDetailsResponse(
                calculation_id=calculation_id,
                results=results_dict,
                statistics=(
                    json.loads(statistics.calculation_summary)
                    if statistics and statistics.calculation_summary
                    else {}
                ),
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


science_warehouse_service: ScienceWarehouseService = ScienceWarehouseService()
