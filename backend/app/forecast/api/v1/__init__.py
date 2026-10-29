#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from backend.app.forecast.api.v1.part import router as part_router

router = APIRouter(prefix="/forecast")

router.include_router(part_router, prefix="/part", tags=["零部件预测"])
