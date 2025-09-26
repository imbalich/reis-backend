#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fastapi import APIRouter

from backend.app.calcu.api.v1.calcu.science_warehouse import (
    router as science_warehouse_router,
)

router = APIRouter(prefix="/calcu")

router.include_router(
    science_warehouse_router, prefix="/science-warehouse", tags=["科学库存计算"]
)
