#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : reis-backend
@File    : __init__.py.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/5/8 15:41
'''
from fastapi import APIRouter

from backend.app.calcu.api.v1.opt.opt_part import router as part_router

router = APIRouter(prefix='/opt')

router.include_router(part_router, prefix='/part', tags=['部件最佳维护周期'])