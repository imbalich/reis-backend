#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：router.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/01/XX XX:XX
@Desc    : RCM模块路由配置
"""

from fastapi import APIRouter

from backend.app.rcm.api.v1.rcm import router as rcm_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(rcm_router)
