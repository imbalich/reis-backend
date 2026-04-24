#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any, List, Sequence

from sqlalchemy import Select, delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.datamanage.model.part_spare_mapping import PartSpareMapping


class CRUDPartSpareMapping(CRUDPlus[PartSpareMapping]):
    """CRUD for part/spare mapping records."""

    async def get_select(
        self,
        product_model: str | None = None,
        derived_code: str | None = None,
        original_part_name: str | None = None,
        original_part_code: str | None = None,
        spare_part_name: str | None = None,
        spare_part_code: str | None = None,
    ) -> Select:
        """Build a filtered select statement for mapping lookup."""
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
        """Clear all mapping rows."""
        await db.execute(delete(PartSpareMapping))
        await db.execute(text("ALTER TABLE dm_part_spare_mapping AUTO_INCREMENT = 1"))
        await db.commit()

    async def bulk_create(
        self, db: AsyncSession, mapping_data: List[dict[str, Any]]
    ) -> List[PartSpareMapping]:
        """Create mapping rows in bulk."""
        mappings = [PartSpareMapping(**data) for data in mapping_data]
        db.add_all(mappings)
        await db.commit()
        for mapping in mappings:
            await db.refresh(mapping)
        return mappings

    async def get_by_spare_part_code(
        self, db: AsyncSession, spare_part_code: str
    ) -> Sequence[PartSpareMapping]:
        """Get mappings by spare part code."""
        stmt = select(self.model).where(self.model.spare_part_code == spare_part_code)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_original_part_code(
        self,
        db: AsyncSession,
        product_model: str,
        product_config_code: str,
        original_part_code: str,
    ) -> PartSpareMapping:
        """Get a mapping by product model, product config code, and original part code."""
        stmt = select(self.model).where(
            self.model.product_model == product_model,
            self.model.product_config_code == product_config_code,
            self.model.original_part_code == original_part_code,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


part_spare_mapping_dao: CRUDPartSpareMapping = CRUDPartSpareMapping(PartSpareMapping)
