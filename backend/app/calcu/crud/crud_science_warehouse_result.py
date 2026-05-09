#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Sequence, Any

from sqlalchemy import Select, delete, distinct, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.calcu.model.science_warehouse_result import ScienceWarehouseResult


class CRUDScienceWarehouseResult(CRUDPlus[ScienceWarehouseResult]):
    """科学库存计算结果数据库操作类"""

    async def get_select(
        self,
        calculation_id: str | None = None,
        product_model: str | None = None,
        product_config_code: str | None = None,
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
        if product_model:
            query = query.where(self.model.product_model == product_model)
        if product_config_code is not None:
            query = query.where(self.model.product_config_code == product_config_code)
        if warehouse_code:
            query = query.where(self.model.warehouse_code == warehouse_code)
        if spare_part_code:
            query = query.where(self.model.spare_part_code == spare_part_code)

        return query

    async def clear_by_calculation_id(
        self, db: AsyncSession, calculation_id: str
    ) -> None:
        """
        清空指定计算批次的结果数据

        :param db: 数据库会话
        :param calculation_id: 计算批次ID
        """
        await db.execute(
            delete(ScienceWarehouseResult).where(
                ScienceWarehouseResult.calculation_id == calculation_id
            )
        )
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

    async def get_warehouse_code_name_pairs(
        self, db: AsyncSession
    ) -> Sequence[List[str]]:
        """
        获取库房编码和名称的列表（去重）

        :param db: 数据库会话
        :return: [[库房编码, 库房名称], ...] 的列表
        """
        stmt = (
            select(
                self.model.warehouse_code,
                self.model.warehouse_name,
            )
            .distinct()
            .order_by(self.model.warehouse_code, self.model.warehouse_name)
        )
        result = await db.execute(stmt)
        return [[row[0], row[1]] for row in result.all()]

    async def get_spare_part_code_name_pairs(
        self,
        db: AsyncSession,
        warehouse_code: str | None = None,
    ) -> Sequence[List[str]]:
        """
        根据库房编码获取备品编码和名称的列表（级联筛选）

        :param db: 数据库会话
        :param warehouse_code: 库房编码（可选，用于级联筛选）
        :return: [[备品编码, 备品名称], ...] 的列表
        """
        stmt = select(
            self.model.spare_part_code,
            self.model.spare_part_name,
        ).distinct()
        if warehouse_code:
            stmt = stmt.where(self.model.warehouse_code == warehouse_code)
        stmt = stmt.order_by(self.model.spare_part_code, self.model.spare_part_name)
        result = await db.execute(stmt)
        return [[row[0], row[1]] for row in result.all()]

    async def get_distinct_calculation_methods(self, db: AsyncSession) -> Sequence[str]:
        """
        获取所有唯一的计算方法

        :param db: 数据库会话
        :return: 计算方法列表
        """
        stmt = select(distinct(self.model.calculation_method)).order_by(
            self.model.calculation_method
        )
        result = await db.execute(stmt)
        return result.scalars().all()


science_warehouse_result_dao: CRUDScienceWarehouseResult = CRUDScienceWarehouseResult(
    ScienceWarehouseResult
)
