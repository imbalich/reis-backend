#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import date

from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_repair import repair_dao
from backend.app.datamanage.crud.crud_replace import replace_dao
from backend.app.fit.schema.base_param import (
    DespatchParam,
    EbomParam,
    ProductParam,
    RepairParam,
    ReplaceParam,
)
from backend.app.fit.utils.convert_model import (
    convert_dict_to_pydantic_model,
    convert_to_pydantic_model,
    convert_to_pydantic_models,
    convert_to_total_quantity,
    get_ebom_tree_with_parents,
)
from backend.app.fit.utils.data_check_utils import datacheckutils
from backend.app.fit.utils.time_utils import dateutils
from backend.app.fit_aaron.service.aaron_part_data_service import aaron_part_data_service
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
        await PartStrategyService._check_base_data(
            model,
            part,
            product_config_code=product_config_code,
            check_failure=False,
        )

        async with async_db_session() as db:
            try:
                raw_despatch_data = await despatch_dao.get_despatchs_by_model(
                    db,
                    model,
                    product_config_code=product_config_code,
                )
                raw_failure_data = await failure_dao.get_by_model_and_part(
                    db,
                    model,
                    part,
                    input_date,
                    product_config_code=product_config_code,
                )
                if not raw_failure_data:
                    raise errors.FailureCheckError(
                        msg=f"型号{model}+零部件{part}的故障信息不存在"
                    )

                raw_product_data = await product_dao.get_by_model(
                    db,
                    model,
                    product_config_code=product_config_code,
                )
                if not raw_product_data:
                    raise errors.DataValidationError(msg=f"型号{model}的产品信息不存在")

                ebom_rows = await get_ebom_tree_with_parents(
                    db,
                    model,
                    product_config_code,
                    part,
                )
                if not ebom_rows:
                    raise errors.DataValidationError(
                        msg=f"型号{model}中零部件{part}的BOM信息不存在"
                    )

                raw_replace_data = await replace_dao.get_by_model_and_part(db, model, part)

                # Aaron于2026-07-31更改：新版本基础数据查询增加product_config_code过滤，保证派生码维度一致。
                # 新增原因：复用main_new.py中必换件与非必换件两条数据处理路径。
                # 新增作用：fit-aaron分支先生成data_result，再统一转换为威布尔可识别的tags。
                despatch_data = convert_to_pydantic_models(raw_despatch_data, DespatchParam)
                product_data = convert_to_pydantic_model(raw_product_data, ProductParam)
                replace_data = convert_to_pydantic_models(raw_replace_data, ReplaceParam)

                total_bl_quantity = convert_to_total_quantity(ebom_rows, part)
                filtered_ebom_rows = [
                    item
                    for item in ebom_rows
                    if hasattr(item, "y8_matbnum1")
                    and getattr(item, "y8_matbnum1", None) is not None
                ]
                if not filtered_ebom_rows:
                    raise errors.DataValidationError(
                        msg=f"型号{model}中零部件{part}的BOM信息缺少有效物料号"
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

                repair_data = None
                repair_despatch_data = None
                if replace_data:
                    raw_repair_data = await repair_dao.get_by_model(
                        db,
                        model,
                        product_config_code=product_config_code,
                    )
                    if not raw_repair_data:
                        raise errors.DataValidationError(msg=f"型号{model}的产品信息不存在")
                    repair_data = convert_to_pydantic_models(raw_repair_data, RepairParam)
                    repair_despatch_data = convert_to_pydantic_models(
                        await despatch_dao.get_by_model_exclude_repair_level(
                            db,
                            model,
                            product_config_code=product_config_code,
                        ),
                        DespatchParam,
                    )

                tags = await aaron_part_data_service.build_tags(
                    model=model,
                    part=part,
                    despatch_data=despatch_data,
                    failure_data=raw_failure_data,
                    product_data=product_data,
                    ebom_data=ebom_data,
                    replace_data=replace_data,
                    repair_data=repair_data,
                    repair_despatch_data=repair_despatch_data,
                    input_date=input_date,
                )
                log.info(
                    "[Aaron标签构建] 型号{} 派生码{} 零部件{} tags数量{}",
                    model,
                    product_config_code,
                    part,
                    len(tags) if tags else 0,
                )
                return tags
            except errors.FailureCheckError as exc:
                raise errors.FailureCheckError(msg=exc.msg)
            except errors.DataValidationError as exc:
                raise errors.DataValidationError(msg=exc.msg)
            except Exception as exc:
                raise errors.DataValidationError(
                    msg=f"型号{model}+零部件{part}处理失败，错误信息: {str(exc)}"
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
        await PartStrategyService._check_base_data(
            model,
            part,
            product_config_code=product_config_code,
            check_failure=False,
        )

        if not filtered_failures:
            raise errors.FailureCheckError(
                msg=f"型号{model}+零部件{part}的故障信息不存在"
            )

        async with async_db_session() as db:
            try:
                raw_despatch_data = await despatch_dao.get_despatchs_by_model(
                    db,
                    model,
                    product_config_code=product_config_code,
                )
                raw_product_data = await product_dao.get_by_model(
                    db,
                    model,
                    product_config_code=product_config_code,
                )
                ebom_rows = await get_ebom_tree_with_parents(
                    db,
                    model,
                    product_config_code,
                    part,
                )
                if not ebom_rows:
                    raise errors.DataValidationError(
                        msg=f"型号{model}中零部件{part}的BOM信息不存在"
                    )
                raw_replace_data = await replace_dao.get_by_model_and_part(db, model, part)

                despatch_data = convert_to_pydantic_models(raw_despatch_data, DespatchParam)
                product_data = convert_to_pydantic_model(raw_product_data, ProductParam)
                replace_data = convert_to_pydantic_models(raw_replace_data, ReplaceParam)
                total_bl_quantity = convert_to_total_quantity(ebom_rows, part)
                filtered_ebom_rows = [
                    item
                    for item in ebom_rows
                    if hasattr(item, "y8_matbnum1")
                    and getattr(item, "y8_matbnum1", None) is not None
                ]
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

                repair_data = None
                repair_despatch_data = None
                if replace_data:
                    raw_repair_data = await repair_dao.get_by_model(
                        db,
                        model,
                        product_config_code=product_config_code,
                    )
                    repair_data = convert_to_pydantic_models(raw_repair_data, RepairParam)
                    repair_despatch_data = convert_to_pydantic_models(
                        await despatch_dao.get_by_model_exclude_repair_level(
                            db,
                            model,
                            product_config_code=product_config_code,
                        ),
                        DespatchParam,
                    )

                return await aaron_part_data_service.build_tags(
                    model=model,
                    part=part,
                    despatch_data=despatch_data,
                    failure_data=filtered_failures,
                    product_data=product_data,
                    ebom_data=ebom_data,
                    replace_data=replace_data,
                    repair_data=repair_data,
                    repair_despatch_data=repair_despatch_data,
                    input_date=input_date,
                )
            except errors.DataValidationError as exc:
                raise errors.DataValidationError(msg=exc.msg)
            except Exception as exc:
                raise errors.DataValidationError(
                    msg=f"型号{model}+零部件{part}处理失败，错误信息: {str(exc)}"
                )

    @staticmethod
    async def _check_base_data(
        model: str,
        part: str,
        product_config_code: str | None = None,
        check_failure: bool = True,
    ) -> None:
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
            raise errors.DataValidationError(msg=f"型号{model}的发运信息不存在")

        if check_failure:
            fault_check = await datacheckutils.check_model_and_part_in_failure(
                model,
                part,
                product_config_code=product_config_code,
            )
            if not fault_check:
                raise errors.FailureCheckError(
                    msg=f"型号{model}+零部件{part}的故障信息不存在"
                )


part_strategy_service: PartStrategyService = PartStrategyService()


