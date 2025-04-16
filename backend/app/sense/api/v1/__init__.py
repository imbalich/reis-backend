#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : __init__.py.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/26 15:06
'''
from fastapi import APIRouter

from backend.app.sense.api.v1.sense import router as sense_router

router = APIRouter(prefix="/sense")

router.include_router(sense_router, tags=["产品级曲线拟合"])