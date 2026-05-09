#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Sequence, Any

from sqlalchemy import Select, delete, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.calcu.model.science_warehouse_statistics import ScienceWarehouseStatistics


class CRUDScienceWarehouseStatistics(CRUDPlus[ScienceWarehouseStatistics]):
    """科学库存计算统计信息数据库操作类"""

    async def get_select(
        self,
        calculation_id: str | None = None,
        product_model: str | None = None,
        product_config_code: str | None = None,
    ) -> Select:
        """
        获取科学库存计算统计信息查询语句

        :param calculation_id: 计算批次ID
        :return: 查询语句
        """
        query = select(self.model)
        if calculation_id:
            query = query.where(self.model.calculation_id == calculation_id)
        if product_model:
            query = query.where(self.model.product_model == product_model)
        if product_config_code is not None:
            query = query.where(self.model.product_config_code == product_config_code)

        return query

    async def clear_by_calculation_id(self, db: AsyncSession, calculation_id: str) -> None:
        """
        清空指定计算批次的统计信息

        :param db: 数据库会话
        :param calculation_id: 计算批次ID
        """
        await db.execute(delete(ScienceWarehouseStatistics).where(
            ScienceWarehouseStatistics.calculation_id == calculation_id
        ))
        await db.commit()

    async def create(self, db: AsyncSession, obj) -> None:
        """
        创建科学库存计算统计信息

        :param db: 数据库会话
        :param obj: 统计信息对象
        """
        await self.create_model(db, obj)


science_warehouse_statistics_dao: CRUDScienceWarehouseStatistics = CRUDScienceWarehouseStatistics(
    ScienceWarehouseStatistics
)
