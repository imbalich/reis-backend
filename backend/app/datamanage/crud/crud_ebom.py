#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：crud_ebom.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/16 14:43
"""

from typing import Any

from sqlalchemy import Select, Sequence, and_, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Ebom


class CRUDEbom(CRUDPlus[Ebom]):
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

    async def get_root_list(self, level1: int = 0, prd_no: str = None) -> Select:
        """
        获取根节点的数据列表
        :param level1: 根节点序号
        :param prd_no: 产品型号
        :return: 根节点列表
        """
        stmt = select(self.model).where(and_(self.model.level1 == level1, self.model.state_now == 1))
        where_list = []
        if prd_no:
            where_list.append(self.model.prd_no == prd_no)
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_node_list(
        self,
        level1: int = 1,
        partid: str = None,
    ) -> Select:
        """
        获取特定子节点的数据列表
        :param level1: 子节点层级序号
        :param partid: 父节点id
        :return: 子节点列表
        """
        stmt = select(self.model).where(
            and_(
                self.model.partid == partid,
                self.model.level1 == level1,
                self.model.state_now == 1,
            )
        )
        return stmt

    async def get_by_model(self, model: str) -> Select:
        """
        根据产品型号获取BOM信息
        :param model: 产品型号
        :return: BOM查询
        """
        stmt = select(self.model)
        where_list = []
        where_list.append(self.model.prd_no == model)
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model_and_part(self, db: AsyncSession, model: str, part: str) -> Sequence[Ebom]:
        """
        查询单型号单零部件BOM信息
        :param db: 数据库会话
        :param model: 产品型号
        :param part: 零部件
        :return: BOM查询
        """
        stmt = select(self.model)
        where_list = []
        where_list.append(self.model.prd_no == model)
        where_list.append(self.model.y8_matbnum1 == part)
        where_list.append(self.model.state_now == 1)
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()


ebom_dao: CRUDEbom = CRUDEbom(Ebom)
