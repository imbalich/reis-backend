#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：router.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2025/1/6 14:33
"""

from fastapi import APIRouter

from backend.app.fit.api.v1 import router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(router)
