#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from typing import Any, List, Sequence

from sqlalchemy import Select, asc, desc, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Allotment


class CRUDAllotment(CRUDPlus[Allotment]):

    async def get_select(
        self,
        vehicle_type: str | None = None,
        vehicle_number: str | None = None,
        product_model: str | None = None,
        ps_code: str | None = None,
        product_number: str | None = None,
        allotment_one: str | None = None,
        allotment_two: str | None = None,
    ) -> Select:
        """
        获取产品配属查询语句

        :param vehicle_type: 车型
        :param vehicle_number: 车号
        :param product_model: 产品型号
        :param ps_code: 派生码
        :param product_number: 产品编号
        :param allotment_one: 一级配属
        :param allotment_two: 二级配属
        :return: 查询语句
        """
        query = select(self.model)
        if vehicle_type:
            query = query.where(self.model.vehicle_type.like(f"%{vehicle_type}%"))
        if vehicle_number:
            query = query.where(self.model.vehicle_number.like(f"%{vehicle_number}%"))
        if product_model:
            query = query.where(self.model.product_model.like(f"%{product_model}%"))
        if ps_code:
            query = query.where(self.model.ps_code.like(f"%{ps_code}%"))
        if product_number:
            query = query.where(self.model.product_number.like(f"%{product_number}%"))
        if allotment_one:
            query = query.where(self.model.allotment_one.like(f"%{allotment_one}%"))
        if allotment_two:
            query = query.where(self.model.allotment_two.like(f"%{allotment_two}%"))

        return query

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
        column = getattr(self.model, column_name)
        stmt = select(distinct(column)).order_by(column)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_product_numbers(
        self, db: AsyncSession, product_numbers: List[str]
    ) -> Sequence[Allotment]:
        """
        根据产品编号列表获取配属信息
        :param db: 数据库会话
        :param product_numbers: 产品编号列表
        :return: 配属信息列表
        """
        if not product_numbers:
            return []

        stmt = select(self.model).where(self.model.product_number.in_(product_numbers))
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_allotment_two(
        self, db: AsyncSession, allotment_two: str
    ) -> Sequence[Allotment]:
        """
        根据二级配属获取配属信息
        :param db: 数据库会话
        :param allotment_two: 二级配属
        :return: 配属信息列表
        """
        stmt = select(self.model).where(self.model.allotment_two == allotment_two)
        result = await db.execute(stmt)
        return result.scalars().all()

    
    async def get_by_allotment_two_and_model(
        self, db: AsyncSession, allotment_two: str, model: str
    ) -> Sequence[Allotment]:
        """
        根据二级配属和产品型号获取配属信息
        :param db: 数据库会话
        :param allotment_two: 二级配属
        :param model: 产品型号
        :return: 配属信息列表
        """
        stmt = select(self.model).where(self.model.allotment_two == allotment_two, self.model.product_model == model)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_allotment_two_and_models(
        self, db: AsyncSession, allotment_two: str, target_models: List[str]
    ) -> Sequence[Allotment]:
        """
        根据二级配属和产品型号列表获取配属信息（优化版本）
        :param db: 数据库会话
        :param allotment_two: 二级配属
        :param target_models: 目标产品型号列表
        :return: 配属信息列表
        """
        if not target_models:
            return []

        stmt = select(self.model).where(
            self.model.allotment_two == allotment_two,
            self.model.product_model.in_(target_models),
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_product_number(
        self, db: AsyncSession, product_number: str
    ) -> Allotment:
        """
        根据产品编号获取配属信息
        :param db: 数据库会话
        :param product_number: 产品编号
        :return: 配属信息
        """
        stmt = select(self.model).where(self.model.product_number == product_number)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


allotment_dao: CRUDAllotment = CRUDAllotment(Allotment)
