#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：pc_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/5/20 17:19
"""
from typing import Sequence

from backend.app.datamanage.crud.crud_pc import pc_dao
from backend.database.db import async_db_session


class PCService:

    @staticmethod
    async def get_distinct_column_by_filter(target_column: str, filters: dict) -> Sequence[str]:
        async with async_db_session() as db:
            results = await pc_dao.get_distinct_column_values_multi(db, filters, target_column)
            return [item for item in results if item and item.strip()]


pc_service: PCService=PCService()