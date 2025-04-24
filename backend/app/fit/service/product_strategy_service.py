#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : product_strategy_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/2/25 下午2:17
"""

from datetime import date
from typing import Any

from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.schema.base_param import DespatchParam, FailureParam, ProductParam
from backend.app.fit.service.product_tag_process_service import product_tag_process_service
from backend.app.fit.utils.convert_model import convert_to_pydantic_model, convert_to_pydantic_models
from backend.app.fit.utils.data_check_utils import datacheckutils
from backend.app.fit.utils.time_utils import dateutils
from backend.common.exception import errors
from backend.database.db import async_db_session


class ProductStrategyService:
    @staticmethod
    async def model_tag_process(model: str, input_date: str | date = None) -> list[list]:
        """
        整机级别，单型号标签处理
        :param model: 产品型号
        :param input_date: 输入日期，格式为 "YYYY-MM-DD" 的字符串或 date 对象，默认为当前日期
        :return: 处理结果
        """
        # 处理 input_date 参数
        input_date = dateutils.validate_and_parse_date(input_date)
        # 处理 model 参数
        # 1.检查产品信息Product
        product_check = await datacheckutils.check_model_in_product(model)
        if not product_check:
            raise errors.DataValidationError(msg=f'型号{model}的产品信息不存在')
        # 2.检查累计运行时间Despatch
        run_time_check = await datacheckutils.check_model_in_despatch(model)
        if not run_time_check:
            raise errors.DataValidationError(msg=f'型号{model}的累计运行时间不足')
        # 3.检查故障信息Failure数量
        fault_check = await datacheckutils.check_model_in_failure(model)
        if not fault_check:
            raise errors.FailureCheckError(msg=f'型号{model}的故障信息数量不足')

        async with async_db_session() as db:
            try:
                # 获取基础数据
                despatch_data = convert_to_pydantic_models(
                    await despatch_dao.get_despatchs_by_model(db, model), DespatchParam
                )
                failure_data = convert_to_pydantic_models(await failure_dao.get_by_model(db, model), FailureParam)
                product_data = convert_to_pydantic_model(await product_dao.get_by_model(db, model), ProductParam)
                # 打标操作
                tags = await product_tag_process_service.process_data(
                    despatch_data, failure_data, product_data, input_date
                )
                return tags
            except Exception as e:
                raise errors.DataValidationError(msg=f'型号{model}打标失败,失败原因：{str(e)}')

    @staticmethod
    async def models_tag_process(models: list[str], input_date: str | date = None) -> dict[str, Any]:
        """
        整机级别，多型号标签处理
        :param models: 产品型号列表
        :param input_date: 输入日期，格式为 "YYYY-MM-DD" 的字符串或 date 对象，默认为当前日期
        :return: 处理结果
        """
        # 处理 input_date 参数
        input_date = dateutils.validate_and_parse_date(input_date)

        async with async_db_session():
            # 这里进行你的处理逻辑
            pass

        # 返回处理结果
        return {'result': '处理完成', 'date': input_date.isoformat()}


product_strategy_service: ProductStrategyService = ProductStrategyService()
