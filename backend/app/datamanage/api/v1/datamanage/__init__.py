#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：__init__.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/25 16:39
"""

from fastapi import APIRouter

from backend.app.datamanage.api.v1.datamanage.despatch import router as despatch_router
from backend.app.datamanage.api.v1.datamanage.ebom import router as ebom_router
from backend.app.datamanage.api.v1.datamanage.failure import router as failure_router
from backend.app.datamanage.api.v1.datamanage.product import router as product_router
from backend.app.datamanage.api.v1.datamanage.repair import router as repair_router
from backend.app.datamanage.api.v1.datamanage.replace import router as replace_router

router = APIRouter(prefix='/datamanage')

router.include_router(despatch_router, prefix='/despatch', tags=['发运数据'])
router.include_router(failure_router, prefix='/failure', tags=['故障数据'])
router.include_router(ebom_router, prefix='/ebom', tags=['ebom数据'])
router.include_router(product_router, prefix='/product', tags=['产品信息数据'])
router.include_router(repair_router, prefix='/repair', tags=['造修阶段数据'])
router.include_router(replace_router, prefix='/replace', tags=['必换件数据'])
