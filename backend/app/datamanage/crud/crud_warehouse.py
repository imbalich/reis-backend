#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Sequence, Any

from sqlalchemy import Select, delete, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model.warehouse import Warehouse


class CRUDWarehouse(CRUDPlus[Warehouse]):
    """仓库数据库操作类"""

    async def get_select(
        self,
        area: str | None = None,
        name: str | None = None,
        code: str | None = None,
    ) -> Select:
        """
        获取仓库查询语句

        :param area: 归属区域
        :param name: 库房名称
        :param code: 库房编码
        :return: 查询语句
        """
        # 使用 select() 而不是 select(Warehouse) 来避免关系字段的懒加载
        query = select(self.model)
        if area:
            query = query.where(self.model.area.like(f"%{area}%"))
        if name:
            query = query.where(self.model.name.like(f"%{name}%"))
        if code:
            query = query.where(self.model.code.like(f"%{code}%"))

        return query

    async def clear_all(self, db: AsyncSession) -> None:
        """
        清空所有仓库数据

        :param db: 数据库会话
        """
        await db.execute(delete(Warehouse))
        await db.execute(text("ALTER TABLE dm_warehouse AUTO_INCREMENT = 1"))
        await db.commit()

    async def bulk_create(
        self, db: AsyncSession, warehouses_data: List[dict[str, Any]]
    ) -> List[Warehouse]:
        """
        批量创建仓库

        :param db: 数据库会话
        :param warehouses_data: 仓库数据列表
        :return: 创建的仓库列表
        """
        warehouses = [Warehouse(**data) for data in warehouses_data]
        db.add_all(warehouses)
        await db.commit()
        for warehouse in warehouses:
            await db.refresh(warehouse)
        return warehouses

    async def get_by_allotment_twos(
        self, db: AsyncSession, allotment_twos: List[str]
    ) -> Sequence[Warehouse]:
        """
        根据二级配属列表获取库房信息
        :param db: 数据库会话
        :param allotment_twos: 二级配属列表
        :return: 库房信息列表
        """
        if not allotment_twos:
            return []

        stmt = select(self.model).where(self.model.allotment_two.in_(allotment_twos))
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_code(self, db: AsyncSession, code: str) -> Sequence[Warehouse]:
        """
        根据库房编码获取库房信息
        :param db: 数据库会话
        :param code: 库房编码
        :return: 库房信息列表
        """
        stmt = select(self.model).where(self.model.code == code)
        result = await db.execute(stmt)
        return result.scalars().all()


warehouse_dao: CRUDWarehouse = CRUDWarehouse(Warehouse)
