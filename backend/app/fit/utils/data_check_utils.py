#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : data_check_utils.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/2/25 下午3:06
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.utils.time_utils import dateutils
from backend.database.db import async_db_session


class DataCheckUtils:
    @staticmethod
    async def check_model_in_product(
        model: str,
        product_config_code: str | None = None,
    ) -> bool:
        """
        检查型号是否在 Product 表中。
        """
        async with async_db_session() as db:
            if product_config_code is None:
                products = await product_dao.get_models_by_product(db)
                if products and model in products:
                    return True
                return False

            product = await product_dao.get_by_model(
                db,
                model,
                product_config_code=product_config_code,
            )
            return product is not None

    @staticmethod
    async def check_model_in_failure(
        model: str,
        product_config_code: str | None = None,
    ) -> bool:
        """
        检查型号是否在 Failure 表中，且故障数量大于 4。
        """
        async with async_db_session() as db:
            failures = await failure_dao.get_by_model(
                db,
                model,
                product_config_code=product_config_code,
            )
            return bool(failures and len(failures) > 4)

    @staticmethod
    async def check_model_and_part_in_failure(
        model: str,
        part: str,
        product_config_code: str | None = None,
    ) -> bool:
        """
        检查型号+零部件是否在 Failure 表中，且故障数量大于 4。
        """
        async with async_db_session() as db:
            failures = await failure_dao.get_by_model_and_part(
                db,
                model,
                part,
                product_config_code=product_config_code,
            )
            return bool(failures and len(failures) > 4)

    @staticmethod
    async def check_model_in_despatch(
        model: str,
        product_config_code: str | None = None,
    ) -> bool:
        """
        检查型号是否在 Despatch 表中，累计运行时间至少 10w 小时。
        """
        async with async_db_session() as db:
            total_hours = await DataCheckUtils.total_run_time(
                db,
                model,
                product_config_code=product_config_code,
            )
            return total_hours >= 100000

    @staticmethod
    async def total_run_time(
        db: AsyncSession,
        model: str,
        input_date: date = None,
        product_config_code: str | None = None,
    ) -> float:
        despatchs = await despatch_dao.get_despatchs_by_model(
            db,
            model,
            product_config_code=product_config_code,
        )
        product = await product_dao.get_by_model(
            db,
            model,
            product_config_code=product_config_code,
        )
        if despatchs and product:
            now = input_date or date.today()
            total_hours = 0.0
            for despatch in despatchs:
                dispatch_date = despatch.life_cycle_time
                if isinstance(dispatch_date, str):
                    dispatch_date = dateutils.validate_and_parse_date(dispatch_date)
                date_diff = (now - dispatch_date).days
                hours = dateutils.run_time(
                    date_diff,
                    product.year_days,
                    product.avg_worktime,
                )
                total_hours += hours
            return total_hours
        return 0

    @staticmethod
    async def check_model_and_part_in_ebom(
        model: str,
        part: str,
        product_config_code: str | None = None,
    ) -> bool:
        """
        检查型号+零部件是否在零部件信息表中。
        """
        async with async_db_session() as db:
            bom_data = await ebom_dao.get_by_model_and_part(
                db,
                model,
                part,
                product_config_code=product_config_code,
            )
            return bool(bom_data)

    @staticmethod
    async def total_run_time_by_input_time(
        db: AsyncSession,
        model: str,
        input_time1: date,
        input_time2: date,
        product_config_code: str | None = None,
    ) -> list[float]:
        despatchs = await despatch_dao.get_despatchs_by_model(
            db,
            model,
            product_config_code=product_config_code,
        )
        product = await product_dao.get_by_model(
            db,
            model,
            product_config_code=product_config_code,
        )
        input_time1 = dateutils.validate_and_parse_date(input_time1)
        input_time2 = dateutils.validate_and_parse_date(input_time2)
        hours1 = []
        hours2 = []
        for despatch in despatchs:
            dispatch_date = despatch.life_cycle_time
            if isinstance(dispatch_date, str):
                dispatch_date = dateutils.validate_and_parse_date(dispatch_date)
            date_diff1 = (input_time1 - dispatch_date).days - 90
            date_diff2 = (input_time2 - dispatch_date).days - 90
            hour1 = dateutils.run_time_no_diff_is_fu(
                date_diff1,
                product.year_days,
                product.avg_worktime,
            )
            hour2 = dateutils.run_time_no_diff_is_fu(
                date_diff2,
                product.year_days,
                product.avg_worktime,
            )
            if hour1 != 0:
                hours1.append(hour1)
            if hour2 != 0:
                hours2.append(hour2)
        return hours1, hours2


datacheckutils: DataCheckUtils = DataCheckUtils()
