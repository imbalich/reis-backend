#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
科学库存改版
思路分析：

"""
from datetime import date, datetime, timedelta
import json
import math
from typing import Optional
from sqlalchemy import select


from backend.app.calcu.crud.crud_science_warehouse_result import (
    science_warehouse_result_dao,
)
from backend.app.fit.schema.base_param import ProductParam
from backend.app.fit.utils.convert_model import convert_to_pydantic_model
from reliability.Distributions import Exponential_Distribution
from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_allotment import allotment_dao
from backend.app.datamanage.crud.crud_part_spare_mapping import part_spare_mapping_dao
from backend.app.datamanage.crud.crud_warehouse_inventory import warehouse_inventory_dao
from backend.app.datamanage.crud.crud_warehouse import warehouse_dao
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.fit.service.part_fit_service import PartFitService
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.utils.data_check_utils import datacheckutils
from backend.common.exception.errors import DataValidationError, FailureCheckError
from backend.common.log import log
from backend.database.db import async_db_session


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


class ScienceWarehouseServiceChange:
    @staticmethod
    async def single_warehouse_single_spare_calculate(
        time_interval_days: int,
        input_date: str | date,
        warehouse_code: str,
        spare_part_code: str,
    ) -> dict:
        """
        单库房-单备品-计算流程

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
        # 4.计算每种故障有多少产品编号被库房管理
        log.info(
            f"[科学库存计算] 库房{warehouse_code}备品{spare_part_code}，开始计算，共{len(model_failure_spare_mappings)}个故障件映射"
        )
        for model_failure_spare_mapping in model_failure_spare_mappings:

            model = model_failure_spare_mapping["product_model"]
            part = model_failure_spare_mapping["original_part_code"]

            products_set = set()

            for allotment in allotments:
                allotment_products = await ScienceWarehouseServiceChange.get_products_by_allotment_two_and_model(
                    allotment, model
                )
                if allotment_products:
                    products_set.update(allotment_products)
            # 4.2 计算一种故障总计有多少需要被这个库房管理
            products = list(products_set)
            product_count = len(products)
            model_failure_spare_mapping["product_count"] = product_count
            model_failure_spare_mapping["products"] = products
            log.info(
                f"[科学库存计算] 型号{model}故障件{part}，在库房{warehouse_code}支撑的路局下共有{product_count}个产品"
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
            if model_failure_spare_mapping["product_count"] == 0:
                # 5.1 如果这种故障件没有型号跑在库房支撑的路局下，则跳过
                model = model_failure_spare_mapping["product_model"]
                part = model_failure_spare_mapping["original_part_code"]
                log.warning(
                    f"[科学库存计算] 型号{model}故障件{part}在库房{warehouse_code}支撑的路局下没有产品，跳过"
                )
                skipped_count += 1
                continue
            # 5.2 如果这种故障件有型号跑在库房支撑的路局下，则计算每个型号+故障件需要多少备品
            model = model_failure_spare_mapping["product_model"]
            part = model_failure_spare_mapping["original_part_code"]
            products = model_failure_spare_mapping["products"]
            # 5.2 打标 - 拟合 - 获取分布
            # 5.2.1 标签获取
            distribution, fit_type = (
                await ScienceWarehouseServiceChange.get_distribution_by_model_and_part(
                    model, part, input_date
                )
            )
            if distribution is None:
                log.error(
                    f"[科学库存计算] 型号{model}故障件{part}获取分布失败（fit_type={fit_type}），跳过"
                )
                skipped_count += 1
                continue
            # 5.3 计算单型号+故障件的备件量
            log.info(
                f"[科学库存计算] 型号{model}故障件{part}开始计算备件量，产品数量={len(products)}，拟合类型={fit_type}"
            )
            quantity = await ScienceWarehouseServiceChange.calculate_spare_quantity(
                distribution, products, model, input_date, time_interval_days
            )
            model_failure_spare_mapping["fit_type"] = fit_type
            model_failure_spare_mapping["quantity"] = quantity
            calculated_count += 1
            log.info(
                f"[科学库存计算] 型号{model}故障件{part}备件量计算完成，quantity={quantity:.4f}"
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
            model = model_failure_spare_mapping["product_model"]
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
                    ceil_quantity = math.ceil(quantity)
                    total_quantity += ceil_quantity
                    quantity_details.append(f"{model}+{part}:{quantity:.4f}(ceil={ceil_quantity})")
                else:
                    quantity_details.append(f"{model}+{part}:None")
            else:
                # 记录被跳过的故障件
                quantity_details.append(f"{model}+{part}:跳过(未计算)")

        log.info(
            f"[科学库存计算] 库房{warehouse_code}备品{spare_part_code}计算完成，"
            f"总故障件映射数={len(model_failure_spare_mappings)}，"
            f"成功计算={calculated_count}，跳过={skipped_count}，"
            f"最终备件量={math.ceil(total_quantity)}，"
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
            "quantity": math.ceil(total_quantity),
            "max_failure_count": total_max_failure_count,
            "calculation_method": "fitted",
            "error_code": None,
            "error_message": None,
            "statistics": {
                "total_mappings": len(model_failure_spare_mappings),
                "calculated_count": calculated_count,
                "skipped_count": skipped_count,
                "total_max_failure_count": total_max_failure_count,  # 统计信息中也包含
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
        :return: 备品支持的 型号-故障件-备品 映射关系去重集（根据product_model，original_part_code，spare_part_code去重）
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

            # 根据product_model，original_part_code，spare_part_code去重
            # 使用字典，以 (product_model, original_part_code, spare_part_code) 作为key
            seen = {}
            deduplicated_models = []

            for model in spare_models:
                key = (
                    model.product_model,
                    model.original_part_code,
                    model.spare_part_code,
                )
                # 如果这个组合还没出现过，添加到结果中
                if key not in seen:
                    seen[key] = True
                    # 将ORM对象转换为字典，便于后续使用
                    model_dict = {
                        "product_model": model.product_model,
                        "derived_code": model.derived_code,
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
    async def get_distribution_by_model_and_part(
        model: str, part: str, input_date: str | date = None
    ):
        """
        获取型号+故障件的分布
        :param model: 产品型号
        :param part: 故障件
        :param input_date: 输入日期
        :return: 分布
        """
        async with async_db_session() as db:
            try:
                tags = await part_strategy_service.part_tag_process(
                    model, part, input_date
                )
                if not tags or len(tags) == 0:
                    log.warning(
                        f"科学库存计算获取型号{model}故障件{part}的标签为空，无法进行拟合"
                    )
                    return None, "insufficient_data"

                log.debug(
                    f"科学库存计算获取型号{model}故障件{part}的标签数量={len(tags)}"
                )

                fit = await PartFitService.tag_fit(tags)
                if fit is None:
                    log.error(f"科学库存计算获取型号{model}故障件{part}的拟合结果为空")
                    return None, "insufficient_data"

                distribution = fit.best_distribution
                if distribution is None:
                    log.error(
                        f"科学库存计算获取型号{model}故障件{part}的最佳分布为空，拟合可能失败"
                    )
                    return None, "insufficient_data"

                return distribution, "fitted"
            except DataValidationError as e:
                # 产品信息不存在或累计运行时间不足等数据验证错误
                log.warning(
                    f"科学库存计算获取型号{model}故障件{part}的分布时遇到数据验证错误：{str(e)}，"
                    f"将跳过该故障件"
                )
                return None, "insufficient_data"
            except FailureCheckError as e:
                log.info(
                    f"科学库存计算获取型号{model}故障件{part}的分布时遇到故障检查错误，"
                    f"将使用指数分布拟合: {str(e)}"
                )
                failures = await fit_part_dao.get_by_model_and_part(
                    db, model, part, input_date
                )
                t = await datacheckutils.total_run_time(db, model)
                # 更严格的检查：避免除零错误（包括浮点数0.0）
                if t is None or t <= 0:
                    log.error(
                        f"科学库存计算获取型号{model}故障件{part}的分布失败，"
                        f"累计运行时间为0或无效（t={t}）"
                    )
                    return None, "insufficient_data"
                # 确保failures不为空
                if not failures or len(failures) == 0:
                    log.warning(
                        f"科学库存计算获取型号{model}故障件{part}的分布失败，"
                        f"故障数据为空，无法进行指数分布拟合"
                    )
                    return None, "insufficient_data"
                lambda_ = len(failures) / t
                # 确保lambda_是有效的正数
                if lambda_ <= 0:
                    log.error(
                        f"科学库存计算获取型号{model}故障件{part}的分布失败，"
                        f"计算出的lambda值无效（lambda_={lambda_}，failures={len(failures)}，t={t}）"
                    )
                    return None, "insufficient_data"
                distribution = Exponential_Distribution(Lambda=lambda_)
                return distribution, "exponential_fit"
            except Exception as e:
                import traceback

                error_trace = traceback.format_exc()
                log.error(
                    f"科学库存计算获取型号{model}故障件{part}的分布失败,"
                    f"异常类型: {type(e).__name__}, "
                    f"失败原因: {str(e)}, "
                    f"堆栈跟踪: {error_trace}"
                )
                return None, "insufficient_data"

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
                await failure_dao.get_failure_count_by_model_and_part_in_products(
                    db, model, part, start_date_str, end_date_str, products
                )
            )
            return failure_count

    @staticmethod
    async def calculate_spare_quantity(
        distribution,
        products: list,
        product_model: str,
        input_date: str | date,
        time_interval_days: int,
    ):
        """
        计算备件量
        优化思路：
        1. 批量查询发运表获取发运日期（优先）
        2. 对于发运表中没有的产品，批量查询故障表获取 manufacturing_date（备选）
        3. 构建完整的产品编号->发运日期映射
        4. 遍历每个产品，计算CDF差值并累加

        :param distribution: 分布对象
        :param products: 需要被管理的产品编号列表
        :param product_model: 产品型号（用于查询故障表）
        :param input_date: 输入日期
        :param time_interval_days: 需求预测时间间隔（天数）
        :return: 备件量
        """
        if not products:
            log.warning(f"[备件量计算] 型号{product_model}产品列表为空，返回0.0")
            return 0.0

        # 确保 input_date 是 date 对象
        if isinstance(input_date, str):
            from backend.app.fit.utils.time_utils import dateutils

            input_date = dateutils.validate_and_parse_date(input_date)

        log.info(
            f"[备件量计算] 型号{product_model}开始计算，产品数量={len(products)}，"
            f"input_date={input_date}，time_interval_days={time_interval_days}，"
            f"产品编号列表={products}"
        )

        async with async_db_session() as db:
            # 1. 获取产品运行参数（只需要查询一次）
            product_data = convert_to_pydantic_model(
                await product_dao.get_by_model(db, product_model), ProductParam
            )

            # 2. 批量查询发运表获取发运日期（优先）
            # 使用 select_models 的 identifier__in 参数进行批量查询
            despatch_data = await despatch_dao.select_models(
                db, identifier__in=products, repair_level__eq="新造"
            )

            # 构建产品编号->发运日期的映射（从发运表）
            product_despatch_map = {}
            for despatch in despatch_data:
                if despatch.identifier and despatch.life_cycle_time:
                    # 如果同一个产品编号有多条记录，取最早的
                    if (
                        despatch.identifier not in product_despatch_map
                        or despatch.life_cycle_time
                        < product_despatch_map[despatch.identifier]
                    ):
                        product_despatch_map[despatch.identifier] = (
                            despatch.life_cycle_time
                        )

            found_products = list(product_despatch_map.keys())
            log.info(
                f"[备件量计算] 型号{product_model}从发运表获取到{len(product_despatch_map)}个产品的发运日期，"
                f"找到的产品编号列表={found_products}"
            )

            # 3. 对于发运表中没有的产品，批量查询故障表获取 manufacturing_date
            missing_products = [p for p in products if p not in product_despatch_map]
            if missing_products:
                log.info(
                    f"[备件量计算] 型号{product_model}有{len(missing_products)}个产品在发运表中未找到，"
                    f"未找到的产品编号列表={missing_products}，尝试从故障表获取manufacturing_date"
                )
                # 批量查询故障表：根据 product_model 和 product_number 列表查询
                # 查询每个产品编号最早的 manufacturing_date
                stmt = (
                    select(failure_dao.model)
                    .where(
                        failure_dao.model.product_model == product_model,
                        failure_dao.model.product_number.in_(missing_products),
                        failure_dao.model.manufacturing_date.isnot(None),
                    )
                    .order_by(
                        failure_dao.model.product_number,
                        failure_dao.model.manufacturing_date,
                    )
                )
                result = await db.execute(stmt)
                failure_data = result.scalars().all()

                # 从故障表中提取 manufacturing_date（取每个产品编号最早的）
                seen_products = set()
                for failure in failure_data:
                    if (
                        failure.product_number
                        and failure.product_number not in seen_products
                    ):
                        seen_products.add(failure.product_number)
                        if failure.manufacturing_date:
                            # 解析 manufacturing_date（可能是字符串）
                            if isinstance(failure.manufacturing_date, str):
                                parsed_date = parse_discovery_date(
                                    failure.manufacturing_date
                                )
                                if parsed_date:
                                    product_despatch_map[failure.product_number] = (
                                        parsed_date
                                    )
                            elif isinstance(failure.manufacturing_date, date):
                                product_despatch_map[failure.product_number] = (
                                    failure.manufacturing_date
                                )
                found_from_failure = list(seen_products)
                log.info(
                    f"[备件量计算] 型号{product_model}从故障表获取到{len(seen_products)}个产品的manufacturing_date，"
                    f"从故障表找到的产品编号列表={found_from_failure}"
                )

            # 统计找不到发运日期的产品数量
            products_without_despatch = [
                p for p in products if p not in product_despatch_map
            ]
            if products_without_despatch:
                log.warning(
                    f"[备件量计算] 型号{product_model}有{len(products_without_despatch)}个产品找不到发运日期，"
                    f"找不到发运日期的产品编号列表={products_without_despatch}"
                )

            # 4. 计算每个产品的备件量（CDF差值）
            result = 0.0
            start_date = input_date
            end_date = input_date + timedelta(days=time_interval_days)
            skipped_products_count = 0  # 被跳过的产品数量
            invalid_interval_count = 0  # 运行时间区间无效的产品数量
            cdf_failed_count = 0  # CDF计算失败的产品数量
            cdf_zero_count = 0  # CDF计算结果为0的产品数量

            for product_number in products:
                # 获取该产品的发运日期
                despatch_date = product_despatch_map.get(product_number)

                # 如果找不到发运日期，跳过该产品
                if not despatch_date:
                    skipped_products_count += 1
                    continue

                # 计算运行时间（小时）
                start_x = (
                    (start_date - despatch_date).days
                    * product_data.year_days
                    * product_data.avg_worktime
                    / 365
                )
                end_x = (
                    (end_date - despatch_date).days
                    * product_data.year_days
                    * product_data.avg_worktime
                    / 365
                )

                # 确保运行时间为非负数
                start_x = max(0, start_x)
                end_x = max(0, end_x)

                # 如果开始时间大于等于结束时间，跳过
                if start_x >= end_x:
                    invalid_interval_count += 1
                    log.debug(
                        f"[备件量计算] 产品编号{product_number}运行时间区间无效，"
                        f"发运日期={despatch_date}，start_x={start_x:.2f}，end_x={end_x:.2f}，跳过"
                    )
                    continue

                # 计算CDF差值
                try:
                    yvals = distribution.CDF(xvals=[start_x, end_x], show_plot=False)
                    prediction = yvals[1] - yvals[0]
                    if prediction <= 0:
                        cdf_zero_count += 1
                        log.debug(
                            f"[备件量计算] 产品编号{product_number}CDF差值<=0，"
                            f"start_x={start_x:.2f}，end_x={end_x:.2f}，prediction={prediction:.6f}，跳过"
                        )
                    else:
                        result += prediction
                except Exception as e:
                    cdf_failed_count += 1
                    log.warning(
                        f"[备件量计算] 产品编号{product_number}计算CDF失败: {e}，跳过"
                    )
                    continue

            log.info(
                f"[备件量计算] 型号{product_model}计算完成，"
                f"总产品数={len(products)}，"
                f"找不到发运日期={skipped_products_count}，"
                f"运行时间区间无效={invalid_interval_count}，"
                f"CDF计算失败={cdf_failed_count}，"
                f"CDF差值<=0={cdf_zero_count}，"
                f"成功计算={len(products) - skipped_products_count - invalid_interval_count - cdf_failed_count - cdf_zero_count}，"
                f"最终备件量={result:.4f}"
            )

            if result == 0.0:
                log.warning(
                    f"[备件量计算] 型号{product_model}备件量计算结果为0，"
                    f"可能原因：所有产品都找不到发运日期({skipped_products_count})，"
                    f"或运行时间区间无效({invalid_interval_count})，"
                    f"或CDF计算失败({cdf_failed_count})，"
                    f"或CDF差值<=0({cdf_zero_count})"
                )

            return result

    @staticmethod
    async def batch_warehouse_spare_calculate(
        time_interval_days: int,
        input_date: str | date,
        warehouse_spare_pairs: list[tuple[str, str]],
        calculation_id: str | None = None,
        save_to_db: bool = False,
    ) -> dict:
        """
        批量计算多个库房-备品组合的备件量

        :param time_interval_days: 需求预测时间间隔（天数）
        :param input_date: 计算截止日期
        :param warehouse_spare_pairs: 库房-备品组合列表，格式：[(warehouse_code, spare_part_code), ...]
        :param calculation_id: 计算批次ID（可选，如果不提供则自动生成）
        :param save_to_db: 是否保存到数据库（默认True）
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
                    "required_quantity": int(required_quantity),  # 确保是整数
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
