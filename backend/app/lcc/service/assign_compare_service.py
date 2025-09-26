#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：assign_compare_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/10 09:48
"""

from typing import Any
from backend.database.db import async_db_session
from backend.app.lcc.service.assign_service import assign_service

class AssignCompareService:
    @staticmethod
    async def get_assign_compare(
        items1: list[dict],
        items2: list[dict],
        fpmh_user: float,
        yan_cost: float,
        shou_cost: float,
        lirun_ratio: float,
        order:int,
        reserved_value:float = 0.2, 
        )-> dict[str, Any]:
        '''
        获取两个方案之间的对比结果
        参数：
        :param items1: 方案1的数据,['产品型号','零部件编码']
        :param items2: 方案2的数据,['产品型号','零部件编码']
        :param fpmh_user: 用户要求的FPMH值
        :param yan_cost: 研发费
        :param shou_cost: 整机售价
        :param lirun_ratio: 利润率
        :param reserved_value: 预留值
        :return: dict[str, Any]
        '''

        # 存储两个方案的结果
        results = []
        items_list = [items1, items2]
        lcc_companies = []
        
        # 循环处理两个方案
        for i, items in enumerate(items_list):
            # 1、判断是否满足用户要求
            fpmh = await assign_service.get_fpmh_by_part(items)
            fpmh_pre = sum(fpmh) * (1 + reserved_value)
            fpmh_result = bool(fpmh_pre < fpmh_user)

            # 2、获取成本计算lcc全寿命周期成本费
            cm_gz_cost = await assign_service.get_cm_cost(items)
            gz_total = sum(cm_gz_cost['gz'])
            cm_total = sum(cm_gz_cost['cm'])
            lcc_company = int(yan_cost + (gz_total + cm_total + shou_cost) * order)
            
            # 4、根据fpmh_result决定是否需要重新分配fpmh
            assigned_fpmh = []
            if fpmh_result:
                # 如果已经满足条件，直接使用原始fpmh
                assigned_fpmh = fpmh
            else:
                # 如果不满足条件，根据限制条件重新分配fpmh
                assigned_fpmh = await assign_service.assign_fpmh(items, fpmh_user)
            
            # 5、构建详细的部件信息列表
            parts_detail = []
            for j, item in enumerate(items):
                model = item['model']
                part = item['part']
                # 获取部件名称和数量
                part_name = cm_gz_cost['part_name'][j] if 'part_name' in cm_gz_cost and j < len(cm_gz_cost['part_name']) else part
                quantity = cm_gz_cost['quantity'][j] if 'quantity' in cm_gz_cost and j < len(cm_gz_cost['quantity']) else 1
                
                parts_detail.append({
                    'model': model,
                    'part': part,
                    'part_name': part_name,
                    'quantity': quantity,
                    'fpmh': round(assigned_fpmh[j], 4)
                })
            
            # 存储结果
            lcc_companies.append(lcc_company)
            results.append({
                'plan': i+1,
                'fpmh_pre': round(fpmh_pre, 4),
                'fpmh_result': fpmh_result,
                'lcc_company': lcc_company,
                'parts_detail': parts_detail
            })
        
        # lcc公司评估计算，以最小值为基准，计算比例
        min_lcc_company = min(lcc_companies)
        for i, result in enumerate(results):
            result['lcc_ratio'] = round(result['lcc_company'] / min_lcc_company, 4)
        
        # 根据lcc公司评估结果排序
        sorted_results = sorted(results, key=lambda x: x['lcc_ratio'])
        for i, sorted_result in enumerate(sorted_results):
            for result in results:
                if result is sorted_result: 
                    result['sort'] = i + 1 

        return results
        

assign_compare_service: AssignCompareService = AssignCompareService()