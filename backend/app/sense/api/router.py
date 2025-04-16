#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : router.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/26 15:06
"""

from fastapi import APIRouter

from backend.app.sense.api.v1 import router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(router)
