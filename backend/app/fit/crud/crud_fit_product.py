#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : crud_fit_product.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/3 下午5:12
"""

from datetime import date
from typing import Sequence

from sqlalchemy import and_, asc, case, desc, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.fit.model.fit_product import FitProduct
from backend.app.fit.schema.fit_param import FitCheckType, FitMethodType


class CRUDFitProduct(CRUDPlus[FitProduct]):
    async def get_last(
        self, db: AsyncSession, model: str, input_date: date = None, method: FitMethodType = FitMethodType.MLE
    ) -> FitProduct | None:
        """
        获取单条型号最后的一条分布信息


        :param db: 数据库会话
        :param model: 产品型号
        :param input_date: 输入日期
        :param method: 拟合方法
        :return: 最新的 FitProduct 记录或 None
        """
        stmt = (
            select(self.model)
            .where(self.model.model == model)
            .where(self.model.method == method)
            .order_by(desc(self.model.created_time))
        )
        where_list = []
        if input_date:
            where_list.append(self.model.input_date == input_date)
        if where_list:
            stmt = stmt.where(and_(*where_list))
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create(self, db: AsyncSession, obj) -> None:
        """
        创建单型号单条分布信息
        """
        await self.create_model(db, obj)

    async def creates(self, db: AsyncSession, objs) -> None:
        """
        创建单型号多条分布信息
        :param db:
        :param objs:
        :return:
        """
        await self.create_models(db, objs)

    async def get_by_model(
        self,
        db: AsyncSession,
        model: str,
        input_date: date = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        source: bool = False,
    ) -> Sequence[FitProduct]:
        """
        根据型号查询拟合信息:查询最新的拟合信息,以一组的形式出现

        :param db: 数据库会话
        :param model: 型号
        :param input_date: 计算截止期
        :param method: 拟合方法
        :param check: 拟合优度检验
        :param source: False为系统默认,True为用户自定义
        :return: 符合条件的最新拟合信息列表
        """
        # 定义排序列
        order_column = case(
            (literal(FitCheckType.Log.value) == literal(check), self.model.log_likelihood),
            (literal(FitCheckType.AICc.value) == literal(check), self.model.aicc),
            (literal(FitCheckType.BIC.value) == literal(check), self.model.bic),
            (literal(FitCheckType.AD.value) == literal(check), self.model.ad),
        )

        # 基本查询条件
        base_conditions = [self.model.model == model, self.model.method == method, self.model.source == source]

        # 如果提供了 input_date，添加到查询条件中
        if input_date:
            base_conditions.append(self.model.input_date == input_date)

        # 子查询：获取最新的group_id
        latest_group_subquery = (
            select(self.model.group_id)
            .where(and_(*base_conditions))
            .order_by(desc(self.model.created_time))
            .limit(1)
            .scalar_subquery()
        )

        # 主查询：获取最新group的所有记录并排序
        stmt = (
            select(self.model)
            .where(and_(*base_conditions, self.model.group_id == latest_group_subquery))
            .order_by(asc(order_column))
        )

        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_model_and_distribution(
        self,
        db: AsyncSession,
        model: str,
        distribution: str,
        input_date: date = None,
        method: FitMethodType = FitMethodType.MLE,
        check: FitCheckType = FitCheckType.BIC,
        source: bool = False,
    ) -> FitProduct:
        """
        根据型号和分布查询拟合信息:查询最新的拟合信息,只选取一个

        :param db: 数据库会话
        :param model: 型号
        :param distribution: 分布
        :param input_date: 计算截止期
        :param method: 拟合方法
        :param check: 拟合优度检验
        :param source: False为系统默认,True为用户自定义
        :return: 符合条件的最新拟合信息列表
        """
        # 定义排序列
        order_column = case(
            (literal(FitCheckType.Log.value) == literal(check), self.model.log_likelihood),
            (literal(FitCheckType.AICc.value) == literal(check), self.model.aicc),
            (literal(FitCheckType.BIC.value) == literal(check), self.model.bic),
            (literal(FitCheckType.AD.value) == literal(check), self.model.ad),
        )

        # 基本查询条件
        base_conditions = [
            self.model.model == model,
            self.model.distribution == distribution,
            self.model.method == method,
            self.model.source == source,
        ]

        # 如果提供了 input_date，添加到查询条件中
        if input_date:
            base_conditions.append(self.model.input_date == input_date)

        # 子查询：获取最新的group_id
        latest_group_subquery = (
            select(self.model.group_id)
            .where(and_(*base_conditions))
            .order_by(desc(self.model.created_time))
            .limit(1)
            .scalar_subquery()
        )

        # 主查询：获取最新group的所有记录并排序
        stmt = (
            select(self.model)
            .where(and_(*base_conditions, self.model.group_id == latest_group_subquery))
            .order_by(asc(order_column))
        )

        result = await db.execute(stmt)
        return result.scalars().first()


fit_product_dao: CRUDFitProduct = CRUDFitProduct(FitProduct)
