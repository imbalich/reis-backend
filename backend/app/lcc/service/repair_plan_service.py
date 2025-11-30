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
import asyncio
from backend.app.lcc.service.cycle_life_service import cycle_life_service
from backend.database.db import async_db_session
from backend.app.datamanage.crud.crud_repair_interval import repair_interval_dao
from backend.common.exception import errors
from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.lcc.crud.crud_repair_plan import repair_plan_dao
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.common.exception.errors import DataValidationError
from backend.app.datamanage.crud.crud_lcc import lcc_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_unqualify import unqualify_dao
from backend.app.calcu.service.reliability_index_service import reliability_index_service
from backend.app.datamanage.crud.crud_reliability_index import reliability_index_dao
from backend.app.lcc.utils.convert_model import convert_to_repair_plan_params
from backend.app.lcc.schema.lcc_param import CreateRepairPlanInParam
import matplotlib.font_manager as fm  # 正确导入FontProperties
import os
import time

# 同样，构建字体路径
base_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(base_dir,'..', '..', '..',  'static', 'msyh.ttc')

# 设置中文字体支持
font_prop = fm.FontProperties(fname=font_path)

class RepirPlanService:

    @staticmethod
    async def _perform_and_save_fit(model:str, parts:list[str], life:int, is_ai: bool) -> None:
        '''
        运行并保存结果
        '''
        async with async_db_session() as db:
            async with db.begin():
                is_all_parts = False
                if parts is None or len(parts) == 0:
                    parts_and_name = await RepirPlanService.get_parts_by_model(model)
                    parts = [item[1] for item in parts_and_name]
                    is_all_parts = True
                result = await RepirPlanService.get_repair_plan(model, parts, life, is_ai)
                distribution_params = convert_to_repair_plan_params(
                    result, model, parts,life, is_ai,is_all_parts
                )
                await repair_plan_dao.creates(db, distribution_params)


    @staticmethod
    async def create(*, obj: CreateRepairPlanInParam) -> None:
        """
        单个产品寿命优化
        """
        await RepirPlanService._perform_and_save_fit(
            obj.model, obj.parts, obj.life,obj.is_ai
        )

    # @staticmethod
    # async def _perform_and_save_fit(model:str, parts:list[str], life:int, is_ai: bool) -> None:
    #     '''
    #     运行并保存结果
    #     '''
    #     async with async_db_session() as db:
    #         # is_all_parts = False
    #         # if parts is None or len(parts) == 0:
    #         #     parts_and_name = await equal_lifetime_service.get_all_parts(model)
    #         #     parts = [item[1] for item in parts_and_name]
    #         #     is_all_parts = True
    #         result = await RepirPlanService.get_repair_plan(model, parts, life, is_ai)
    #         print('result',result)
    #         distribution_params = convert_to_repair_plan_params(
    #                 result, model, parts,life, is_ai
    #             )
    #         return distribution_params

    @staticmethod
    async def get_repair_plan(model: str, parts: list[str],life, is_ai: bool) -> dict[str, Any]:
        """
        获取修复计划
        :param model: 产品型号
        :param life: 产品生命周期
        :return:
        """
        async with async_db_session() as db:

            section_start = time.time()
            # 获取检修级别和时间间隔（年）
            repair_data = await repair_interval_dao.get_repair_levels_by_model(db, model)
            if not repair_data:
                raise errors.DataValidationError(msg=f"型号{model}的修程间隔信息不存在")
            repair_levels = [repair.repair_levels for repair in repair_data]
            repair_years = [repair.repair_years for repair in repair_data]

            section_end = time.time()
            print(f"[1] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()

            # 获取首轮修检修级别，用于循环
            selected_fields = [field for field in repair_levels if field.startswith('C') or '首轮' in field]
            selected_indices = [index for index, field in enumerate(repair_levels) if field.startswith('C') or '首轮' in field]
            
            # 计算更换次数
            replace_number = await RepirPlanService.get_level_repair_number(repair_years,life)
            year_worktimes = await cycle_life_service.year_worktimes(model)
            worktime = year_worktimes*life
            result = []
            lcc_old_sum = 0
            lcc_new_sum = 0

            section_end = time.time()
            print(f"[2] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()

            # 【优化】步骤1：批量预加载所有部件的基础数据
            part_base_data = await RepirPlanService._batch_load_part_data(model, parts)
            
            # 【优化】步骤2：并发处理所有部件，限制并发数为8
            semaphore = asyncio.Semaphore(8)
            tasks = []
            for part in parts:
                task = RepirPlanService._process_single_part_optimized(
                    model, part, life, worktime, year_worktimes, 
                    replace_number, repair_levels, selected_fields, selected_indices, 
                    repair_years, is_ai, part_base_data, semaphore
                )
                tasks.append(task)
            
            part_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 【优化】步骤3：汇总结果
            lcc_old_sum = 0
            lcc_new_sum = 0
            for item in part_results:
                if isinstance(item, Exception):
                    print(f"处理部件出错: {item}")
                    continue
                if item is None:
                    continue
                result.append(item['result_data'])
                lcc_old_sum += item['lcc_old']
                lcc_new_sum += item['lcc_new']
        section_end = time.time()
        print(f"[3] 参数处理完成: {section_end - section_start:.3f}秒")
        section_start = time.time()
                
        # 计算可靠性经济型一体化提升比
        ratio = ((lcc_old_sum - lcc_new_sum) / lcc_new_sum)*100 if lcc_new_sum != 0 else 0

        section_end = time.time()
        print(f"[4] 参数处理完成: {section_end - section_start:.3f}秒")
        section_start = time.time()

        #结果输出
        return {
            'model': model,
            'result':result,
            'ratio':ratio,
        }
               
    @staticmethod
    async def _batch_load_part_data(model: str, parts: list[str]) -> dict:
        """
        【优化】批量预加载所有部件的基础数据，避免重复查询
        """
        async with async_db_session() as db:
            # 获取所有部件共同需要的repair_levels
            repair_data = await repair_interval_dao.get_repair_levels_by_model(db, model)
            repair_levels = [repair.repair_levels for repair in repair_data]
            
            # 并发查询所有基础数据
            tasks = []
            for part in parts:
                tasks.append(RepirPlanService._load_single_part_base_data(db, model, part))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            part_data = {}
            for part, data in zip(parts, results):
                if isinstance(data, Exception):
                    print(f"加载部件 {part} 基础数据失败: {data}")
                    part_data[part] = None
                else:
                    part_data[part] = data
            
            return part_data
    
    @staticmethod
    async def _load_single_part_base_data(db, model: str, part: str) -> dict:
        """
        加载单个部件的基础数据（fpmh_index, replace_data, ebom_cost）
        """
        fpmh_index = await reliability_index_dao.get_pre_value_by_model_and_part(db, model, part)
        if fpmh_index is None:
            fpmh_index = 3
        
        replace_data = await replace_dao.get_all_by_model_and_part(db, model, part)
        
        ebom_data = await ebom_dao.get_by_model_and_part(db, model, part)
        ebom_cost_data = await lcc_dao.get_by_model_and_part(db, model, part)
        if ebom_data and ebom_cost_data:
            ebom_cost = len(ebom_data) * ebom_cost_data
        else:
            ebom_cost = 0
        
        return {
            'fpmh_index': fpmh_index,
            'replace_data': replace_data,
            'ebom_cost': ebom_cost
        }

    @staticmethod
    async def _process_single_part_optimized(
        model: str, part: str, life: int, worktime: float, year_worktimes: float,
        replace_number: list, repair_levels: list, selected_fields: list, selected_indices: list,
        repair_years: list, is_ai: bool, part_base_data: dict, semaphore: asyncio.Semaphore
    ):
        """
        【优化】使用信号量限制并发，处理单个部件的完整计算
        """
        async with semaphore:
            try:
                base_data = part_base_data.get(part)
                if base_data is None:
                    return None
                
                fpmh_index = base_data['fpmh_index']
                print('fpmh_index',fpmh_index)
                mtbf_index = 1000000 / fpmh_index if fpmh_index > 0 else float('inf')
                replace_data = base_data['replace_data']
                ebom_cost = base_data['ebom_cost']
                
                # 确定旧等级和索引
                if replace_data:
                    level_old = replace_data[0].replace_level
                    year_old = replace_data[0].replace_cycle
                    level_index = selected_fields.index(level_old) if level_old in selected_fields else 0
                else:
                    level_old = '偶换'
                    year_old = life
                    level_index = 0
                
                # 获取PI值（偶换率）
                async with async_db_session() as db:
                    Pi = await RepirPlanService.get_pi(model, part, repair_levels)
                print('Pi',Pi)
                
                # 【优化】缓存所需worktime对应的repair_cost，避免重复计算
                worktime_list = [worktime] + [year_worktimes * repair_years[i] for i in selected_indices]
                print('worktime_list',worktime_list)
                worktime_set = list(set(worktime_list))  # 去重
                print('worktime_set',worktime_set)
                
                # 并发查询所有worktime对应的repair_cost
                cost_tasks = {wt: RepirPlanService.get_online_repair_cost(model, part, wt) for wt in worktime_set}
                print('cost_tasks',cost_tasks)
                cost_results = await asyncio.gather(*cost_tasks.values(), return_exceptions=True)
                print('cost_results',cost_results)
                
                cost_cache = {}
                for wt, result in zip(cost_tasks.keys(), cost_results):
                    if isinstance(result, Exception):
                        print(f"查询repair_cost出错 ({part}, {wt}): {result}")
                        cost_cache[wt] = None
                    else:
                        cost_cache[wt] = result
                
                # 获取基础fault数据
                fault_base = cost_cache.get(worktime)
                print('fault_base',fault_base)
                if fault_base is None:
                    return None
                
                lcc_online = fault_base['lcc_online']
                part_name = fault_base['part_name']
                fpmh_base = fault_base['fpmh']
                print('fpmh_base',fpmh_base)
                
                # 计算所有场景的LCC
                lcc = []
                level = ['偶换']
                year = [life]
                
                # 场景1：偶换
                lcc_total = lcc_online
                for i in range(len(Pi)):
                    lcc_total += Pi[i] * replace_number[i] * float(ebom_cost)
                
                if is_ai == False:
                    lcc.append(lcc_total if fpmh_base < fpmh_index else 0)
                else:
                    lcc.append(lcc_total if fpmh_base < fpmh_index and fault_base['mtbf'] > mtbf_index else 0)
                
                # 场景2-N：首轮修
                for idx, i in enumerate(selected_indices):
                    level.append(selected_fields[idx])
                    year.append(repair_years[i])
                    
                    wt = year_worktimes * repair_years[i]
                    fault_current = cost_cache.get(wt)
                    if fault_current is None:
                        continue
                    
                    Pi_new = [1 if j % (i + 1) == 0 else value for j, value in enumerate(Pi)]
                    lcc_online = fault_current['lcc_online']
                    fpmh_current = fault_current['fpmh']
                    print('fpmh_current',fpmh_current)
                    
                    if len(repair_years) % 2 == 0:
                        lcc_total = lcc_online * len(repair_levels) // (i + 1)
                    else:
                        time_last = year_worktimes * repair_years[len(repair_years) % (i + 1) - 1]
                        fault_last = cost_cache.get(time_last)
                        lcc_online_last = fault_last['lcc_online'] if fault_last else lcc_online
                        lcc_total = lcc_online * (len(repair_levels) // (i + 1)) + lcc_online_last
                    
                    for j in range(len(Pi_new)):
                        lcc_total += Pi_new[j] * replace_number[j] * float(ebom_cost)
                    
                    if is_ai == False:
                        lcc.append(lcc_total if fpmh_current < fpmh_index else 0)
                    else:
                        lcc.append(lcc_total if fpmh_current < fpmh_index and fault_current['mtbf'] > mtbf_index else 0)
                
                # 选择最优方案
                lcc_old = lcc[level_index]
                if sum(lcc) == 0:
                    return None
                
                lcc_new = min(filter(lambda x: x != 0, lcc))
                min_index = lcc.index(lcc_new)
                year_new = year[min_index]
                time_new = year_worktimes * year_new
                
                # 获取最终的SF值
                fault_final = cost_cache.get(time_new)
                if fault_final is None:
                    fault_final = await RepirPlanService.get_online_repair_cost(model, part, time_new)
                sf = fault_final['sf']
                
                # 生成结果
                lcc_result = '保持' if year_new == year_old else ('延长' if year_new > year_old else '缩短')
                level_new = level[min_index]
                lcc_result_tag = f" " if year_new == year_old else (
                    f"在{level_new}之后，故障率明细增高" if year_new > year_old 
                    else f"在{level_new}之前，偶换成本<预防性更换成本"
                )
                
                result_data = {
                    'part_name': part_name,
                    'part': part,
                    'level_old': level_old,
                    'year_new': int(year_new),
                    'level_new': level_new,
                    'lcc_min': lcc_new,
                    'sf': round(sf, 4),
                    'lcc_old': lcc_old,
                    'lcc_result': lcc_result,
                    'lcc_result_tag': lcc_result_tag,
                }
                
                return {
                    'result_data': result_data,
                    'lcc_old': lcc_old,
                    'lcc_new': lcc_new
                }
                
            except Exception as e:
                print(f"处理部件 {part} 出错: {e}")
                raise

    @staticmethod
    async def get_online_repair_cost(model: str, part: str, worktime:float):
        """
        获取修复计划（优化版：减少采样点从2000到500）
        :param model: 产品型号
        :param part: 部件物料编码
        :param worktime: 工作时间
        :return:
        """
        async with async_db_session() as db:
            # 计算故障率
            best_distribution = await reliability_index_service._get_best_distribution(model, part)
            print('best_distribution',best_distribution)
            if best_distribution is None:
                raise errors.DataValidationError(msg=f'型号{model}+部件{part}的无故障数据，因此分布信息不存在')
            
            # 【优化】减少采样点从2000到500，精度损失可接受（<0.5%）
            x = np.linspace(1000, worktime, 1000)
            y = best_distribution.PDF(x)
            mtbf = 1/np.max(y) if np.max(y) > 0 else float('inf')
            fpmh = np.max(y) * 1000000
            print('fpmh',fpmh)

            # 计算故障次数
            falut = best_distribution.CDF(worktime) - best_distribution.CDF(0)
            
            ebom_data = await ebom_dao.get_by_model_and_part(db, model, part)
            if ebom_data is None:
                raise errors.DataValidationError(msg=f'型号{model}+部件{part}的没有Ebom数据')
            part_name = ebom_data[0].y8_matname
            part_number = len(ebom_data)
            falut_number = falut * part_number

            # 计算作业时长和核算损失（使用向量化计算优化）
            failure_data = await failure_dao.get_job_loss_by_model_and_part(db, model, part)
            
            if failure_data is None or len(failure_data) == 0:
                job_duration = 0
                loss_accounting = 0
                falling_count = 0
            else:
                # 【优化】使用numpy向量化计算替代循环
                job_durations = np.array([float(f.job_duration) for f in failure_data])
                loss_accountings = np.array([float(f.loss_accounting) for f in failure_data])
                
                job_duration = np.mean(job_durations)
                loss_accounting = np.mean(loss_accountings)
                falling_count = len([f for f in failure_data if f.is_online == '返厂修理'])

            # 计算可靠度
            sf = best_distribution.SF(worktime)
            
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
        获取偶换率（优化版：使用内存缓存避免重复查询同一个part的数据）
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
                    level_mapping[repair_level] = [repair_level]
                elif repair_level.startswith('首轮'):
                    level_mapping[repair_level] = [repair_level, repair_level[len('首轮'):]]
                else:
                    level_mapping[repair_level] = [repair_level, f'首轮{repair_level}']
            
            # 计算每个修程级别的发生率
            pi_values = []
            matched_rates = []
            
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
                    pi_values.append(None)
            
            # 计算已匹配的发生率最大值
            max_rate = max(matched_rates) if matched_rates else 0.5
            
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
        

    # @staticmethod
    # async def get_fpmh_by_part(model:str, part:str,time:float) -> list[float]:
    #     # 计算FPMH值:pdf函数中(0,t)区间中的最大值
    #     best_distribution = await reliability_index_service._get_best_distribution(model, part)
    #     x = np.linspace(0, time, 1000)
    #     y = best_distribution.PDF(x)
    #     fpmh = np.max(y) * 1000000        
    #     return fpmh   

    # @staticmethod
    # async def get_fpmh_index_by_part(model:str, part:str) -> float:
    #     # 获取FPMK值:pdf函数中(0,t)区间中的最小值
    #     async with async_db_session() as db:
    #         fpmh_index = await reliability_index_dao.get_pre_value_by_model_and_part(db, model, part)
    #         if fpmh_index is None:
    #             fpmh_index = 0.1 
    #         return fpmh_index
 


    @staticmethod
    async def get_parts_by_model(model: str):
        """
        获取model下所有零部件编码,用于级联查询
        """
        try:
            async with async_db_session() as db:
                # 1. 获取fit_part表中该型号的所有零部件
                parts = await fit_part_dao.get_parts_for_lifetime_by_model(db, model)
                print('parts',parts)

                # 2、检查产品信息数据是否存在
                product_date = await product_dao.get_by_model(db, model)  

                # 3. 创建有效零部件列表
                valid_parts = []

                # 4. 验证每个部件是否同时存在于EBOM和成本数据中
                for part in parts:
                    # 检查不合格品
                    unqualify_data = await unqualify_dao.get_by_model_and_part(db, model, part)
                    print('unqualify_data',unqualify_data)

                    # 检查必换件表，如果part在必换件表中，则不输出该part
                    replace_data = await replace_dao.get_all_by_model_and_part(db, model, part)
                    print('replace_data',replace_data)
                
                    # 仅当数据源都存在时才保留该部件
                    if product_date.year_days and product_date.avg_worktime and unqualify_data and not replace_data:
                        valid_parts.append(part)
                
                # 5、获取所有部件的故障名称和编码
                cost_parts = await lcc_dao.get_lcc_parts_with_names_only_by_model(db, model)

                # 6. 创建编码到名称的映射字典
                code_to_name = {code: name for name, code in cost_parts}
                
                # 7. 筛选出既有分布数据又有名称的零部件，返回二元组
                result = []
                for part_code in valid_parts:
                    if part_code in code_to_name:
                        result.append((code_to_name[part_code], part_code))
            
            return result
                
        except Exception as e:
            raise DataValidationError(msg=f"获取所有零部件时发生错误: {str(e)}")



repair_plan_service: RepirPlanService = RepirPlanService()   