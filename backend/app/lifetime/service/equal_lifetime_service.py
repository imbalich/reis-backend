#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：equal_lifetime.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/15 14:03
"""
import asyncio
import json
from typing import Any
from backend.common.exception import errors
from backend.app.calcu.service.distribute_service import distribute_service
from backend.app.lifetime.service.pso_service import pso_service
from backend.app.lifetime.service.find_point_service import find_point_service
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.lifetime.crud.crud_lifetime_new import equal_lifetimenew_dao
from backend.app.lifetime.service.plot_lifetime_service import plot_lifetime_service
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.common.exception.errors import DataValidationError
from backend.database.db import async_db_session
from backend.app.calcu.schema.distribute_param import DistributeType
from backend.app.calcu.conf import predict_settings
from backend.app.lifetime.utils.convert_model import (
    convert_to_euqal_lifetime_params1,
)
from backend.app.lifetime.schema.lifetime_param import CreateEuqalLifetimeInParam
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
            
            # 需要优化的部件，收集参数用于并发
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

        # 并发执行PSO优化
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

        if part_params_list:
            tasks = [optimize_one(params) for params in part_params_list]
            optimized_results = await asyncio.gather(*tasks)
            for result in optimized_results:
                results[result["part"]] = result
        
        return results

    @staticmethod
    async def _perform_and_save_fit(model:str, parts:list[str], target_sf:float,step_start:float,step_end:float) -> None:
        '''
        运行并保存结果
        '''
        async with async_db_session() as db:
            async with db.begin():
                result = await find_point_service.find_equal_lifetime_point(model, parts, step_start,step_end)
                distribution_params = convert_to_euqal_lifetime_params1(
                    result, model, parts,target_sf,step_start,step_end
                )
                await equal_lifetimenew_dao.creates(db, distribution_params)
    
    @staticmethod
    async def create(*, obj: CreateEuqalLifetimeInParam) -> None:
        """
        单个产品拟合：
        如果输入日期是当前日期且拟合方法为MLE，检查是否存在最近7天内的记录，如果存在，不再进行拟合
        如果用户独立输入日期或不同拟合方法，进行拟合
        """
        # 处理 input_date 参数
        await EqualLifetimeService._perform_and_save_fit(
            obj.model, obj.parts, obj.target_sf,obj.step_start,obj.step_end
        )
    
    @staticmethod
    async def get_best_by_model_and_parts(
        model: str,
        parts: list[str],
        target_sf: float,
        step_start: float,
        step_end: float
    ):
        async with async_db_session() as db:
        
            models = await equal_lifetimenew_dao.get_by_model(db, model,target_sf,step_start,step_end)
            if not models:
                return None
            
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
                    return group_results
                
            return None
        
    
    @staticmethod
    async def get_optimize_result(
        model: str,
        parts: list[str],
        target_sf: float,
        step_start: float,
        step_end: float
    ):
        async with async_db_session() as db:
            if parts is None or len(parts) == 0:
                parts = await find_point_service.get_part_by_model(model)

            optimize_result = await EqualLifetimeService.get_best_by_model_and_parts(model, parts,target_sf,step_start,step_end)
            if not optimize_result: 
                return None
            equal_lifetime_t = optimize_result[0].equal_lifetime_t
            equal_lifetime_sf = optimize_result[0].equal_lifetime_sf
            t = int(optimize_result[0].time_point)

            pso_results = await EqualLifetimeService.get_result(model, parts,target_sf,equal_lifetime_t,equal_lifetime_sf,t)
            failure_parts = await failure_dao.get_parts_with_names_only_by_model(db, model)
                
            # 2. 创建编码到名称的映射字典
            code_to_name = {code: name for name, code in failure_parts}

            if not optimize_result: 
                return None
            plot_original_result = await plot_lifetime_service.plot_original_result(model,parts,t,target_sf,pso_results)
            plot_optimize_result = await plot_lifetime_service.plot_optimize_result(model,pso_results,t,target_sf,code_to_name,equal_lifetime_t,equal_lifetime_sf)
            parts_results = []
            result = []
            for part,pso_result in pso_results.items():
                parts_results = {
                    "part": part,
                    "part_name": code_to_name[part],
                    "original_pdf": pso_result['original_pdf'],
                    "optimized_pdf": pso_result['optimized_pdf'] if 'optimized_pdf' in pso_result else None,
                    "original_equal_point_pdf": pso_result['original_equal_point_pdf'] if 'original_equal_point_pdf' in pso_result else None,
                    "optimized_equal_point_pdf": pso_result['optimized_equal_point_pdf'] if 'optimized_equal_point_pdf' in pso_result else None,
                    "need_optimization":pso_result['need_optimization']
                }
                result.append(parts_results)
            result = sorted(result, key=lambda x: x['need_optimization'], reverse=True)
            return {
                "result": result,
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
                parts = await fit_part_dao.get_parts_for_lifetime_by_model(db, model)      

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



    
equal_lifetime_service: EqualLifetimeService = EqualLifetimeService()