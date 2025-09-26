#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：router.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/15 14:02
"""
from fastapi import APIRouter

from backend.app.lifetime.api.v1 import router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(router)