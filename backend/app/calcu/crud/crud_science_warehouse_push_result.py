#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.calcu.model.science_warehouse_push_result import (
    ScienceWarehousePushResult,
)


class CRUDScienceWarehousePushResult(CRUDPlus[ScienceWarehousePushResult]):
    """科学库存待推送结果数据库操作类。"""

    async def get_by_calculation_id(
        self, db: AsyncSession, calculation_id: str
    ) -> list[ScienceWarehousePushResult]:
        """按计算批次获取人工审查后的待推送结果。"""
        return await self.select_models(db, calculation_id__eq=calculation_id)

    async def count_by_calculation_id(
        self, db: AsyncSession, calculation_id: str
    ) -> int:
        """统计指定计算批次的待推送结果数量。"""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.calculation_id == calculation_id)
        )
        result = await db.execute(stmt)
        return int(result.scalar_one())


science_warehouse_push_result_dao: CRUDScienceWarehousePushResult = (
    CRUDScienceWarehousePushResult(ScienceWarehousePushResult)
)
