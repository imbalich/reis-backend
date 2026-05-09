#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : spare_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/4/27 11:07
"""

import math
from datetime import date, timedelta

from backend.app.calcu.schema.distribute_param import DistributeType
from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.datamanage.crud.crud_allotment import allotment_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.fit.schema.base_param import ProductParam
from backend.app.fit.schema.fit_param import FitCheckType, FitMethodType
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.service.product_strategy_service import product_strategy_service
from backend.app.fit.utils.convert_model import convert_to_pydantic_model
from backend.app.fit.utils.time_utils import dateutils
from backend.common.exception import errors
from backend.common.log import log
from backend.database.db import async_db_session


class SpareService:
    @staticmethod
    def _build_despatch_map(tags: list[list]) -> dict[str | tuple[str, str], date]:
        if not tags:
            return {}

        tag_len = len(tags[0])
        despatch_map: dict[str | tuple[str, str], date] = {}

        for tag in tags:
            if len(tag) != tag_len:
                key = tag[0]
            elif tag_len >= 7:
                key = (tag[0], tag[1])
            else:
                key = tag[0]

            start_tag = tag[-5]
            if key not in despatch_map or start_tag < despatch_map[key]:
                despatch_map[key] = start_tag

        return despatch_map

    @staticmethod
    async def get_spare_num(
        tags: list[list],
        start_date: date,
        end_date: date,
        product_data: ProductParam,
        distribution,
    ) -> int:
        """根据标签和分布对象计算备件数量，返回向上取整后的结果。"""
        if not tags:
            return 0

        result = 0.0
        despatch_map = SpareService._build_despatch_map(tags)

        for despatch_date in despatch_map.values():
            if (start_date - despatch_date).days < 0 or (end_date - despatch_date).days < 0:
                continue

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
            yvals = distribution.CDF(xvals=xvals, show_plot=False)
            result += yvals[1] - yvals[0]

        return math.ceil(result)

    @staticmethod
    async def get_spare_num_float(
        tags: list[list],
        start_date: date,
        end_date: date,
        product_data: ProductParam,
        distribution,
    ) -> float:
        """根据标签和分布对象计算备件数量，返回浮点结果。"""
        if not tags:
            return 0.0

        result = 0.0
        despatch_map = SpareService._build_despatch_map(tags)

        for despatch_date in despatch_map.values():
            if (start_date - despatch_date).days < 0 or (end_date - despatch_date).days < 0:
                continue

            xvals = [
                (start_date - despatch_date + timedelta(days=90)).days
                * product_data.year_days
                * product_data.avg_worktime
                / 365,
                (end_date - despatch_date + timedelta(days=90)).days
                * product_data.year_days
                * product_data.avg_worktime
                / 365,
            ]
            yvals = distribution.CDF(xvals=xvals, show_plot=False)
            result += yvals[1] - yvals[0]

        return result

    @staticmethod
    async def get_spare_num_float_by_allotment(
        db,
        tags: list[list],
        start_date: date,
        end_date: date,
        input_date: date,
        product_data: ProductParam,
        distribution,
        product_config_code: str | None = None,
    ) -> float:
        """按配属日期过滤后计算备件数量，返回浮点结果。"""
        if not tags:
            return 0.0

        product_numbers = {tag[0] for tag in tags if tag}
        log.info("备件计算过滤统计 - 标签产品编号数量: {}", len(product_numbers))
        if not product_numbers:
            return 0.0

        allotments = await allotment_dao.get_by_product_numbers(db, list(product_numbers))
        valid_product_numbers = {
            allotment.product_number
            for allotment in allotments
            if allotment.allotment_date and allotment.allotment_date <= input_date
        }
        log.info(
            "备件计算过滤统计 - 配属记录总数: {}, 有效配属产品编号: {}",
            len(allotments),
            len(valid_product_numbers),
        )
        if not valid_product_numbers:
            return 0.0

        filtered_tags = [tag for tag in tags if tag and tag[0] in valid_product_numbers]
        despatch_map = SpareService._build_despatch_map(filtered_tags)
        log.info("备件计算过滤统计 - 最终参与CDF计算的产品数量: {}", len(despatch_map))

        result = 0.0
        for despatch_date in despatch_map.values():
            if (start_date - despatch_date).days < 0 or (end_date - despatch_date).days < 0:
                continue

            xvals = [
                (start_date - despatch_date + timedelta(days=90)).days
                * product_data.year_days
                * product_data.avg_worktime
                / 365,
                (end_date - despatch_date + timedelta(days=90)).days
                * product_data.year_days
                * product_data.avg_worktime
                / 365,
            ]
            yvals = distribution.CDF(xvals=xvals, show_plot=False)
            result += yvals[1] - yvals[0]

        return result

    @staticmethod
    async def get_spare_num_by_fit(
        tags: list[list],
        start_date: date,
        end_date: date,
        product_data: ProductParam,
        method: FitMethodType,
    ) -> int:
        """基于标签重新拟合最优分布后计算备件数量。"""
        if not tags:
            return 0

        despatch_map = SpareService._build_despatch_map(tags)
        distribution = await part_fit_service.tag_fit(tags, method)

        result = 0.0
        for despatch_date in despatch_map.values():
            xvals = [
                (start_date - despatch_date + timedelta(days=90)).days
                * product_data.year_days
                * product_data.avg_worktime
                / 365,
                (end_date - despatch_date + timedelta(days=90)).days
                * product_data.year_days
                * product_data.avg_worktime
                / 365,
            ]
            yvals = distribution.best_distribution.CDF(xvals=xvals, show_plot=False)
            result += yvals[1] - yvals[0]

        return math.ceil(result)

    @staticmethod
    async def _get_product_param(
        model: str, product_config_code: str | None = None
    ) -> ProductParam:
        async with async_db_session() as db:
            product = await product_dao.get_by_model(
                db,
                model,
                product_config_code=product_config_code,
            )
        return convert_to_pydantic_model(product, ProductParam)

    @staticmethod
    async def get_product_spare_num(
        model: str,
        product_config_code: str | None = None,
        distribution_type: DistributeType = DistributeType.Weibull_2P,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        input_date: str | date = None,
        start_date: str | date = None,
        end_date: str | date = None,
        source: bool | None = False,
    ) -> int:
        """获取产品级备件预测结果。"""
        distribution = await distribute_service.get_product_distribution(
            model=model,
            product_config_code=product_config_code,
            distribution_type=distribution_type,
            method=method,
            check=check,
        )
        tags = await product_strategy_service.model_tag_process(
            model,
            input_date,
            product_config_code=product_config_code,
        )
        start_date = dateutils.validate_and_parse_date(start_date)
        end_date = dateutils.validate_and_parse_date(end_date)
        product_data = await SpareService._get_product_param(
            model=model,
            product_config_code=product_config_code,
        )
        return await SpareService.get_spare_num(
            tags,
            start_date,
            end_date,
            product_data,
            distribution,
        )

    @staticmethod
    async def get_part_spare_num(
        model: str,
        part: str,
        product_config_code: str | None = None,
        distribution_type: DistributeType = DistributeType.Weibull_2P,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        input_date: str | date = None,
        start_date: str | date = None,
        end_date: str | date = None,
        source: bool | None = False,
    ) -> int:
        """获取零部件级备件预测结果。"""
        distribution = await distribute_service.get_part_distribution(
            model=model,
            part=part,
            product_config_code=product_config_code,
            distribution_type=distribution_type,
            method=method,
            check=check,
            source=source,
        )
        log.info("型号{}的零部件{}分布: {}", model, part, distribution)
        if distribution is None:
            raise errors.DataValidationError(
                msg=(
                    f"型号{model}的零部件{part}未找到匹配的拟合分布，"
                    f"请检查 source={source} 或拟合结果"
                )
            )

        tags = await part_strategy_service.part_tag_process(
            model,
            part,
            input_date,
            product_config_code=product_config_code,
        )
        start_date = dateutils.validate_and_parse_date(start_date)
        end_date = dateutils.validate_and_parse_date(end_date)
        product_data = await SpareService._get_product_param(
            model=model,
            product_config_code=product_config_code,
        )
        return await SpareService.get_spare_num(
            tags,
            start_date,
            end_date,
            product_data,
            distribution,
        )

    @staticmethod
    async def get_all_parts_spare_num_by_model(
        model: str,
        product_config_code: str | None = None,
        distribution_type: DistributeType = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        input_date: str | date = None,
        start_date: str | date = None,
        end_date: str | date = None,
        source: bool | None = False,
    ) -> dict:
        """获取单型号下全部零部件的备件预测结果。"""
        async with async_db_session() as db:
            parts = await fit_part_dao.get_by_model(
                db,
                model,
                product_config_code=product_config_code,
            )
            if not parts:
                raise errors.DataValidationError(
                    msg=f"型号{model}没有零部件拥有拟合分布"
                )

        start_date = dateutils.validate_and_parse_date(start_date)
        end_date = dateutils.validate_and_parse_date(end_date)
        product_data = await SpareService._get_product_param(
            model=model,
            product_config_code=product_config_code,
        )

        results = {
            "model": model,
            "product_config_code": product_config_code,
            "input_date": input_date,
            "start_date": start_date,
            "end_date": end_date,
            "distribution": distribution_type,
            "method": method,
            "check": check,
            "total": len(parts),
            "success": 0,
            "fail": 0,
            "parts": {},
        }
        errors_info = {}

        for part in parts:
            try:
                distribution = await distribute_service.get_part_distribution(
                    model=model,
                    part=part,
                    product_config_code=product_config_code,
                    distribution_type=distribution_type,
                    method=method,
                    check=check,
                    source=source,
                )
                if distribution is None:
                    raise errors.DataValidationError(
                        msg=(
                            f"型号{model}的零部件{part}未找到匹配的拟合分布，"
                            f"请检查 source={source} 或拟合数据"
                        )
                    )

                tags = await part_strategy_service.part_tag_process(
                    model,
                    part,
                    input_date,
                    product_config_code=product_config_code,
                )
                result = await SpareService.get_spare_num(
                    tags,
                    start_date,
                    end_date,
                    product_data,
                    distribution,
                )
                results["success"] += 1
                results["parts"][part] = result
            except Exception as exc:
                results["fail"] += 1
                error_msg = getattr(exc, "msg", None) or str(exc) or repr(exc) or "未知错误"
                errors_info[part] = (
                    f"型号{model}的零部件{part}计算失败，错误信息为 {error_msg}"
                )

        if errors_info:
            results["errors"] = errors_info
        return results


spare_service: SpareService = SpareService()
