#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : product_fit_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/2/28 下午3:42
"""

import math

from datetime import date, datetime

from reliability.Distributions import Exponential_Distribution
from reliability.Fitters import Fit_Everything
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.fit.crud.crud_fit_product import fit_product_dao
from backend.app.fit.schema.fit_param import CreateFitProductInParam, FitCheckType, FitMethodType
from backend.app.fit.service.product_strategy_service import product_strategy_service
from backend.app.fit.utils.convert_model import (
    convert_method_to_str,
    convert_to_product_distribution_params,
    convert_to_product_exponential_distribution_params,
)
from backend.app.fit.utils.data_check_utils import datacheckutils
from backend.app.fit.utils.time_utils import dateutils
from backend.common.exception.errors import DataValidationError, FailureCheckError
from backend.database.db import async_db_session


class ProductFitService:
    @staticmethod
    async def tag_fit(
        tags: list[list],
        method: FitMethodType | str | None = FitMethodType.MLE,
    ) -> Fit_Everything:
        """
        单个产品拟合
        :param tags:
        :param method:
        :return: 拟合优度排序
        """
        # 使用工具函数转换method
        method_str = convert_method_to_str(method)

        # 处理成两列
        failure_time = []
        suspense_time = []
        for item in tags:
            if item[-1] == 'suspense':
                suspense_time.append(item[-2])
            else:
                failure_time.append(item[-2])
        fit = Fit_Everything(
            failures=failure_time,
            right_censored=suspense_time,
            show_PP_plot=False,
            show_histogram_plot=False,
            show_probability_plot=False,
            show_best_distribution_probability_plot=False,
            print_results=False,
            exclude=['Weibull_Mixture', 'Weibull_CR', 'Weibull_DS'],
            method=method_str,
        )

        return fit

    @staticmethod
    async def none_tag_fit(db: AsyncSession, model: str) -> float:
        """
        无标签(无故障)拟合:指定为指数分布
        """
        # 1. 计算故障总数,总运行时间
        failures = await failure_dao.get_by_model(db, model)
        t = await datacheckutils.total_run_time(db, model)
        if t == 0:
            raise DataValidationError(msg=f'型号{model}的累计运行时间为0')
        # 2. 按照故障数量划分计算指数分布
        if len(failures) > 0:
            # 2.1 存在故障，计算指数分布公式:λ = n / T
            lambda_ = len(failures) / t
        else:
            # 2.2 不存在故障，计算指数分布公式:λ = t/-ln(1/e)
            lambda_ = -(math.log(1 / math.e)) / t
        distribution_lambda = Exponential_Distribution(Lambda=lambda_).Lambda
        return distribution_lambda

    @staticmethod
    async def create_old(
        model: str,
        input_date: str | date = None,
        method: FitMethodType = FitMethodType.MLE,
    ) -> None:
        """
        单个产品拟合：
        如果输入日期是当前日期且拟合方法为MLE，检查是否存在最近7天内的记录，如果存在，不再进行拟合
        如果用户独立输入日期或不同拟合方法，进行拟合
        """
        # 处理 input_date 参数
        input_date = dateutils.validate_and_parse_date(input_date)
        is_system_default = input_date == date.today() and method == FitMethodType.MLE

        async with async_db_session() as db:
            if is_system_default:
                # 如果输入日期是今天并且拟合方法为MLE，检查是否存在最近7天内的记录，如果存在，不再进行拟合
                distribution = await fit_product_dao.get_last(db, model, input_date, method)
                if distribution and distribution.created_time:
                    days_difference = (datetime.now().date() - distribution.created_time).days
                    if days_difference < 7:
                        return

                tags = await product_strategy_service.model_tag_process(model, input_date)
                fit = await ProductFitService.tag_fit(tags, method)
                # 1.将fit.result转换为数据模型
                distribution_params = convert_to_product_distribution_params(
                    fit.results, model, input_date, method, not is_system_default
                )
                # 2.将数据模型保存到数据库
                await fit_product_dao.creates(db, distribution_params)
                return

            # 如果用户独立输入日期或不同拟合方法，进行拟合
            tags = await product_strategy_service.model_tag_process(model, input_date)
            fit = await ProductFitService.tag_fit(tags, method)
            # 1.将fit.result转换为数据模型
            distribution_params = convert_to_product_distribution_params(
                fit.results, model, input_date, method, not is_system_default
            )
            # 2.将数据模型保存到数据库
            await fit_product_dao.creates(db, distribution_params)
            return

    @staticmethod
    async def create(*, obj: CreateFitProductInParam) -> None:
        """
        单个产品拟合：
        如果输入日期是当前日期且拟合方法为MLE，检查是否存在最近7天内的记录，如果存在，不再进行拟合
        如果用户独立输入日期或不同拟合方法，进行拟合
        """
        # 处理 input_date 参数
        input_date = dateutils.validate_and_parse_date(obj.input_date)
        is_system_default = input_date == date.today() and obj.method == FitMethodType.MLE

        async with async_db_session() as db:
            if is_system_default and await ProductFitService._recent_fit_exists(db, obj.model, input_date, obj.method):
                return

            await ProductFitService._perform_and_save_fit(obj.model, input_date, obj.method, not is_system_default)

    @staticmethod
    async def _recent_fit_exists(db: AsyncSession, model: str, input_date: date, method: FitMethodType) -> bool:
        distribution = await fit_product_dao.get_last(db, model, input_date, method)
        if distribution and distribution.created_time:
            days_difference = (datetime.now().date() - distribution.created_time).days
            return days_difference < 7
        return False

    @staticmethod
    async def _perform_and_save_fit(model: str, input_date: date, method: FitMethodType, is_user_input: bool) -> None:
        async with async_db_session() as db:
            async with db.begin():
                try:
                    tags = await product_strategy_service.model_tag_process(model, input_date)
                    fit = await ProductFitService.tag_fit(tags, method)
                    distribution_params = convert_to_product_distribution_params(
                        fit.results, model, input_date, method, is_user_input
                    )
                    await fit_product_dao.creates(db, distribution_params)
                except FailureCheckError:
                    lambda_ = await ProductFitService.none_tag_fit(db, model)
                    distribution_param = convert_to_product_exponential_distribution_params(
                        model, input_date, method, is_user_input, lambda_
                    )
                    await fit_product_dao.create_model(db, distribution_param)

    @staticmethod
    async def get_by_model(
        model: str,
        input_date: str | date = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        source: bool = False,
    ):
        """
        根据型号查询拟合信息:查询最新的拟合信息,以一组的形式出现

        :param model: 型号
        :param input_date: 计算截止日
        :param method: 拟合方法
        :param check: 拟合优度检验
        :param source: 0系统默认,1用户自定义
        :return:
        """
        async with async_db_session() as db:
            results = await fit_product_dao.get_by_model(db, model, input_date, method, check, source)
            return results

    @staticmethod
    async def get_best_by_model(
        model: str,
        input_date: str | date = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        source: bool = False,
    ):
        """
        根据型号查询拟合信息:查询最新的拟合信息,查询最优的拟合信息
        :param model:
        :param input_date: 计算截止日
        :param method:
        :param check:
        :param source:
        :return:
        """
        async with async_db_session() as db:
            results = await fit_product_dao.get_by_model(db, model, input_date, method, check, source)
            if not results:
                return None
            return results[0]


product_fit_service: ProductFitService = ProductFitService()
