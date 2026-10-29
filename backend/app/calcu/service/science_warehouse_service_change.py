#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
科学库存改版
思路分析：

"""
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import numpy as np
import pandas as pd

from backend.app.calcu.crud.crud_science_warehouse_result import (
    science_warehouse_result_dao,
)
from backend.app.fit.schema.base_param import DespatchParam, ProductParam
from backend.app.fit.utils.convert_model import (
    convert_to_pydantic_model,
    convert_to_pydantic_models,
    convert_to_total_quantity,
    get_ebom_tree_with_parents,
)
from reliability.Distributions import Exponential_Distribution
from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_allotment import allotment_dao
from backend.app.datamanage.crud.crud_part_spare_mapping import part_spare_mapping_dao
from backend.app.datamanage.crud.crud_warehouse_inventory import warehouse_inventory_dao
from backend.app.datamanage.crud.crud_warehouse import warehouse_dao
from backend.app.calcu.schema.distribute_param import DistributionParams
from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.fit.schema.fit_param import (
    CreateFitPartInParam,
    FitCheckType,
    FitMethodType,
)
from backend.app.fit_aaron.service.aaron_part_data_service import (
    build_base_result,
    normalize_failure_dataframe,
    objects_to_dataframe,
)
from backend.app.fit_aaron.service.part_fit_service import (
    part_fit_service as aaron_part_fit_service,
)
from backend.app.fit_aaron.service.part_strategy_service import (
    part_strategy_service as aaron_part_strategy_service,
)
from backend.common.exception.errors import DataValidationError, FailureCheckError
from backend.common.industry import Industry, resolve_industry
from backend.common.log import log
from backend.common.product_config import normalize_product_config_code
from backend.database.db import async_db_session

_REQUIRED_QUANTITY_PLACES = Decimal("0.00001")

# 截止日前故障数超过该值才走 Aaron 拟合，否则按 Aaron 的指数口径估计
_MIN_FAILURES_FOR_FIT = 4


def round_required_quantity(value) -> Decimal:
    """需求数量保留五位小数，四舍五入。"""
    if value is None:
        return Decimal("0.00000")
    return Decimal(str(value)).quantize(
        _REQUIRED_QUANTITY_PLACES, rounding=ROUND_HALF_UP
    )


def to_date(value) -> Optional[date]:
    """把 date/datetime/Timestamp/字符串统一转成 date，无法解析返回 None。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def build_units_by_product(
    model: str,
    despatch_data: list,
    failure_data: list,
    bl_quantity: int,
) -> dict[str, list[Optional[date]]]:
    """
    复用 Aaron 构建样本的规则生成零件位置：
    每个产品按 BOM 用量展开为多个位置，寿命起点取发运日期与故障表生产日期中较早者。

    :return: 产品编号 -> 各零件位置的寿命起点列表
    """
    despatch_df = objects_to_dataframe(despatch_data)
    failure_df = normalize_failure_dataframe(objects_to_dataframe(failure_data))
    base_result = build_base_result(
        model, despatch_df, failure_df, bl_quantity if bl_quantity > 0 else 1
    )
    units_by_product: dict[str, list[Optional[date]]] = {}
    for identifier, life_cycle_time in zip(
        base_result["identifier"], base_result["life_cycle_time"]
    ):
        if identifier is None or pd.isna(identifier):
            continue
        units_by_product.setdefault(str(identifier), []).append(to_date(life_cycle_time))
    return units_by_product


