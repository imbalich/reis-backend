#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from fastapi import APIRouter

from backend.app.fit_aaron.api.v1 import router
from backend.core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(router)
