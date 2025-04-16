#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：router.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2024/12/27 15:46 
'''
from fastapi import APIRouter

from backend.app.datamanage.api.v1.datamanage import router as despatch_router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(despatch_router)