class ScienceWarehouseServiceChange:
    @staticmethod
    async def single_warehouse_single_spare_calculate(
        time_interval_days: int,
        input_date: str | date,
        warehouse_code: str,
        spare_part_code: str,
        use_cached_fit: bool = True,
        fit_context_cache: dict | None = None,
    ) -> dict:
        """
        单库房-单备品-计算流程

        :param use_cached_fit: True 先读 fit_part 已入库结果，没有再 Aaron 拟合入库；
            False 每次现场 Aaron 拟合且只在内存中使用，不读写 fit_part（测试口径）
        :param fit_context_cache: 批次内共享的 型号+派生码+故障件 计算上下文缓存

        输出0的主要场景：
            所有故障件在库房支撑的路局下都没有产品
            所有故障件的分布获取失败
            所有产品都找不到发运日期
            所有产品的运行时间区间无效（发运日期太晚）
            所有产品的CDF计算结果为0或失败
            所有故障件的 quantity 累加后为 0
        """
        # 1.获取库房备品信息
        warehouse_spare = (
            await ScienceWarehouseServiceChange.get_single_warehouse_spare(
                warehouse_code, spare_part_code
            )
        )
        if warehouse_spare is None:
            return {
                "success": False,
                "warehouse_code": warehouse_code,
                "spare_part_code": spare_part_code,
                "warehouse_name": None,
                "spare_part_name": None,
                "quantity": 0,
                "max_failure_count": 0,  # 错误情况下为0
                "calculation_method": "failed",
                "error_code": "NO_WAREHOUSE_SPARE",
                "error_message": f"库房{warehouse_code}备品{spare_part_code}信息不存在",
                "statistics": {
                    "total_mappings": 0,
                    "calculated_count": 0,
                    "skipped_count": 0,
                    "total_max_failure_count": 0,
                },
            }
        # 2.备品支持的 型号-故障件-备品 映射关系去重集
        model_failure_spare_mappings = (
            await ScienceWarehouseServiceChange.get_spare_models_by_spare_part_code(
                spare_part_code
            )
        )
        if model_failure_spare_mappings is None:
            return {
                "success": False,
                "warehouse_code": warehouse_code,
                "spare_part_code": spare_part_code,
                "warehouse_name": warehouse_spare.warehouse_name,
                "spare_part_name": warehouse_spare.part_name,
                "quantity": 0,
                "max_failure_count": 0,  # 错误情况下为0
                "calculation_method": "failed",
                "error_code": "NO_MAPPINGS",
                "error_message": f"备品{spare_part_code}支持的型号-故障件-备品映射关系不存在",
                "statistics": {
                    "total_mappings": 0,
                    "calculated_count": 0,
                    "skipped_count": 0,
                    "total_max_failure_count": 0,
                },
            }
        # 3.库房支撑的路局
        allotments = (
            await ScienceWarehouseServiceChange.get_allotments_by_warehouse_code(
                warehouse_code
            )
        )
        if allotments is None:
            return {
                "success": False,
                "warehouse_code": warehouse_code,
                "spare_part_code": spare_part_code,
                "warehouse_name": warehouse_spare.warehouse_name,
                "spare_part_name": warehouse_spare.part_name,
                "quantity": 0,
                "max_failure_count": 0,  # 错误情况下为0
                "calculation_method": "failed",
                "error_code": "NO_ALLOTMENTS",
                "error_message": f"库房{warehouse_code}支撑的路局不存在",
                "statistics": {
                    "total_mappings": len(model_failure_spare_mappings),
                    "calculated_count": 0,
                    "skipped_count": 0,
                    "total_max_failure_count": 0,
                },
            }
        # 4.计算每种故障有多少产品编号被库房管理（按派生码归属过滤）
        log.info(
            f"[科学库存计算] 库房{warehouse_code}备品{spare_part_code}，开始计算，共{len(model_failure_spare_mappings)}个故障件映射"
        )
        if fit_context_cache is None:
            fit_context_cache = {}
        for model_failure_spare_mapping in model_failure_spare_mappings:

            model = model_failure_spare_mapping["product_model"]
            product_config_code = model_failure_spare_mapping["product_config_code"]
            part = model_failure_spare_mapping["original_part_code"]

            products_set = set()

            for allotment in allotments:
                allotment_products = await ScienceWarehouseServiceChange.get_products_by_allotment_two_and_model(
                    allotment, model
                )
                if allotment_products:
                    products_set.update(allotment_products)
            # 4.1 型号+派生码+故障件的计算上下文（零件位置、运行参数、分布），批次内复用
            context = await ScienceWarehouseServiceChange.get_mapping_context(
                model,
                product_config_code,
                part,
                input_date,
                use_cached_fit=use_cached_fit,
                cache=fit_context_cache,
            )
            # 4.2 只保留属于该派生码的产品（以 Aaron 样本中的发运/故障派生码为准）
            units_by_product = context["units_by_product"]
            products = sorted(p for p in products_set if p in units_by_product)
            product_count = len(products)
            model_failure_spare_mapping["allotment_product_count"] = len(products_set)
            model_failure_spare_mapping["product_count"] = product_count
            model_failure_spare_mapping["products"] = products
            model_failure_spare_mapping["unit_count"] = sum(
                len(units_by_product[p]) for p in products
            )
            model_failure_spare_mapping["context"] = context
            log.info(
                f"[科学库存计算] 型号{model}派生码{product_config_code}故障件{part}，"
                f"库房{warehouse_code}支撑的路局下共有{len(products_set)}个产品，"
                f"属于该派生码{product_count}个，零件位置{model_failure_spare_mapping['unit_count']}个"
            )

        # 5.计算每个型号+故障件在过去x天内的故障次数最大值（滚动计算）
        log.info(
            f"[科学库存计算] 开始计算库房{warehouse_code}备品{spare_part_code}的最大滚动故障次数，"
            f"共{len(model_failure_spare_mappings)}个型号+故障件映射"
        )
        for model_failure_spare_mapping in model_failure_spare_mappings:
            # 滚动最大周期
            gap = 30
            # 滚动回溯最远日期
            start_date = input_date - timedelta(days=365 * 3)
            model = model_failure_spare_mapping["product_model"]
            part = model_failure_spare_mapping["original_part_code"]
            products = model_failure_spare_mapping["products"]

            # 检查产品列表是否为空
            if not products or len(products) == 0:
                log.warning(
                    f"[科学库存计算] 型号{model}故障件{part}在库房{warehouse_code}下没有产品，"
                    f"设置max_failure_count=0（没有产品则无故障）"
                )
                model_failure_spare_mapping["max_failure_count"] = 0
                continue

            # 计算每个型号+故障件在过去x天内的故障次数最大值
            max_failure_count = 0
            period_count = 0
            max_period_start = None
            max_period_end = None
            log.debug(
                f"[科学库存计算] 开始滚动计算型号{model}故障件{part}的最大故障次数，"
                f"产品数量={len(products)}，回溯日期={start_date.strftime('%Y-%m-%d')}到{input_date.strftime('%Y-%m-%d')}"
            )

            while start_date <= input_date:
                period_count += 1
                end_date = start_date + timedelta(days=gap)
                if end_date > input_date:
                    end_date = input_date

                failure_count = await ScienceWarehouseServiceChange.get_failure_count_by_model_and_part_in_products(
                    model, part, start_date, end_date, products
                )

                if failure_count > max_failure_count:
                    max_failure_count = failure_count
                    max_period_start = start_date
                    max_period_end = end_date

                log.debug(
                    f"[科学库存计算] 型号{model}故障件{part}周期{period_count} "
                    f"({start_date.strftime('%Y-%m-%d')}到{end_date.strftime('%Y-%m-%d')}) "
                    f"故障次数={failure_count}，当前最大值={max_failure_count}"
                )

                start_date += timedelta(days=gap)

            # 保持实际计算结果，不强制设为1（如果历史数据中确实没有故障，则为0）
            model_failure_spare_mapping["max_failure_count"] = max_failure_count
            log.info(
                f"[科学库存计算] 型号{model}故障件{part}最大滚动故障次数计算完成，"
                f"最大值={max_failure_count}，共计算{period_count}个周期"
                + (
                    f"，最大值出现在{max_period_start.strftime('%Y-%m-%d')}到{max_period_end.strftime('%Y-%m-%d')}"
                    if max_period_start and max_period_end
                    else ""
                )
            )

        # 6.计算每个型号+故障件需要多少备品
        skipped_count = 0  # 被跳过的故障件数量
        calculated_count = 0  # 成功计算的故障件数量
        for model_failure_spare_mapping in model_failure_spare_mappings:
            model = model_failure_spare_mapping["product_model"]
            product_config_code = model_failure_spare_mapping["product_config_code"]
            part = model_failure_spare_mapping["original_part_code"]
            context = model_failure_spare_mapping["context"]
            if model_failure_spare_mapping["product_count"] == 0:
                # 5.1 如果这种故障件没有该派生码的产品跑在库房支撑的路局下，则跳过
                log.warning(
                    f"[科学库存计算] 型号{model}派生码{product_config_code}故障件{part}"
                    f"在库房{warehouse_code}支撑的路局下没有产品，跳过"
                    + (f"（{context['error']}）" if context["error"] else "")
                )
                skipped_count += 1
                continue
            # 5.2 获取分布（上下文中已按故障数选择 Aaron 拟合或指数估计）
            distribution = context["distribution"]
            fit_type = context["fit_type"]
            if distribution is None:
                log.error(
                    f"[科学库存计算] 型号{model}派生码{product_config_code}故障件{part}"
                    f"获取分布失败（fit_type={fit_type}，{context['error']}），跳过"
                )
                skipped_count += 1
                continue
            # 5.3 按零件位置累加备件量（BOM 用量已体现在位置数中）
            quantity = ScienceWarehouseServiceChange.calculate_spare_quantity_by_units(
                distribution,
                context["units_by_product"],
                model_failure_spare_mapping["products"],
                context["hours_per_day"],
                input_date,
                time_interval_days,
            )
            model_failure_spare_mapping["fit_type"] = fit_type
            model_failure_spare_mapping["quantity"] = quantity
            calculated_count += 1
            log.info(
                f"[科学库存计算] 型号{model}派生码{product_config_code}故障件{part}备件量计算完成，"
                f"产品数={model_failure_spare_mapping['product_count']}，"
                f"零件位置数={model_failure_spare_mapping['unit_count']}，"
                f"拟合类型={fit_type}，分布={context['distribution_name']}，quantity={quantity:.5f}"
            )

        # 7.计算该库房-单备品的备件量 以及 最大滚动故障次数
        total_quantity = 0
        total_max_failure_count = 0
        quantity_details = []  # 记录每个故障件的quantity详情
        max_failure_count_details = []  # 记录每个故障件的max_failure_count详情

        log.info(
            f"[科学库存计算] 开始累加库房{warehouse_code}备品{spare_part_code}的备件量和最大故障次数"
        )

        for model_failure_spare_mapping in model_failure_spare_mappings:
            model = (
                f"{model_failure_spare_mapping['product_model']}"
                f"({model_failure_spare_mapping['product_config_code']})"
            )
            part = model_failure_spare_mapping["original_part_code"]

            # 累加最大故障次数（只累加有产品的映射，没有产品的映射不参与累加）
            if model_failure_spare_mapping.get("product_count", 0) > 0:
                if "max_failure_count" in model_failure_spare_mapping:
                    max_failure_count = model_failure_spare_mapping["max_failure_count"]
                    total_max_failure_count += max_failure_count
                    max_failure_count_details.append(
                        f"{model}+{part}:{max_failure_count}"
                    )
                else:
                    log.warning(
                        f"[科学库存计算] 型号{model}故障件{part}缺少max_failure_count字段，跳过累加"
                    )
                    max_failure_count_details.append(f"{model}+{part}:缺失")
            else:
                # 没有产品的映射，max_failure_count应该是0，但不参与累加（因为该映射已被跳过）
                max_failure_count = model_failure_spare_mapping.get(
                    "max_failure_count", 0
                )
                max_failure_count_details.append(
                    f"{model}+{part}:{max_failure_count}(无产品，不累加)"
                )

            # 累加备件量
            if "quantity" in model_failure_spare_mapping:
                quantity = model_failure_spare_mapping["quantity"]
                if quantity is not None:
                    total_quantity += quantity
                    quantity_details.append(f"{model}+{part}:{quantity:.5f}")
                else:
                    quantity_details.append(f"{model}+{part}:None")
            else:
                # 记录被跳过的故障件
                quantity_details.append(f"{model}+{part}:跳过(未计算)")

        rounded_quantity = round_required_quantity(total_quantity)
        log.info(
            f"[科学库存计算] 库房{warehouse_code}备品{spare_part_code}计算完成，"
            f"总故障件映射数={len(model_failure_spare_mappings)}，"
            f"成功计算={calculated_count}，跳过={skipped_count}，"
            f"最终备件量={rounded_quantity}，"
            f"总最大故障次数={total_max_failure_count}"
        )
        if quantity_details:
            log.debug(
                f"[科学库存计算] 库房{warehouse_code}备品{spare_part_code}各故障件备件量详情: {', '.join(quantity_details)}"
            )
        if max_failure_count_details:
            log.debug(
                f"[科学库存计算] 库房{warehouse_code}备品{spare_part_code}各故障件最大故障次数详情: {', '.join(max_failure_count_details)}"
            )

        result = {
            "success": True,
            "warehouse_code": warehouse_code,
            "warehouse_name": warehouse_spare.warehouse_name,
            "spare_part_code": spare_part_code,
            "spare_part_name": warehouse_spare.part_name,
            "quantity": rounded_quantity,
            "max_failure_count": total_max_failure_count,
            "calculation_method": "fitted",
            "error_code": None,
            "error_message": None,
            "statistics": {
                "total_mappings": len(model_failure_spare_mappings),
                "calculated_count": calculated_count,
                "skipped_count": skipped_count,
                "total_max_failure_count": total_max_failure_count,  # 统计信息中也包含
                "mapping_details": [
                    {
                        "product_model": m["product_model"],
                        "product_config_code": m["product_config_code"],
                        "original_part_code": m["original_part_code"],
                        "allotment_product_count": m.get("allotment_product_count", 0),
                        "product_count": m.get("product_count", 0),
                        "unit_count": m.get("unit_count", 0),
                        "bl_quantity": m["context"]["bl_quantity"],
                        "failure_count": m["context"]["failure_count"],
                        "fit_type": m["context"]["fit_type"],
                        "distribution": m["context"]["distribution_name"],
                        "quantity": m.get("quantity"),
                        "max_failure_count": m.get("max_failure_count", 0),
                        "error": m["context"]["error"],
                    }
                    for m in model_failure_spare_mappings
                ],
            },
        }
        return result

    @staticmethod
    async def get_single_warehouse_spare(warehouse_code: str, spare_part_code: str):
        """
        获取单库房-单备品信息
        数据示例：
        {
            "warehouse_code": "xx",
            "warehouse_name": "xx",
            "part_code": "xx",
            "part_name": "xx",
            "default_quantity": xx
        }
        """
        async with async_db_session() as db:
            warehouse_spare = await warehouse_inventory_dao.get_by_warehouse_and_part(
                db, warehouse_code, spare_part_code
            )
            if warehouse_spare is None:
                log.error(f"库房{warehouse_code}备品{spare_part_code}信息不存在")
                return None
            return warehouse_spare

    @staticmethod
    async def get_spare_models_by_spare_part_code(spare_part_code: str):
        """
        获取备品支持的 型号-故障件-备品 映射关系去重集
        数据示例：
        [
            {product_model:xx,derived_code:xx,original_part_name:xx,original_part_code:xx,spare_part_name:xx,spare_part_code:xx,created_by:xx,changed_time:xx},
            {product_model:xx,derived_code:xx,original_part_name:xx,original_part_code:xx,spare_part_name:xx,spare_part_code:xx,created_by:xx,changed_time:xx},
        :param spare_part_code: 备品编码
        :return: 备品支持的 型号-派生码-故障件-备品 映射关系去重集
            （根据product_model，规范化后的product_config_code，original_part_code，spare_part_code去重）
        """
        async with async_db_session() as db:
            spare_models = await part_spare_mapping_dao.get_by_spare_part_code(
                db, spare_part_code
            )
            if spare_models is None or len(spare_models) == 0:
                log.error(
                    f"备品{spare_part_code}支持的 型号-故障件-备品 映射关系不存在"
                )
                return None

            # 同一型号多个派生码各自独立计算，空派生码按 PS00 合并
            seen = {}
            deduplicated_models = []

            for model in spare_models:
                product_config_code = normalize_product_config_code(
                    model.product_config_code
                )
                # 科学库存只针对铁路(评审PR#3意见): 剔除风电型号
                if await resolve_industry(
                    db, str(model.product_model).strip()
                ) != Industry.RAILWAY:
                    continue
                key = (
                    model.product_model,
                    product_config_code,
                    model.original_part_code,
                    model.spare_part_code,
                )
                # 如果这个组合还没出现过，添加到结果中
                if key not in seen:
                    seen[key] = True
                    # 将ORM对象转换为字典，便于后续使用
                    model_dict = {
                        "product_model": model.product_model,
                        "product_config_code": product_config_code,
                        "original_part_name": model.original_part_name,
                        "original_part_code": model.original_part_code,
                        "spare_part_name": model.spare_part_name,
                        "spare_part_code": model.spare_part_code,
                        "created_by": model.created_by,
                        "changed_time": model.changed_time,
                    }
                    deduplicated_models.append(model_dict)

            return deduplicated_models

    @staticmethod
    async def get_allotments_by_warehouse_code(warehouse_code: str):
        """
        获取库房支撑的路局
        数据示例：
        [
            "xx","xx"
        ]
        :param warehouse_code: 库房编码
        :return: 库房支撑的路局
        """
        async with async_db_session() as db:
            allotments = await warehouse_dao.get_by_code(db, warehouse_code)
            if allotments is None or len(allotments) == 0:
                log.error(f"库房{warehouse_code}支撑的路局不存在")
                return None
            # 过滤掉None值，避免查询失败
            allotment_two_list = [
                allotment.allotment_two
                for allotment in allotments
                if allotment.allotment_two is not None
            ]
            if not allotment_two_list:
                log.warning(f"库房{warehouse_code}的所有配属记录的二级配属字段都是None")
                return None
            return list(set(allotment_two_list))

    @staticmethod
    async def get_products_by_allotment_two_and_model(allotment_two: str, model: str):
        """
        获取指定二级配属下的所有产品编号（型号在指定型号列表中）
        数据示例：
        [
            "xx","xx"
        ]
        :param allotment_two: 二级配属
        :param model: 产品型号
        :return: 指定二级配属下的所有产品编号（型号在指定型号列表中）
        """
        # 如果allotment_two为None，直接返回None，避免查询失败
        if allotment_two is None:
            log.warning(f"二级配属为None，无法查询产品编号（型号={model}）")
            return None

        async with async_db_session() as db:
            products = await allotment_dao.get_by_allotment_two_and_model(
                db, allotment_two, model
            )
            if products is None or len(products) == 0:
                log.debug(f"二级配属{allotment_two}下的产品编号不存在（型号={model}）")
                return None
            return list(set([product.product_number for product in products]))

    @staticmethod
    async def _lookup_aaron_distribution(
        model: str,
        part: str,
        input_date: date,
        product_config_code: str,
    ):
        """按型号、派生码、故障件和截止日期读取已入库的 Aaron 分布。"""
        for source in (False, True):
            async with async_db_session() as db:
                rows = await fit_part_dao.get_by_model_and_part(
                    db,
                    model,
                    part,
                    input_date,
                    method=FitMethodType.MLE,
                    check=FitCheckType.BIC,
                    source=source,
                    product_config_code=product_config_code,
                    industry='railway',
                )
            if not rows:
                continue
            params = convert_to_pydantic_model(rows[0], DistributionParams)
            distribution = await distribute_service.get_distribution_by_params(params)
            if distribution is not None:
                return distribution
        return None

    @staticmethod
    async def _get_or_create_aaron_distribution(
        model: str,
        part: str,
        input_date: date,
        product_config_code: str,
    ):
        """先读拟合结果，没有则 Aaron 计算入库后再读。"""
        distribution = await ScienceWarehouseServiceChange._lookup_aaron_distribution(
            model, part, input_date, product_config_code
        )
        if distribution is not None:
            return distribution

        input_date_text = (
            input_date.isoformat() if isinstance(input_date, date) else str(input_date)
        )
        await aaron_part_fit_service.create(
            obj=CreateFitPartInParam(
                model=model,
                part=part,
                product_config_code=product_config_code,
                input_date=input_date_text,
                method=FitMethodType.MLE,
            )
        )
        return await ScienceWarehouseServiceChange._lookup_aaron_distribution(
            model, part, input_date, product_config_code
        )

    @staticmethod
    async def get_mapping_context(
        model: str,
        product_config_code: str | None,
        part: str,
        input_date: date,
        use_cached_fit: bool = True,
        cache: dict | None = None,
    ) -> dict:
        """
        型号+派生码+故障件的计算上下文：零件位置、运行参数、分布。
        同一批次内按 key 缓存，避免每个库房重复打标拟合。
        """
        product_config_code = normalize_product_config_code(product_config_code)
        key = (model, product_config_code, part, input_date, use_cached_fit)
        if cache is not None and key in cache:
            return cache[key]
        context = await ScienceWarehouseServiceChange._build_mapping_context(
            model, product_config_code, part, input_date, use_cached_fit
        )
        if cache is not None:
            cache[key] = context
        return context

    @staticmethod
    async def _build_mapping_context(
        model: str,
        product_config_code: str,
        part: str,
        input_date: date,
        use_cached_fit: bool,
    ) -> dict:
        context = {
            "units_by_product": {},
            "bl_quantity": 0,
            "hours_per_day": 0.0,
            "failure_count": 0,
            "distribution": None,
            "distribution_name": None,
            "fit_type": "insufficient_data",
            "error": None,
        }
        async with async_db_session() as db:
            despatch_rows = await despatch_dao.get_despatchs_by_model(
                db, model, product_config_code=product_config_code
            )
            failure_rows = await failure_dao.railway.get_by_model_and_part(
                db, model, part, input_date, product_config_code=product_config_code
            )
            ebom_rows = await get_ebom_tree_with_parents(
                db, model, product_config_code, part
            )
            product_row = await product_dao.railway.get_by_model(
                db, model, product_config_code=product_config_code
            )
        context["failure_count"] = len(failure_rows)

        if product_row is None:
            context["error"] = f"型号{model}派生码{product_config_code}的产品运行参数不存在"
            return context
        if not ebom_rows:
            context["error"] = f"型号{model}派生码{product_config_code}中零部件{part}的BOM信息不存在"
            return context
        product_data = convert_to_pydantic_model(product_row, ProductParam)
        context["hours_per_day"] = (
            product_data.year_days * product_data.avg_worktime / 365
        )
        context["bl_quantity"] = convert_to_total_quantity(ebom_rows, part)
        context["units_by_product"] = build_units_by_product(
            model,
            convert_to_pydantic_models(despatch_rows, DespatchParam),
            failure_rows,
            context["bl_quantity"],
        )

        try:
            if context["failure_count"] > _MIN_FAILURES_FOR_FIT:
                await ScienceWarehouseServiceChange._resolve_fitted_distribution(
                    context, model, product_config_code, part, input_date, use_cached_fit
                )
            else:
                # 样本不足：λ = 故障数 / (派生码维度累计运行时间 × BOM用量)，零故障按 1/t
                async with async_db_session() as db:
                    lambda_ = await aaron_part_fit_service.none_tag_fit(
                        db, model, part, input_date, product_config_code=product_config_code
                    )
                context["distribution"] = Exponential_Distribution(Lambda=lambda_)
                context["distribution_name"] = f"Exponential_1P(λ={lambda_:.6e})"
                context["fit_type"] = "exponential_fit"
        except (DataValidationError, FailureCheckError) as e:
            context["error"] = e.msg
        except Exception as e:
            log.exception(
                f"[科学库存计算] 型号{model}派生码{product_config_code}故障件{part}获取分布异常: {e}"
            )
            context["error"] = f"{type(e).__name__}: {e}"
        return context

    @staticmethod
    async def _resolve_fitted_distribution(
        context: dict,
        model: str,
        product_config_code: str,
        part: str,
        input_date: date,
        use_cached_fit: bool,
    ) -> None:
        """故障数足够时取 Aaron 拟合的 BIC 最优分布。"""
        if use_cached_fit:
            distribution = await ScienceWarehouseServiceChange._get_or_create_aaron_distribution(
                model, part, input_date, product_config_code
            )
            if distribution is None:
                context["error"] = "Aaron 拟合结果为空"
                return
        else:
            tags = await aaron_part_strategy_service.part_tag_process(
                model, part, input_date, product_config_code=product_config_code
            )
            fit = await aaron_part_fit_service.tag_fit(tags, FitMethodType.MLE)
            distribution = fit.best_distribution
        context["distribution"] = distribution
        context["distribution_name"] = getattr(
            distribution, "param_title_long", type(distribution).__name__
        )
        context["fit_type"] = "fitted"

    @staticmethod
    async def get_failure_count_by_model_and_part_in_products(
        model: str, part: str, start_date: date, end_date: date, products: list
    ):
        """
        获取型号+故障件在指定时间范围内的故障次数
        :param model: 产品型号
        :param part: 故障件
        :param start_date: 开始日期（date对象）
        :param end_date: 结束日期（date对象）
        :param products: 需要被管理的产品编号列表
        :return: 故障次数（整数）
        """
        # 将date对象转换为字符串格式 "YYYY-MM-DD"，因为discovery_date字段是String类型
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        async with async_db_session() as db:
            failure_count = (
                await failure_dao.railway.get_failure_count_by_model_and_part_in_products(
                    db, model, part, start_date_str, end_date_str, products
                )
            )
            return failure_count

    @staticmethod
    def calculate_spare_quantity_by_units(
        distribution,
        units_by_product: dict[str, list[Optional[date]]],
        products: list,
        hours_per_day: float,
        input_date: date,
        time_interval_days: int,
    ) -> float:
        """
        按零件位置计算备件量：每个位置 F(t+Δ) - F(t) 累加。
        t 为截止日距寿命起点的累计运行小时，起点晚于截止日的位置从 0 开始计。

        :param units_by_product: 产品编号 -> 各零件位置寿命起点
        :param products: 需要被管理的产品编号列表
        :param hours_per_day: 日历日折算运行小时 = year_days * avg_worktime / 365
        :return: 备件量
        """
        end_date = input_date + timedelta(days=time_interval_days)
        start_hours, end_hours = [], []
        missing_start_count = 0
        for product_number in products:
            for life_start in units_by_product.get(product_number, []):
                if life_start is None:
                    missing_start_count += 1
                    continue
                start_hours.append(max(0.0, (input_date - life_start).days * hours_per_day))
                end_hours.append(max(0.0, (end_date - life_start).days * hours_per_day))
        if missing_start_count:
            log.warning(f"[备件量计算] {missing_start_count}个零件位置缺少寿命起点，跳过")
        if not start_hours:
            return 0.0
        start_cdf = np.atleast_1d(distribution.CDF(xvals=np.array(start_hours), show_plot=False))
        end_cdf = np.atleast_1d(distribution.CDF(xvals=np.array(end_hours), show_plot=False))
        return float(np.clip(end_cdf - start_cdf, 0.0, None).sum())

    @staticmethod
    async def batch_warehouse_spare_calculate(
        time_interval_days: int,
        input_date: str | date,
        warehouse_spare_pairs: list[tuple[str, str]],
        calculation_id: str | None = None,
        save_to_db: bool = False,
        use_cached_fit: bool = True,
    ) -> dict:
        """
        批量计算多个库房-备品组合的备件量

        :param time_interval_days: 需求预测时间间隔（天数）
        :param input_date: 计算截止日期
        :param warehouse_spare_pairs: 库房-备品组合列表，格式：[(warehouse_code, spare_part_code), ...]
        :param calculation_id: 计算批次ID（可选，如果不提供则自动生成）
        :param save_to_db: 是否保存到数据库（默认True）
        :param use_cached_fit: False 时全部现场 Aaron 拟合、不读写 fit_part（测试口径）
        :return: 批量计算结果统计
        """
        from datetime import date as date_type
        from backend.utils.snowflake import snowflake
        from backend.app.calcu.crud.crud_science_warehouse_result import (
            science_warehouse_result_dao,
        )

        # 生成计算批次ID
        if calculation_id is None:
            calculation_id = f"SW_{snowflake.generate()}"

        # 确保 input_date 是 date 对象
        if isinstance(input_date, str):
            from backend.app.fit.utils.time_utils import dateutils

            input_date = dateutils.validate_and_parse_date(input_date)

        results = []
        success_count = 0
        failed_count = 0
        total_quantity = 0
        fit_context_cache: dict = {}

        log.info(
            f"[批量科学库存计算] 开始计算，批次ID={calculation_id}，"
            f"共{len(warehouse_spare_pairs)}个库房-备品组合"
        )

        # 批量计算
        for idx, (warehouse_code, spare_part_code) in enumerate(
            warehouse_spare_pairs, 1
        ):
            log.info(
                f"[批量科学库存计算] 进度 {idx}/{len(warehouse_spare_pairs)}: "
                f"库房{warehouse_code}备品{spare_part_code}"
            )

            try:
                result = await ScienceWarehouseServiceChange.single_warehouse_single_spare_calculate(
                    time_interval_days=time_interval_days,
                    input_date=input_date,
                    warehouse_code=warehouse_code,
                    spare_part_code=spare_part_code,
                    use_cached_fit=use_cached_fit,
                    fit_context_cache=fit_context_cache,
                )

                # 统一处理成功和失败的结果
                if result.get("success", False):
                    success_count += 1
                    total_quantity += result.get("quantity", 0)
                else:
                    failed_count += 1
                    log.warning(
                        f"[批量科学库存计算] 库房{warehouse_code}备品{spare_part_code}计算失败: "
                        f"{result.get('error_code')} - {result.get('error_message')}"
                    )

                results.append(result)

            except Exception as e:
                failed_count += 1
                log.error(
                    f"[批量科学库存计算] 库房{warehouse_code}备品{spare_part_code}计算异常: {str(e)}"
                )
                # 创建失败结果
                results.append(
                    {
                        "success": False,
                        "warehouse_code": warehouse_code,
                        "spare_part_code": spare_part_code,
                        "warehouse_name": None,
                        "spare_part_name": None,
                        "quantity": 0,
                        "max_failure_count": 0,  # 异常情况下为0
                        "calculation_method": "failed",
                        "error_code": "EXCEPTION",
                        "error_message": str(e),
                        "statistics": {
                            "total_mappings": 0,
                            "calculated_count": 0,
                            "skipped_count": 0,
                            "total_max_failure_count": 0,
                        },
                    }
                )

        # 保存到数据库
        if save_to_db:
            await ScienceWarehouseServiceChange._save_batch_results_to_db(
                calculation_id=calculation_id,
                results=results,
                time_interval_days=time_interval_days,
                input_date=input_date,
            )

        log.info(
            f"[批量科学库存计算] 批次ID={calculation_id}计算完成，"
            f"成功={success_count}，失败={failed_count}，总备件量={total_quantity}"
        )

        return {
            "calculation_id": calculation_id,
            "total_pairs": len(warehouse_spare_pairs),
            "success_count": success_count,
            "failed_count": failed_count,
            "total_quantity": total_quantity,
            "results": results,
        }

    @staticmethod
    async def _save_batch_results_to_db(
        calculation_id: str,
        results: list[dict],
        time_interval_days: int,
        input_date: date,
    ):
        """
        将批量计算结果保存到数据库

        根据数据表结构：
        - 必填字段（nullable=False）：calculation_id, warehouse_code, warehouse_name,
          spare_part_code, spare_part_name, required_quantity, calculation_method,
          time_interval_days, input_date, created_time, confidence, max_failure_count

        :param calculation_id: 计算批次ID
        :param results: 计算结果列表
        :param time_interval_days: 时间间隔（天）
        :param input_date: 输入日期
        """

        async with async_db_session() as db:
            # 1. 清空该批次的历史数据
            await science_warehouse_result_dao.clear_by_calculation_id(
                db, calculation_id
            )

            # 2. 准备结果数据（只保存成功的结果）
            result_data = []
            for result in results:
                # 只保存成功的结果
                if not result.get("success", False):
                    continue

                # 确保必填字段都有值（不能为None）
                warehouse_code = result.get("warehouse_code") or ""
                warehouse_name = (
                    result.get("warehouse_name") or warehouse_code or "未知库房"
                )
                spare_part_code = result.get("spare_part_code") or ""
                spare_part_name = (
                    result.get("spare_part_name") or spare_part_code or "未知备品"
                )
                required_quantity = result.get("quantity", 0)
                calculation_method = result.get("calculation_method") or "fitted"
                confidence = 0.9  # 成功计算的置信度
                max_failure_count = result.get(
                    "max_failure_count", 0
                )  # 最大滚动故障次数

                # 构建必填字段数据
                db_record = {
                    "calculation_id": calculation_id,
                    "warehouse_code": warehouse_code,
                    "warehouse_name": warehouse_name,
                    "spare_part_code": spare_part_code,
                    "spare_part_name": spare_part_name,
                    "required_quantity": round_required_quantity(required_quantity),
                    "calculation_method": calculation_method,
                    "time_interval_days": time_interval_days,
                    "input_date": input_date,
                    "created_time": date.today(),
                    "confidence": confidence,
                    "max_failure_count": int(max_failure_count),  # 确保是整数
                }

                result_data.append(db_record)

            # 3. 批量保存结果数据
            if result_data:
                await science_warehouse_result_dao.bulk_create(db, result_data)
                log.info(
                    f"[批量科学库存计算] 批次ID={calculation_id}保存了{len(result_data)}条结果到数据库"
                )
            else:
                log.warning(
                    f"[批量科学库存计算] 批次ID={calculation_id}没有成功的结果需要保存到数据库"
                )
