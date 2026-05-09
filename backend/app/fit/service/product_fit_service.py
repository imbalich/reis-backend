#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : product_fit_service.py
"""

import math
from datetime import date, datetime

from reliability.Distributions import Exponential_Distribution
from reliability.Fitters import Fit_Everything
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.fit.crud.crud_fit_product import fit_product_dao
from backend.app.fit.schema.fit_param import (
    CreateFitProductInParam,
    FitCheckType,
    FitMethodType,
)
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
        method_str = convert_method_to_str(method)

        failure_time = []
        suspense_time = []
        for item in tags:
            if item[-1] == "suspense":
                suspense_time.append(item[-2])
            else:
                failure_time.append(item[-2])

        if not failure_time and not suspense_time:
            raise DataValidationError(msg="打标结果为空，无法执行拟合")

        return Fit_Everything(
            failures=failure_time,
            right_censored=suspense_time,
            show_PP_plot=False,
            show_histogram_plot=False,
            show_probability_plot=False,
            show_best_distribution_probability_plot=False,
            print_results=False,
            exclude=["Weibull_Mixture", "Weibull_CR", "Weibull_DS"],
            method=method_str,
        )

    @staticmethod
    async def none_tag_fit(
        db: AsyncSession,
        model: str,
        product_config_code: str | None = None,
    ) -> float:
        failures = await failure_dao.get_by_model(
            db,
            model,
            product_config_code=product_config_code,
        )
        t = await datacheckutils.total_run_time(
            db,
            model,
            product_config_code=product_config_code,
        )
        if t == 0:
            raise DataValidationError(msg=f"型号{model}的累计运行时间为0")

        if len(failures) > 0:
            lambda_ = len(failures) / t
        else:
            lambda_ = -(math.log(1 / math.e)) / t
        return Exponential_Distribution(Lambda=lambda_).Lambda

    @staticmethod
    async def create_old(
        model: str,
        input_date: str | date = None,
        method: FitMethodType = FitMethodType.MLE,
        product_config_code: str | None = None,
    ) -> None:
        await ProductFitService.create(
            obj=CreateFitProductInParam(
                model=model,
                product_config_code=product_config_code,
                input_date=input_date,
                method=method,
            )
        )

    @staticmethod
    async def create(*, obj: CreateFitProductInParam) -> None:
        input_date = dateutils.validate_and_parse_date(obj.input_date)
        is_system_default = input_date == date.today() and obj.method == FitMethodType.MLE

        async with async_db_session() as db:
            if is_system_default and await ProductFitService._recent_fit_exists(
                db,
                obj.model,
                input_date,
                obj.method,
                product_config_code=obj.product_config_code,
            ):
                return

        await ProductFitService._perform_and_save_fit(
            obj.model,
            input_date,
            obj.method,
            not is_system_default,
            product_config_code=obj.product_config_code,
        )

    @staticmethod
    async def _recent_fit_exists(
        db: AsyncSession,
        model: str,
        input_date: date,
        method: FitMethodType,
        product_config_code: str | None = None,
    ) -> bool:
        distribution = await fit_product_dao.get_last(
            db,
            model,
            input_date,
            method,
            product_config_code=product_config_code,
        )
        if distribution and distribution.created_time:
            days_difference = (datetime.now().date() - distribution.created_time).days
            return days_difference < 7
        return False

    @staticmethod
    async def _perform_and_save_fit(
        model: str,
        input_date: date,
        method: FitMethodType,
        is_user_input: bool,
        product_config_code: str | None = None,
    ) -> None:
        async with async_db_session() as db:
            async with db.begin():
                try:
                    tags = await product_strategy_service.model_tag_process(
                        model,
                        input_date,
                        product_config_code=product_config_code,
                    )
                    fit = await ProductFitService.tag_fit(tags, method)
                    distribution_params = convert_to_product_distribution_params(
                        fit.results,
                        model,
                        product_config_code,
                        input_date,
                        method,
                        is_user_input,
                    )
                    await fit_product_dao.creates(db, distribution_params)
                except FailureCheckError:
                    lambda_ = await ProductFitService.none_tag_fit(
                        db,
                        model,
                        product_config_code=product_config_code,
                    )
                    distribution_param = convert_to_product_exponential_distribution_params(
                        model,
                        product_config_code,
                        input_date,
                        method,
                        is_user_input,
                        lambda_,
                    )
                    await fit_product_dao.create_model(db, distribution_param)

    @staticmethod
    async def get_by_model(
        model: str,
        input_date: str | date = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        source: bool = False,
        product_config_code: str | None = None,
    ):
        async with async_db_session() as db:
            return await fit_product_dao.get_by_model(
                db,
                model,
                input_date,
                method,
                check,
                source,
                product_config_code=product_config_code,
            )

    @staticmethod
    async def get_best_by_model(
        model: str,
        input_date: str | date = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        source: bool = False,
        product_config_code: str | None = None,
    ):
        async with async_db_session() as db:
            results = await fit_product_dao.get_by_model(
                db,
                model,
                input_date,
                method,
                check,
                source,
                product_config_code=product_config_code,
            )
            if not results:
                return None
            return results[0]


product_fit_service: ProductFitService = ProductFitService()
