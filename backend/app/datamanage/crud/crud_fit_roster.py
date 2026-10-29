#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model.fit_roster import FitRoster


class CRUDFitRoster(CRUDPlus[FitRoster]):
    """寿命拟合名单。"""

    async def get_select(
        self,
        product_model: str | None = None,
        product_config_code: str | None = None,
        part_code: str | None = None,
        part_name: str | None = None,
        family: str | None = None,
    ) -> Select:
        query = select(self.model).order_by(
            self.model.product_model,
            self.model.product_config_code,
            self.model.part_code,
        )
        if product_model:
            query = query.where(self.model.product_model.like(f"%{product_model}%"))
        if product_config_code:
            query = query.where(self.model.product_config_code == product_config_code)
        if part_code:
            query = query.where(self.model.part_code.like(f"%{part_code}%"))
        if part_name:
            query = query.where(self.model.part_name.like(f"%{part_name}%"))
        if family:
            query = query.where(self.model.family == family)
        return query

    async def get_all(self, db: AsyncSession) -> list[FitRoster]:
        result = await db.execute(
            select(self.model).order_by(
                self.model.product_model,
                self.model.product_config_code,
                self.model.part_code,
            )
        )
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, pk: int) -> FitRoster | None:
        return await self.select_model(db, pk)

    async def get_by_key(
        self,
        db: AsyncSession,
        product_model: str,
        product_config_code: str,
        part_code: str,
    ) -> FitRoster | None:
        stmt = select(self.model).where(
            self.model.product_model == product_model,
            self.model.product_config_code == product_config_code,
            self.model.part_code == part_code,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> FitRoster:
        row = FitRoster(**data)
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row

    async def update_fields(self, db: AsyncSession, row: FitRoster, data: dict) -> FitRoster:
        for key, value in data.items():
            setattr(row, key, value)
        await db.commit()
        await db.refresh(row)
        return row

    async def delete_ids(self, db: AsyncSession, ids: list[int]) -> int:
        if not ids:
            return 0
        rows = (
            await db.execute(select(self.model).where(self.model.id.in_(ids)))
        ).scalars().all()
        count = len(rows)
        for row in rows:
            await db.delete(row)
        await db.commit()
        return count

    async def replace_all(self, db: AsyncSession, rows: list[dict]) -> None:
        """按文件内容更换整张名单。同一事务内完成增删改。"""
        current = await self.get_all(db)
        current_by_key = {
            (row.product_model, row.product_config_code, row.part_code): row
            for row in current
        }
        incoming_keys = set()
        for data in rows:
            key = (data["product_model"], data["product_config_code"], data["part_code"])
            incoming_keys.add(key)
            existing = current_by_key.get(key)
            if existing is None:
                db.add(FitRoster(**data))
                continue
            existing.part_name = data["part_name"]
            existing.family = data["family"]
            if data.get("created_by"):
                existing.created_by = data["created_by"]
        for key, existing in current_by_key.items():
            if key not in incoming_keys:
                await db.delete(existing)
        await db.commit()


fit_roster_dao: CRUDFitRoster = CRUDFitRoster(FitRoster)
