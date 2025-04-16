#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：__init__.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/1/6 14:33 
'''
from fastapi import APIRouter

from backend.app.fit.api.v1.fit_part import router as part_router
from backend.app.fit.api.v1.fit_product import router as product_router

router = APIRouter(prefix="/fit")

router.include_router(product_router, prefix="/product", tags=["产品级曲线拟合"])
router.include_router(part_router, prefix="/part", tags=["部件级曲线拟合"])