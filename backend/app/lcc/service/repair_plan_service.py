#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：repair_plan_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/10/10 14:09
"""
from typing import Any
import numpy as np
from backend.app.lcc.service.cycle_life_service import cycle_life_service
from backend.database.db import async_db_session
from backend.app.datamanage.crud.crud_repair_interval import repair_interval_dao
from backend.common.exception import errors
from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.common.exception.errors import DataValidationError
from backend.app.datamanage.crud.crud_lcc import lcc_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_unqualify import unqualify_dao
from backend.app.calcu.service.reliability_index_service import reliability_index_service
from backend.app.datamanage.crud.crud_reliability_index import reliability_index_dao

class RepirPlanService:

    @staticmethod
    async def get_repair_plan(model: str, parts: list[str],life, is_ai: bool) -> dict[str, Any]:
        """
        获取修复计划
        :param model: 产品型号
        :param life: 产品生命周期
        :return:
        """
        async with async_db_session() as db:
            # 获取检修级别和时间间隔（年）
            repair_data = await repair_interval_dao.get_repair_levels_by_model(db, model)
            if not repair_data:
                raise errors.DataValidationError(msg=f"型号{model}的修程间隔信息不存在")
            repair_levels = [repair.repair_levels for repair in repair_data]
            repair_years = [repair.repair_years for repair in repair_data]

            # 获取首轮修检修级别，用于循环
            selected_fields = [field for field in repair_levels if field.startswith('C') or '首轮' in field]
            selected_indices = [index for index, field in enumerate(repair_levels) if field.startswith('C') or '首轮' in field]
            
            # 计算更换次数
            replace_number = await RepirPlanService.get_level_repair_number(repair_years,life)
            year_worktimes = await cycle_life_service.year_worktimes(model)
            time = year_worktimes*life
            result = []
            lcc_old_sum = 0
            lcc_new_sum = 0

            #循环每个部件
            for part in parts:
                # 获取每个部件的预计值fpmh，用于比较
                fpmh_index = await RepirPlanService.get_fpmh_index_by_part(model, part)
                mtbf_index = 1000000/fpmh_index
                
                # 计算在线修LCC
                fault = await RepirPlanService.get_online_repair_cost(model, part, time)
                lcc_online = fault['lcc_online']
                fpmh = []
                fpmh.append(fault['fpmh'])
                part_name = fault['part_name']
                # ai = fault['ai']

                # 等级修LCC
                replace_data = await RepirPlanService.get_replace_data(model, part)
                if replace_data:
                    level_old = replace_data[0].replace_level
                    year_old = replace_data[0].replace_cycle
                    level_index = selected_fields.index(level_old)
                else:
                    level_old = '偶换'
                    year_old = life
                    level_index = 0

                # 获取该部件的EBOM数量和成本之积，用于计算等级修lcc
                ebom_cost = await RepirPlanService.get_ebom_number_and_cost(model, part)

                # 计算每个阶段总的lcc
                ## 偶换的总lcc
                lcc = []
                level = ['偶换']
                year = [life]
                Pi = await RepirPlanService.get_pi(model, part, repair_levels)
                lcc_total = lcc_online
                for i in range(len(Pi)):
                    lcc_total += Pi[i] * replace_number[i] * float(ebom_cost)


                if is_ai == False:
                    lcc.append(lcc_total if fault['fpmh'] < fpmh_index else 0)
                else:
                    lcc.append(lcc_total if fault['fpmh'] < fpmh_index and fault['mtbf'] > mtbf_index else 0)

                ## 循环每个首轮修必换、计算总的lcc
                for i in selected_indices:
                    level.append(selected_fields[i])
                    year.append(repair_years[i])
                    Pi_new = [1 if j % (i+1) == 0 else value for j, value in enumerate(Pi)]
                    time = year_worktimes * repair_years[i]
                    fault = await RepirPlanService.get_online_repair_cost(model, part, time)
                    lcc_online = fault['lcc_online']
                    fpmh.append(fault['fpmh'])
                    if len(repair_years) % 2 == 0:
                        lcc_total = lcc_online * len(repair_levels)// (i+1)
                    else:
                        time_last = year_worktimes * repair_years[len(repair_years) % (i+1)-1]
                        lcc_online_last = await RepirPlanService.get_online_repair_cost(model, part, time_last)
                        lcc_total = lcc_online * (len(repair_levels)//(i+1)) + lcc_online_last
                    for i in range(len(Pi_new)):
                        lcc_total += Pi_new[i] * replace_number[i] * float(ebom_cost)
        
                    if is_ai == False:
                        lcc.append(lcc_total if fault['fpmh'] < fpmh_index else 0)
                    else:
                        lcc.append(lcc_total if fault['fpmh'] < fpmh_index and fault['mtbf'] > mtbf_index else 0)
                # 找出满足限制条件的lcc最小值，并输出需要的结果
                lcc_old = lcc[level_index]
                ## 需要考虑限制条件不满足，lcc全部为0的条件
                if sum(lcc) == 0:
                    print(f"跳过部件 {part}，所有的情况都不满足限制条件")
                    continue
                lcc_new = min(filter(lambda x: x != 0, lcc))
                min_index = lcc.index(lcc_new)
                year_new = year[min_index]
                time_new = year_worktimes*year_new
                fault = await RepirPlanService.get_online_repair_cost(model, part, time_new)
                sf = fault['sf']
                lcc_result = '保持' if year_new == year_old else ('延长' if year_new > year_old else '缩短')
                level_new = level[min_index]
                lcc_old_sum += lcc_old
                lcc_new_sum += lcc_new

                # 每个部件计算输出
                result.append({
                'part_name': part_name,
                'part': part,
                'level_old': level_old,
                'year_new': int(year_new),
                'level_new': level_new,
                'lcc_min': lcc_new,
                'sf': round(sf,4),
                'lcc_old': lcc_old,
                'lcc_result': lcc_result,
            })
                
        # 计算可靠性经济型一体化提升比
        ratio = ((lcc_old_sum - lcc_new_sum) / lcc_new_sum)*100 if lcc_new_sum != 0 else 0

        #结果输出
        return {
            'model': model,
            'result':result,
            'ratio':ratio,
        }
               
    @staticmethod
    async def get_online_repair_cost(model: str, part: str, time:float):
        """
        获取修复计划
        :param model: 产品型号
        :param life: 产品生命周期
        :return:
        """
        async with async_db_session() as db:
            # 计算故障率
            # falut = await cycle_life_service.get_fault_number_by_part(model, part, time)
            best_distribution = await reliability_index_service._get_best_distribution(model, part)
            if best_distribution is None:
                raise errors.DataValidationError(msg=f'型号{model}+部件{part}的无故障数据，因此分布信息不存在')
            # 计算FPMH
            x = np.linspace(0, time, 2000)
            y = best_distribution.PDF(x)
            mtbf = 1/np.max(y)
            fpmh = np.max(y) * 1000000

            # 计算故障次数
            falut = best_distribution.CDF(time) - best_distribution.CDF(0)
            ebom_data = await ebom_dao.get_by_model_and_part(db, model, part)
            if ebom_data is None:
                raise errors.DataValidationError(msg=f'型号{model}+部件{part}的没有Ebom数据')
            part_name = ebom_data[0].y8_matname
            part_number = len(ebom_data)
            falut_number = falut * part_number

            # 计算作业时长和核算损失
            failure_data = await failure_dao.get_job_loss_by_model_and_part(db, model, part)
            falling_count = len([f for f in failure_data if f.is_online == '返厂修理'])

            if failure_data is None or len(failure_data) == 0:
                job_duration = 0
                loss_accounting = 0
            else:
                job_duration = (sum(float(failure_data[i].job_duration) for i in range(len(failure_data))))/len(failure_data)
                loss_accounting = (sum(float(failure_data[i].loss_accounting) for i in range(len(failure_data))))/len(failure_data)

            # 计算可用度Ai
            # ai = mtbf/(mtbf+job_duration*falut_number)

            # 计算可靠度
            sf = best_distribution.SF(time)
            # 计算在线修lcc
            lcc_online = falut_number * (falling_count * 50000 + job_duration * 50 + loss_accounting)
        return {
            'fpmh': fpmh,
            'lcc_online': lcc_online,
            'mtbf': mtbf,
            'sf': sf,
            'part_name': part_name
        }
    

    @staticmethod
    async def get_level_repair_number(repair_years: list[float], life: int):
        """
        获取EBOM数量和成本
        :param model: 产品型号
        :param part: 部件物料编码
        :return:
        """
        # 步骤1：计算初始N值（向下取整）
        initial_N = [life // year for year in repair_years]

        # 步骤2：创建修正后的N值副本
        adjusted_N = initial_N.copy()

        # 步骤3：从倒数第二个开始向前循环
        n = len(repair_years)
        for i in range(n-2, -1, -1):  # 从倒数第二个到第一个
            current_year = repair_years[i]
            # 检查当前修程年限是否是后面所有修程年限的约数
            for j in range(i+1, n):
                later_year = repair_years[j]
                # 如果当前修程年限是后面修程年限的约数
                if later_year % current_year == 0:
                    # 从当前N值中减去后面的N值
                    adjusted_N[i] -= adjusted_N[j]
        return adjusted_N
    
    @staticmethod
    async def get_pi(model: str, part: str, repair_levels: list[str]) -> list[float]:
        """
        获取偶换率
        :param model: 产品型号
        :param part: 部件物料编码
        :param repair_levels: 修程级别列表，如 ['C5', 'C6', '2C5', '2C6']
        :return: 对应偶换率
        """
        async with async_db_session() as db:
            # 获取不合格品数据
            unqualify_data = await unqualify_dao.get_by_model_and_part(db, model, part)

            if not unqualify_data:
                raise errors.DataValidationError(
                    msg=f"型号{model}+部件{part}的不合格品数据不存在"
                )
            
            # 创建匹配映射规则
            level_mapping = {}
            for repair_level in repair_levels:
                # 为每个修程级别创建可能的匹配模式
                if repair_level.startswith('2') or repair_level.startswith('次轮') or repair_level.startswith('三轮') or repair_level.startswith('四轮'):
                    # 对于2C5, 2C6, 次轮三级修等，尝试匹配精确的级别
                    level_mapping[repair_level] = [repair_level]
                elif repair_level.startswith('首轮'):
                    # 对于首轮三级修,首轮四级修等，尝试匹配精确级别和没有首轮级别
                    level_mapping[repair_level] = [repair_level, repair_level[len('首轮'):]]
                else:
                    # 对于C5, C6等，尝试匹配精确级别和首轮级别
                    level_mapping[repair_level] = [repair_level, f'首轮{repair_level}']
            
            # 计算每个修程级别的发生率
            pi_values = []
            matched_rates = []  # 用于存储已匹配的发生率
            
            for repair_level in repair_levels:
                possible_matches = level_mapping.get(repair_level, [repair_level])
                found_rate = None
                
                # 尝试匹配每个可能的模式
                for pattern in possible_matches:
                    for item in unqualify_data:
                        if (item.repair_levels and 
                            item.occurrence_rate is not None and 
                            (item.repair_levels == pattern or 
                             item.repair_levels.endswith(pattern))):
                            found_rate = float(item.occurrence_rate)
                            matched_rates.append(found_rate)
                            break
                    if found_rate is not None:
                        break
                
                # 如果找到了发生率，添加到结果中
                if found_rate is not None:
                    pi_values.append(found_rate)
                else:
                    # 如果没有找到，暂时设为None，后面用最大值填充
                    pi_values.append(None)
            
            # 计算已匹配的发生率最大值
            max_rate = max(matched_rates) if matched_rates else 0.5  # 默认值0.5
            
            # 用最大值填充未找到的修程级别
            for i in range(len(pi_values)):
                if pi_values[i] is None:
                    pi_values[i] = max_rate
        
            return pi_values
            

    @staticmethod
    async def get_repair_levels(model: str):
        """
        获取修级顺序表
        :param model: 产品型号
        :return:
        """
        async with async_db_session() as db:
            repair_data = await repair_interval_dao.get_repair_levels_by_model(db, model)
            if repair_data is None or len(repair_data) == 0:
                raise errors.DataValidationError(
                            msg=f"型号{model}的修程信息不存在"
                        )
        return repair_data
    
    @staticmethod
    async def get_replace_data(model: str, part:str):
        """
        获取必换件数据
        :param model: 产品型号
        :param part: 部件物料编码
        :return:
        """
        async with async_db_session() as db:
            replace_data = await replace_dao.get_all_by_model_and_part(db, model, part)
        return replace_data
    
    @staticmethod
    async def get_ebom_number_and_cost(model: str, part:str):
        """
        获取EBOM数量和费用
        :param model: 产品型号
        :param part: 部件物料编码
        :return:
        """
        async with async_db_session() as db:
            # 获取该部件的EBOM数量
            ebom_data = await ebom_dao.get_by_model_and_part(db, model, part)
            if ebom_data is None:
                raise errors.DataValidationError(msg=f'型号{model}+部件{part}的没有Ebom数据')
            part_number = len(ebom_data)
            # 获取该部件的费用
            cost = await lcc_dao.get_by_model_and_part(db, model, part)
            if cost is None:
                    raise errors.DataValidationError(msg=f'型号{model}+部件{part}没有成本数据')            
            return part_number*cost
        

    @staticmethod
    async def get_fpmh_by_part(model:str, part:str,time:float) -> list[float]:
        # 计算FPMH值:pdf函数中(0,t)区间中的最大值
        best_distribution = await reliability_index_service._get_best_distribution(model, part)
        x = np.linspace(0, time, 2000)
        y = best_distribution.PDF(x)
        fpmh = np.max(y) * 1000000        
        return fpmh   

    @staticmethod
    async def get_fpmh_index_by_part(model:str, part:str) -> float:
        # 获取FPMK值:pdf函数中(0,t)区间中的最小值
        async with async_db_session() as db:
            fpmh_index = await reliability_index_dao.get_pre_value_by_model_and_part(db, model, part)
            if fpmh_index is None:
                fpmh_index = 0.01 
            return fpmh_index
 


    @staticmethod
    async def get_parts_by_model(model: str):
        """
        获取model下所有零部件编码,用于级联查询
        """
        try:
            async with async_db_session() as db:
                # 1. 获取fit_part表中该型号的所有零部件
                parts = await fit_part_dao.get_parts_for_lifetime_by_model(db, model)   

                # 2. 创建有效零部件列表
                valid_parts = []

                # 3. 验证每个部件是否同时存在于EBOM和成本数据中
                for part in parts:
                    # 检查EBOM数据是否存在
                    ebom_data = await ebom_dao.get_by_model_and_part(db, model, part)
                    # 检查产品信息数据是否存在
                    product_date = await product_dao.get_by_model(db, model)
                    # 检查LCC数据
                    lcc_data = await lcc_dao.get_by_model_and_part(db, model, part)
                    # 检查不合格品
                    unqualify_data = await unqualify_dao.get_by_model_and_part(db, model, part)
                
                    # 仅当两个数据源都存在时才保留该部件
                    if ebom_data and product_date.year_days and product_date.avg_worktime and lcc_data and unqualify_data:
                        valid_parts.append(part)
                
                 # 4、获取所有部件的故障名称和编码
                failure_parts = await failure_dao.get_parts_with_names_only_by_model(db, model)

                # 5. 创建编码到名称的映射字典
                code_to_name = {code: name for name, code in failure_parts}
                
                # 6. 筛选出既有分布数据又有名称的零部件，返回二元组
                result = []
                for part_code in valid_parts:
                    if part_code in code_to_name:
                        result.append((code_to_name[part_code], part_code))
            
            return result
                
        except Exception as e:
            raise DataValidationError(msg=f"获取所有零部件时发生错误: {str(e)}")



repair_plan_service: RepirPlanService = RepirPlanService()   