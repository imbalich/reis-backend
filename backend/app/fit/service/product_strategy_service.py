#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : product_strategy_service.py
"""

from datetime import date
from typing import Any

from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.fit.schema.base_param import DespatchParam, FailureParam, ProductParam
from backend.app.fit.service.product_tag_process_service import product_tag_process_service
from backend.app.fit.utils.convert_model import (
    convert_to_pydantic_model,
    convert_to_pydantic_models,
)
from backend.app.fit.utils.data_check_utils import datacheckutils
from backend.app.fit.utils.time_utils import dateutils
from backend.common.exception import errors
from backend.database.db import async_db_session


class ProductStrategyService:
    @staticmethod
    async def model_tag_process(
        model: str,
        input_date: str | date = None,
        product_config_code: str | None = None,
    ) -> list[list]:
        input_date = dateutils.validate_and_parse_date(input_date)

        product_check = await datacheckutils.check_model_in_product(
            model,
            product_config_code=product_config_code,
        )
        if not product_check:
            raise errors.DataValidationError(msg=f"型号{model}的产品信息不存在")

        run_time_check = await datacheckutils.check_model_in_despatch(
            model,
            product_config_code=product_config_code,
        )
        if not run_time_check:
            raise errors.DataValidationError(msg=f"型号{model}的累计运行时间不足")

        fault_check = await datacheckutils.check_model_in_failure(
            model,
            product_config_code=product_config_code,
        )
        if not fault_check:
            raise errors.FailureCheckError(msg=f"型号{model}的故障信息数量不足")

        async with async_db_session() as db:
            try:
                despatch_data = convert_to_pydantic_models(
                    await despatch_dao.get_despatchs_by_model(
                        db,
                        model,
                        product_config_code=product_config_code,
                    ),
                    DespatchParam,
                )
                failure_data = convert_to_pydantic_models(
                    await failure_dao.get_by_model(
                        db,
                        model,
                        product_config_code=product_config_code,
                    ),
                    FailureParam,
                )
                product_data = convert_to_pydantic_model(
                    await product_dao.get_by_model(
                        db,
                        model,
                        product_config_code=product_config_code,
                    ),
                    ProductParam,
                )
                return await product_tag_process_service.process_data(
                    despatch_data,
                    failure_data,
                    product_data,
                    input_date,
                )
            except Exception as exc:
                raise errors.DataValidationError(
                    msg=f"型号{model}打标失败，失败原因为：{exc}"
                )

    @staticmethod
    async def models_tag_process(
        models: list[str],
        input_date: str | date = None,
    ) -> dict[str, Any]:
        input_date = dateutils.validate_and_parse_date(input_date)
        return {"result": "处理完成", "date": input_date.isoformat(), "models": models}


product_strategy_service: ProductStrategyService = ProductStrategyService()
