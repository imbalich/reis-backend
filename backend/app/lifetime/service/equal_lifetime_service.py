#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：equal_lifetime.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/15 14:03
"""
import time
import asyncio
import os
import json
from typing import Any
import matplotlib.font_manager as fm  # 正确导入FontProperties
from backend.app.lcc.crud.crud_repair_plan import repair_plan_dao
from backend.app.datamanage.crud.crud_repair_interval import repair_interval_dao
from backend.app.datamanage.crud.crud_unqualify import unqualify_dao
from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.common.exception import errors
from backend.app.lifetime.utils.convert_model import convert_to_equal_lifetime_params_with_classification
from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.lifetime.service.pso_service import pso_service
from backend.app.lifetime.service.find_point_service import find_point_service
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.lifetime.crud.crud_lifetime import equal_lifetime_dao
from backend.app.lifetime.service.plot_lifetime_service import plot_lifetime_service
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.common.exception.errors import DataValidationError
from backend.database.db import async_db_session
from backend.app.calcu.schema.distribute_param import DistributeType
from backend.app.calcu.conf import predict_settings
from backend.app.lcc.service.cycle_life_service import cycle_life_service
from backend.app.lifetime.utils.convert_model import (
    convert_to_euqal_lifetime_params,
)
from backend.app.lifetime.schema.lifetime_param import CreateEuqalLifetimeInParam


# 同样，构建字体路径
base_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(base_dir,'..', '..', '..',  'static', 'msyh.ttc')

# 验证字体文件是否存在
if not os.path.exists(font_path):
    print(f"警告：字体文件不存在于 {font_path}")
    # 可以添加备用方案
else:
    # print(f"使用字体文件: {font_path}")
    pass


# 设置中文字体支持
font_prop = fm.FontProperties(fname=font_path)

class EqualLifetimeService:
                    
    @staticmethod
    async def get_result(model:str, parts:list[str], target_sf:float,equal_lifetime_t:int,equal_lifetime_sf:float,t:int) -> dict[str, Any]: 
        """
        通过粒子群优化算法优化所有部件的参数
        """
        
        results = {}
        need_optimization = False

        # 并发任务列表
        tasks = []
        part_params_list = []
        
        # 1、获取所有部件分布信息
        for part in parts:  
            distribution_params = await distribute_service.get_part_distribution_params(
                model, part
            )
            distribution_type = DistributeType(distribution_params.distribution)
            distribution_class = predict_settings.DISTRIBUTION_FUNCTIONS.get(distribution_type)
            best_distribution = await distribute_service.get_part_distribution(model, part)
            original_sf_value = best_distribution.SF(t)
            
            if equal_lifetime_t is not None:
                equal_point_sf = best_distribution.SF(equal_lifetime_t)
                equal_point_diff = abs(equal_point_sf - equal_lifetime_sf)
                # 判断是否需要优化：同时满足可靠度要求和经过等寿命点
                if original_sf_value >= target_sf and equal_point_diff < 0.001:
                    results[part] = {
                        "part": part,
                        "need_optimization": need_optimization,
                        "original_pdf": round(best_distribution.PDF(t)*1000000,4),
                        "original_equal_point_pdf": round(best_distribution.PDF(equal_lifetime_t)*1000000,4),
                        "original_distribution" : best_distribution,
                    }
                    continue
            else:
                # 只判断可靠度是否达标
                if original_sf_value >= target_sf:
                    results[part] = {
                        "part": part,
                        "need_optimization": need_optimization,
                        "original_pdf":round(best_distribution.PDF(t)*1000000,4),
                        "original_distribution" : best_distribution,
                    }
                    continue

            param_mapping = predict_settings.PARAM_MAPPING.get(distribution_type, {})
            param_names = list(param_mapping.keys())
            original_params = {}
            for dist_param, db_param in param_mapping.items():
                value = getattr(distribution_params, db_param, None)
                if value is not None:
                    original_params[dist_param] = value
            
            # 2、需要优化的部件，收集参数用于并发
            part_params_list.append({
                "param_names": param_names,
                "original_params": original_params,
                "distribution_class": distribution_class,
                "t": t,
                "target_sf": target_sf,
                "equal_lifetime_t": equal_lifetime_t,
                "equal_lifetime_sf": equal_lifetime_sf,
                "part": part,
                "best_distribution": best_distribution,
            })

        # 3、 并发执行PSO优化
        async def optimize_one(params):
            optimized_result = await pso_service.pso_optimize_params(
                params["param_names"],
                params["original_params"],
                params["distribution_class"],
                params["t"],
                params["target_sf"],
                params["equal_lifetime_t"],
                params["equal_lifetime_sf"]
            )
            optimized_result["part"] = params["part"]
            optimized_result["need_optimization"] = True
            optimized_result["original_distribution"] = params["best_distribution"]
            return optimized_result

        # 4、 并发执行
        if part_params_list:
            tasks = [optimize_one(params) for params in part_params_list]
            optimized_results = await asyncio.gather(*tasks)
            for result in optimized_results:
                results[result["part"]] = result
        
        return results

    # @staticmethod
    # async def _perform_and_save_fit(model:str, parts:list[str], target_sf:float,step_start:float,step_end:float) -> None:
    #     '''
    #     运行并保存结果
    #     '''
    #     async with async_db_session() as db:
    #         async with db.begin():
    #             is_all_parts = False
    #             if parts is None or len(parts) == 0:
    #                 parts_and_name = await equal_lifetime_service.get_all_parts(model)
    #                 parts = [item[1] for item in parts_and_name]
    #                 is_all_parts = True
    #             result = await find_point_service.find_equal_lifetime_point(model, parts, step_start,step_end)
    #             distribution_params = convert_to_euqal_lifetime_params(
    #                 result, model, parts,target_sf,step_start,step_end,is_all_parts
    #             )
    #             await equal_lifetime_dao.creates(db, distribution_params)
    

    @staticmethod
    async def _perform_and_save_fit(model: str, parts: list[str], target_sf: float, step_start: float, step_end: float) -> None:
        '''
        运行并保存分类后的结果
        '''
        async with async_db_session() as db:
            async with db.begin():
                is_all_parts = False
                if parts is None or len(parts) == 0:
                    parts_and_name = await equal_lifetime_service.get_all_parts(model)
                    parts = [item[1] for item in parts_and_name]
                    is_all_parts = True

                year_worktimes = await cycle_life_service.year_worktimes(model)
                repair_result = await repair_interval_dao.get_repair_parts_with_names_only_by_model(db, model)
            
                # 【改进】调用新的分类方法
                classification_results = await find_point_service.find_equal_lifetime_point_with_classification(
                    model, parts, step_start, step_end,year_worktimes,repair_result
                )


         
                # 【改进】转换为三条记录（每个分类一条）
                distribution_params = convert_to_equal_lifetime_params_with_classification(
                    classification_results,
                    model,
                    target_sf,
                    step_start,
                    step_end,
                    is_all_parts
                )
            
                await equal_lifetime_dao.creates(db, distribution_params)


    # @staticmethod
    # async def _perform_and_save_fit(model: str, parts: list[str], target_sf: float, step_start: float, step_end: float) -> None:
    #     '''
    #     运行并保存分类后的结果
    #     '''
    #     async with async_db_session() as db:
    #         is_all_parts = False
    #         print('is_all_parts',is_all_parts)
    #         print('old_parts',parts)
    #         if parts is None or len(parts) == 0:
    #             parts_and_name = await equal_lifetime_service.get_all_parts(model)
    #             print('parts_and_name',parts_and_name)
    #             parts = [item[1] for item in parts_and_name]
    #             is_all_parts = True
    #         print(parts)
            
    #         # 【改进】调用新的分类方法
    #         classification_results = await find_point_service.find_equal_lifetime_point_with_classification(
    #             model, parts, step_start, step_end
    #         )

    #         return classification_results

    @staticmethod
    async def create(*, obj: CreateEuqalLifetimeInParam) -> None:
        """
        单个产品寿命优化
        """
        await EqualLifetimeService._perform_and_save_fit(
            obj.model, obj.parts, obj.target_sf,obj.step_start,obj.step_end
        )
    
    @staticmethod
    async def get_best_by_model_and_parts(
        model: str,
        parts: list[str],
        target_sf: float,
        step_start: float,
        step_end: float,
        is_all_parts: bool = False
    ):
        """
        获取指定模型和部件的等寿命点结果
        """
        async with async_db_session() as db:
        
            models = await equal_lifetime_dao.get_by_model(db, model,target_sf,step_start,step_end,is_all_parts)
            if not models:
                return None
            if is_all_parts == True:
                return models[0]
            # 按group_id分组，保持原有顺序（已经按created_time排序）
            groups = {}
            for item in models:
                if item.group_id not in groups:
                    groups[item.group_id] = []
                groups[item.group_id].append(item)
            
            # 检查每个group中是否包含所有parts
            for group_id, group_results in groups.items():
                 # 取出数据库中的 parts 字段（字符串），转为 list
                db_parts_str = group_results[0].parts
                db_parts = json.loads(db_parts_str) if isinstance(db_parts_str, str) else db_parts_str

                if sorted(db_parts) == sorted(parts):
                # 找到匹配的group，返回该group的所有记录
                    return group_results[0]
                                
            return None
    
    @staticmethod
    async def _get_group_by_model_and_parts(
            model: str,
            parts: list[str] | None,
            target_sf: float,
            step_start: float,
            step_end: float,
            is_all_parts: bool = False
    ) -> list:
        """
        返回匹配的 group 的所有记录（按 category 分条记录）
        - 如果 parts 提供：寻找 group 中 parts 列表与之完全匹配的 group_id，返回该 group 的所有记录
        - 如果 parts 为 None：返回最新的 group（is_all_parts=True 时常用）
        """
        async with async_db_session() as db:
            models = await equal_lifetime_dao.get_by_model(db, model, target_sf, step_start, step_end, is_all_parts)
            if not models:
                return []

            # 按 group_id 分组
            groups: dict[str, list] = {}
            for item in models:
                groups.setdefault(item.group_id, []).append(item)

            if parts:
                # 找到 parts 完全匹配的 group
                for group_id, group_results in groups.items():
                    # group_results 中每条记录的 parts 字段是重复的（存储相同 parts JSON）
                    db_parts_str = group_results[0].parts
                    db_parts = json.loads(db_parts_str) if isinstance(db_parts_str, str) else db_parts_str
                    if sorted(db_parts) == sorted(parts):
                        return group_results
                return []
            else:
                # parts 未提供：返回最新创建的 group（models 已按 created_time 排序）
                # models[0] 属于最新 group_id
                latest_group_id = models[0].group_id
                return groups.get(latest_group_id, [])
        
    
    # @staticmethod
    # async def get_optimize_result(
    #     model: str,
    #     parts: list[str],
    #     target_sf: float,
    #     step_start: float,
    #     step_end: float
    # ):
    #     '''获取优化结果'''
    #     async with async_db_session() as db:

    #         # 1. 如果传入部件为空，获取fit_parts表中型号下所有部件
    #         is_all_parts = False
    #         if parts is None or len(parts) == 0:
    #             # parts = await find_point_service.get_part_by_model(model)
    #             is_all_parts = True

    #         # 2、获取等寿命点结果
    #         optimize_result = await EqualLifetimeService.get_best_by_model_and_parts(model, parts,target_sf,step_start,step_end,is_all_parts)
    #         if not optimize_result: 
    #             return None
    #         equal_lifetime_t = optimize_result.equal_lifetime_t
    #         equal_lifetime_sf = optimize_result.equal_lifetime_sf
    #         t = int(optimize_result.time_point)
    #         parts = json.loads(optimize_result.parts) if isinstance(optimize_result.parts, str) else optimize_result.parts

    #         # 3. 获取PSO优化结果
    #         pso_results = await EqualLifetimeService.get_result(model, parts,target_sf,equal_lifetime_t,equal_lifetime_sf,t)
            
    #         # 4、创建编码到名称的映射字典
    #         failure_parts = await failure_dao.get_parts_with_names_only_by_model(db, model)
    #         code_to_name = {code: name for name, code in failure_parts}

    #         # 5. 绘制优化前后SF图
    #         year_worktimes = await cycle_life_service.year_worktimes(model)
    #         plot_original_result = await plot_lifetime_service.plot_original_result(model,parts,t,target_sf,pso_results,year_worktimes)
    #         plot_optimize_result = await plot_lifetime_service.plot_optimize_result(model,pso_results,t,target_sf,code_to_name,equal_lifetime_t,equal_lifetime_sf,year_worktimes)
            
    #         # 6. 创建结果
    #         parts_results = []
    #         result = []
    #         for part,pso_result in pso_results.items():
    #             parts_results = {
    #                 "part": part,
    #                 "part_name": code_to_name[part],
    #                 "original_pdf": pso_result['original_pdf'],
    #                 "optimized_pdf": pso_result['optimized_pdf'] if 'optimized_pdf' in pso_result else None,
    #                 "original_equal_point_pdf": pso_result['original_equal_point_pdf'] if 'original_equal_point_pdf' in pso_result else None,
    #                 "optimized_equal_point_pdf": pso_result['optimized_equal_point_pdf'] if 'optimized_equal_point_pdf' in pso_result else None,
    #                 "need_optimization":pso_result['need_optimization']
    #             }
    #             result.append(parts_results)
    #         result = sorted(result, key=lambda x: x['need_optimization'], reverse=True)
    #         return {
    #             "result": result,
    #             "equal_lifetime_t" : equal_lifetime_t,
    #             "img_original_result": plot_original_result,
    #             "img_optimize_result": plot_optimize_result,
    #         }

    @staticmethod
    async def get_optimize_result(
            model: str,
            parts: list[str] | None,
            target_sf: float,
            step_start: float,
            step_end: float
    ):
        """
        获取优化结果 - 分类感知版本
        处理逻辑：
          - 读取同一 group_id 下 A/B/C 的记录
          - A: 跳过 PSO，仅打标签并返回原始分布信息
          - B/C: 为各自集合并发执行 PSO（复用 get_result）
          - 绘图：原始图显示 A/B/C 标注；优化图仅显示 B/C 的优化曲线
        返回结构与原来兼容，但将 equal_lifetime_t 用 dict 返回（按 category）
        """
        start_time = time.time()
        section_start = time.time()
        async with async_db_session() as db:
            # 1. 处理 parts 是否为空（保持原有行为）
            is_all_parts = False
            if parts is None or len(parts) == 0:
                is_all_parts = True

            section_end = time.time()
            print(f"[1] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()

            # 2. 获取匹配的 group（返回多条记录：A/B/C）
            group_records = await EqualLifetimeService._get_group_by_model_and_parts(
                model, parts, target_sf, step_start, step_end, is_all_parts
            )
            # print('group_records',group_records)
            if not group_records:
                return None
            
            section_end = time.time()
            print(f"[2] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()

            # 构造成 category->record 映射
            category_map = {rec.category: rec for rec in group_records if getattr(rec, 'category', None) is not None}

            section_end = time.time()
            print(f"[3] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()

            # 基本时间 t、year_worktimes（以第一条记录为准）
            t = int(group_records[0].time_point)
            year_worktimes = await cycle_life_service.year_worktimes(model)
            repair_result = await repair_interval_dao.get_repair_parts_with_names_only_by_model(db, model)
            repair_result_dict = {name: score for score, name in repair_result}

            # 构造最终的 pso_results（包含所有部件，无论是否优化）
            pso_results: dict[str, dict] = {}

            # 保证 pso_results 字典包含所有 parts（A/B/C）
            # parts_all：按原始请求的 parts 或从数据库获取
            if parts is None or len(parts) == 0:
                # 取 group_records 中任意一条的 parts 字段（理应所有分类的 parts 相同）
                parts_all = []
                for i in range(len(group_records)):
                    parts_group = json.loads(group_records[i].parts) if isinstance(group_records[0].parts, str) else group_records[0].parts
                    parts_all.extend(parts_group)
            else:
                parts_all = parts
                
            # 并发批量获取所有parts的major_part
            async def fetch_major_part(part):
                try:
                    major_part = await unqualify_dao.get_major_repair_by_model_and_part(db, model, part)
                    major_part_t = repair_result_dict.get(major_part) if major_part else None
                    return part, major_part, major_part_t
                except Exception as e:
                    return part, None, None

            major_part_map = {}  # {part: (major_part, major_part_t)}
            if parts_all:
                major_tasks = [fetch_major_part(part) for part in parts_all]
                major_results = await asyncio.gather(*major_tasks)
                for part, major_part, major_part_t in major_results:
                    major_part_map[part] = (major_part, major_part_t)

            # 预加载failure_parts和code_to_name
            failure_parts = await failure_dao.get_parts_with_names_only_by_model(db, model)
            code_to_name = {code: name for name, code in failure_parts}

            pso_results: dict[str, dict] = {}

            section_start = time.time()

            # 3. A 类：不优化，仅收集原始分布信息（并发获取）
            if 'A' in category_map:
                rec_a = category_map['A']
                parts_a = json.loads(rec_a.parts) if isinstance(rec_a.parts, str) else rec_a.parts
                # 并发取每个部件的 distribution
                async def fetch_original(part):
                    dist = await distribute_service.get_part_distribution(model, part)
                    # major_part = await unqualify_dao.get_major_repair_by_model_and_part(db, model, part)
                    # print(f"major_part: {major_part}")
                    # major_part_t = repair_result_dict.get(major_part)
                    # print(f"major_part_t: {major_part_t}")
                    # return part, dist, major_part,major_part_t
                    major_part, major_part_t = major_part_map.get(part, (None, None))
                    # 根据major_part决定用哪个t点计算PDF
                    if major_part_t is not None:
                        pdf_t = float(major_part_t * year_worktimes)
                        original_pdf = round(dist.PDF(pdf_t) * 1000000, 4)
                    else:
                        original_pdf = round(dist.PDF(t) * 1000000, 4)
                
                    # original_equal_t_year：如果major_part存在则为major_part，否则为'偶换'
                    original_equal_t_year = major_part + '大修' if major_part else '偶换维护'
                
                    return part, dist, original_pdf, original_equal_t_year

                if parts_a:
                    tasks = [fetch_original(part) for part in parts_a]
                    fetched = await asyncio.gather(*tasks)
                    for part, dist, original_pdf, original_equal_t_year in fetched:
                        pso_results[part] = {
                            'part': part,
                            'original_distribution': dist,
                            'original_pdf': original_pdf,
                            'original_equal_point_pdf': None,
                            'need_optimization': False,
                            'category': 'A',
                            'original_equal_t_year': original_equal_t_year,
                            'equal_lifetime_t_year': original_equal_t_year,
                            
                        }
            section_end = time.time()
            print(f"[4] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()
            semaphore = asyncio.Semaphore(3)  # 同时最多3个PSO任务

            # 4. B、C 类：并发执行 PSO（每个分类调用一次 get_result）
            async def run_part_pso(category_label, part, equal_t, equal_sf, equal_lifetime_t_year):
                async with semaphore:
                    async with async_db_session() as task_db:
                        major_part, major_part_t = major_part_map.get(part, (None, None))
                        t_for_pso = int(major_part_t * year_worktimes) if major_part_t is not None else t
                        result_dict = await EqualLifetimeService.get_result(
                            model, [part], target_sf, equal_t, equal_sf, t_for_pso
                        )
                        if part in result_dict:
                            rr = result_dict[part]
                            rr['category'] = category_label
                            rr['equal_lifetime_t_year'] = equal_lifetime_t_year + '大修' if major_part else equal_lifetime_t_year + '维护'
                            rr['original_equal_t_year'] = major_part + '大修' if major_part else '偶换维护'
                        return result_dict

            b_parts, c_parts = [], []
            if 'B' in category_map:
                rec_b = category_map['B']
                b_parts = json.loads(rec_b.parts) if isinstance(rec_b.parts, str) else rec_b.parts
            if 'C' in category_map:
                rec_c = category_map['C']
                c_parts = json.loads(rec_c.parts) if isinstance(rec_c.parts, str) else rec_c.parts

            pso_category_tasks = []
            if 'B' in category_map:
                rec_b = category_map['B']
                equal_t_b = int(rec_b.equal_lifetime_t) if rec_b.equal_lifetime_t else None
                equal_sf_b = float(rec_b.equal_lifetime_sf) if rec_b.equal_lifetime_sf else None
                equal_lifetime_t_year_b = rec_b.equal_lifetime_t_year
                for part in b_parts:
                    pso_category_tasks.append(
                        run_part_pso('B', part, equal_t_b, equal_sf_b, equal_lifetime_t_year_b)
                    )
            if 'C' in category_map:
                rec_c = category_map['C']
                equal_t_c = int(rec_c.equal_lifetime_t) if rec_c.equal_lifetime_t else None
                equal_sf_c = float(rec_c.equal_lifetime_sf) if rec_c.equal_lifetime_sf else None
                equal_lifetime_t_year_c = rec_c.equal_lifetime_t_year 
                for part in c_parts:
                    pso_category_tasks.append(
                        run_part_pso('C', part, equal_t_c, equal_sf_c, equal_lifetime_t_year_c)
                    )
            # b_parts = []
            # c_parts = []
            # if 'B' in category_map:
            #     rec_b = category_map['B']
            #     b_parts = json.loads(rec_b.parts) if isinstance(rec_b.parts, str) else rec_b.parts
            # if 'C' in category_map:
            #     rec_c = category_map['C']
            #     c_parts = json.loads(rec_c.parts) if isinstance(rec_c.parts, str) else rec_c.parts

            # print('B类parts:', b_parts)
            # print('C类parts:', c_parts)

            # section_end = time.time()
            # print(f"[5] B/C类准备完成: {section_end - section_start:.3f}秒")
            # section_start = time.time()

            # # 并发运行 B/C 的 PSO（每个part调用一次get_result，传入对应的t）
            # async def run_part_pso(category_label, part, equal_t, equal_sf, equal_lifetime_t_year):
            #     # 获取该part的major_part信息
            #     major_part, major_part_t = major_part_map.get(part, (None, None))
            
            #     # 决定传入get_result的t值
            #     if major_part_t is not None:
            #         t_for_pso = int(major_part_t * year_worktimes)
            #     else:
            #         t_for_pso = t
            
            #     # 调用get_result进行PSO优化
            #     result_dict = await EqualLifetimeService.get_result(
            #         model, [part], target_sf, equal_t, equal_sf, t_for_pso
            #     )
            
            #     # 给该part的结果添加category和original_equal_t_year标记
            #     if part in result_dict:
            #         rr = result_dict[part]
            #         rr['category'] = category_label
            #         rr['equal_lifetime_t_year'] = equal_lifetime_t_year
            #         # 添加original_equal_t_year：如果major_part存在则为major_part，否则为'偶换'
            #         rr['original_equal_t_year'] = major_part if major_part else '偶换'
            
            #     return result_dict

            # # 构造B/C类的所有part任务
            # pso_category_tasks = []
            # if 'B' in category_map:
            #     rec_b = category_map['B']
            #     equal_t_b = int(rec_b.equal_lifetime_t) if rec_b.equal_lifetime_t else None
            #     equal_sf_b = float(rec_b.equal_lifetime_sf) if rec_b.equal_lifetime_sf else None
            #     equal_lifetime_t_year_b = rec_b.equal_lifetime_t_year
            #     for part in b_parts:
            #         pso_category_tasks.append(
            #             run_part_pso('B', part, equal_t_b, equal_sf_b, equal_lifetime_t_year_b)
            #         )

            # if 'C' in category_map:
            #     rec_c = category_map['C']
            #     equal_t_c = int(rec_c.equal_lifetime_t) if rec_c.equal_lifetime_t else None
            #     equal_sf_c = float(rec_c.equal_lifetime_sf) if rec_c.equal_lifetime_sf else None
            #     equal_lifetime_t_year_c = rec_c.equal_lifetime_t_year
            #     for part in c_parts:
            #         pso_category_tasks.append(
            #             run_part_pso('C', part, equal_t_c, equal_sf_c, equal_lifetime_t_year_c)
            #         )

            section_end = time.time()
            print(f"[4.5] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()
            
            # D类（必换件）
            if 'D' in category_map:
                rec_d = category_map['D']
                parts_d = json.loads(rec_d.parts) if isinstance(rec_d.parts, str) else rec_d.parts

                async def fetch_replace_info(part):
                    async with async_db_session() as db:
                        replaces = await replace_dao.get_first_by_model_with_min_repair_level(db, model, part)
                        replace_cycle = replaces.replace_cycle
                        replace_level = replaces.replace_level
                        return part, replace_cycle, replace_level

                replace_infos = await asyncio.gather(*[fetch_replace_info(part) for part in parts_d])
                replace_info_map = {part: (replace_cycle, replace_level) for part, replace_cycle, replace_level in replace_infos}

                async def run_d_part_pso(part, equal_t, equal_sf):
                    replace_cycle, replace_level = replace_info_map.get(part, (None, None))
                    t_for_pso = int(replace_cycle * year_worktimes) if replace_cycle is not None else t
                    result_dict = await EqualLifetimeService.get_result(
                        model, [part], target_sf, equal_t, equal_sf, t_for_pso
                    )
                    if part in result_dict:
                        rr = result_dict[part]
                        rr['category'] = 'D'
                        rr['equal_lifetime_t_year'] = replace_level + "必换"
                        rr['original_equal_t_year'] = replace_level + "必换"
                    return result_dict

                equal_t_d = int(rec_d.equal_lifetime_t) if rec_d.equal_lifetime_t else None
                equal_sf_d = float(rec_d.equal_lifetime_sf) if rec_d.equal_lifetime_sf else None
                for part in parts_d:
                    pso_category_tasks.append(
                        run_d_part_pso(part, equal_t_d, equal_sf_d)
                    )

                # print('pso_category_tasks count:', len(pso_category_tasks))
            if pso_category_tasks:
                category_results_list = await asyncio.gather(*pso_category_tasks)
                # print('category_results_list count:', len(category_results_list))
                # 合并到 pso_results
                for cat_res in category_results_list:
                    for part_key, rr in cat_res.items():
                        pso_results[part_key] = rr
            # print('pso_results', pso_results)
            # b_task = c_task = None
            # tasks_to_run = []
            # if 'B' in category_map:
            #     rec_b = category_map['B']
            #     parts_b = json.loads(rec_b.parts) if isinstance(rec_b.parts, str) else rec_b.parts
            #     t_b = int(rec_b.equal_lifetime_t) if rec_b.equal_lifetime_t else None
            #     sf_b = float(rec_b.equal_lifetime_sf) if rec_b.equal_lifetime_sf else None
            #     year_b = rec_b.equal_lifetime_t_year
            #     if parts_b:
            #         tasks_to_run.append(('B', parts_b, t_b, sf_b,year_b))
            # if 'C' in category_map:
            #     rec_c = category_map['C']
            #     parts_c = json.loads(rec_c.parts) if isinstance(rec_c.parts, str) else rec_c.parts
            #     t_c = int(rec_c.equal_lifetime_t) if rec_c.equal_lifetime_t else None
            #     sf_c = float(rec_c.equal_lifetime_sf) if rec_c.equal_lifetime_sf else None
            #     year_c = rec_c.equal_lifetime_t_year
            #     if parts_c:
            #         tasks_to_run.append(('C', parts_c, t_c, sf_c,year_c))
            # print('tasks_to_run',tasks_to_run)
            
            # section_end = time.time()
            # print(f"[5] 参数处理完成: {section_end - section_start:.3f}秒")
            # section_start = time.time()

            # # 并发运行 B/C 的 PSO（每个元素调用 get_result）
            # async def run_category_pso(category_label, parts_list, equal_t, equal_sf,equal_lifetime_t_year):
            #     # equal_t 可能为 None 或 int，但 get_result 需要 t:int（时间点）作为参数用于 PDF 计算
            #     # 我们传入 group time t（整体 time_point）作为 get_result 的 t 参数（保持一致）
            #     result_dict = await EqualLifetimeService.get_result(model, parts_list, target_sf, equal_t, equal_sf, t)
            #     # 给每个 part 添加 category 标记
            #     for part_key, rr in result_dict.items():
            #         rr['category'] = category_label
            #         rr['equal_lifetime_t_year'] = equal_lifetime_t_year
            #     return result_dict

            # # gather all category PSO tasks
            # pso_category_tasks = [
            #     run_category_pso(cat, ps, et, es, ys) for (cat, ps, et, es, ys) in tasks_to_run
            # ]
            # print('pso_category_tasks', pso_category_tasks)
            # if pso_category_tasks:
            #     category_results_list = await asyncio.gather(*pso_category_tasks)
            #     print('category_results_list', category_results_list)
            #     # 合并到 pso_results
            #     for cat_res in category_results_list:
            #         for part_key, rr in cat_res.items():
            #             pso_results[part_key] = rr
            # print('pso_results', pso_results)


            
            
            section_end = time.time()
            print(f"[6] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()


            # 5. 准备绘图输入

            # code->name 映射
            failure_parts = await failure_dao.get_parts_with_names_only_by_model(db, model)
            code_to_name = {code: name for name, code in failure_parts}

            # 标注每个 part 的 category（若某个 part 未在 pso_results 中出现，可能是没有分到任何分类）
            # for part in parts_all:
            #     if part not in pso_results:
            #         # 尝试查找该部件所属分类（基于 category_map 中的 parts 列表）
            #         assigned = False
            #         for cat_label, rec in category_map.items():
            #             rec_parts = json.loads(rec.parts) if isinstance(rec.parts, str) else rec.parts
            #             if part in rec_parts:
            #                 pso_results[part] = {
            #                     'part': part,
            #                     'original_distribution': await distribute_service.get_part_distribution(model, part),
            #                     'original_pdf': None,
            #                     'original_equal_point_pdf': None,
            #                     'need_optimization': False,
            #                     'category': cat_label
            #                 }
            #                 assigned = True
            #                 break
            #         if not assigned:
            #             # 最后兜底：原始分布
            #             dist = await distribute_service.get_part_distribution(model, part)
            #             pso_results[part] = {
            #                 'part': part,
            #                 'original_distribution': dist,
            #                 'original_pdf': round(dist.PDF(t) * 1000000, 4),
            #                 'original_equal_point_pdf': None,
            #                 'need_optimization': False,
            #                 'category': 'unknown'
            #             }
            
            section_end = time.time()
            print(f"[7] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()

            # 6. 绘图：原始图需要展示 A/B/C 标注；优化图仅展示 B/C 优化后的结果
            # 构造 equal_points dict（按 category）
            equal_points = {}
            for cat_label in ['B', 'C']:
                if cat_label in category_map:
                    rec = category_map[cat_label]
                    if rec.equal_lifetime_t and rec.equal_lifetime_sf:
                        equal_points[cat_label] = ((rec.equal_lifetime_t_year), int(rec.equal_lifetime_t), float(rec.equal_lifetime_sf))

            # # 只把需要优化/展示的部分传给 plot_optimize_result（过滤出存在 optimized_distribution 或 need_optimization True）
            # optimized_pso_results = {
            #     k: v for k, v in pso_results.items()
            #     if v.get('need_optimization') or v.get('optimized_distribution') or v.get('optimized_pdf') is not None
            # }

            # 只把需要优化/展示的部分传给 plot_optimize_result（过滤出 B 类和 C 类）
            optimized_pso_results = {
                k: v for k, v in pso_results.items()
                if v.get('category') in ['B', 'C']
            }

            section_end = time.time()
            print(f"[7.5] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()

            # 原始图（pso_results 中包含 category 字段）
            plot_original_result = await plot_lifetime_service.plot_original_result(
                model, optimized_pso_results, t, target_sf, code_to_name, year_worktimes
            )

            plot_optimize_result = await plot_lifetime_service.plot_optimize_result(
                model, optimized_pso_results, t, equal_points, target_sf, code_to_name
            )

            section_end = time.time()
            print(f"[8] 参数处理完成: {section_end - section_start:.3f}秒")
            section_start = time.time()

            #
            # repair_year_map = await repair_plan_dao.get_lcc_parts_with_names_only_by_model(db, model, parts_all)

            # 7. 组织返回结果（保持兼容：result 列表、equal_lifetime_t 以 dict 形式返回）
            parts_results_list = []
            for part, pso_r in pso_results.items():
                parts_results_list.append({
                    "part": part,
                    "part_name": code_to_name.get(part, part),
                    "original_pdf": pso_r.get('original_pdf'),
                    "optimized_pdf": pso_r.get('optimized_pdf') if 'optimized_pdf' in pso_r else None,
                    "original_equal_point_pdf": pso_r.get('original_equal_point_pdf'),
                    # D 类（必换件）要求把 optimized_equal_point_pdf 设为 optimized_pdf 的结果
                    "optimized_equal_point_pdf": (
                        pso_r.get('optimized_pdf') if pso_r.get('category') == 'D' else (
                            pso_r.get('optimized_equal_point_pdf') if 'optimized_equal_point_pdf' in pso_r else None
                        )
                    ),
                    "need_optimization": pso_r.get('need_optimization', False),
                    "category": pso_r.get('category'),
                    "equal_lifetime_t_year": pso_r.get('equal_lifetime_t_year'),
                    "rapair_plan": pso_r.get('original_equal_t_year'),
                    # "rapair_plan": repair_year_map.get(part) if part in repair_year_map else '偶换',
                })

            parts_results_list = sorted(parts_results_list, key=lambda x: (x['category'], x['rapair_plan']), reverse=True)
            return {
                "result": parts_results_list,
                "equal_lifetime_points": equal_points,  # per-category equal lifetime points
                "img_original_result": plot_original_result,
                "img_optimize_result": plot_optimize_result,
            }
        
    @staticmethod
    async def get_all_models():
        """
        获取所有型号:获取所有能够计算等寿命设计的型号,级联筛选获取所有能满足等寿命设计的型号
        """
        async with async_db_session() as db:
            models = await fit_part_dao.get_distinct_column_values(db, 'model')
            if not models:
                raise errors.NotFoundError(msg='故障数据中未找到产品型号')
            return models
        
    
    @staticmethod
    async def get_all_parts(model: str):
        """
        获取所有零部件
        返回格式: [("零部件名称", "零部件物料编码"), ...]
        """
        try:
            async with async_db_session() as db:
                # 1. 获取fit_part表中该型号的所有零部件
                parts = await fit_part_dao.get_parts_for_lifetime_by_model1(db, model)   

                # 2. 获取故障表中该型号的所有零部件名称和编码映射
                failure_parts = await failure_dao.get_parts_with_names_only_by_model(db, model)
                # 3. 创建编码到名称的映射字典
                code_to_name = {code: name for name, code in failure_parts}
                
                # 4. 筛选出既有分布数据又有名称的零部件，返回二元组
                result = []
                for part_code in parts:
                    if part_code in code_to_name:
                        result.append((code_to_name[part_code], part_code))
                
                return result
                
        except Exception as e:
            raise DataValidationError(msg=f"获取所有零部件时发生错误: {str(e)}")
        

    @staticmethod
    async def delete_all_equal_lifetime() -> None:
        """清空所有等寿命数据"""
        async with async_db_session.begin() as db:
            await equal_lifetime_dao.delete_all(db)



    
equal_lifetime_service: EqualLifetimeService = EqualLifetimeService()