#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：__init__.py.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/15 14:02
"""
from fastapi import APIRouter

from backend.app.lifetime.api.v1.equal_lifetime import router as euqal_lifetime_router

router = APIRouter(prefix='/lifetime')

router.include_router(euqal_lifetime_router, prefix='/equal_lifetime', tags=['等寿命设计'])