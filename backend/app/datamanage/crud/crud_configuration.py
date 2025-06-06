#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：crud_configuration.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/3/24 14:13
"""

from typing import Any, Sequence

from sqlalchemy import distinct, select
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

    async def get_by_model_and_part_check(self, db: AsyncSession, model: str, part: str) -> Sequence[Configuration]:
        """
        根据产品型号和零部件编号获取配置列表,仅检测使用
        :param db: 数据库会话
        :param model: 产品型号
        :param part: 零部件编号
        :return: 配置列表
        """

        stmt = select(self.model).order_by(self.model.product_serial_no)
        where_list = []
        where_list.append(self.model.extra_material_code == part)
        where_list.append(self.model.prod_model == model)
        where_list.append(self.model.product_no is not None)
        where_list.append(self.model.extra_source_code not in ['无', '/', '有'])
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    ## 根据产品型号获取配置列表
    async def get_by_model_and_part(self, db: AsyncSession, model: str, part: str, stage: str, process_name: str,
                                    extra_material_name: str) -> Sequence[Configuration]:
        """
        根据产品型号、零部件编号、造修阶段、工序名称、零部件名称获取配置列表
        :param db: 数据库会话
        :param model: 产品型号
        :param part: 零部件编号
        :param stage: 造修阶段
        :param process_name: 工序名称
        :param extra_material_name: 零部件名称
        :return: 配置列表
        """

        where_list = [
            self.model.prod_model == model,
            self.model.repair_level == stage,
            self.model.product_no.isnot(None),
            self.model.extra_source_code.notin_(['无', '/', '有']),
            self.model.extra_supplier.notin_(['有', '无', '/', '.']),
        ]

        # 1. 检查是否存在符合所有条件 + extra_material_code == part 的记录
        if process_name:
            process_base = process_name.split("（")[0]
            where_list.append(self.model.process_name.startswith(process_base))
        if extra_material_name:
            where_list.append(self.model.extra_material_name == extra_material_name)
        # 2. 检查是否存在符合所有条件 + extra_material_code == part 的记录
        part_exists = await db.scalar(
            select(self.model)
            .where(*where_list, self.model.extra_material_code == part)
            .limit(1)
        )
        # 3. 如果存在，则添加 part 条件
        if part_exists:
            where_list.append(self.model.extra_material_code == part)

        stmt = select(self.model).where(*where_list).order_by(self.model.product_serial_no)
        result = await db.execute(stmt)
        return result.scalars().all()


configuration_dao: CRUDConfiguration = CRUDConfiguration(Configuration)
