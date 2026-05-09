#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : fastapi-base-backend
@File    : crud_despatch.py
"""

from typing import Any, Sequence

from sqlalchemy import Select, asc, desc, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Despatch


class CRUDDespatch(CRUDPlus[Despatch]):
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
        product_config_code: str = None,
        identifier: str = None,
        repair_level: str = None,
        time_range: list[str] = None,
    ) -> Select:
        stmt = select(self.model).order_by(desc(self.model.model))
        where_list = []
        if model:
            where_list.append(self.model.model == model)
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        if identifier is not None:
            where_list.append(self.model.identifier == identifier)
        if repair_level is not None:
            where_list.append(self.model.repair_level == repair_level)
        if time_range:
            where_list.append(
                self.model.life_cycle_time.between(time_range[0], time_range[1])
            )
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model(
        self,
        db: AsyncSession,
        model: str,
        product_config_code: str | None = None,
    ) -> Despatch:
        filters = {"model": model}
        if product_config_code is not None:
            filters["product_config_code"] = product_config_code
        return await self.select_model_by_column(db, **filters)

    async def get_despatchs_by_model(
        self,
        db: AsyncSession,
        model: str,
        product_config_code: str | None = None,
    ) -> Sequence[Despatch]:
        stmt = select(self.model)
        where_list = [
            self.model.model == model,
            self.model.repair_level == "新造",
            ~self.model.identifier.like("0000%"),
        ]
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        stmt = stmt.where(*where_list)
        results = await db.execute(stmt)
        return results.scalars().all()

    async def get_by_model_exclude_repair_level(
        self,
        db: AsyncSession,
        model: str,
        product_config_code: str | None = None,
    ) -> Sequence[Despatch]:
        exclude_repair_level = ["新造", "故障修"]

        stmt = select(self.model).order_by(asc(self.model.life_cycle_time))
        where_list = [
            self.model.model == model,
            self.model.repair_level.notin_(exclude_repair_level),
            ~self.model.identifier.like("0000%"),
        ]
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        stmt = stmt.where(*where_list)
        results = await db.execute(stmt)
        return results.scalars().all()

    async def get_models_by_despatch(self, db: AsyncSession) -> Sequence[str]:
        stmt = select(distinct(self.model.model)).order_by(self.model.model)
        stmt = stmt.where(self.model.repair_level == "新造")
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_life_cycle_time_by_model(
        self,
        db: AsyncSession,
        model: str,
        product_config_code: str | None = None,
    ) -> list:
        stmt = select(self.model.life_cycle_time)
        where_list = [
            self.model.model == model,
            self.model.repair_level == "新造",
        ]
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()


despatch_dao: CRUDDespatch = CRUDDespatch(Despatch)
