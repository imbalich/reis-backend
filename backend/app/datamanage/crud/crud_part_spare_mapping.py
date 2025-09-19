#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Sequence, Any

from sqlalchemy import Select, delete, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model.part_spare_mapping import PartSpareMapping


class CRUDPartSpareMapping(CRUDPlus[PartSpareMapping]):
    """部件与备品对应关系数据库操作类"""

    async def get_select(
        self,
        product_model: str | None = None,
        derived_code: str | None = None,
        original_part_name: str | None = None,
        original_part_code: str | None = None,
        spare_part_name: str | None = None,
        spare_part_code: str | None = None,
    ) -> Select:
        """
        获取部件与备品对应关系查询语句

        :param product_model: 产品型号
        :param derived_code: 派生码
        :param original_part_name: 零部件名称（原装）
        :param original_part_code: 零部件物料编码（原装）
        :param spare_part_name: 零部件名称（备品）
        :param spare_part_code: 零部件物料编码（备品）
        :return: 查询语句
        """
        query = select(self.model)
        if product_model:
            query = query.where(self.model.product_model.like(f"%{product_model}%"))
        if derived_code:
            query = query.where(self.model.derived_code.like(f"%{derived_code}%"))
        if original_part_name:
            query = query.where(
                self.model.original_part_name.like(f"%{original_part_name}%")
            )
        if original_part_code:
            query = query.where(
                self.model.original_part_code.like(f"%{original_part_code}%")
            )
        if spare_part_name:
            query = query.where(self.model.spare_part_name.like(f"%{spare_part_name}%"))
        if spare_part_code:
            query = query.where(self.model.spare_part_code.like(f"%{spare_part_code}%"))

        return query

    async def clear_all(self, db: AsyncSession) -> None:
        """
        清空所有部件与备品对应关系数据

        :param db: 数据库会话
        """
        await db.execute(delete(PartSpareMapping))
        await db.execute(text("ALTER TABLE dm_part_spare_mapping AUTO_INCREMENT = 1"))
        await db.commit()

    async def bulk_create(
        self, db: AsyncSession, mapping_data: List[dict[str, Any]]
    ) -> List[PartSpareMapping]:
        """
        批量创建部件与备品对应关系

        :param db: 数据库会话
        :param mapping_data: 部件与备品对应关系数据列表
        :return: 创建的部件与备品对应关系列表
        """
        mappings = [PartSpareMapping(**data) for data in mapping_data]
        db.add_all(mappings)
        await db.commit()
        for mapping in mappings:
            await db.refresh(mapping)
        return mappings

    async def get_by_spare_part_code(
        self, db: AsyncSession, spare_part_code: str
    ) -> Sequence[PartSpareMapping]:
        """
        根据备品编码获取映射关系
        :param db: 数据库会话
        :param spare_part_code: 备品编码
        :return: 映射关系列表
        """
        stmt = select(self.model).where(self.model.spare_part_code == spare_part_code)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_original_part_code(
        self, db: AsyncSession, product_model: str, original_part_code: str
    ) -> PartSpareMapping:
        """
        根据产品型号和原装部件编码获取映射关系
        :param db: 数据库会话
        :param product_model: 产品型号
        :param original_part_code: 原装部件编码
        :return: 映射关系
        """
        stmt = select(self.model).where(
            self.model.product_model == product_model,
            self.model.original_part_code == original_part_code,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


part_spare_mapping_dao: CRUDPartSpareMapping = CRUDPartSpareMapping(PartSpareMapping)
