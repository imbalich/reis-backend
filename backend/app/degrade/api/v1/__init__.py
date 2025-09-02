#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：__init__.py.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/20 18:05
"""
from fastapi import APIRouter

from backend.app.degrade.api.v1.degrade_product import router as degrade_product_router

router = APIRouter(prefix='/degrade')

router.include_router(degrade_product_router, prefix='/product', tags=['产品级参数退化评估'])