#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : reliability_index_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/4/22 17:24
"""

from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


class ReliabilityIndexService:
    @staticmethod
    async def _get_best_distribution(
        model: str,
        part: str | None = None,
        product_config_code: str | None = None,
    ):
        if not part:
            best_distribution = await distribute_service.get_product_distribution(
                model, product_config_code=product_config_code
            )
        else:
            best_distribution = await distribute_service.get_part_distribution(
                model, part, product_config_code=product_config_code
            )

        if not best_distribution:
            return None
        return best_distribution

    @staticmethod
    async def _get_product_params(
        model: str,
        product_config_code: str | None = None,
    ):
        async with async_db_session() as db:
            product = await product_dao.get_by_model(
                db, model, product_config_code=product_config_code
            )
            return product

    @staticmethod
    async def _get_t(
        model: str,
        part: str | None = None,
        t: float | None = None,
        product_config_code: str | None = None,
    ):
        product = await ReliabilityIndexService._get_product_params(
            model, product_config_code=product_config_code
        )
        if not product:
            raise errors.DataValidationError(msg=f"型号{model}产品信息不存在")

        default_max_time = product.avg_worktime * product.year_days * 30

        if not part:
            return min(t, default_max_time) if t else default_max_time

        async with async_db_session() as db:
            replace_items = await replace_dao.get_by_model_and_part(db, model, part)

            if not replace_items:
                return min(t, default_max_time) if t else default_max_time

            replace_data = await replace_dao.get_first_by_model_with_min_repair_level(
                db, model, part
            )
            if not replace_data:
                raise errors.DataValidationError(
                    msg=f"型号{model}零部件{part}的必换件信息不存在"
                )

            replace_max_time = (
                replace_data.replace_cycle * product.year_days * product.avg_worktime
            )

            return min(t, replace_max_time) if t else replace_max_time

    @staticmethod
    async def get_fpmh(
        model: str,
        part: str | None = None,
        t: float | None = None,
        distribution=None,
        product_config_code: str | None = None,
    ) -> float:
        best_distribution = distribution
        if not distribution:
            best_distribution = await ReliabilityIndexService._get_best_distribution(
                model, part, product_config_code=product_config_code
            )
        if not best_distribution:
            raise errors.DataValidationError(
                msg=f"型号{model} 零部件{part} 的分布信息不存在"
            )
        time = await ReliabilityIndexService._get_t(
            model, part, t, product_config_code=product_config_code
        )
        fpmh = best_distribution.PDF(time) * 1000000
        return fpmh

    @staticmethod
    async def get_fpmk(
        model: str,
        part: str | None = None,
        t: float | None = None,
        product_config_code: str | None = None,
    ) -> float:
        product = await ReliabilityIndexService._get_product_params(
            model, product_config_code=product_config_code
        )
        v = product.avg_speed
        fpmk = await ReliabilityIndexService.get_fpmh(
            model, part, t, product_config_code=product_config_code
        ) / v
        return fpmk

    @staticmethod
    async def get_mtbf(
        model: str,
        part: str | None = None,
        t: float | None = None,
        product_config_code: str | None = None,
    ) -> float:
        mtbf = 1000000 / await ReliabilityIndexService.get_fpmh(
            model, part, t, product_config_code=product_config_code
        )
        return mtbf

    @staticmethod
    async def get_r(
        model: str,
        part: str | None = None,
        t: float | None = None,
        distribution=None,
        product_config_code: str | None = None,
    ) -> float:
        best_distribution = distribution
        if not distribution:
            best_distribution = await ReliabilityIndexService._get_best_distribution(
                model, part, product_config_code=product_config_code
            )
        if not t:
            t = await ReliabilityIndexService._get_t(
                model, part, product_config_code=product_config_code
            )
        r = best_distribution.SF(t)
        return r

    @staticmethod
    async def get_inverse_r(
        model: str,
        part: str | None = None,
        r: float = 0.9,
        distribution=None,
        product_config_code: str | None = None,
    ) -> float:
        if r < 0 or r > 1:
            raise errors.DataValidationError(msg="可用度R值必须在0和1之间")
        best_distribution = distribution
        if not distribution:
            best_distribution = await ReliabilityIndexService._get_best_distribution(
                model, part, product_config_code=product_config_code
            )
        inverse_r = best_distribution.inverse_SF(r)
        return inverse_r

    @staticmethod
    async def get_mean_residual_life(
        model: str,
        part: str | None = None,
        t: float | None = None,
        distribution=None,
        product_config_code: str | None = None,
    ) -> float:
        best_distribution = distribution
        if not distribution:
            best_distribution = await ReliabilityIndexService._get_best_distribution(
                model, part, product_config_code=product_config_code
            )
        if not t:
            t = await ReliabilityIndexService._get_t(
                model, part, product_config_code=product_config_code
            )
        mean_residual_life = best_distribution.mean_residual_life(t)
        return mean_residual_life

    @staticmethod
    async def get_mttr():
        pass

    @staticmethod
    async def get_ai():
        pass

    @staticmethod
    async def get_all_index(
        model: str,
        part: str | None = None,
        t: float | None = None,
        distribution=None,
        product_config_code: str | None = None,
    ):
        fpmh = await ReliabilityIndexService.get_fpmh(
            model, part, t, distribution, product_config_code=product_config_code
        )
        fpmk = await ReliabilityIndexService.get_fpmk(
            model, part, t, product_config_code=product_config_code
        )
        mtbf = await ReliabilityIndexService.get_mtbf(
            model, part, t, product_config_code=product_config_code
        )
        r = await ReliabilityIndexService.get_r(
            model, part, t, distribution, product_config_code=product_config_code
        )
        inverse_r = await ReliabilityIndexService.get_inverse_r(
            model, part, r, distribution, product_config_code=product_config_code
        )
        mean_residual_life = await ReliabilityIndexService.get_mean_residual_life(
            model, part, t, distribution, product_config_code=product_config_code
        )
        return fpmh, fpmk, mtbf, r, inverse_r, mean_residual_life


reliability_index_service: ReliabilityIndexService = ReliabilityIndexService()
