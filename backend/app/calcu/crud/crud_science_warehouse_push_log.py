#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.calcu.model.science_warehouse_push_log import (
    ScienceWarehousePushLog,
)


class CRUDScienceWarehousePushLog(CRUDPlus[ScienceWarehousePushLog]):
    """科学库存推送日志数据库操作类。"""

    async def create_log(
        self, db: AsyncSession, data: dict[str, Any]
    ) -> ScienceWarehousePushLog:
        """创建推送日志。"""
        log = ScienceWarehousePushLog(**data)
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    async def update_log(
        self,
        db: AsyncSession,
        log: ScienceWarehousePushLog,
        data: dict[str, Any],
    ) -> ScienceWarehousePushLog:
        """更新推送日志。"""
        for key, value in data.items():
            setattr(log, key, value)
        await db.commit()
        await db.refresh(log)
        return log


science_warehouse_push_log_dao: CRUDScienceWarehousePushLog = (
    CRUDScienceWarehousePushLog(ScienceWarehousePushLog)
)
