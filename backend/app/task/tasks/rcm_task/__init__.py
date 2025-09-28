#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RCM计算任务模块
"""

from backend.app.task.tasks.rcm_task.tasks import (
    rcm_batch_calculation_task,
)

__all__ = [
    "rcm_batch_calculation_task",
]
