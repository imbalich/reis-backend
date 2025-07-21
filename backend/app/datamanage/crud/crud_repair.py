#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：crud_repair.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/16 14:52
"""

from typing import Any

from sqlalchemy import Select, Sequence, desc, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Repair


class CRUDRepair(CRUDPlus[Repair]):
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

    async def get_list(self, model: str = None, state_now: bool = None) -> Select:
        """
        获取修程级别列表
        :param model: 产品型号
        :param state_now: 状态
        :return: 修程级别表
        """
        stmt = select(self.model).order_by(desc(self.model.model))
        where_list = []
        if model is not None:
            where_list.append(self.model.model == model)
        if state_now is not None:
            where_list.append(self.model.state_now == state_now)
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model(self, db: AsyncSession, model: str) -> Sequence[Repair]:
        """
        根据产品型号修程级别
        :param db: 数据库会话
        :param model: 产品型号
        :return: 修成级别表
        """
        stmt = select(self.model).order_by(desc(self.model.id_repair))
        where_list = []
        where_list.append(self.model.model == model)
        where_list.append(self.model.state_now == 1)
        if where_list:
            stmt = stmt.where(*where_list)
        results = await db.execute(stmt)
        return results.scalars().all()


repair_dao: CRUDRepair = CRUDRepair(Repair)
