#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : __init__.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : RCM业务API模块初始化
"""

from fastapi import APIRouter

from backend.app.rcm.api.v1.rcm.rcm_base_data import router as rcm_base_data_router
from backend.app.rcm.api.v1.rcm.rcm_calculation import router as rcm_calculation_router

router = APIRouter(prefix="/rcm")

router.include_router(rcm_base_data_router, prefix="/base-data", tags=["RCM基础数据"])

router.include_router(rcm_calculation_router, prefix="/calculation", tags=["RCM计算"])
