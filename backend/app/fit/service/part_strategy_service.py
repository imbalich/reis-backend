#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : part_strategy_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/3/19 17:27
"""

from datetime import date

from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_ebom import ebom_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_repair import repair_dao
from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.app.fit.schema.base_param import (
    DespatchParam,
    EbomParam,
    FailureParam,
    ProductParam,
    RepairParam,
    ReplaceParam,
)
from backend.app.fit.service.part_tag_process_service import part_tag_process_service
from backend.app.fit.utils.convert_model import (
    convert_dict_to_pydantic_model,
    convert_to_pydantic_model,
    convert_to_pydantic_models,
    convert_to_total_quantity,
)
from backend.app.fit.utils.data_check_utils import datacheckutils
from backend.app.fit.utils.time_utils import dateutils
from backend.common.exception import errors
from backend.database.db import async_db_session


class PartStrategyService:
    @staticmethod
    async def part_tag_process(model: str, part: str, input_date: str | date = None) -> list[list]:
        """
        零部件级别，单型号&单零部件标签处理
        :param model: 产品型号
        :param part: 零部件物料编码
        :param input_date: 输入日期，格式为 "YYYY-MM-DD" 的字符串或 date 对象，默认为当前日期
        :return: 处理结果
        """
        # 处理 input_date 参数
        input_date = dateutils.validate_and_parse_date(input_date)
        # 处理 model & part 参数
        # 1.检查产品信息Product
        product_check = await datacheckutils.check_model_in_product(model)
        if not product_check:
            raise errors.DataValidationError(msg=f'型号{model}的产品信息不存在')
        # 2.检查故障信息Failure数量
        fault_check = await datacheckutils.check_model_and_part_in_failure(model, part)
        if not fault_check:
            raise errors.DataValidationError(msg=f'型号{model}+零部件{part}的故障信息数量不足')
        # 3.检查累计运行时间Despatch
        run_time_check = await datacheckutils.check_model_in_despatch(model)
        if not run_time_check:
            raise errors.DataValidationError(msg=f'型号{model}的累计运行时间不足')

        async with async_db_session() as db:
            try:
                # 获取基础数据
                despatch_data = convert_to_pydantic_models(
                    await despatch_dao.get_despatchs_by_model(db, model), DespatchParam
                )
                failure_data = convert_to_pydantic_models(
                    await failure_dao.get_by_model_and_part(db, model, part), FailureParam
                )
                product_data = convert_to_pydantic_model(await product_dao.get_by_model(db, model), ProductParam)
                ebom_data = await ebom_dao.get_by_model_and_part(db, model, part)
                if not ebom_data:
                    raise errors.DataValidationError(msg=f'型号{model}的零部件{part}的BOM信息不存在')
                # bom合并
                ebom_data = convert_to_pydantic_models(ebom_data, EbomParam)

                # 获取bl_quantity
                total_bl_quantity = convert_to_total_quantity(ebom_data)

                # 处理ebom_dict
                ebom_dict = {
                    'prd_no': model,
                    'y8_matbnum1': part,
                    'y8_matname': ebom_data[0].y8_matname if hasattr(ebom_data[0], 'y8_matname') else None,
                    'bl_quantity': str(total_bl_quantity),
                }

                ebom_data = convert_dict_to_pydantic_model(ebom_dict, EbomParam)

                replace_data = convert_to_pydantic_models(
                    await replace_dao.get_by_model_and_part(db, model, part), ReplaceParam
                )
                # 检查必换件修程级别是否存在,不存在抛出异常
                if replace_data:
                    repair_data = await repair_dao.get_by_model(db, model)
                    if not repair_data:
                        raise errors.DataValidationError(msg=f'型号{model}的修程信息不存在')
                    repair_data = convert_to_pydantic_models(repair_data, RepairParam)
                    repair_despatch_data = convert_to_pydantic_models(
                        await despatch_dao.get_by_model_exclude_repair_level(db, model), DespatchParam
                    )

                # 打标操作
                # 根据replace_data是否存在决定传入的参数
                if replace_data and repair_data:
                    tags = await part_tag_process_service.process_data(
                        despatch_data,
                        failure_data,
                        product_data,
                        ebom_data,
                        input_date,
                        replace_data=replace_data,
                        repair_data=repair_data,
                        repair_despatch_data=repair_despatch_data,
                    )
                else:
                    tags = await part_tag_process_service.process_data(
                        despatch_data, failure_data, product_data, ebom_data, input_date
                    )

                return tags

            except errors.DataValidationError as e:
                # 直接重新抛出 DataValidationError
                raise errors.DataValidationError(msg=e.msg)

            except Exception as e:
                raise errors.DataValidationError(msg=f'型号{model}+零部件{part}打标失败,失败原因：{str(e)}')


part_strategy_service: PartStrategyService = PartStrategyService()
