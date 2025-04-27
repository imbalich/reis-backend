#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : distribute_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/28 10:54
"""

from typing import Callable, Optional

from backend.app.calcu.conf import predict_settings
from backend.app.calcu.schema.distribute_param import DistributeType, DistributionParams
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.fit.crud.crud_fit_product import fit_product_dao
from backend.app.fit.model import FitProduct
from backend.app.fit.model.fit_part import FitPart
from backend.app.fit.schema.fit_param import FitCheckType, FitMethodType
from backend.app.fit.utils.convert_model import (
    convert_to_pydantic_model,
)
from backend.database.db import async_db_session


class DistributeService:
    @staticmethod
    async def get_product_distribution_params(
        model: str,
        distribution: Optional[str] = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
    ) -> FitProduct | None:
        """
        根据名称和参数自动获取分布
        根据有无 distribution 区分指定或直接获取默认的最优

        :param model: 产品型号
        :param distribution: 指定分布
        :param method: 拟合方法
        :param check: 拟合优度
        :return:
        """
        async with async_db_session() as db:
            if distribution:
                result = await fit_product_dao.get_by_model_and_distribution(
                    db, model, distribution, method=method, check=check
                )
                distribution_params = result if result else None
            else:
                results = await fit_product_dao.get_by_model(db, model, method=method, check=check)
                distribution_params = results[0] if results else None

            return distribution_params

    @staticmethod
    async def get_part_distribution_params(
        model: str,
        part: str,
        distribution: Optional[str] = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
    ) -> FitPart | None:
        """
        根据名称和参数自动获取分布
        根据有无 distribution 区分指定或直接获取默认的最优

        :param model: 产品型号
        :param part: 零部件
        :param distribution: 指定分布
        :param method: 拟合方法
        :param check: 拟合优度
        :return:
        """
        async with async_db_session() as db:
            if distribution:
                result = await fit_part_dao.get_by_model_and_part_and_distribution(
                    db, model, part, distribution, method=method, check=check
                )
                distribution_params = result if result else None
            else:
                results = await fit_part_dao.get_by_model_and_part(db, model, part, method=method, check=check)
                distribution_params = results[0] if results else None
            return distribution_params

    @staticmethod
    async def get_distribution_function(distribute_type: DistributeType) -> Callable:
        # 获取分布方法
        return predict_settings.DISTRIBUTION_FUNCTIONS[distribute_type]

    @staticmethod
    async def get_distribution_by_params(params: DistributionParams):
        distribute_type = DistributeType(params.distribution)
        distribution_class = predict_settings.DISTRIBUTION_FUNCTIONS.get(distribute_type)
        if not distribution_class:
            return None

        param_mapping = predict_settings.PARAM_MAPPING.get(distribute_type, {})
        distribution_params = {}

        for dist_param, db_param in param_mapping.items():
            value = getattr(params, db_param, None)
            if value is not None:
                distribution_params[dist_param] = value
        # 创建分布实例对象
        if distribution_params:
            distribution = distribution_class(**distribution_params)
            return distribution
        return None

    @staticmethod
    async def get_product_distribution(
        model: str,
        distribution_type: DistributeType = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
    ):
        """
        产品级别分布对象:单个计算的时候允许选择分布
        """
        distribution_params = await DistributeService.get_product_distribution_params(
            model, distribution_type, method, check
        )
        if distribution_params:
            # 转换pydantic模型
            distribution_params = convert_to_pydantic_model(distribution_params, DistributionParams)
            # 获取分布对象
            return await DistributeService.get_distribution_by_params(distribution_params)
        return None

    @staticmethod
    async def get_part_distribution(
        model: str,
        part: str,
        distribution_type: DistributeType = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
    ):
        """
        零部件级别分布对象:单个计算的时候允许选择分布
        """
        distribution_params = await DistributeService.get_part_distribution_params(
            model, part, distribution_type, method, check
        )
        if distribution_params:
            # 转换pydantic模型
            distribution_params = convert_to_pydantic_model(distribution_params, DistributionParams)
            # 获取分布对象
            return await DistributeService.get_distribution_by_params(distribution_params)
        return None

    @staticmethod
    async def get_distribution(
        model: str,
        part: str | None = None,
        distribution_type: DistributeType = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
    ):
        """
        通过指定分布类型获取产品/零部件的分布对象obj
        """
        if not distribution_type:
            return None
        if part:
            return await DistributeService.get_part_distribution(model, part, distribution_type, method, check)
        return await DistributeService.get_product_distribution(model, distribution_type, method, check)


distribute_service: DistributeService = DistributeService()
