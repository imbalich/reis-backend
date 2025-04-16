#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：crud_product.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/14 14:24
"""

from typing import Any, Sequence

from sqlalchemy import Select, desc, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Product


class CRUDProduct(CRUDPlus[Product]):
    async def get_list(self, model: str = None) -> Select:
        """
        获取数据列表
        :param model: 产品型号
        :return: 查询语句
        """
        stmt = select(self.model).order_by(desc(self.model.model))
        where_list = []
        if model:
            where_list.append(self.model.model == model)
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_distinct_column_values(self, db: AsyncSession, column_name: str) -> Sequence[Any]:
        """
        获取指定列的所有唯一值
        :param db: 数据库会话
        :param column_name: 列名
        :return: 唯一值列表
        """
        # 确保列名存在于模型中
        if not hasattr(self.model, column_name):
            raise ValueError(f'Column {column_name} does not exist in model {self.model.__name__}')

        # 构建查询
        column = getattr(self.model, column_name)
        stmt = select(distinct(column)).order_by(column)
        # 执行查询
        result = await db.execute(stmt)

        # 返回结果
        return result.scalars().all()

    async def get_models_by_product(self, db: AsyncSession) -> Sequence[str]:
        """
        获取model列的所有唯一值,且avg_worktime、avg_speed、year_days不为空
        :param db: 数据库会话
        :return: 唯一值列表
        """
        stmt = select(distinct(self.model.model)).order_by(self.model.model)
        where_list = []
        where_list.append(self.model.avg_worktime.is_not(None))
        where_list.append(self.model.avg_speed.is_not(None))
        where_list.append(self.model.year_days.is_not(None))
        where_list.append(self.model.avg_worktime != 0)
        where_list.append(self.model.avg_speed != 0)
        where_list.append(self.model.year_days != 0)
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_model(self, db: AsyncSession, model: str) -> Product:
        """
        更具型号查询单条产品信息
        :param db: 数据库会话
        :param model: 产品型号
        :return: 查询语句
        """
        stmt = select(self.model).order_by(desc(self.model.year_days))
        where_list = []
        if model:
            where_list.append(self.model.model == model)
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().first()


product_dao: CRUDProduct = CRUDProduct(Product)
