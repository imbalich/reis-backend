#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：product_service.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/16 16:52
"""

from typing import Dict, List, Sequence

from sqlalchemy import Select

from backend.app.datamanage.crud.crud_product import product_dao
from backend.common.exception import errors
from backend.database.db import async_db_session


class ProductService:
    @staticmethod
    async def get_models() -> Sequence[str]:
        async with async_db_session() as db:
            models = await product_dao.get_distinct_column_values(db, "model")
            if not models:
                raise errors.NotFoundError(msg="产品数据中未找到型号")
            return models

    @staticmethod
    async def get_run_time_parameters(model: str) -> List[int | None]:
        """
        根据型号获取产品的年运行天数与日均工作小时数

        Args:
            model: 产品型号

        Returns:
            包含 年运行天数、日均工作小时数、平均时速的列表
        """
        async with async_db_session() as db:
            product = await product_dao.get_by_model(db, model)
            if product is None:
                raise errors.NotFoundError(msg=f"未找到型号为 {model} 的产品信息")

            return [product.year_days, product.avg_worktime,product.avg_speed]

    @staticmethod
    async def get_select(*, model: str = None) -> Select:
        return await product_dao.get_list(model=model)


product_service: ProductService = ProductService()
