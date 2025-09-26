#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：assign_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/10 09:48
"""

import numpy as np
from typing import Any
from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.app.calcu.service.reliability_index_service import reliability_index_service
from backend.app.datamanage.crud.crud_lcc import lcc_dao

class AssignService:
    
    @staticmethod
    async def get_assign_result(
        items: list[dict],
        fpmh_user: float,
        yan_cost: float,
        shou_cost: float,
        lirun_ratio: float,
        reserved_value:float = 0.2, 
        )-> dict[str, Any]:
        '''
        可靠性经济型评估及分配: 1、判断是否满足用户要求、2、计算亏损订单数量阈值
        3、计算实现利润目标阈值、4、根据fpmh_result决定是否需要重新分配fpmh
        :param items: 列表,包含model和part
        :param fpmh_user: 用户要求的FPMH值
        :param yan_cost: 研发费
        :param shou_cost: 整机售价
        :param lirun_ratio: 利润率
        :param reserved_value: 预留值
        :return: dict[str, Any]
        '''
        # 1、判断是否满足用户要求
        fpmh = await AssignService.get_fpmh_by_part(items)
        fpmh_pre = sum(fpmh)
        fpmh_user = fpmh_user * (1 - reserved_value)
        fpmh_result = bool(fpmh_pre < fpmh_user)

        # 2、获取成本
        cm_gz_cost = await AssignService.get_cm_cost(items)
        gz_total = sum(cm_gz_cost['gz'])
        cm_total = sum(cm_gz_cost['cm'])

        # 2、计算亏损订单数量阈值
        n1 = int(yan_cost / shou_cost)

        # 3、计算实现利润目标阈值
        n2 = int(yan_cost / (shou_cost * (1 - lirun_ratio * 0.01) - gz_total - cm_total))
        
        # 4、根据fpmh_result决定是否需要重新分配fpmh
        assigned_fpmh = []
        if fpmh_result:
            # 如果已经满足条件，直接使用原始fpmh
            assigned_fpmh = fpmh
        else:
            # 如果不满足条件，根据限制条件重新分配fpmh
            assigned_fpmh = await AssignService.assign_fpmh(items, fpmh_user)
            # assigned_fpmh = await AssignService.assign_fpmh(fpmh, fpmh_user,fpmh_pre)
        
        # 5、构建详细的部件信息列表
        parts_detail = []
        for i, item in enumerate(items):
            model = item['model']
            part = item['part']         
            parts_detail.append({
                'model': model,
                'part': part,
                'part_name': cm_gz_cost['part_name'][i],
                'quantity': cm_gz_cost['quantity'][i],
                'fpmh': round(assigned_fpmh[i],4)
            })
        
        return {
            'fpmh_pre': round(fpmh_pre,4),
            'fpmh_result': fpmh_result,
            'n1': n1,
            'n2': n2,
            'parts_detail': parts_detail
        }
    
    @staticmethod
    async def get_fpmh_by_part(items: list[dict]) -> list[float]:
        # 计算FPMH值:pdf函数中(0,t)区间中的最大值
        fpmh=[]
        for item in items:
            model = item['model']
            part = item['part']
            best_distribution = await reliability_index_service._get_best_distribution(model, part)
            time = await reliability_index_service._get_t(model, part)
            x = np.linspace(0, time, 2000)
            y = best_distribution.PDF(x)
            f = np.max(y) * 1000000
            fpmh.append(f)
        return fpmh
    

    @staticmethod
    async def get_cm_cost(items: list[dict])-> dict[str, Any]:
        # 计算每一个部件的直接材料费和修复性维修费
        async with async_db_session() as db:
            fault_number_list = []
            cm_list=[]
            gz_list=[]
            part_name = []
            quantity = []
            for item in items:
                model = item['model']
                part = item['part']
                best_distribution = await reliability_index_service._get_best_distribution(model, part)
                time = await reliability_index_service._get_t(model, part)
                area = best_distribution.CDF(time) - best_distribution.CDF(0)
                ebom_data = await ebom_dao.get_by_model_and_part(db, model, part)
                quantity.append(len(ebom_data))
                part_name.append([item.y8_matname for item in ebom_data][0])
                cost = await lcc_dao.get_by_model_and_part(db, model, part)
                if cost is None:
                    raise errors.DataValidationError(msg=f'型号{model}+部件{part}没有成本数据')
                gz_list.append(float(cost))
                cm = float(cost) * area
                fault_number_list.append(area)
                cm_list.append(cm)
            return {
                'part_name': part_name,
                'quantity': quantity,
                'fault_number': fault_number_list,
                'cm': cm_list,
                'gz': gz_list
            }
    
    # @staticmethod
    # async def assign_fpmh(fpmh, fpmh_user,fpmh_pre) -> list[float]:
    #     """
    #     对每一个part的fpmh进行分配，满足两个限制条件：
    #     1. 计算得到的每个fpmh之和要小于fpmh_user
    #     2. 每一个fpmh要大于（y = best_distribution.PDF(x)）*100000的平均值
        
    #     :param fpmh: 初始的各部件fpmh列表
    #     :param fpmh_user: 用户要求的FPMH值
    #     :param fpmh_pre: 原始的fpmh总值
    #     :return: 分配后的每个部件的fpmh列表
    #     """
        
    #     # 计算原始的fpmh值
    #     original_fpmh = fpmh
    #     # 计算缩放因子
    #     scale_factor = fpmh_user / fpmh_pre
    #     # 计算缩放后的fpmh值
    #     final_fpmh = [fpmh * scale_factor for fpmh in original_fpmh]     
    #     return final_fpmh
            
    @staticmethod
    async def assign_fpmh(items: list[dict], fpmh_user: float) -> list[float]:
        """
        对每一个part的fpmh进行分配，满足两个限制条件：
        1. 计算得到的每个fpmh之和要小于fpmh_user
        2. 每一个fpmh要大于（y = best_distribution.PDF(x)）*100000的平均值
        
        :param items: 包含model和part的列表
        :param fpmh_user: 用户要求的FPMH值
        :return: 分配后的每个部件的fpmh列表
        """
        # 获取每个部件的PDF曲线和平均值
        pdf_avg_list = []
        for item in items:
            model = item['model']
            part = item['part']
            best_distribution = await reliability_index_service._get_best_distribution(model, part)
            time = await reliability_index_service._get_t(model, part)
            x = np.linspace(0, time, 2000)
            y = best_distribution.PDF(x)
            # 计算PDF平均值 * 1000000
            pdf_avg = np.mean(y) * 1000000
            pdf_avg_list.append(pdf_avg)
        
        # 计算原始的fpmh值
        # original_fpmh = await AssignService.get_fpmh_by_part(items)
        
        # 需要重新分配fpmh
        adjusted_fpmh = pdf_avg_list.copy()

        # 计算调整后的总和
        adjusted_total = sum(adjusted_fpmh)
        
        # 如果调整后的总和仍然超过用户要求，按比例缩减
        if adjusted_total > fpmh_user:
            # 计算缩减比例
            scale_factor = fpmh_user / adjusted_total

            # 按比例缩减每个部件的FPMH8
            final_fpmh = [fpmh * scale_factor for fpmh in adjusted_fpmh]
        else:
            final_fpmh = adjusted_fpmh
            
        return final_fpmh



assign_service: AssignService = AssignService()