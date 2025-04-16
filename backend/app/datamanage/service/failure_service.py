#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：despatch_service.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/26 16:52
"""

from typing import Sequence

from sqlalchemy import Select

from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


class FailureService:
    @staticmethod
    async def get_product_lifetime_stage() -> Sequence[str]:
        async with async_db_session() as db:
            models = await failure_dao.get_distinct_column_values(db, 'product_lifetime_stage')
            if not models:
                raise errors.NotFoundError(msg='故障数据中未找到产品寿命阶段')
            return models

    @staticmethod
    async def get_fault_mode() -> Sequence[str]:
        async with async_db_session() as db:
            models = await failure_dao.get_distinct_column_values(db, 'fault_mode')
            if not models:
                raise errors.NotFoundError(msg='故障数据中未找到终判故障模式')
            return models

    @staticmethod
    async def get_product_model() -> Sequence[str]:
        async with async_db_session() as db:
            models = await failure_dao.get_distinct_column_values(db, 'product_model')
            if not models:
                raise errors.NotFoundError(msg='故障数据中未找到产品型号')
            return models

    @staticmethod
    async def get_fault_location_by_product_model(product_model: str = None) -> Sequence[str]:
        async with async_db_session() as db:
            if product_model:
                results = await failure_dao.get_distinct_columns_values_by_product_model(
                    db, product_model, ['fault_location', 'fault_material_code']
                )
            else:
                raise errors.NotFoundError(msg='请输入产品型号')
            models = []
            for fl, mc in results:
                if mc:
                    combined = f'{fl}（{mc}）'
                else:
                    combined = fl
                models.append(combined)
            return list(dict.fromkeys(models))

    @staticmethod
    async def get_select(
        *,
        product_model: str = None,
        fault_location: str = None,
        product_lifetime_stage: str = None,
        product_number: str = None,
        fault_mode: str = None,
        time_range: list[str] = None,
        is_zero_distance: int = 1,
        fault_material_code: str = None,
    ) -> Select:
        # 时间范围
        return await failure_dao.get_list(
            product_model=product_model,
            fault_location=fault_location,
            product_lifetime_stage=product_lifetime_stage,
            product_number=product_number,
            fault_mode=fault_mode,
            time_range=time_range,
            is_zero_distance=is_zero_distance,
            fault_material_code=fault_material_code,
        )

    @staticmethod
    async def get_parts_by_model(product_model: str = None) -> Sequence[str]:
        async with async_db_session() as db:
            parts = await failure_dao.get_distinct_column_values_by_product_model(
                db, product_model, 'fault_material_code'
            )
            return parts


failure_service: FailureService = FailureService()
