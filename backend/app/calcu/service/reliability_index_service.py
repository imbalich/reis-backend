#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : reis-backend
@File    : reliability_index_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/4/22 17:24
'''
from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


class ReliabilityIndexService:
    @staticmethod
    async def _get_best_distribution(model: str, part: str | None = None):
        # 获取分布
        if not part:
            best_distribution = await distribute_service.get_product_distribution(model)
        else:
            best_distribution = await distribute_service.get_part_distribution(model, part)

        if not best_distribution:
            return None
        return best_distribution

    @staticmethod
    async def _get_product_params(model: str):
        # 获取产品参数
        async with async_db_session() as db:
            product = await product_dao.get_by_model(db, model)
            return product

    @staticmethod
    async def _get_t(model: str, part: str | None = None, t: float | None = None):
        """
        计算时间参数t，根据不同情况有不同的计算逻辑

        计算规则：
        1. 如果未指定零部件(产品级)，或零部件不是必换件：
           - 使用 min(t, product.avg_worktime * product.year_days * 30)
        2. 如果指定了零部件且是必换件：
           - 使用 min(t, replace_data.replace_cycle * product.year_days * product.avg_worktime)

        :param model: 产品型号
        :param part: 零部件编码，可选
        :param t: 用户指定的时间值，可选
        :return: 计算得到的时间值
        :raises: DataValidationError 当产品信息不存在或必换件信息不存在时
        """
        # 获取产品参数
        product = await ReliabilityIndexService._get_product_params(model)
        if not product:
            raise errors.DataValidationError(msg=f'型号{model}产品信息不存在')

        # 计算默认最大时间（30年的工作时间）
        default_max_time = product.avg_worktime * product.year_days * 30

        # 如果未指定零部件，直接返回计算结果
        if not part:
            return min(t, default_max_time) if t else default_max_time

        # 如果指定了零部件，检查是否是必换件
        async with async_db_session() as db:
            replace_items = await replace_dao.get_by_model_and_part(db, model, part)

            # 如果不是必换件，使用默认时间计算
            if not replace_items:
                return min(t, default_max_time) if t else default_max_time

            # 如果是必换件，获取修造级别最小的必换件数据
            replace_data = await replace_dao.get_first_by_model_with_min_repair_level(db, model, part)
            if not replace_data:
                raise errors.DataValidationError(msg=f'型号{model}零部件{part}的必换件信息不存在')

            # 计算基于必换周期的最大时间
            replace_max_time = replace_data.replace_cycle * product.year_days * product.avg_worktime

            # 返回计算结果
            return min(t, replace_max_time) if t else replace_max_time

    @staticmethod
    async def get_fpmh(model: str, part: str | None = None, t: float | None = None, distribution=None) -> float:
        # 计算FPMH值:pdf函数中t位置的y值
        best_distribution = distribution
        if not distribution:
            best_distribution = await ReliabilityIndexService._get_best_distribution(model, part)
        if not best_distribution:
            raise errors.DataValidationError(msg=f'型号{model} 零部件{part} 的分布信息不存在')
        time = await ReliabilityIndexService._get_t(model, part, t)
        fpmh = best_distribution.PDF(time) * 1000000
        return fpmh

    @staticmethod
    async def get_fpmk(model: str, part: str | None = None, t: float | None = None) -> float:
        # 获取FPMK值:fpmh/v
        product = await ReliabilityIndexService._get_product_params(model)
        v = product.avg_speed
        fpmk = await ReliabilityIndexService.get_fpmh(model, part, t) / v
        return fpmk

    @staticmethod
    async def get_mtbf(model: str, part: str | None = None, t: float | None = None) -> float:
        # 获取MTBF值:1000000/FPMH
        mtbf = 1000000 / await ReliabilityIndexService.get_fpmh(model, part, t)
        return mtbf

    @staticmethod
    async def get_r(model: str, part: str | None = None, t: float | None = None, distribution=None) -> float:
        # 获取R值,t时间下的可靠度
        best_distribution = distribution
        if not distribution:
            best_distribution = await ReliabilityIndexService._get_best_distribution(model, part)
        if not t:
            t = await ReliabilityIndexService._get_t(model, part)
        r = best_distribution.SF(t)
        return r

    @staticmethod
    async def get_inverse_r(model: str, part: str | None = None, r: float = 0.9, distribution=None) -> float:
        # 计算R的逆函数,R值下的使用时间
        if r < 0 or r > 1:
            raise errors.DataValidationError(msg='可用度R值必须在0和1之间')
        best_distribution = distribution
        if not distribution:
            best_distribution = await ReliabilityIndexService._get_best_distribution(model, part)
        inverse_r = best_distribution.inverse_SF(r)
        return inverse_r

    @staticmethod
    async def get_mean_residual_life(model: str, part: str | None = None, t: float | None = None, distribution=None) -> float:
        # 获取平均剩余寿命值
        best_distribution = distribution
        if not distribution:
            best_distribution = await ReliabilityIndexService._get_best_distribution(model, part)
        if not t:
            t = await ReliabilityIndexService._get_t(model, part)
        mean_residual_life = best_distribution.mean_residual_life(t)
        return mean_residual_life

    @staticmethod
    async def get_mttr():
        # 平均修复时间MTTR:从何工那里要一张表
        pass

    @staticmethod
    async def get_ai():
        # 固有可用度AI:MTBF/(MTBF+MTTR)
        pass

    @staticmethod
    async def get_all_index(model: str, part: str | None = None, t: float | None = None, distribution=None):
        # 获取所有指标值
        fpmh = await ReliabilityIndexService.get_fpmh(model, part, t, distribution)
        fpmk = await ReliabilityIndexService.get_fpmk(model, part, t)
        mtbf = await ReliabilityIndexService.get_mtbf(model, part, t)
        r = await ReliabilityIndexService.get_r(model, part, t, distribution)
        inverse_r = await ReliabilityIndexService.get_inverse_r(model, part, r, distribution)
        mean_residual_life = await ReliabilityIndexService.get_mean_residual_life(model, part, t, distribution)
        return fpmh, fpmk, mtbf, r, inverse_r, mean_residual_life


reliability_index_service: ReliabilityIndexService = ReliabilityIndexService()
