#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from backend.app.forecast.schema.forecast_param import PartForecastParam
from backend.app.forecast.service.part_forecast_service import part_forecast_service
from backend.common.response.response_schema import response_base

router = APIRouter()


@router.post("", summary="零部件预测：按已有标签和拟合分布计算未来窗口期望故障次数")
async def forecast_part(obj: PartForecastParam):
    data = await part_forecast_service.forecast(obj)
    return response_base.success(data=data)
