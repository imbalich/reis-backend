#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：fastapi-base-backend 
@File    ：format_format_utils.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/3/31 17:39 
'''

import re
from typing import Any, Dict, List


def standard_data(s: str) -> str:
    """处理字符串：大写、去空格、去括号内容"""
    if not s:
        return s
    # 转大写、去空格
    s = s.upper().replace(' ', '')
    # 去除括号及内容（支持中英文括号）
    s = re.sub(r'[$\（].*?[$\）]', '', s)
    return s

def split_rela_self_value(value: str) -> List[str]:
    """根据公共分隔符将rela_self_value拆分为多个部分"""
    if not value:
        return []
    # Split by comma, space, semicolon, or other common delimiters
    parts = re.split(r'[,\s;，；/]+', value.strip())
    return [p.strip() for p in parts if p.strip()]

def split_part_into_sub_values(part: str) -> List[str]:
    """使用“/”、“-”或空格进一步拆分为子值。"""
    if not part:
        return []
    sub_parts = re.split(r'[/\ ]+', part.strip())
    return [p.strip() for p in sub_parts if p.strip()]

def convert_time_to_minutes(time_str: str) -> int:
    """将时间字符串“HH:MM”转换为总分钟数。."""
    try:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    except ValueError:
        return 0

def process_sub_value(sub_val: str) -> str:
    """将子值处理为所需的格式."""
    if re.match(r'^\d{1,2}:\d{2}-\d{1,2}:\d{2}$', sub_val):
        start_str, end_str = sub_val.split('-')
        start = convert_time_to_minutes(start_str)
        end = convert_time_to_minutes(end_str)
        if start >= 480 and end <= 1200:
            return '1'
        else:
            return '2'
    elif re.match(r'^\d{1,2}:\d{2}$', sub_val):
        time_min = convert_time_to_minutes(sub_val)
        if 480 <= time_min <= 1200:
            return '1'
        else:
            return '2'
    elif re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$', sub_val):
        time_part = sub_val.split(' ')[1]
        time_min = convert_time_to_minutes(time_part)
        if 480 <= time_min <= 1200:
            return '1'
        else:
            return '2'
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', sub_val):
        return '无'
    else:
        numbers = re.findall(r'-?\d+\.?\d*', sub_val)
        return numbers[0] if numbers else sub_val