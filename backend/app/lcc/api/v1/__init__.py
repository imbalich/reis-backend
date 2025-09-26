#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：__init__.py.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/2 14:54
"""
from fastapi import APIRouter

from backend.app.lcc.api.v1.cycle_life import router as cycle_life_router
from backend.app.lcc.api.v1.assign import router as assign_router

router = APIRouter(prefix='/lcc')

router.include_router(cycle_life_router, prefix='/cycle_life', tags=['可靠性经济性指标分配'])
router.include_router(assign_router, prefix='/assign', tags=['全寿命周期可靠性经济性评估'])