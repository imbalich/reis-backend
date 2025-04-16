#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@Project : fastapi-base-backend
@File    : time_utils.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/2/24 下午5:21
'''
from datetime import date, datetime
from typing import Union

from backend.common.exception.errors import DataValidationError


class DateUtils:

    @staticmethod
    def run_time(diff: int, day: int, hour: int) -> float:
        """
        计算运行时间

        :param diff: 时间差（单位：天）
        :param day: 天数
        :param hour: 小时数
        :return: 计算后的运行时间（单位：小时）
        """
        if diff <= 0:
            t = 15
        else:
            t = diff * day * hour / 365
        return round(t, 2)

    @staticmethod
    def validate_and_parse_date(input_date: Union[str, date, None]) -> date:
        """
        验证并解析日期参数

        :param input_date: 输入日期，可以是 'YYYY-MM-DD' 格式的字符串、date 对象或 None
        :return: 解析后的 date 对象
        :raises DataValidationError: 当日期格式不正确或类型不匹配时
        """
        if input_date is None or input_date == '':
            return date.today()
        elif isinstance(input_date, str):
            try:
                return datetime.strptime(input_date, '%Y-%m-%d').date()
            except ValueError:
                raise DataValidationError(msg="input_date 格式错误,必须是 'YYYY-MM-DD' 格式的字符串")
        elif isinstance(input_date, date):
            return input_date.today()
        else:
            raise DataValidationError(msg="input_date 必须是字符串或 date 对象")


dateutils: DateUtils = DateUtils()
