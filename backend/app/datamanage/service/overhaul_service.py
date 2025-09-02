#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：overhaul_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/26 14:43
"""
from typing import Sequence


from backend.app.datamanage.crud.crud_overhaul import overhaul_dao
from backend.common.exception import errors
from backend.database.db import async_db_session

class OverhaulService:
    @staticmethod
    async def get_product_model() -> Sequence[str]:
        async with async_db_session() as db:
            models = await overhaul_dao.get_distinct_column_values(db, 'product_model')
            if not models:
                raise errors.NotFoundError(msg='故障数据中未找到产品型号')
            return models
    
    @staticmethod
    async def get_check_bezier_by_product_model(product_model: str = None) -> Sequence[str]:
        async with async_db_session() as db:
            parts = await overhaul_dao.get_distinct_column_values_by_product_model(
                db, product_model, 'check_bezier'
            )
            return parts
    
    @staticmethod
    async def get_product_no_by_product_model(product_model: str = None) -> Sequence[str]:
        async with async_db_session() as db:
            product_no = await overhaul_dao.get_distinct_column_values_by_product_model(
                db, product_model, 'product_no'
            )
            return product_no
        
overhaul_service: OverhaulService = OverhaulService()