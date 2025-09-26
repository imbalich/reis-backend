#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Sequence, Any

from sqlalchemy import Select, delete, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.calcu.model.science_warehouse_result import ScienceWarehouseResult


class CRUDScienceWarehouseResult(CRUDPlus[ScienceWarehouseResult]):
    """科学库存计算结果数据库操作类"""

    async def get_select(
        self,
        calculation_id: str | None = None,
        warehouse_code: str | None = None,
        spare_part_code: str | None = None,
    ) -> Select:
        """
        获取科学库存计算结果查询语句

        :param calculation_id: 计算批次ID
        :param warehouse_code: 库房编码
        :param spare_part_code: 备品编码
        :return: 查询语句
        """
        query = select(self.model)
        if calculation_id:
            query = query.where(self.model.calculation_id == calculation_id)
        if warehouse_code:
            query = query.where(self.model.warehouse_code == warehouse_code)
        if spare_part_code:
            query = query.where(self.model.spare_part_code == spare_part_code)

        return query

    async def clear_by_calculation_id(self, db: AsyncSession, calculation_id: str) -> None:
        """
        清空指定计算批次的结果数据

        :param db: 数据库会话
        :param calculation_id: 计算批次ID
        """
        await db.execute(delete(ScienceWarehouseResult).where(
            ScienceWarehouseResult.calculation_id == calculation_id
        ))
        await db.commit()

    async def bulk_create(
        self, db: AsyncSession, result_data: List[dict[str, Any]]
    ) -> List[ScienceWarehouseResult]:
        """
        批量创建科学库存计算结果

        :param db: 数据库会话
        :param result_data: 结果数据列表
        :return: 创建的结果列表
        """
        results = [ScienceWarehouseResult(**data) for data in result_data]
        db.add_all(results)
        await db.commit()
        for result in results:
            await db.refresh(result)
        return results


science_warehouse_result_dao: CRUDScienceWarehouseResult = CRUDScienceWarehouseResult(
    ScienceWarehouseResult
)
