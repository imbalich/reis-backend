#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：reis-backend
@File    ：cycle_life_service.py
@IDE     ：PyCharm
@Author  ：Seven-ln
@Date    ：2025/9/10 09:48
"""
import logging
from typing import Any
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.common.exception.errors import DataValidationError
from backend.common.exception import errors
from backend.database.db import async_db_session
from backend.app.calcu.service.reliability_index_service import reliability_index_service
from backend.app.lcc.schema.cycle_life_service import CycleLifeSchemaBase, CycleLifeTotalSchemaBase
from backend.app.fit.crud.crud_fit_part import fit_part_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.common.exception.errors import DataValidationError
logger = logging.getLogger(__name__)

class CycleLifeService:

    @staticmethod
    async def get_cycle_life_result(items: list[dict], life:int) -> dict[str, Any]:
        async with async_db_session() as db:
            # 创建一个列表来存储所有处理后的结果
            results = []            
            for item in items:
                result = {}
                result['model'] = item['model']
                parts = item['part']
                # 判断传递的数据中part是否为空
                if item['part'] is None or len(item['part']) == 0: 
                    item['part'] = await CycleLifeService.get_all_parts(result['model'])
                    parts = item['part']
                for part in parts:
                    result['part'] = part
                    ebom_data = await ebom_dao.get_by_model_and_part(db, result['model'], result['part'])
                    if ebom_data is None:
                        raise errors.DataValidationError(msg=f'型号{item['model']}+部件{item['part']}的没有Ebom数据')
                    result['part_number'] = len(ebom_data)
                    year_worktimes = await CycleLifeService.year_worktimes(result['model'])
                    time = year_worktimes*life
                    falut = await CycleLifeService.get_fault_number_by_part(result['model'], result['part'], time)
                    result['falut_number'] = round(falut * result['part_number'],4)
                    replace = await CycleLifeService.get_replace_number(result['model'], result['part'], life)
                    result['replace_number'] = int(replace['replace_number'] * result['part_number'])
                    result['build_repair_retio'] = round(
                        (result['falut_number'] + result['replace_number']) / result['part_number'],2)
                    result['totle_number'] = result['falut_number'] + result['replace_number'] + result['part_number']
                    result['part_name'] = replace['part_name']
                    # 创建 CycleLifeSchemaBase 实例并添加到结果列表
                    cycle_life_schema = CycleLifeSchemaBase(**result)
                    results.append(cycle_life_schema)
            # 按 build_repair_retio 升序排序
            sorted_results = sorted(results, key=lambda x: x.build_repair_retio)
            
            # 为每个元素分配排名（最小为1）
            for index, instance in enumerate(sorted_results, start=1):
                instance.order = index
            
            return CycleLifeTotalSchemaBase(result=sorted_results)
    
    @staticmethod
    async def get_fault_number_by_part(model,part,time) -> float:
        # 计算故障次数
        best_distribution = await reliability_index_service._get_best_distribution(model, part)
        if best_distribution is None:
            raise errors.DataValidationError(msg=f'型号{model}+部件{part}的无故障数据，因此分布信息不存在')
        falut_number = best_distribution.CDF(time) - best_distribution.CDF(0)
        return falut_number
   
    @staticmethod
    async def get_replace_number(model, part, life):
        async with async_db_session() as db:
            replace_data = await replace_dao.get_all_by_model_and_part(db, model, part)
            if not replace_data:
                raise errors.DataValidationError(msg=f'型号{model}+部件{part}的必换件数据不存在')
            replace_cycles = [item.replace_cycle for item in replace_data]
            part_name = [item.part_name for item in replace_data][0]
            if len(replace_cycles) == 1:
                replace_number = life // replace_cycles[0]                
            elif len(replace_cycles) > 1:
                if (replace_cycles[1] / replace_cycles[0]) % 1 == 0:
                    replace_number = life // replace_cycles[0]
                else:
                    replace_number = life // replace_cycles[0] + life // replace_cycles[1]
            return {
                'replace_number': replace_number,
                'part_name': part_name
            }
        
    @staticmethod
    async def year_worktimes(model:str):
        '''
        年运行小时
        :param model: 产品型号
        :return: 年运行小时
        '''
        async with async_db_session() as db:
            try:
                product_date = await product_dao.get_by_model(db, model)
                if product_date.year_days is None or product_date.avg_worktime is None:
                    raise DataValidationError(
                        msg=f"型号为 {model} 的产品信息不存在"
                    )
                year_worktimes = product_date.year_days * product_date.avg_worktime
                return year_worktimes
            except DataValidationError:
                raise
    
    @staticmethod
    async def get_all_parts(model: str):
        """
        获取model下所有零部件编码
        """
        try:
            async with async_db_session() as db:
                # 1. 获取fit_part表中该型号的所有零部件
                parts = await fit_part_dao.get_parts_for_lifetime_by_model(db, model)      

                # 2. 创建有效零部件列表
                valid_parts = []

                # 3. 验证每个部件是否同时存在于EBOM和成本数据中
                for part in parts:
                    # 检查产品信息数据是否存在
                    product_date = await product_dao.get_by_model(db, model)
                    # 检查必换件数据
                    replace_data = await replace_dao.get_all_by_model_and_part(db, model, part)
                
                    # 仅当两个数据源都存在时才保留该部件
                    if product_date.year_days and product_date.avg_worktime and replace_data:
                        valid_parts.append(part)
                    else:
                        # 可选：添加日志记录缺失数据的部件
                        logger.warning(
                            f"部件 {part} 缺少必要数据 - 产品信息: {bool(product_date)}, 必换件: {bool(replace_data)}")
                        pass
            
            return valid_parts
                
        except Exception as e:
            raise DataValidationError(msg=f"获取所有零部件时发生错误: {str(e)}")
        


    @staticmethod
    async def get_parts_by_model(model: str):
        """
        获取model下所有零部件编码,用于级联查询
        """
        try:
            async with async_db_session() as db:
                # 1. 获取fit_part表中该型号的所有零部件
                parts = await fit_part_dao.get_parts_for_lifetime_by_model(db, model)

                # 2、# 检查产品信息数据是否存在
                product_date = await product_dao.get_by_model(db, model)      

                if product_date.year_days is None or product_date.avg_worktime is None:
                    return None
                
                # 3、获取必换件信息
                replace_parts = await replace_dao.get_replace_parts_with_names_only_by_model(db, model)

                # 5. 创建编码到名称的映射字典
                code_to_name = {code: name for name, code in replace_parts}
                
                # 6. 筛选出既有分布数据又有名称的零部件，返回二元组
                result = []
                for part_code in parts:
                    if part_code in code_to_name:
                        result.append((code_to_name[part_code], part_code))
            
            return result
                
        except Exception as e:
            raise DataValidationError(msg=f"获取所有零部件时发生错误: {str(e)}")


cycle_life_service: CycleLifeService = CycleLifeService()