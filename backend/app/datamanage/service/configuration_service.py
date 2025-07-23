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
    async def get_material_name_by_filter(product_model: str = None, process_name: str = None) -> Sequence[list]:
        async with async_db_session() as db:
            results = await configuration_dao.get_material_name_and_code(
                db, product_model=product_model, process_name=process_name
            )
            def is_valid(val):
                return val and val.strip() and val.strip() != "/"
            return [
                [row.extra_material_name, row.extra_material_code]
                for row in results
                if is_valid(row.extra_material_name) and is_valid(row.extra_material_code)
            ]


configuration_service: ConfigurationService = ConfigurationService()