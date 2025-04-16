#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：crud_configuration.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/3/24 14:13 
'''
from typing import Sequence, Any

from sqlalchemy import Select, select, distinct, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Configuration


class CRUDConfiguration(CRUDPlus[Configuration]):
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

    ## 根据产品型号获取配置列表
    async def get_by_model_and_part(self, db: AsyncSession, model: str, part: str) -> Sequence[Configuration]:

        stmt = select(self.model).order_by(self.model.product_serial_no)
        where_list = []
        where_list.append(self.model.extra_material_code == part)
        where_list.append(self.model.prod_model == model)
        # where_list.append(self.model.process_name == '总装配')
        where_list.append(self.model.product_no is not None)
        where_list.append(self.model.extra_source_code not in ['无', '/', '有'])
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()


configuration_dao: CRUDConfiguration = CRUDConfiguration(Configuration)
