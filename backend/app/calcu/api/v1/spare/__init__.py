#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : reis-backend
@File    : __init__.py.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/4/22 14:20
'''
from fastapi import APIRouter

from backend.app.calcu.api.v1.spare.predict_part import router as part_router
from backend.app.calcu.api.v1.spare.predict_product import router as product_router

router = APIRouter(prefix='/spare')

router.include_router(product_router, prefix='/product', tags=['产品级备件量预测'])
router.include_router(part_router, prefix='/part', tags=['部件级备件量预测'])