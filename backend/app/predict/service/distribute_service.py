#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : distribute_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/28 10:54
'''
import math
from datetime import date
from typing import Optional, Callable, Union

from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.fit.crud.crud_fit_product import fit_product_dao
from backend.app.fit.model import FitProduct
from backend.app.fit.model.fit_part import FitPart
from backend.app.fit.schema.base_param import ProductParam, EbomParam
from backend.app.fit.schema.fit_param import FitMethodType, FitCheckType
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.service.product_strategy_service import product_strategy_service
from backend.app.fit.utils.convert_model import convert_to_pydantic_model, convert_to_pydantic_models, \
    convert_to_total_quantity
from backend.app.fit.utils.time_utils import dateutils
from backend.app.predict.conf import predict_settings
from backend.app.predict.schema.distribute_param import DistributeType, DistributionParams
from backend.common.exception import errors
from backend.database.db import async_db_session


class DistributeService:

    @staticmethod
    async def get_product_distribution_params(
            model: str,
            distribution: Optional[str] = None,
            method: FitMethodType = FitMethodType.MLE,
            check: FitCheckType = FitCheckType.BIC
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
            check: FitCheckType = FitCheckType.BIC
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
    async def get_distribution(params: DistributionParams):

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
            distribution_type: DistributeType = DistributeType.Weibull_2P,
            method: FitMethodType = FitMethodType.MLE,
            check: FitCheckType = FitCheckType.BIC,
    ):

        """
        产品级别分布对象:单个计算的时候允许选择分布
        """
        distribution_params = await DistributeService.get_product_distribution_params(
            model, distribution_type, method, check)
        if distribution_params:
            # 转换pydantic模型
            distribution_params = convert_to_pydantic_model(distribution_params, DistributionParams)
            # 获取分布对象
            return await DistributeService.get_distribution(distribution_params)
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
            model, part, distribution_type, method, check)
        if distribution_params:
            # 转换pydantic模型
            distribution_params = convert_to_pydantic_model(distribution_params, DistributionParams)
            # 获取分布对象
            return await DistributeService.get_distribution(distribution_params)
        return None

    @staticmethod
    async def get_spare_num(
            tags: list[list],
            start_date: date,
            end_date: date,
            product_data: ProductParam,
            distribution
    ):
        # 备件量计算方法
        result = 0
        product_list = {}
        for tag in tags:
            # 遍历标签，给每个产品编号找到发运日期
            if tag[0] not in product_list:
                product_list[tag[0]] = {
                    "despetch": tag[-5]
                }
            else:
                if tag[-5] < product_list[tag[0]]["despetch"]:
                    product_list[tag[0]]["despetch"] = tag[-5]
        for key, product in product_list.items():
            product["xvals"] = [
                (start_date - product["despetch"]).days * product_data.year_days * product_data.avg_worktime / 365,
                (end_date - product["despetch"]).days * product_data.year_days * product_data.avg_worktime / 365
            ]
            product["yvals"] = distribution.CDF(xvals=product["xvals"], show_plot=False)
            product["predict"] = product["yvals"][1] - product["yvals"][0]
            result += product["predict"]
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
        product_list = {}
        for tag in tags:
            # 遍历标签，给每个产品编号找到发运日期
            if tag[0] not in product_list:
                product_list[tag[0]] = {
                    "despetch": tag[-5]
                }
            else:
                if tag[-5] < product_list[tag[0]]["despetch"]:
                    product_list[tag[0]]["despetch"] = tag[-5]
        distribution = await part_fit_service.tag_fit(tags, method)
        for key, product in product_list.items():
            product["xvals"] = [
                (start_date - product["despetch"]).days * product_data.year_days * product_data.avg_worktime / 365,
                (end_date - product["despetch"]).days * product_data.year_days * product_data.avg_worktime / 365
            ]
            product["yvals"] = distribution.best_distribution.CDF(xvals=product["xvals"], show_plot=False)
            product["predict"] = product["yvals"][1] - product["yvals"][0]
            result += product["predict"]
        return math.ceil(result)

    @staticmethod
    async def get_product_spare_num(
            model: str,
            distribution_type: DistributeType = DistributeType.Weibull_2P,
            method: FitMethodType = FitMethodType.MLE,
            check: FitCheckType = FitCheckType.BIC,
            input_date: Union[str, date] = None,
            start_date: Union[str, date] = None,
            end_date: Union[str, date] = None
    ):
        """
        获取产品级备件量
        """
        # 1. 确定分布:查库获取分布字段
        distribution = await DistributeService.get_product_distribution(model, distribution_type, method, check)
        # 2. 计算备件量:两个时间点之间CDF的差值,需要标签，用标签中每一个去算(我滴龟龟，麻了)
        tags = await product_strategy_service.model_tag_process(model, input_date)
        # 3. 日期转换
        start_date = dateutils.validate_and_parse_date(start_date)
        end_date = dateutils.validate_and_parse_date(end_date)
        # 4.产品信息
        async with async_db_session() as db:
            product_data = convert_to_pydantic_model(await product_dao.get_by_model(db, model), ProductParam)
        # 5.计算数量
        result = await DistributeService.get_spare_num(tags, start_date, end_date, product_data, distribution)
        return result

    @staticmethod
    async def get_part_spare_num(
            model: str,
            part: str,
            distribution_type: DistributeType = DistributeType.Weibull_2P,
            method: FitMethodType = FitMethodType.MLE,
            check: FitCheckType = FitCheckType.BIC,
            input_date: Union[str, date] = None,
            start_date: Union[str, date] = None,
            end_date: Union[str, date] = None
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
        distribution = await DistributeService.get_part_distribution(model, part, distribution_type, method, check)
        # 2. 计算备件量:两个时间点之间CDF的差值,需要标签，用标签中每一个去算(我滴龟龟，麻了)
        tags = await part_strategy_service.part_tag_process(model, part, input_date)
        # 3. 日期转换
        start_date = dateutils.validate_and_parse_date(start_date)
        end_date = dateutils.validate_and_parse_date(end_date)
        # 4.产品信息
        async with async_db_session() as db:
            product_data = convert_to_pydantic_model(await product_dao.get_by_model(db, model), ProductParam)
        # 5.计算数量
        result = await DistributeService.get_spare_num(tags, start_date, end_date, product_data, distribution)
        return result

    @staticmethod
    async def get_all_parts_spare_num_by_model(
            model: str,
            distribution_type: DistributeType = None,
            method: FitMethodType = FitMethodType.MLE,
            check: FitCheckType = FitCheckType.BIC,
            input_date: Union[str, date] = None,
            start_date: Union[str, date] = None,
            end_date: Union[str, date] = None
    ):
        # 1. 确定哪些零部件有分布
        async with async_db_session() as db:
            parts = await fit_part_dao.get_by_model(db, model)
            if not parts:
                raise errors.DataValidationError(msg=f'型号{model}没有零部件拥有拟合分布')
        # 2. 处理参数
        start_date = dateutils.validate_and_parse_date(start_date)
        end_date = dateutils.validate_and_parse_date(end_date)
        async with async_db_session() as db:
            product_data = convert_to_pydantic_model(await product_dao.get_by_model(db, model), ProductParam)
        # 3. 获取每个零部件的备件量
        results = {
            'model': model,
            'input_date': input_date,
            'start_date': start_date,
            'end_date': end_date,
            'distribution': distribution_type,
            'method': method,
            'check': check,
            'total': len(parts),
            'success': 0,
            'fail': 0,
            'parts': {},
        }
        errors_info = {}
        for part in parts:
            try:
                # part_distribution = await DistributeService.get_part_distribution(model, part, distribution_type,
                #                                                                   method, check)
                tags = await part_strategy_service.part_tag_process(model, part, input_date)
                # 利用之前计算的分布计算备件量
                # result = await DistributeService.get_spare_num(tags, start_date, end_date, product_data, part_distribution)
                # 利用标签现算最优分布，进行计算
                result = await DistributeService.get_spare_num_by_fit(tags, start_date, end_date, product_data, method)
                # 需要再乘以bom数量
                ebom_data = await ebom_dao.get_by_model_and_part(db, model, part)
                ebom_data = convert_to_pydantic_models(ebom_data, EbomParam)
                total_bl_quantity = convert_to_total_quantity(ebom_data)
                results['success'] += 1
                results['parts'][part] = result * total_bl_quantity
            except Exception as e:
                results['fail'] += 1
                errors_info[part] = f'型号{model}没有零部件{part}计算失败，错误信息为{str(e)}'
        if errors_info:
            results['errors'] = errors_info
        return results


distribute_service: DistributeService = DistributeService()
