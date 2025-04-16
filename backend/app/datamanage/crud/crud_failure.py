#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：crud_failure.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/26 16:51
"""

from typing import Any, List, Sequence

from sqlalchemy import Row, Select, desc, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Failure


class CRUDFailure(CRUDPlus[Failure]):
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
            raise ValueError(f'Column {column_name} does not exist in model {self.model.__name__}')

        # 构建查询
        column = getattr(self.model, column_name)
        # 先查产品型号==column下的所有product_model，然后针对product_model去重
        stmt = select(distinct(column)).where(self.model.product_model == product_model).order_by(column)
        # 执行查询
        result = await db.execute(stmt)

        # 返回结果
        return result.scalars().all()

    async def get_distinct_columns_values_by_product_model(
        self, db: AsyncSession, product_model: str, column_names: List[str]
    ) -> Sequence[Row[tuple[Any, ...]]]:
        """
        获取指定两列的所有唯一值，根据产品型号
        :param db: 数据库会话
        :param product_model: 产品型号
        :param column_name: '故障部位‘
        :return: 产品型号下故障部位的唯一列表
        """
        for col in column_names:
            if not hasattr(self.model, col):
                raise ValueError(f'Column {col} does not exist in model {self.model.__name__}')
        columns = [getattr(self.model, col) for col in column_names]
        # 构建查询，按列排序
        stmt = select(*columns).distinct().where(self.model.product_model == product_model).order_by(*columns)
        result = await db.execute(stmt)
        return result.all()

    async def get_list(
        self,
        product_model: str = None,
        fault_location: str = None,
        product_lifetime_stage: str = None,
        product_number: str = None,
        fault_mode: str = None,
        time_range: list[str] = None,
        is_zero_distance: int = 1,
        fault_material_code: str = None,
    ) -> Select:
        """
        获取数据列表
        :param product_model:
        :param fault_location:
        :param product_lifetime_stage:
        :param product_number:
        :param fault_mode:
        :param time_range:
        :param is_zero_distance:
        :param fault_material_code:
        :return: 查询语句
        """
        stmt = select(self.model).order_by(desc(self.model.product_model))
        where_list = []
        if product_model:
            where_list.append(self.model.product_model == product_model)
        if fault_location is not None:
            where_list.append(self.model.fault_location == fault_location)
        if product_lifetime_stage is not None:
            where_list.append(self.model.product_lifetime_stage == product_lifetime_stage)
        if product_number is not None:
            where_list.append(self.model.product_number == product_number)
        if fault_mode is not None:
            where_list.append(self.model.fault_mode == fault_mode)
        if time_range:
            where_list.append(self.model.discovery_date.between(time_range[0], time_range[1]))
        if is_zero_distance is not None:
            where_list.append(self.model.is_zero_distance == is_zero_distance)
        if fault_material_code is not None:
            where_list.append(self.model.fault_material_code == fault_material_code)
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model(self, db: AsyncSession, model: str) -> Sequence[Failure]:
        """
        根据产品型号获取故障列表
        :param db: 数据库会话
        :param model: 产品型号
        :return: 故障列表
        """
        stmt = select(self.model).order_by(self.model.discovery_date)
        where_list = []
        where_list.append(self.model.product_model == model)
        where_list.append(self.model.is_zero_distance == 0)
        where_list.append(self.model.final_fault_responsibility != '用户')
        where_list.append(self.model.manufacturing_date.isnot(None))  # 添加这个条件
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_models_by_part(self, part: str) -> Select:
        """
        根据零部件在故障清单中获取产品型号，主要用于校验检验零部件是否在故障单中
        :param part: 零部件
        :return: 产品型号
        """
        stmt = select(distinct(self.model.product_model))
        where_list = []
        where_list.append(self.model.fault_material_code == part)
        where_list.append(self.model.is_zero_distance == 0)
        where_list.append(self.model.final_fault_responsibility != '用户')
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model_and_part(self, db: AsyncSession, model: str, part: str) -> Sequence[Failure]:
        """
        查询单型号单零部件故障信息:做检测用，不用考虑是否新造
        :param db: 数据库会话
        :param model: 产品型号
        :param part: 零部件
        :return: 故障列表
        """
        stmt = select(self.model).order_by(self.model.discovery_date)
        where_list = []
        where_list.append(self.model.product_model == model)
        where_list.append(self.model.fault_material_code == part)
        where_list.append(self.model.is_zero_distance == 0)
        where_list.append(self.model.final_fault_responsibility != '用户')
        where_list.append(self.model.manufacturing_date.isnot(None))  # 添加这个条件
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_number_by_model(self, db: AsyncSession, model: str, part: str) -> Sequence[str]:
        """ """
        stmt = select(distinct(self.model.product_number))
        where_list = []
        where_list.append(self.model.product_model == model)
        where_list.append(self.model.fault_material_code == part)
        if where_list:
            stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()


failure_dao: CRUDFailure = CRUDFailure(Failure)
