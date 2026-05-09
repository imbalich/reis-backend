#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project 锛歠astapi-base-backend
@File    锛歝rud_product.py
@IDE     锛歅yCharm
@Author  锛歩mbalich
@Date    锛?025/1/14 14:24
"""

from typing import Any, List, Sequence

from sqlalchemy import Row, Select, desc, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Product


class CRUDProduct(CRUDPlus[Product]):
    async def get_list(
        self, model: str = None, product_config_code: str | None = None
    ) -> Select:
        """
        鑾峰彇鏁版嵁鍒楄〃
        """
        stmt = select(self.model).order_by(desc(self.model.model))
        where_list = []
        if model:
            where_list.append(self.model.model == model)
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_distinct_column_values(self, db: AsyncSession, column_name: str) -> Sequence[Any]:
        """
        鑾峰彇鎸囧畾鍒楃殑鎵€鏈夊敮涓€鍊?
        """
        if not hasattr(self.model, column_name):
            raise ValueError(f'Column {column_name} does not exist in model {self.model.__name__}')

        column = getattr(self.model, column_name)
        stmt = select(distinct(column)).order_by(column)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_distinct_columns_values(
        self, db: AsyncSession, column_names: List[str]
    ) -> Sequence[Row[tuple[Any, ...]]]:
        for col in column_names:
            if not hasattr(self.model, col):
                raise ValueError(f'Column {col} does not exist in model {self.model.__name__}')

        columns = [getattr(self.model, col) for col in column_names]
        stmt = select(*columns).distinct().order_by(*columns)
        result = await db.execute(stmt)
        return result.all()

    async def get_models_by_product(self, db: AsyncSession) -> Sequence[str]:
        stmt = select(distinct(self.model.model)).order_by(self.model.model)
        where_list = [
            self.model.avg_worktime.is_not(None),
            self.model.avg_speed.is_not(None),
            self.model.year_days.is_not(None),
            self.model.avg_worktime != 0,
            self.model.avg_speed != 0,
            self.model.year_days != 0,
        ]
        stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_model(
        self, db: AsyncSession, model: str, product_config_code: str | None = None
    ) -> Product:
        stmt = select(self.model).order_by(desc(self.model.year_days))
        where_list = []
        if model:
            where_list.append(self.model.model == model)
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().first()


product_dao: CRUDProduct = CRUDProduct(Product)
