#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from datetime import date, datetime

from reliability.Distributions import Exponential_Distribution
from reliability.Fitters import Fit_Everything
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.calcu.service.reliability_index_service import reliability_index_service
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.fit.schema.fit_param import CreateFitPartInParam, FitCheckType, FitMethodType
from backend.app.fit.utils.convert_model import (
    convert_method_to_str,
    convert_to_part_distribution_params,
    convert_to_part_exponential_distribution_params,
    convert_to_total_quantity,
    get_ebom_tree_with_parents,
)
from backend.app.fit.utils.data_check_utils import datacheckutils
from backend.app.fit.utils.time_utils import dateutils
from backend.app.fit_aaron.service.part_strategy_service import part_strategy_service
from backend.common.exception import errors
from backend.common.exception.errors import DataValidationError, FailureCheckError
from backend.database.db import async_db_session


class PartFitService:
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
            raise DataValidationError(msg="?????????????")

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
        part: str,
        input_date: date,
        product_config_code: str | None = None,
    ) -> float:
        failures = await failure_dao.get_by_model_and_part(
            db,
            model,
            part,
            input_date,
            product_config_code=product_config_code,
        )

        t = await datacheckutils.total_run_time(
            db,
            model,
            product_config_code=product_config_code,
        )
        if t == 0:
            raise DataValidationError(msg=f"?? {model} ??? {part} ????????0")

        ebom_data = await get_ebom_tree_with_parents(
            db,
            model,
            product_config_code,
            part,
        )
        if not ebom_data:
            raise errors.DataValidationError(
                msg=f"??????????{model}????{part}?BOM?????"
            )

        total_bl_quantity = convert_to_total_quantity(ebom_data, part)
        t = t * total_bl_quantity
        if len(failures) > 0:
            lambda_ = len(failures) / t
        else:
            lambda_ = -(math.log(1 / math.e)) / t
        return Exponential_Distribution(Lambda=lambda_).Lambda

    @staticmethod
    async def create(*, obj: CreateFitPartInParam) -> None:
        input_date = dateutils.validate_and_parse_date(obj.input_date)
        is_system_default = input_date == date.today() and obj.method == FitMethodType.MLE

        async with async_db_session() as db:
            if is_system_default and await PartFitService._recent_fit_exists(
                db,
                obj.model,
                obj.part,
                input_date,
                obj.method,
                product_config_code=obj.product_config_code,
            ):
                return

        await PartFitService._perform_and_save_fit(
            obj.model,
            obj.part,
            input_date,
            obj.method,
            not is_system_default,
            product_config_code=obj.product_config_code,
        )

    @staticmethod
    async def _recent_fit_exists(
        db: AsyncSession,
        model: str,
        part: str,
        input_date: date,
        method: FitMethodType,
        product_config_code: str | None = None,
    ) -> bool:
        distribution = await fit_part_dao.get_last(
            db,
            model,
            part,
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
        part: str,
        input_date: date,
        method: FitMethodType,
        is_user_input: bool,
        product_config_code: str | None = None,
    ) -> None:
        async with async_db_session() as db:
            async with db.begin():
                try:
                    # Aaron?2026-07-31???????Aaron??????tags
                    # ?????Aaron?????main_new.py????data_result1/data_result_replace???????
                    # ???????????? -> data_result -> tags -> Fit_Everything
                    tags = await part_strategy_service.part_tag_process(
                        model,
                        part,
                        input_date,
                        product_config_code=product_config_code,
                    )
                    fit = await PartFitService.tag_fit(tags, method)
                    distribution_params = convert_to_part_distribution_params(
                        fit.results,
                        model,
                        product_config_code,
                        part,
                        input_date,
                        method,
                        is_user_input,
                    )
                    await fit_part_dao.creates(db, distribution_params)
                except FailureCheckError:
                    lambda_ = await PartFitService.none_tag_fit(
                        db,
                        model,
                        part,
                        input_date,
                        product_config_code=product_config_code,
                    )
                    distribution_param = convert_to_part_exponential_distribution_params(
                        model,
                        product_config_code,
                        part,
                        input_date,
                        method,
                        is_user_input,
                        lambda_,
                    )
                    await fit_part_dao.create(db, distribution_param)

    @staticmethod
    async def get_by_model_and_part(
        model: str,
        part: str,
        input_date: str | date = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        source: bool = False,
        product_config_code: str | None = None,
    ):
        async with async_db_session() as db:
            return await fit_part_dao.get_by_model_and_part(
                db,
                model,
                part,
                input_date,
                method,
                check,
                source,
                product_config_code=product_config_code,
            )

    @staticmethod
    async def get_best_by_model_and_part(
        model: str,
        part: str,
        input_date: str | date = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        source: bool = False,
        product_config_code: str | None = None,
    ):
        async with async_db_session() as db:
            results = await fit_part_dao.get_by_model_and_part(
                db,
                model,
                part,
                input_date,
                method,
                check,
                source,
                product_config_code=product_config_code,
            )
            if not results:
                return None
            return results[0]

    @staticmethod
    async def get_equivalent_lamda(
        model: str,
        part: str,
        input_time1: date,
        input_time2: date,
        product_config_code: str | None = None,
    ):
        async with async_db_session() as db:
            t1_list1, t2_list1 = await datacheckutils.total_run_time_by_input_time(
                db,
                model,
                input_time1,
                input_time2,
                product_config_code=product_config_code,
            )
            t1_list2 = [x + 1 for x in t1_list1]
            t2_list2 = [x + 1 for x in t2_list1]
            best_distribution = await reliability_index_service._get_best_distribution(
                model,
                part,
                product_config_code=product_config_code,
            )
            cumulative_sum1 = (
                sum(
                    best_distribution.CDF(t2) - best_distribution.CDF(t1)
                    for t1, t2 in zip(t1_list1, t1_list2)
                )
                / len(t1_list1)
            ) * 1000000
            cumulative_sum2 = (
                sum(
                    best_distribution.CDF(t2) - best_distribution.CDF(t1)
                    for t1, t2 in zip(t2_list1, t2_list2)
                )
                / len(t2_list1)
            ) * 1000000
            rate = round(((cumulative_sum2 - cumulative_sum1) / cumulative_sum1) * 100, 2)
            return round(cumulative_sum1, 4), round(cumulative_sum2, 4), rate


part_fit_service: PartFitService = PartFitService()
