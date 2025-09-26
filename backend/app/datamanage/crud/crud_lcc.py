#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：crud_overhual.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/20 09:36
"""

from typing import Sequence, Any, Optional

from sqlalchemy import select,or_,func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import distinct
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import LCC


class CRUDLCC(CRUDPlus[LCC]):

    async def get_distinct_column_values(
        self, db: AsyncSession, column_name: str
    ) -> Sequence[Any]:
        """
        获取指定列的所有唯一值
        :param db: 数据库会话
        :param column_name: 列名
        :return: 唯一值列表
        """
        # 确保列名存在于模型中
        if not hasattr(self.model, column_name):
            raise ValueError(
                f"Column {column_name} does not exist in model {self.model.__name__}"
            )

        # 构建查询
        column = getattr(self.model, column_name)
        stmt = select(distinct(column)).order_by(column)
        # 执行查询
        result = await db.execute(stmt)

        # 返回结果
        return result.scalars().all()
    
    async def get_distinct_column_values_by_product_model(
        self, db: AsyncSession, product_model: str, column_name: str
    ) -> Sequence[Any]:
        """
        获取指定列的所有唯一值，根据产品型号
        :param db: 数据库会话
        :param product_model: 产品型号
        :param column_name: '故障部位‘
        :return: 产品型号下故障部位的唯一列表
        """
        # 确保列名存在于模型中
        if not hasattr(self.model, column_name):
            raise ValueError(
                f"Column {column_name} does not exist in model {self.model.__name__}"
            )

        # 构建查询
        column = getattr(self.model, column_name)
        # 先查产品型号==column下的所有product_model，然后针对product_model去重
        stmt = (
            select(distinct(column))
            .where(self.model.product_model == product_model)
            .order_by(column)
        )
        # 执行查询
        result = await db.execute(stmt)

        # 返回结果
        return result.scalars().all()

    async def get_by_model_and_part(
            self,
            db: AsyncSession,
            model: str,
            part: str
    ) -> Sequence[LCC]:
        '''
        根据产品型号和检测项点获取所有数据
        :param db: 数据库会话
        :param product_model: 产品型号
        :param check_bezier: 检测项点
        :return: 所有数据
        '''
        stmt = select(self.model.cost)
        where_list = []
        where_list.append(self.model.model == model)
        where_list.append(self.model.material_code == part)
        if where_list:
            stmt = stmt.where(*where_list)
            stmt = stmt.limit(1)
        result = await db.execute(stmt)
        return result.scalars().first()

lcc_dao: CRUDLCC = CRUDLCC(LCC)





















