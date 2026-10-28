#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from backend.app.forecast.schema.forecast_param import PartForecastParam, PartForecastResult


class PartForecastService:
    """打标和拟合之后的预测。不读取库房、备品和配属。"""

    async def forecast(self, obj: PartForecastParam) -> PartForecastResult:
        """
        计算一个零部件在窗口内的期望故障次数。

        后续实现顺序：
        1. 读取截止日期之前的标签，得到每个零件位置的寿命起点。
        2. 读取该截止日期已经拟合好的分布。
        3. 只保留窗口开始日已经在役的位置。
        4. 每个位置用 F(当前年龄 + 窗口运行小时) - F(当前年龄) 累加。
        """
        raise NotImplementedError("零部件预测尚未实现")


part_forecast_service = PartForecastService()
