#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : reis-backend
@File    : __init__.py.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/4/22 14:49
'''
from fastapi import APIRouter

from backend.app.calcu.api.v1.reliability_index.normal import router as normal_router

router = APIRouter(prefix='/reliability-index')

router.include_router(normal_router, prefix='/normal', tags=['可靠性指标'])