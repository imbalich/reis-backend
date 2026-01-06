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
from datetime import date

from backend.app.calcu.schema.distribute_param import DistributeType
from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.fit.schema.base_param import ProductParam, EbomParam
from backend.app.fit.schema.fit_param import FitMethodType, FitCheckType
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.service.product_strategy_service import product_strategy_service
from backend.app.fit.utils.convert_model import (
    convert_to_pydantic_model,
    convert_to_pydantic_models,
    convert_to_total_quantity,
)
from backend.app.fit.utils.time_utils import dateutils
from backend.common.exception import errors
from backend.common.log import log
from backend.database.db import async_db_session


class SpareService:
    @staticmethod
    async def get_spare_num(
        tags: list[list],
        start_date: date,
        end_date: date,
        product_data: ProductParam,
        distribution,
    ):
        # 备件量计算方法
        result = 0
        if not tags:
            return 0

        # 兼容整机级（product_tag）和零部件级（part_tag）两种标签结构
        # - 整机级: [产品编号, 开始日期, 结束日期, 天数差, 运行时间, 类型]  -> len == 6
        # - 零部件级: [产品编号, 虚拟物料编码, 开始日期, 结束日期, 天数差, 运行时间, 类型] -> len == 7
        tag_len = len(tags[0])

        # 第一步：根据结构构建“发运日期”映射
        # 整机级: key = 产品编号
        # 零部件级: key = (产品编号, 虚拟物料编码)
        despatch_map = {}
        for tag in tags:
            # 防止混合结构，长度不一致时退化为按产品编号
            if len(tag) != tag_len:
                key = tag[0]
            else:
                if tag_len >= 7:
                    # 零部件级：产品编号 + 虚拟键
                    key = (tag[0], tag[1])
                else:
                    # 整机级：只有产品编号
                    key = tag[0]

            start_tag = tag[-5]  # 开始日期（统一使用 tag[-5]）
            if key not in despatch_map or start_tag < despatch_map[key]:
                despatch_map[key] = start_tag

        # 第二步：对每个 key（整机或"产品+虚拟件"组合）计算 CDF 差值并累加
        for key, despatch_date in despatch_map.items():
            # 检查发运日期是否晚于计算日期，如果是则跳过该产品
            if (start_date - despatch_date).days < 0 or (end_date - despatch_date).days < 0:
                # 发运日期晚于计算日期，跳过该产品
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
    async def get_spare_num_by_fit(
        tags: list[list],
        start_date: date,
        end_date: date,
        product_data: ProductParam,
        method: FitMethodType,
    ):
        """
        重新拟合出结果,只能选取最优分布
        """
        # 备件量计算方法
        result = 0
        if not tags:
            return 0

        # 兼容整机级（product_tag）和零部件级（part_tag）两种标签结构
        tag_len = len(tags[0])

        # 第一步：根据结构构建“发运日期”映射
        despatch_map = {}
        for tag in tags:
            if len(tag) != tag_len:
                key = tag[0]
            else:
                if tag_len >= 7:
                    key = (tag[0], tag[1])
                else:
                    key = tag[0]

            start_tag = tag[-5]  # 开始日期
            if key not in despatch_map or start_tag < despatch_map[key]:
                despatch_map[key] = start_tag

        # 第二步：进行拟合
        distribution = await part_fit_service.tag_fit(tags, method)

        # 第三步：对每个 key（整机或“产品+虚拟件”组合）计算 CDF 差值并累加
        for key, despatch_date in despatch_map.items():
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
            yvals = distribution.best_distribution.CDF(xvals=xvals, show_plot=False)
            result += yvals[1] - yvals[0]

        return math.ceil(result)

    @staticmethod
    async def get_product_spare_num(
            model: str,
            distribution_type: DistributeType = DistributeType.Weibull_2P,
            method: FitMethodType = FitMethodType.MLE,
            check: FitCheckType = FitCheckType.BIC,
            input_date: str | date = None,
            start_date: str | date = None,
            end_date: str | date = None,
        source: bool | None = False,
    ):
        """
        获取产品级备件量
        """
        # 1. 确定分布:查库获取分布字段
        distribution = await distribute_service.get_product_distribution(
            model, distribution_type, method, check
        )
        # 2. 计算备件量:两个时间点之间CDF的差值,需要标签，用标签中每一个去算(我滴龟龟，麻了)
        tags = await product_strategy_service.model_tag_process(model, input_date)
        # 3. 日期转换
        start_date = dateutils.validate_and_parse_date(start_date)
        end_date = dateutils.validate_and_parse_date(end_date)
        # 4.产品信息
        async with async_db_session() as db:
            product_data = convert_to_pydantic_model(
                await product_dao.get_by_model(db, model), ProductParam
            )
        # 5.计算数量
        result = await SpareService.get_spare_num(
            tags, start_date, end_date, product_data, distribution
        )
        return result

    @staticmethod
    async def get_part_spare_num(
            model: str,
            part: str,
            distribution_type: DistributeType = DistributeType.Weibull_2P,
            method: FitMethodType = FitMethodType.MLE,
            check: FitCheckType = FitCheckType.BIC,
            input_date: str | date = None,
            start_date: str | date = None,
            end_date: str | date = None,
        source: bool | None = False,
    ):
        """
        获取零部件级备件量
        :param model:
        :param part:
        :param distribution_type:
        :param method:
        :param check:
        :param input_date:
        :param start_date:
        :param end_date:
        :return:
        """
        # 1. 确定分布:查库获取分布字段
        distribution = await distribute_service.get_part_distribution(
            model, part, distribution_type, method, check, source
        )
        log.info(f"型号{model}的零部件{part}的分布: {distribution}")
        if distribution is None:
            raise errors.DataValidationError(
                msg=f"型号{model}的零部件{part}未找到匹配的拟合分布，请检查source={source}或拟合结果"
            )
        # 1. 计算备件量:两个时间点之间CDF的差值,需要标签，用标签中每一个去算(我滴龟龟，麻了)
        tags = await part_strategy_service.part_tag_process(model, part, input_date)
        # # 2. 根据标签拟合分布自动选取最优分布
        # distribution = await part_fit_service.tag_fit(tags, method)
        # 3. 日期转换
        start_date = dateutils.validate_and_parse_date(start_date)
        end_date = dateutils.validate_and_parse_date(end_date)
        # 4.产品信息
        async with async_db_session() as db:
            product_data = convert_to_pydantic_model(
                await product_dao.get_by_model(db, model), ProductParam
            )
        # 5.计算数量
        result = await SpareService.get_spare_num(
            tags, start_date, end_date, product_data, distribution
        )
        return result

    @staticmethod
    async def get_all_parts_spare_num_by_model(
            model: str,
            distribution_type: DistributeType = None,
            method: FitMethodType = FitMethodType.MLE,
            check: FitCheckType = FitCheckType.BIC,
            input_date: str | date = None,
            start_date: str | date = None,
            end_date: str | date = None,
        source: bool | None = False,
    ):
        # 1. 确定哪些零部件有分布
        async with async_db_session() as db:
            parts = await fit_part_dao.get_by_model(db, model)
            if not parts:
                raise errors.DataValidationError(
                    msg=f"型号{model}没有零部件拥有拟合分布"
                )

        # 2. 处理参数
        start_date = dateutils.validate_and_parse_date(start_date)
        end_date = dateutils.validate_and_parse_date(end_date)

        async with async_db_session() as db:
            product_data = convert_to_pydantic_model(
                await product_dao.get_by_model(db, model), ProductParam
            )

        # 3. 获取每个零部件的备件量
        results = {
            "model": model,
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
                    model, part, distribution_type, method, check, source
                )
                if distribution is None:
                    raise errors.DataValidationError(
                        msg=f"型号{model}的零部件{part}未找到匹配的拟合分布，请检查source={source}或拟合数据"
                    )
                tags = await part_strategy_service.part_tag_process(
                    model, part, input_date
                )
                # 使用固定分布计算，确保与单零部件预测一致
                result = await SpareService.get_spare_num(
                    tags, start_date, end_date, product_data, distribution
                )
                # 需要再乘以bom数量 —— 为保持与单零部件接口一致，先保留原逻辑但注释掉
                # async with async_db_session() as db:
                #     ebom_data = await ebom_dao.get_by_model_and_part(db, model, part)
                #     if not ebom_data:
                #         raise errors.DataValidationError(
                #             msg=f"型号{model}的零部件{part}的BOM信息不存在"
                #         )
                #     ebom_data = convert_to_pydantic_models(ebom_data, EbomParam)
                #     total_bl_quantity = convert_to_total_quantity(ebom_data)
                results["success"] += 1
                results["parts"][part] = result
            except Exception as e:
                results["fail"] += 1
                # 优先使用自定义异常的msg属性，否则使用str(e)或repr(e)
                error_msg = getattr(e, "msg", None) or str(e) or repr(e) or "未知错误"
                errors_info[part] = (
                    f"型号{model}没有零部件{part}计算失败，错误信息为{error_msg}"
                )
        if errors_info:
            results["errors"] = errors_info
        return results


spare_service: SpareService = SpareService()
