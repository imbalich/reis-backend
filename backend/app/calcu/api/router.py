#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : router.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/28 14:31
"""

from fastapi import APIRouter

from backend.app.calcu.api.v1.reliability_index import router as ri_router
from backend.app.calcu.api.v1.spare import router as spare_router
from backend.app.calcu.api.v1.opt import router as opt_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(spare_router)
v1.include_router(ri_router)
v1.include_router(opt_router)