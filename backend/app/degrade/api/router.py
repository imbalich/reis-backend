#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：router.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/8/20 18:06
"""
from fastapi import APIRouter

from backend.app.degrade.api.v1 import router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(router)