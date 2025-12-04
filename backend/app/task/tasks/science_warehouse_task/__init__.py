#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
科学库存计算任务模块
"""

from backend.app.task.tasks.science_warehouse_task.tasks import (
    science_warehouse_calculation_task,
    science_warehouse_calculation_and_api_task,
    science_warehouse_calculation_v2_task,
)

__all__ = [
    "science_warehouse_calculation_task",
    "science_warehouse_calculation_and_api_task",
    "science_warehouse_calculation_v2_task",
]
