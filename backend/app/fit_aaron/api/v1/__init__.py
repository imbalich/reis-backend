#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from fastapi import APIRouter

from backend.app.fit_aaron.api.v1.fit_part import router as part_router
from backend.app.fit_aaron.api.v1.fit_product import router as product_router

router = APIRouter(prefix="/fit-aaron")

router.include_router(product_router, prefix="/product", tags=["???????-Aaron"])
router.include_router(part_router, prefix="/part", tags=["???????-Aaron"])
