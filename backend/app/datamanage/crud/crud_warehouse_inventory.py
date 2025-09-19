#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Sequence, Any

from sqlalchemy import Select, delete, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model.warehouse_inventory import WarehouseInventory


class CRUDWarehouseInventory(CRUDPlus[WarehouseInventory]):
    """库房备品清单数据库操作类"""

    async def get_select(
        self,
        warehouse_code: str | None = None,
        warehouse_name: str | None = None,
        part_code: str | None = None,
        part_name: str | None = None,
    ) -> Select:
        """
        获取库房备品清单查询语句

        :param warehouse_code: 库房编号
        :param warehouse_name: 库房名称
        :param part_code: 零部件物料编码
        :param part_name: 零部件名称
        :return: 查询语句
        """
        query = select(self.model)
        if warehouse_code:
            query = query.where(self.model.warehouse_code.like(f"%{warehouse_code}%"))
        if warehouse_name:
            query = query.where(self.model.warehouse_name.like(f"%{warehouse_name}%"))
        if part_code:
            query = query.where(self.model.part_code.like(f"%{part_code}%"))
        if part_name:
            query = query.where(self.model.part_name.like(f"%{part_name}%"))

        return query

    async def clear_all(self, db: AsyncSession) -> None:
        """
        清空所有库房备品清单数据

        :param db: 数据库会话
        """
        await db.execute(delete(WarehouseInventory))
        await db.execute(text("ALTER TABLE dm_warehouse_inventory AUTO_INCREMENT = 1"))
        await db.commit()

    async def bulk_create(
        self, db: AsyncSession, inventory_data: List[dict[str, Any]]
    ) -> List[WarehouseInventory]:
        """
        批量创建库房备品清单

        :param db: 数据库会话
        :param inventory_data: 库房备品清单数据列表
        :return: 创建的库房备品清单列表
        """
        inventories = [WarehouseInventory(**data) for data in inventory_data]
        db.add_all(inventories)
        await db.commit()
        for inventory in inventories:
            await db.refresh(inventory)
        return inventories

    async def get_all(self, db: AsyncSession) -> Sequence[WarehouseInventory]:
        """
        获取所有库房备品清单
        :param db: 数据库会话
        :return: 库房备品清单列表
        """
        stmt = select(self.model)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_warehouse_and_part(
        self, db: AsyncSession, warehouse_code: str, part_code: str
    ) -> WarehouseInventory:
        """
        根据库房编码和备品编码获取库房备品信息
        :param db: 数据库会话
        :param warehouse_code: 库房编码
        :param part_code: 备品编码
        :return: 库房备品信息
        """
        stmt = select(self.model).where(
            self.model.warehouse_code == warehouse_code,
            self.model.part_code == part_code,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


warehouse_inventory_dao: CRUDWarehouseInventory = CRUDWarehouseInventory(
    WarehouseInventory
)
