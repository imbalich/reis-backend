#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : fastapi-base-backend
@File    : crud_ebom.py
"""

from typing import Any

from sqlalchemy import Select, Sequence, and_, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model import Ebom


class CRUDEbom(CRUDPlus[Ebom]):
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

    async def get_root_list(
        self,
        level1: int = 0,
        prd_no: str = None,
        product_config_code: str | None = None,
    ) -> Select:
        stmt = select(self.model).where(
            and_(self.model.level1 == level1, self.model.state_now == 1)
        )
        where_list = []
        if prd_no:
            where_list.append(self.model.prd_no == prd_no)
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        if where_list:
            stmt = stmt.where(*where_list)
        return stmt

    async def get_node_list(
        self,
        level1: int = 1,
        partid: str = None,
    ) -> Select:
        stmt = select(self.model).where(
            and_(
                self.model.partid == partid,
                self.model.level1 == level1,
                self.model.state_now == 1,
            )
        )
        return stmt

    async def get_by_model(
        self,
        model: str,
        product_config_code: str | None = None,
    ) -> Select:
        stmt = select(self.model)
        where_list = [self.model.prd_no == model]
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        stmt = stmt.where(*where_list)
        return stmt

    async def get_by_model_and_part(
        self,
        db: AsyncSession,
        model: str,
        product_config_code: str | None = None,
        part: str | None = None,
    ) -> Sequence[Ebom]:
        stmt = select(self.model)
        where_list = [
            self.model.prd_no == model,
            self.model.y8_matbnum1 == part,
            self.model.state_now == 1,
        ]
        if product_config_code is not None:
            where_list.append(self.model.product_config_code == product_config_code)
        stmt = stmt.where(*where_list)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, id: str) -> Ebom | None:
        stmt = select(self.model).where(
            self.model.id == id,
            self.model.state_now == 1,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


ebom_dao: CRUDEbom = CRUDEbom(Ebom)
