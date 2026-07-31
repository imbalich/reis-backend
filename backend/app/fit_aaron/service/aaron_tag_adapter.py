#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Any

import pandas as pd


# Aaron于2026-07-17新增：Aaron数据处理结果到后端拟合tags的适配层
# 新增原因：main_new.py输出的是data_result表，客户后端Fit_Everything入口使用的是tags列表
# 新增作用：只负责字段格式转换，不参与原始数据查询，也不修改威布尔拟合算法

def data_result_to_tags(data_result: pd.DataFrame) -> list[list[Any]]:
    """
    将 Aaron 数据处理结果转换为客户后端 Weibull 拟合所需的 tags。

    data_result 来源：
    - 非必换件：process_fault_data_rowwise1(...)
    - 必换件：process_fault_data_rowwise_replace(...)

    tag_fit(tags) 实际只使用每条 tag 的最后两列：
    - item[-2]：运行时间
    - item[-1]：状态，failure 或 suspense
    """
    tags: list[list[Any]] = []

    if data_result is None or data_result.empty:
        return tags

    for _, row in data_result.iterrows():
        fault_time = row.get('fault_time_1')
        state = row.get('state_1')

        # Aaron于2026-07-17更改：统一本地算法与客户后端的删失状态命名
        # 更改原因：本地输出为suspension，客户后端tag_fit识别的是suspense
        if state == 'suspension':
            state = 'suspense'

        # Aaron于2026-07-17新增：过滤无效寿命样本
        # 新增原因：Fit_Everything不能接收None、空值、0或负运行时间
        if pd.isna(fault_time) or fault_time <= 0:
            continue

        if state not in {'failure', 'suspense'}:
            continue

        tags.append(
            [
                row.get('identifier'),
                row.get('identifier_index'),
                row.get('life_cycle_time'),
                row.get('fault_1'),
                row.get('fault_day_1'),
                fault_time,
                state,
            ]
        )

    return tags
