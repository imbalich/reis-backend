#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：product_service.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/16 16:52
"""

from typing import Sequence

from sqlalchemy import Select

from backend.app.datamanage.crud.crud_product import product_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


class ProductService:
    @staticmethod
    async def get_models() -> Sequence[str]:
        async with async_db_session() as db:
            models = await product_dao.get_distinct_column_values(db, 'model')
            if not models:
                raise errors.NotFoundError(msg='产品数据中未找到型号')
            return models

    @staticmethod
    async def get_select(*, model: str = None) -> Select:
        return await product_dao.get_list(model=model)


product_service: ProductService = ProductService()
