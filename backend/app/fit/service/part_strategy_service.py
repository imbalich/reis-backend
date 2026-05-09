#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : part_strategy_service.py
"""

from datetime import date

from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_repair import repair_dao
from backend.app.fit.schema.base_param import (
    DespatchParam,
    EbomParam,
    FailureParam,
    ProductParam,
    RepairParam,
)
from backend.app.fit.service.part_tag_process_service import part_tag_process_service
from backend.app.fit.utils.convert_model import (
    convert_dict_to_pydantic_model,
    convert_to_pydantic_model,
    convert_to_pydantic_models,
    convert_to_total_quantity,
    get_ebom_tree_with_parents,
)
from backend.app.fit.utils.data_check_utils import datacheckutils
from backend.app.fit.utils.time_utils import dateutils
from backend.common.exception import errors
from backend.common.log import log
from backend.database.db import async_db_session


class PartStrategyService:
    @staticmethod
    async def part_tag_process(
        model: str,
        part: str,
        input_date: str | date = None,
        product_config_code: str | None = None,
    ) -> list[list]:
        input_date = dateutils.validate_and_parse_date(input_date)
        product_check = await datacheckutils.check_model_in_product(
            model,
            product_config_code=product_config_code,
        )
        if not product_check:
            raise errors.DataValidationError(msg=f"型号{model}的产品信息不存在")

        run_time_check = await datacheckutils.check_model_in_despatch(
            model,
            product_config_code=product_config_code,
        )
        if not run_time_check:
            raise errors.DataValidationError(msg=f"型号{model}的累计运行时间不足")

        fault_check = await datacheckutils.check_model_and_part_in_failure(
            model,
            part,
            product_config_code=product_config_code,
        )
        if not fault_check:
            raise errors.FailureCheckError(
                msg=f"型号{model}+零部件{part}的故障信息数量不足"
            )

        async with async_db_session() as db:
            try:
                despatch_data = convert_to_pydantic_models(
                    await despatch_dao.get_despatchs_by_model(
                        db,
                        model,
                        product_config_code=product_config_code,
                    ),
                    DespatchParam,
                )
                failure_data = convert_to_pydantic_models(
                    await failure_dao.get_by_model_and_part(
                        db,
                        model,
                        part,
                        product_config_code=product_config_code,
                    ),
                    FailureParam,
                )

                log.info(
                    "[零部件打标] 型号{} 零部件{} 故障数据共{}",
                    model,
                    part,
                    len(failure_data),
                )

                product_data = convert_to_pydantic_model(
                    await product_dao.get_by_model(
                        db,
                        model,
                        product_config_code=product_config_code,
                    ),
                    ProductParam,
                )
                if product_data.repair_times is None or product_data.repair_times == 0:
                    raise errors.DataValidationError(
                        msg=f"型号{model}的产品信息中repair_times为0或不存在"
                    )

                ebom_rows = await get_ebom_tree_with_parents(
                    db,
                    model,
                    product_config_code,
                    part,
                )
                if not ebom_rows:
                    raise errors.DataValidationError(
                        msg=f"型号{model}的零部件{part}的BOM信息不存在"
                    )

                total_bl_quantity = convert_to_total_quantity(ebom_rows, part)
                filtered_ebom_rows = [
                    item
                    for item in ebom_rows
                    if hasattr(item, "y8_matbnum1")
                    and getattr(item, "y8_matbnum1", None) is not None
                ]
                if not filtered_ebom_rows:
                    raise errors.DataValidationError(
                        msg=f"型号{model}的零部件{part}的BOM信息中未找到有效节点"
                    )
                ebom_items = convert_to_pydantic_models(filtered_ebom_rows, EbomParam)
                ebom_data = convert_dict_to_pydantic_model(
                    {
                        "prd_no": model,
                        "y8_matbnum1": part,
                        "y8_matname": getattr(ebom_items[0], "y8_matname", None),
                        "bl_quantity": str(total_bl_quantity),
                    },
                    EbomParam,
                )

                repair_rows = await repair_dao.get_by_model(
                    db,
                    model,
                    product_config_code=product_config_code,
                )
                repair_data = None
                repair_despatch_data = None
                if repair_rows:
                    repair_data = convert_to_pydantic_models(repair_rows, RepairParam)
                    repair_despatch_data = convert_to_pydantic_models(
                        await despatch_dao.get_by_model_exclude_repair_level(
                            db,
                            model,
                            product_config_code=product_config_code,
                        ),
                        DespatchParam,
                    )

                if repair_data and repair_despatch_data:
                    tags = await part_tag_process_service.process_data(
                        despatch_data,
                        failure_data,
                        product_data,
                        ebom_data,
                        input_date,
                        repair_data=repair_data,
                        repair_despatch_data=repair_despatch_data,
                    )
                else:
                    tags = await part_tag_process_service.process_data(
                        despatch_data,
                        failure_data,
                        product_data,
                        ebom_data,
                        input_date,
                    )

                log.info(
                    "[零部件打标] 型号{} 零部件{} 打标完成，标签条数{}",
                    model,
                    part,
                    len(tags) if tags else 0,
                )
                return tags
            except errors.DataValidationError as exc:
                raise errors.DataValidationError(msg=exc.msg)
            except Exception as exc:
                raise errors.DataValidationError(
                    msg=f"型号{model}+零部件{part}打标失败, 失败原因: {str(exc)}"
                )

    @staticmethod
    async def part_tag_process_with_failures(
        model: str,
        part: str,
        input_date: str | date = None,
        filtered_failures: list = None,
        product_config_code: str | None = None,
    ) -> list[list]:
        input_date = dateutils.validate_and_parse_date(input_date)

        product_check = await datacheckutils.check_model_in_product(
            model,
            product_config_code=product_config_code,
        )
        if not product_check:
            raise errors.DataValidationError(msg=f"型号{model}的产品信息不存在")

        run_time_check = await datacheckutils.check_model_in_despatch(
            model,
            product_config_code=product_config_code,
        )
        if not run_time_check:
            raise errors.DataValidationError(msg=f"型号{model}的累计运行时间不足")

        if not filtered_failures:
            raise errors.FailureCheckError(
                msg=f"型号{model}+零部件{part}的故障信息数量不足"
            )

        async with async_db_session() as db:
            try:
                despatch_data = convert_to_pydantic_models(
                    await despatch_dao.get_despatchs_by_model(
                        db,
                        model,
                        product_config_code=product_config_code,
                    ),
                    DespatchParam,
                )
                failure_data = convert_to_pydantic_models(
                    filtered_failures,
                    FailureParam,
                )
                product_data = convert_to_pydantic_model(
                    await product_dao.get_by_model(
                        db,
                        model,
                        product_config_code=product_config_code,
                    ),
                    ProductParam,
                )

                ebom_rows = await get_ebom_tree_with_parents(
                    db,
                    model,
                    product_config_code,
                    part,
                )
                if not ebom_rows:
                    raise errors.DataValidationError(
                        msg=f"型号{model}的零部件{part}的BOM信息不存在"
                    )

                total_bl_quantity = convert_to_total_quantity(ebom_rows, part)
                filtered_ebom_rows = [
                    item
                    for item in ebom_rows
                    if hasattr(item, "y8_matbnum1")
                    and getattr(item, "y8_matbnum1", None) is not None
                ]
                if not filtered_ebom_rows:
                    raise errors.DataValidationError(
                        msg=f"型号{model}的零部件{part}的BOM信息中未找到有效节点"
                    )
                ebom_items = convert_to_pydantic_models(filtered_ebom_rows, EbomParam)
                ebom_data = convert_dict_to_pydantic_model(
                    {
                        "prd_no": model,
                        "y8_matbnum1": part,
                        "y8_matname": getattr(ebom_items[0], "y8_matname", None),
                        "bl_quantity": str(total_bl_quantity),
                    },
                    EbomParam,
                )

                repair_rows = await repair_dao.get_by_model(
                    db,
                    model,
                    product_config_code=product_config_code,
                )
                repair_data = None
                repair_despatch_data = None
                if repair_rows:
                    repair_data = convert_to_pydantic_models(repair_rows, RepairParam)
                    repair_despatch_data = convert_to_pydantic_models(
                        await despatch_dao.get_by_model_exclude_repair_level(
                            db,
                            model,
                            product_config_code=product_config_code,
                        ),
                        DespatchParam,
                    )

                if repair_data and repair_despatch_data:
                    return await part_tag_process_service.process_data(
                        despatch_data,
                        failure_data,
                        product_data,
                        ebom_data,
                        input_date,
                        repair_data=repair_data,
                        repair_despatch_data=repair_despatch_data,
                    )
                return await part_tag_process_service.process_data(
                    despatch_data,
                    failure_data,
                    product_data,
                    ebom_data,
                    input_date,
                )
            except errors.DataValidationError as exc:
                raise errors.DataValidationError(msg=exc.msg)
            except Exception as exc:
                raise errors.DataValidationError(
                    msg=f"型号{model}+零部件{part}打标失败, 失败原因: {str(exc)}"
                )


part_strategy_service: PartStrategyService = PartStrategyService()
