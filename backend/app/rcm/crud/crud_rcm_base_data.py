#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : crud_rcm_base_data.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : RCM基础数据CRUD操作
"""

from typing import List, Sequence, Any

from sqlalchemy import Select, delete, select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.rcm.model.rcm_base_data import RcmBaseData


class CRUDRcmBaseData(CRUDPlus[RcmBaseData]):
    """RCM基础数据库操作类"""

    async def get_select(
        self,
        product_model: str | None = None,
        component_name: str | None = None,
        component_material_code: str | None = None,
        failure_mode: str | None = None,
        is_key_component: bool | None = None,
        is_consumable_part: bool | None = None,
    ) -> Select:
        """
        获取RCM基础数据查询语句

        :param product_model: 产品型号
        :param component_name: 部件名称
        :param component_material_code: 零部件物料编码
        :param failure_mode: 故障模式
        :param is_key_component: 是否关键部件
        :param is_consumable_part: 是否耗损型部件
        :return: 查询语句
        """
        query = select(self.model)

        if product_model:
            query = query.where(self.model.product_model.like(f"%{product_model}%"))
        if component_name:
            query = query.where(self.model.component_name.like(f"%{component_name}%"))
        if component_material_code:
            query = query.where(
                self.model.component_material_code.like(f"%{component_material_code}%")
            )
        if failure_mode:
            query = query.where(self.model.failure_mode.like(f"%{failure_mode}%"))
        if is_key_component is not None:
            query = query.where(self.model.is_key_component == is_key_component)
        if is_consumable_part is not None:
            query = query.where(self.model.is_consumable_part == is_consumable_part)

        return query

    async def clear_all(self, db: AsyncSession) -> None:
        """
        清空所有RCM基础数据

        :param db: 数据库会话
        """
        await db.execute(delete(RcmBaseData))
        await db.execute(text("ALTER TABLE rcm_base_data AUTO_INCREMENT = 1"))
        await db.commit()

    async def bulk_create(
        self, db: AsyncSession, rcm_data: List[dict[str, Any]]
    ) -> List[RcmBaseData]:
        """
        批量创建RCM基础数据

        :param db: 数据库会话
        :param rcm_data: RCM基础数据列表
        :return: 创建的RCM基础数据列表
        """
        rcm_records = [RcmBaseData(**data) for data in rcm_data]
        db.add_all(rcm_records)
        await db.commit()
        for record in rcm_records:
            await db.refresh(record)
        return rcm_records

    async def get_product_models(self, db: AsyncSession) -> Sequence[str]:
        """
        获取所有产品型号

        :param db: 数据库会话
        :return: 产品型号列表
        """
        stmt = select(self.model.product_model).distinct()
        result = await db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def get_component_names_by_model(
        self, db: AsyncSession, product_model: str
    ) -> Sequence[str]:
        """
        根据产品型号获取部件名称列表

        :param db: 数据库会话
        :param product_model: 产品型号
        :return: 部件名称列表
        """
        stmt = (
            select(self.model.component_name)
            .where(self.model.product_model == product_model)
            .distinct()
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def get_failure_modes_by_model(
        self, db: AsyncSession, product_model: str
    ) -> Sequence[str]:
        """
        根据产品型号获取故障模式列表

        :param db: 数据库会话
        :param product_model: 产品型号
        :return: 故障模式列表
        """
        stmt = (
            select(self.model.failure_mode)
            .where(self.model.product_model == product_model)
            .distinct()
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.fetchall()]


rcm_base_data_dao: CRUDRcmBaseData = CRUDRcmBaseData(RcmBaseData)
