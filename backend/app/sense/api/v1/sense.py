#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : sense.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/26 15:08
'''
from fastapi import APIRouter

from backend.common.response.response_schema import response_base

router = APIRouter()


@router.post("/analysis", summary="敏感度分析数据分析")
async def sense_analysis():
    data = {}
    return response_base.success(data=data)