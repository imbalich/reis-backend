#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：crud_despatch.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2024/12/26 16:51 
'''
from typing import Sequence, Any

from sqlalchemy import Select, select, distinct, desc, and_, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Despatch


class CRUDDespatch(CRUDPlus[Despatch]):

    async def get_distinct_column_values(self, db: AsyncSession, column_name: str) -> Sequence[Any]:
        """
        获取指定列的所有唯一值
        :param db: 数据库会话
        :param column_name: 列名
        :return: 唯一值列表
        """
        # 确保列名存在于模型中
        if not hasattr(self.model, column_name):
            raise ValueError(f"Column {column_name} does not exist in model {self.model.__name__}")

        # 构建查询
        column = getattr(self.model, column_name)
        stmt = select(distinct(column)).order_by(column)
        # 执行查询
        result = await db.execute(stmt)

        # 返回结果
        return result.scalars().all()

    async def get_list(self, model: str = None, identifier: str = None, repair_level: str = None,
                       time_range: list[str] = None) -> Select:
        """
        获取数据列表
        :param model: 产品型号
        :param identifier: 产品标识
        :param repair_level: 修造级别
        :param time_range: 时间范围
        :return: 查询语句
        """
        stmt = select(self.model).order_by(desc(self.model.model))
        where_list = []
        if model:
            where_list.append(self.model.model == model)
        if identifier is not None:
            where_list.append(self.model.identifier == identifier)
        if repair_level is not None:
            where_list.append(self.model.repair_level == repair_level)
        if time_range:
            where_list.append(self.model.life_cycle_time.between(time_range[0], time_range[1]))
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model(self, db: AsyncSession, model: str) -> Despatch:
        """
        根据 model 获取单个despatch:做检测用，不用考虑是不是新造条件
        :param db: 数据库会话
        :param model: 产品型号
        :return: 查询结果
        """
        return await self.select_model_by_column(db, model=model)

    async def get_despatchs_by_model(self, db: AsyncSession, model: str) -> Sequence[Despatch]:
        """
        根据 model 获取多个despatchs
        :param db: 数据库会话
        :param model: 产品型号
        :return: 查询结果
        """
        return await self.select_models(db, model__eq=model, repair_level__eq='新造')

    async def get_by_model_exclude_repair_level(self, db: AsyncSession, model: str) -> Sequence[Despatch]:
        """
        根据 model 批量获取修造级别不为['新造', '故障修']的数据
        :param db: 数据库会话
        :param model: 产品型号
        :return: 查询语句
        """
        exclude_repair_level = ['新造', '故障修']

        stmt = select(self.model).order_by(asc(self.model.life_cycle_time))
        where_list = []
        where_list.append(self.model.model == model)
        where_list.append(self.model.repair_level.notin_(exclude_repair_level))
        if where_list:
            stmt = stmt.where(*where_list)
        results = await db.execute(stmt)
        return results.scalars().all()

    async def get_models_by_despatch(self, db: AsyncSession) -> Sequence[str]:
        """
        获取所有产品型号，repair_level 为 '新造'
        :param db: 数据库会话
        :return: 产品型号列表
        """
        stmt = select(distinct(self.model.model)).order_by(self.model.model)
        where_list = []
        where_list.append(self.model.repair_level == '新造')
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        models = result.scalars().all()
        return models


despatch_dao: CRUDDespatch = CRUDDespatch(Despatch)
