#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : fastapi-base-backend
@File    : crud_repair.py
"""

from typing import Any

from sqlalchemy import Select, Sequence, asc, desc, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Repair


class CRUDRepair(CRUDPlus[Repair]):
    async def get_distinct_column_values(
        self, db: AsyncSession, column_name: str
    ) -> Sequence[Any]:
        if not hasattr(self.model, column_name):
            raise ValueError(
                f"Column {column_name} does not exist in model {self.model.__name__}"
            )

        column = getattr(self.model, column_name)
        stmt = select(distinct(column)).order_by(column)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_list(
        self,
        model: str = None,
        product_config_code: str | None = None,
        state_now: bool = None,
    ) -> Select:
        stmt = select(self.model).order_by(desc(self.model.model))
        where_list = []
        if model is not None:
            where_list.append(self.model.model == model)
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        if state_now is not None:
            where_list.append(self.model.state_now == state_now)
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model(
        self,
        db: AsyncSession,
        model: str,
        product_config_code: str | None = None,
    ) -> Sequence[Repair]:
        stmt = select(self.model).order_by(desc(self.model.id_repair))
        where_list = [
            self.model.model == model,
            self.model.state_now == 1,
        ]
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        stmt = stmt.where(*where_list)
        results = await db.execute(stmt)
        return results.scalars().all()

    async def get_repair_levels_by_model(
        self,
        db: AsyncSession,
        model: str,
        product_config_code: str | None = None,
    ) -> Sequence[Repair]:
        stmt = select(self.model.repair_levels).order_by(asc(self.model.id_repair))
        where_list = [
            self.model.model == model,
            self.model.state_now == 1,
            self.model.repair_levels != "新造",
        ]
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        stmt = stmt.where(*where_list)
        results = await db.execute(stmt)
        return results.scalars().all()


repair_dao: CRUDRepair = CRUDRepair(Repair)
