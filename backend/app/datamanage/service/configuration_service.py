#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：configuration_service.py.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/5/20 09:52
"""
from typing import Sequence

from backend.app.datamanage.crud.crud_configuration import configuration_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


class ConfigurationService:

    @staticmethod
    async def get_process_name_by_product_model(product_model: str=None) -> Sequence[str]:
        async with async_db_session() as db:
            process_name = await configuration_dao.get_distinct_column_values_by_product_model(
                db, product_model, 'process_name'
            )
            return process_name


    @staticmethod
    async def get_material_name_by_process_name(process_name: str = None) -> Sequence[str]:
        async with async_db_session() as db:
            if process_name:
                results = await configuration_dao.get_distinct_columns_values_by_process_name(
                    db, process_name, ['extra_material_name', 'extra_material_code']
                )
            else:
                raise errors.NotFoundError(msg='请输入检修工序')
            models = []
            for fl, mc in results:
                if mc and mc != '/':
                    combined = f'{fl}（{mc}）'
                    models.append(combined)
            return list(dict.fromkeys(models))


configuration_service: ConfigurationService = ConfigurationService()