#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : fastapi-base-backend
@File    : part_tag_process_service.py
"""

from datetime import date, timedelta
from typing import Any

from backend.app.datamanage.model import Despatch, Ebom, FailureModel, Product
from backend.app.fit.schema.base_param import (
    DespatchParam,
    EbomParam,
    FailureParam,
    RepairParam,
)
from backend.app.fit.service.tag_process_service import TagProcessService
from backend.app.fit.utils.time_utils import dateutils


class PartTagProcessService(TagProcessService):
    async def process_data(
        self,
        despatch_data: list[Despatch],
        failure_data: list[FailureModel],
        product_data: Product,
        bom_data: Ebom,
        input_date: str | date = None,
        **kwargs: Any,
    ) -> list[list]:
        repair_data = kwargs.get("repair_data")
        repair_despatch_data = kwargs.get("repair_despatch_data")
        if not repair_data or not repair_despatch_data:
            return await self._process_non_essential(
                despatch_data,
                failure_data,
                product_data,
                bom_data,
                input_date,
            )
        return await self._process_essential(
            despatch_data,
            failure_data,
            product_data,
            bom_data,
            repair_data,
            repair_despatch_data,
            input_date,
        )

    async def _process_non_essential(
        self,
        despatch_data: list[Despatch],
        failure_data: list[FailureModel],
        product_data: Product,
        bom_data: Ebom,
        input_date: str | date = None,
    ) -> list[list]:
        despatch_data = await self.process_despatch_data(despatch_data, input_date)
        failure_data = await self.process_failure_data(failure_data, input_date)
        bom_data = (
            EbomParam.model_validate(bom_data)
            if not isinstance(bom_data, EbomParam)
            else bom_data
        )
        container = await self.container_create(despatch_data, bom_data)
        container = await self.container_inspect(container, failure_data, bom_data)
        container, error_info_list = await self.container_insert_non_essential(
            container,
            failure_data,
        )
        tags = await self.tag_create_non_essential(container, product_data, input_date)
        data = {"tags": tags}
        if error_info_list:
            data["error_info_list"] = error_info_list
        return data["tags"]

    async def _process_essential(
        self,
        despatch_data: list[Despatch],
        failure_data: list[FailureModel],
        product_data: Product,
        bom_data: Ebom,
        repair_data: list[RepairParam],
        repair_despatch_data: list[Despatch],
        input_date: str | date = None,
    ) -> list[list]:
        despatch_data = await self.process_despatch_data(despatch_data, input_date)
        failure_data = await self.process_failure_data(failure_data, input_date)
        bom_data = (
            EbomParam.model_validate(bom_data)
            if not isinstance(bom_data, EbomParam)
            else bom_data
        )
        repair_despatch_data = await self.process_despatch_data(
            repair_despatch_data,
            input_date,
        )
        container = await self.container_create(despatch_data, bom_data)
        container = await self.container_inspect(container, failure_data, bom_data)
        container, error_info_list_repair = await self.container_insert_essential_repair(
            container,
            repair_despatch_data,
        )
        container, error_info_list_failure = await self.container_insert_non_essential(
            container,
            failure_data,
        )
        tags = await self.tag_create_essential(container, product_data, input_date)
        results = {"tags": tags}
        if error_info_list_repair:
            results["error_info_list_repair"] = error_info_list_repair
        if error_info_list_failure:
            results["error_info_list_failure"] = error_info_list_failure
        return results["tags"]

    async def process_despatch_data(
        self,
        despatch_data: list[Despatch],
        input_date: date,
    ):
        return await super().process_despatch_data(despatch_data, input_date)

    async def process_failure_data(
        self,
        failure_data: list[FailureModel],
        input_date: date,
    ):
        return await super().process_failure_data(failure_data, input_date)

    @staticmethod
    async def container_create(
        despatch_data: list[DespatchParam],
        bom_data: EbomParam,
    ) -> dict[str, Any]:
        result = {
            "model": bom_data.prd_no,
            "part_name": bom_data.y8_matname,
            "part_code": bom_data.y8_matbnum1,
            "part_container": {},
        }
        for despatch in despatch_data:
            product = {
                "source": "despatch_data",
                "despatch_date": despatch.life_cycle_time + timedelta(days=90),
                "sub_container": {},
            }
            for i in range(int(bom_data.bl_quantity)):
                material_code_virtual = f"{bom_data.y8_matbnum1}-{i + 1}"
                product["sub_container"][material_code_virtual] = {
                    "fault_date_list": [
                        (despatch.life_cycle_time + timedelta(days=90), "despatch", 1)
                    ],
                    "fault_part_list": [],
                }
            result["part_container"][despatch.identifier] = product
        return result

    @staticmethod
    async def container_inspect(
        container: dict[str, Any],
        failure_data: list[FailureParam],
        bom_data: EbomParam,
    ) -> dict[str, Any]:
        for failure in failure_data:
            if failure.manufacturing_date is None:
                continue
            if failure.product_number in container["part_container"]:
                if (
                    failure.manufacturing_date
                    < container["part_container"][failure.product_number]["despatch_date"]
                ):
                    container["part_container"][failure.product_number][
                        "despatch_date"
                    ] = failure.manufacturing_date
            if failure.product_number not in container["part_container"]:
                product = {
                    "source": "failure_data",
                    "despatch_date": failure.manufacturing_date + timedelta(days=90),
                    "sub_container": {},
                }
                for i in range(int(bom_data.bl_quantity)):
                    material_code_virtual = f"{bom_data.y8_matbnum1}-{i + 1}"
                    product["sub_container"][material_code_virtual] = {
                        "fault_date_list": [
                            (
                                failure.manufacturing_date + timedelta(days=90),
                                "despatch",
                                1,
                            )
                        ],
                        "fault_part_list": [],
                    }
                container["part_container"][failure.product_number] = product
        return container

    @staticmethod
    async def container_insert_non_essential(
        container: dict[str, Any],
        failure_data: list[FailureParam],
    ) -> tuple[dict, list]:
        error_info_list = []
        for failure in failure_data:
            is_used = False
            for _, pt in container["part_container"][failure.product_number][
                "sub_container"
            ].items():
                if (
                    len(pt["fault_part_list"]) > 0
                    and pt["fault_part_list"][-1] == failure.fault_part_number
                    and not is_used
                ):
                    pt["fault_part_list"].append(failure.replacement_part_number)
                    pt["fault_date_list"].append((failure.discovery_date, "failure", 0))
                    is_used = True
                    break
                if len(pt["fault_part_list"]) == 0 and not is_used:
                    pt["fault_part_list"].append(failure.replacement_part_number)
                    pt["fault_date_list"].append((failure.discovery_date, "failure", 0))
                    is_used = True
                    break
            if not is_used:
                for _, pt in container["part_container"][failure.product_number][
                    "sub_container"
                ].items():
                    if failure.fault_part_number in pt["fault_part_list"]:
                        pt["fault_part_list"].append(failure.replacement_part_number)
                        pt["fault_date_list"].append(
                            (failure.discovery_date, "failure", 0)
                        )
                        is_used = True
                        break
            if not is_used:
                container["part_container"][failure.product_number]["sub_container"][
                    failure.fault_material_code + "-1"
                ]["fault_part_list"].append(failure.replacement_part_number)
                container["part_container"][failure.product_number]["sub_container"][
                    failure.fault_material_code + "-1"
                ]["fault_date_list"].append((failure.discovery_date, "failure", 0))
                is_used = True
            if not is_used:
                error_info_message = (
                    f"型号 {failure.product_model} 部件 {failure.fault_location} "
                    f"物料编码 {failure.fault_material_code} 故障报告ID {failure.report_id} "
                    "故障插入失败，请核查数据完整性"
                )
                error_info_list.append(error_info_message)
        return container, error_info_list

    @staticmethod
    async def tag_create_non_essential(
        container: dict[str, Any],
        product_data: Product,
        input_date: date,
    ) -> list[list[Any]]:
        result = []
        for bh, part in container["part_container"].items():
            for vt, context in part["sub_container"].items():
                context["fault_date_list"].append((input_date, "end", 99))
                for i in range(1, len(context["fault_date_list"])):
                    diff = (
                        context["fault_date_list"][i][0]
                        - context["fault_date_list"][i - 1][0]
                    )
                    t = dateutils.run_time(
                        diff.days,
                        product_data.year_days,
                        product_data.avg_worktime,
                    )
                    cur = [
                        bh,
                        vt,
                        context["fault_date_list"][i - 1][0],
                        context["fault_date_list"][i][0],
                        diff.days,
                        t,
                    ]
                    cur.append("suspense" if i == len(context["fault_date_list"]) - 1 else "failure")
                    result.append(cur)
        return result

    @staticmethod
    async def container_insert_essential_repair(
        container: dict[str, Any],
        repair_despatch_data: list[DespatchParam],
    ) -> tuple[dict, list]:
        error_info_list = []
        for despatch in repair_despatch_data:
            if despatch.identifier in container["part_container"]:
                for _, pt in container["part_container"][despatch.identifier][
                    "sub_container"
                ].items():
                    if despatch.life_cycle_time <= pt["fault_date_list"][-1][0]:
                        error_info_message = (
                            f"产品 {despatch.model} 编号 {despatch.identifier} "
                            f"等级修 {despatch.repair_level} 插入失败, "
                            f"时间 {despatch.life_cycle_time} "
                            f"小于前值 {pt['fault_date_list'][-1][0]}"
                        )
                        error_info_list.append(error_info_message)
                        break
                    pt["fault_date_list"].append(
                        (despatch.life_cycle_time, "repair", despatch.repair_level_num)
                    )
        return container, error_info_list

    @staticmethod
    async def tag_create_essential(
        container: dict[str, Any],
        product_data: Product,
        input_date: date,
    ) -> list[list[Any]]:
        result = []
        for bh, part in container["part_container"].items():
            for vt, context in part["sub_container"].items():
                context["fault_date_list"] = sorted(
                    context["fault_date_list"],
                    key=lambda x: x[0],
                )
                context["fault_date_list"].append((input_date, "end", 99))
                for i in range(1, len(context["fault_date_list"])):
                    diff = (
                        context["fault_date_list"][i][0]
                        - context["fault_date_list"][i - 1][0]
                    )
                    if context["fault_date_list"][i][1] in ["repair", "end"]:
                        cur = [
                            bh,
                            vt,
                            context["fault_date_list"][i - 1][0],
                            context["fault_date_list"][i][0],
                        ]
                        if diff.days <= product_data.repair_times:
                            cur.append(diff.days)
                            t = dateutils.run_time(
                                diff.days,
                                product_data.year_days,
                                product_data.avg_worktime,
                            )
                            cur.append(t)
                            cur.append("suspense")
                        else:
                            cur.append(product_data.repair_times)
                            t = dateutils.run_time(
                                product_data.repair_times,
                                product_data.year_days,
                                product_data.avg_worktime,
                            )
                            cur.append(t)
                            cur.append("suspense")
                        result.append(cur)
                    if context["fault_date_list"][i][1] == "failure":
                        if diff.days <= product_data.repair_times:
                            t = dateutils.run_time(
                                diff.days,
                                product_data.year_days,
                                product_data.avg_worktime,
                            )
                            cur = [
                                bh,
                                vt,
                                context["fault_date_list"][i - 1][0],
                                context["fault_date_list"][i][0],
                                diff.days,
                                t,
                                "failure",
                            ]
                            result.append(cur)
                        else:
                            _, remainder = divmod(diff.days, product_data.repair_times)
                            t = dateutils.run_time(
                                product_data.repair_times,
                                product_data.year_days,
                                product_data.avg_worktime,
                            )
                            result.append(
                                [
                                    bh,
                                    vt,
                                    context["fault_date_list"][i - 1][0],
                                    context["fault_date_list"][i][0],
                                    product_data.repair_times,
                                    t,
                                    "suspense",
                                ]
                            )
                            t = dateutils.run_time(
                                remainder,
                                product_data.year_days,
                                product_data.avg_worktime,
                            )
                            result.append(
                                [
                                    bh,
                                    vt,
                                    context["fault_date_list"][i - 1][0],
                                    context["fault_date_list"][i][0],
                                    remainder,
                                    t,
                                    "failure",
                                ]
                            )
        return result


part_tag_process_service: PartTagProcessService = PartTagProcessService()
