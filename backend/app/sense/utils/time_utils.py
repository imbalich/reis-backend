#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：reis-backend 
@File    ：time_utils.py.py
@IDE     ：PyCharm 
@Author  ：imbalich
@Date    ：2025/4/25 10:14 
'''

from datetime import date, datetime
from typing import Union

from backend.common.exception.errors import DataValidationError


class DateUtils:

    @staticmethod
    def validate_and_parse_date(input_date: Union[str, date, None]) -> date:
        """
        验证并解析日期参数

        :param input_date: 输入日期，可以是 'YYYY-MM-DD' 格式的字符串、date 对象或 None
        :return: 解析后的 date 对象
        :raises DataValidationError: 当日期格式不正确或类型不匹配时
        """
        if input_date is None or input_date == '':
            return None
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