#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : __init__.py.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/28 14:30
'''
from fastapi import APIRouter

from backend.app.predict.api.v1.predict_part import router as part_router
from backend.app.predict.api.v1.predict_product import router as product_router

router = APIRouter(prefix="/predict")

router.include_router(product_router, prefix="/product", tags=["产品级预测"])
router.include_router(part_router, prefix="/part", tags=["部件级预测"])