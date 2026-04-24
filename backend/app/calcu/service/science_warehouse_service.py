#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 绉戝搴撳瓨鏈嶅姟,鏀彺鍥介搧鍞悗闇€姹?import math
import json
import time
from collections import defaultdict
from datetime import date, timedelta, datetime
from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.calcu.schema.science_warehouse import (
        ScienceWarehouseCalculationResponse,
        ScienceWarehouseDetailsResponse,
    )

from backend.app.datamanage.crud.crud_warehouse import warehouse_dao
from backend.app.datamanage.crud.crud_warehouse_inventory import warehouse_inventory_dao
from backend.app.datamanage.crud.crud_part_spare_mapping import part_spare_mapping_dao
from backend.app.datamanage.crud.crud_allotment import allotment_dao
from backend.app.datamanage.crud.crud_failure import failure_dao
from backend.app.datamanage.crud.crud_product import product_dao
from backend.app.datamanage.crud.crud_despatch import despatch_dao
from backend.app.calcu.crud.crud_science_warehouse_result import (
    science_warehouse_result_dao,
)
from typing import Sequence

# 缁熻琛ㄧ浉鍏抽€昏緫宸茬Щ闄わ紝涓嶅啀瀵煎叆
# from backend.app.calcu.crud.crud_science_warehouse_statistics import (
#     science_warehouse_statistics_dao,
# )
from backend.app.fit.service.part_strategy_service import part_strategy_service
from backend.app.fit.service.part_fit_service import part_fit_service
from backend.app.fit.utils.time_utils import dateutils
from backend.database.db import async_db_session
from backend.utils.snowflake import snowflake


def parse_discovery_date(discovery_date_str: str) -> Optional[date]:
    """
    瑙ｆ瀽鏁呴殰鍙戠幇鏃ユ湡瀛楃涓蹭负date瀵硅薄

    :param discovery_date_str: 鏃ユ湡瀛楃涓?    :return: 瑙ｆ瀽鍚庣殑date瀵硅薄锛岃В鏋愬け璐ヨ繑鍥濶one
    """
    if not discovery_date_str or not isinstance(discovery_date_str, str):
        return None

    # 鍘婚櫎鍓嶅悗绌烘牸
    discovery_date_str = discovery_date_str.strip()

    if not discovery_date_str:
        return None

    # 灏濊瘯澶氱鏃ユ湡鏍煎紡
    date_formats = [
        "%Y-%m-%d",  # 2023-12-25
        "%Y/%m/%d",  # 2023/12/25
        "%Y%m%d",  # 20231225
        "%Y-%m-%d %H:%M:%S",  # 2023-12-25 10:30:00
        "%Y/%m/%d %H:%M:%S",  # 2023/12/25 10:30:00
        "%Y-%m-%d %H:%M",  # 2023-12-25 10:30
        "%Y/%m/%d %H:%M",  # 2023/12/25 10:30
    ]

    for fmt in date_formats:
        try:
            parsed_datetime = datetime.strptime(discovery_date_str, fmt)
            return parsed_datetime.date()
        except ValueError:
            continue

    # 濡傛灉鎵€鏈夋牸寮忛兘澶辫触锛屽皾璇昿andas鐨勮嚜鍔ㄨВ鏋?    try:
        import pandas as pd

        parsed_datetime = pd.to_datetime(discovery_date_str)
        return parsed_datetime.date()
    except:
        pass

    return None


def is_failure_date_valid(failure_date_str: str, cutoff_date: date) -> bool:
    """
    妫€鏌ユ晠闅滄棩鏈熸槸鍚﹀湪鎴鏃ユ湡涔嬪墠鎴栫瓑浜庢埅姝㈡棩鏈?
    :param failure_date_str: 鏁呴殰鏃ユ湡瀛楃涓?    :param cutoff_date: 鎴鏃ユ湡
    :return: 鏄惁鏈夋晥
    """
    parsed_date = parse_discovery_date(failure_date_str)
    if parsed_date is None:
        return False

    return parsed_date <= cutoff_date


class ScienceWarehouseService:
    @staticmethod
    async def calculate_science_warehouse_requirements(
        time_interval_days: int = 180,
        input_date: date = None,
        product_model: str | None = None,
        product_config_code: str | None = None,
    ) -> "ScienceWarehouseCalculationResponse":
        """
        绉戝搴撳瓨闇€姹傝绠椾富娴佺▼

        :param time_interval_days: 闇€姹傞娴嬫椂闂撮棿闅旓紙澶╂暟锛?榛樿180澶?        :param input_date: 璁＄畻鎴鏃ユ湡锛堢敤浜庢嫙鍚堬級
        :return: 璁＄畻缁撴灉鍜岀粺璁′俊鎭?        """
        start_time = time.time()

        if not input_date:
            input_date = date.today()

        # 1. 鑾峰彇鎵€鏈夊簱鎴垮鍝佹竻鍗?        warehouse_spares = await ScienceWarehouseService.get_all_warehouse_spare_list()

        # 缁熻鎬诲鍝佹暟閲?        total_spares = sum(len(spares) for spares in warehouse_spares.values())

        # 2. 鍒濆鍖栫粨鏋滃拰缁熻
        results = {}
        statistics = {
            "total_warehouse_spares": 0,
            "calculated_spares": 0,
            "default_spares": 0,
            "insufficient_failure_data_spares": 0,  # 鏂板锛氭晠闅滄暟鎹笉瓒崇殑澶囧搧鏁伴噺
            "exponential_fit_success_spares": 0,  # 鏂板锛氭寚鏁板垎甯冩嫙鍚堟垚鍔熺殑澶囧搧鏁伴噺
            "exponential_fit_fail_spares": 0,  # 鏂板锛氭寚鏁板垎甯冩嫙鍚堝け璐ョ殑澶囧搧鏁伴噺
            "skipped_failures": [],
            "mapping_errors": [],
            "maintenance_responsibility_analysis": {},
        }

        # 3. 鎸夊簱鎴?澶囧搧缁村害璁＄畻
        calculation_start = time.time()
        processed_warehouses = 0
        processed_spares = 0

        for warehouse_code, spare_parts in warehouse_spares.items():
            processed_warehouses += 1
            results[warehouse_code] = {}
            statistics["maintenance_responsibility_analysis"][warehouse_code] = {
                "total_spares": len(spare_parts),
                "calculated": 0,
                "default": 0,
                "responsible_products": 0,
                "non_responsible_products": 0,
            }

            for spare_part in spare_parts:
                processed_spares += 1
                statistics["total_warehouse_spares"] += 1

                # 璁＄畻璇ュ簱鎴胯澶囧搧鐨勯渶姹?                spare_start = time.time()
                requirement_result = await ScienceWarehouseService.calculate_spare_requirement_with_coverage(
                    warehouse_code,
                    spare_part,
                    time_interval_days,
                    input_date,
                    product_model=product_model,
                    product_config_code=product_config_code,
                )
                spare_duration = time.time() - spare_start

                if requirement_result["calculated"]:
                    # 妫€鏌ユ槸鍚︿娇鐢ㄤ簡鎸囨暟鍒嗗竷鎷熷悎
                    maintenance_analysis = requirement_result.get(
                        "maintenance_analysis", {}
                    )
                    exponential_success = maintenance_analysis.get(
                        "exponential_fit_success_count", 0
                    )

                    if exponential_success > 0:
                        # 浣跨敤浜嗘寚鏁板垎甯冩嫙鍚?                        calculation_method = "exponential_fit"
                        confidence = 0.5  # 鎸囨暟鍒嗗竷鎷熷悎鐨勭疆淇″害杈冧綆
                        statistics["exponential_fit_success_spares"] += 1
                    else:
                        # 浣跨敤姝ｅ父鎷熷悎
                        calculation_method = "fitted"
                        confidence = requirement_result.get("confidence", 0.8)
                        statistics["calculated_spares"] += 1

                    results[warehouse_code][spare_part["part_code"]] = {
                        "part_name": spare_part["part_name"],
                        "required_quantity": requirement_result["quantity"],
                        "calculation_method": calculation_method,
                        "confidence": confidence,
                    }
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "calculated"
                    ] += 1
                elif requirement_result.get("insufficient_failure_data", False):
                    # 妫€鏌ユ槸鍚﹀皾璇曚簡鎸囨暟鍒嗗竷鎷熷悎浣嗗け璐?                    maintenance_analysis = requirement_result.get(
                        "maintenance_analysis", {}
                    )
                    exponential_fail = maintenance_analysis.get(
                        "exponential_fit_fail_count", 0
                    )

                    if exponential_fail > 0:
                        # 鎸囨暟鍒嗗竷鎷熷悎澶辫触锛屼娇鐢ㄩ粯璁ゆ暟閲?                        calculation_method = "exponential_fit_failed"
                        statistics["exponential_fit_fail_spares"] += 1
                    else:
                        # 鐩存帴浣跨敤榛樿鏁伴噺锛堟病鏈夊皾璇曟寚鏁板垎甯冩嫙鍚堬級
                        calculation_method = "insufficient_data"
                        statistics["insufficient_failure_data_spares"] += 1

                    results[warehouse_code][spare_part["part_code"]] = {
                        "part_name": spare_part["part_name"],
                        "required_quantity": spare_part["default_quantity"],
                        "calculation_method": calculation_method,
                        "confidence": 0.3,
                    }
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "default"
                    ] += 1
                else:
                    # 鍏朵粬鍘熷洜浣跨敤榛樿鏁伴噺
                    results[warehouse_code][spare_part["part_code"]] = {
                        "part_name": spare_part["part_name"],
                        "required_quantity": spare_part["default_quantity"],
                        "calculation_method": "default",
                        "confidence": 0.5,
                    }
                    statistics["default_spares"] += 1
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "default"
                    ] += 1

                # 鍙褰曢敊璇暟閲忥紝涓嶄繚瀛樿缁嗛敊璇俊鎭紙鍑忓皯鍐呭瓨浣跨敤锛?                statistics["skipped_failures"].extend(
                    requirement_result.get("skipped_failures", [])
                )
                statistics["mapping_errors"].extend(
                    requirement_result.get("mapping_errors", [])
                )

                # 绠€鍖栫淮鎶よ矗浠诲垎鏋愮粺璁?                if requirement_result.get("maintenance_analysis"):
                    maintenance_analysis = requirement_result["maintenance_analysis"]
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "responsible_products"
                    ] += maintenance_analysis.get("responsible_products", 0)
                    statistics["maintenance_responsibility_analysis"][warehouse_code][
                        "non_responsible_products"
                    ] += maintenance_analysis.get("non_responsible_products", 0)

        calculation_duration = time.time() - calculation_start

        # 4. 鐢熸垚璁＄畻鎵规ID
        calculation_id = f"SW_{snowflake.generate()}"

        # 5. 淇濆瓨璁＄畻缁撴灉鍒版暟鎹簱
        await ScienceWarehouseService.save_calculation_results(
            calculation_id,
            results,
            statistics,
            time_interval_days,
            input_date,
            product_model=product_model,
            product_config_code=product_config_code,
        )

        # 瀵煎叆Schema绫?        from backend.app.calcu.schema.science_warehouse import (
            ScienceWarehouseCalculationResponse,
        )

        total_duration = time.time() - start_time

        return ScienceWarehouseCalculationResponse(
            calculation_id=calculation_id,
            statistics=statistics,
            calculation_period={
                "time_interval_days": time_interval_days,
                "input_date": input_date.isoformat() if input_date else None,
            },
        )

    @staticmethod
    def build_failure_dimension_key(failure: Any) -> str:
        return "_".join(
            [
                getattr(failure, "product_model", "") or "",
                getattr(failure, "product_config_code", "") or "",
                getattr(failure, "fault_material_code", "") or "",
            ]
        )

    @staticmethod
    def group_failures_by_dimension(failures: List[Any]) -> dict[str, list[Any]]:
        grouped: dict[str, list[Any]] = defaultdict(list)
        for failure in failures:
            grouped[ScienceWarehouseService.build_failure_dimension_key(failure)].append(
                failure
            )
        return grouped

    @staticmethod
    async def get_all_warehouse_spare_list() -> Dict[str, List[Dict[str, Any]]]:
        """
        鑾峰彇鎵€鏈夊簱鎴垮鍝佹竻鍗?
        :return: 鎸夊簱鎴垮垎缁勭殑澶囧搧娓呭崟 {搴撴埧缂栫爜: [澶囧搧淇℃伅鍒楄〃]}
        """
        async with async_db_session() as db:
            # 鑾峰彇鎵€鏈夊簱鎴垮鍝佹竻鍗?            warehouse_inventories = await warehouse_inventory_dao.get_all(db)

            # 鎸夊簱鎴垮垎缁?            warehouse_spares = defaultdict(list)
            for inventory in warehouse_inventories:
                warehouse_spares[inventory.warehouse_code].append(
                    {
                        "part_code": inventory.part_code,
                        "part_name": inventory.part_name,
                        "default_quantity": inventory.default_quantity,
                    }
                )

            return dict(warehouse_spares)

    @staticmethod
    async def calculate_spare_requirement_with_coverage(
        warehouse_code: str,
        spare_part: dict,
        time_interval_days: int,
        input_date: date,
        product_model: str | None = None,
        product_config_code: str | None = None,
    ) -> Dict[str, Any]:
        """
        璁＄畻鍗曚釜搴撴埧鍗曚釜澶囧搧鐨勯渶姹傛暟閲忥紙鑰冭檻搴撴埧-璺眬-浜у搧鍏崇郴锛?        """

        result = {
            "calculated": False,
            "quantity": 0,
            "skipped_failures": [],
            "mapping_errors": [],
            "maintenance_analysis": {},
        }

        try:
            # 1. 鑾峰彇搴撴埧鏀寔鐨勪簩绾ч厤灞烇紙璺眬锛?            warehouse_allotments = (
                await ScienceWarehouseService.get_warehouse_allotments(warehouse_code)
            )

            if not warehouse_allotments:
                result["mapping_errors"].append(
                    {
                        "type": "no_warehouse_allotments",
                        "warehouse_code": warehouse_code,
                        "message": f"搴撴埧 {warehouse_code} 鏈壘鍒版敮鎸佺殑浜岀骇閰嶅睘",
                    }
                )
                return result

            # 2. 鑾峰彇浣跨敤姝ゅ鍝佺殑浜у搧鍨嬪彿锛堥€氳繃鏄犲皠琛級
            related_models = await ScienceWarehouseService.get_models_using_spare(
                spare_part["part_code"]
            )
            if product_model is not None:
                related_models = [model for model in related_models if model == product_model]

            if not related_models:
                result["mapping_errors"].append(
                    {
                        "type": "no_related_models",
                        "spare_part_code": spare_part["part_code"],
                        "message": f"澶囧搧 {spare_part['part_code']} 鏈壘鍒扮浉鍏充骇鍝佸瀷鍙?,
                    }
                )
                return result

            # 3. 鑾峰彇杩愯鍦ㄥ簱鎴胯鐩栬矾灞€涓婁笖鍨嬪彿鍖归厤鐨勪骇鍝佺紪鍙凤紙浼樺寲鐗堟湰锛?            filtered_products = []
            for allotment_two in warehouse_allotments:
                products_in_allotment = await ScienceWarehouseService.get_products_by_allotment_two_and_models(
                    allotment_two, related_models
                )
                filtered_products.extend(products_in_allotment)

            # 鍘婚噸
            filtered_products = list(set(filtered_products))

            if not filtered_products:
                result["mapping_errors"].append(
                    {
                        "type": "no_relevant_products",
                        "spare_part_code": spare_part["part_code"],
                        "warehouse_code": warehouse_code,
                        "message": f"澶囧搧 {spare_part['part_code']} 鍦ㄥ簱鎴?{warehouse_code} 瑕嗙洊鐨勮矾灞€涓婃棤鐩稿叧浜у搧",
                    }
                )
                return result

            # 5. 鑾峰彇鐩稿叧浜у搧鐨勬晠闅滄暟鎹?            all_failures = []
            skipped_failures = []

            for product_number in filtered_products:
                product_failures = (
                    await ScienceWarehouseService.get_failures_by_product_number(
                        product_number
                    )
                )

                # 杩囨护鏃堕棿鑼冨洿
                time_filtered_failures = []
                date_parse_errors = []

                for f in product_failures:
                    if is_failure_date_valid(f.discovery_date, input_date):
                        time_filtered_failures.append(f)
                    else:
                        # 璁板綍鏃ユ湡瑙ｆ瀽澶辫触鐨勬儏鍐?                        parsed_date = parse_discovery_date(f.discovery_date)
                        if parsed_date is None:
                            date_parse_errors.append(
                                {
                                    "failure_id": f.id,
                                    "product_number": f.product_number,
                                    "discovery_date": f.discovery_date,
                                    "reason": "invalid_date_format",
                                }
                            )
                        else:
                            # 鏃ユ湡鏍煎紡姝ｇ‘浣嗚秴鍑烘椂闂磋寖鍥?                            date_parse_errors.append(
                                {
                                    "failure_id": f.id,
                                    "product_number": f.product_number,
                                    "discovery_date": f.discovery_date,
                                    "parsed_date": str(parsed_date),
                                    "cutoff_date": str(input_date),
                                    "reason": "date_out_of_range",
                                }
                            )

                # 璁板綍鏃堕棿杩囨护缁撴灉

                # 灏嗘棩鏈熻В鏋愰敊璇坊鍔犲埌璺宠繃鐨勬晠闅滀腑
                skipped_failures.extend(date_parse_errors)

                # 妫€鏌ユ晠闅滈儴浠舵槸鍚﹁兘鏄犲皠鍒扮洰鏍囧鍝?                for failure in time_filtered_failures:
                    if product_model is not None and failure.product_model != product_model:
                        continue
                    if (
                        product_config_code is not None
                        and getattr(failure, "product_config_code", None) != product_config_code
                    ):
                        continue
                    mapping = await ScienceWarehouseService.get_part_spare_mapping(
                        failure.product_model, failure.fault_material_code
                    )

                    if mapping and mapping.spare_part_code == spare_part["part_code"]:
                        all_failures.append(failure)
                    else:
                        skipped_failures.append(
                            {
                                "failure_id": failure.id,
                                "product_number": failure.product_number,
                                "product_model": failure.product_model,
                                "fault_material_code": failure.fault_material_code,
                                "reason": (
                                    "no_mapping_to_target_spare"
                                    if not mapping
                                    else "mapped_to_different_spare"
                                ),
                            }
                        )

            result["skipped_failures"] = skipped_failures

            if not all_failures:
                result["mapping_errors"].append(
                    {
                        "type": "no_relevant_failures",
                        "spare_part_code": spare_part["part_code"],
                        "warehouse_code": warehouse_code,
                        "message": f"澶囧搧 {spare_part['part_code']} 鍦ㄥ簱鎴?{warehouse_code} 鏈壘鍒扮浉鍏虫晠闅滄暟鎹?,
                    }
                )
                return result

            # 6. 杩涜瀵垮懡鎷熷悎鍜屽浠堕噺璁＄畻
            calculation_result = (
                await ScienceWarehouseService.perform_spare_calculation_with_fit(
                    all_failures,
                    time_interval_days,
                    input_date,
                    warehouse_code,
                    spare_part["part_code"],
                )
            )

            if calculation_result["success"]:
                # 妫€鏌ユ槸鍚︽湁鏁呴殰鏁版嵁涓嶈冻鐨勬儏鍐?                maintenance_analysis = calculation_result.get(
                    "maintenance_analysis", {}
                )
                if (
                    maintenance_analysis.get(
                        "insufficient_failure_data_combinations", 0
                    )
                    > 0
                ):
                    result["insufficient_failure_data"] = True
                    result["calculated"] = False
                    result["quantity"] = 0
                    result["confidence"] = 0.3
                else:
                    result["calculated"] = True
                    result["quantity"] = calculation_result["quantity"]
                    result["confidence"] = calculation_result.get("confidence", 0.8)
                    result["maintenance_analysis"] = maintenance_analysis
            else:
                result["mapping_errors"].append(
                    {
                        "type": "calculation_failed",
                        "spare_part_code": spare_part["part_code"],
                        "warehouse_code": warehouse_code,
                        "error": calculation_result.get("error", "鏈煡閿欒"),
                    }
                )

        except Exception as e:
            result["mapping_errors"].append(
                {
                    "type": "exception",
                    "spare_part_code": spare_part["part_code"],
                    "warehouse_code": warehouse_code,
                    "error": str(e),
                }
            )

        return result

    @staticmethod
    async def perform_spare_calculation_with_fit(
        failures: List,
        time_interval_days: int,
        input_date: date,
        warehouse_code: str,
        spare_part_code: str,
    ) -> Dict[str, Any]:
        """
        鍩轰簬鏁呴殰鏁版嵁杩涜瀵垮懡鎷熷悎鍜屽浠堕噺璁＄畻锛堣€冭檻搴撴埧缁存姢璐ｄ换锛?        """

        try:
            # 1. 鎸変骇鍝佸瀷鍙?娲剧敓鐮?闆堕儴浠剁紪鐮佸垎缁勬晠闅滄暟鎹?            failures_by_model_part = ScienceWarehouseService.group_failures_by_dimension(
                failures
            )

            # 2. 瀵规瘡涓瀷鍙?闆堕儴浠剁粍鍚堣繘琛屽浠堕噺璁＄畻
            total_requirement = 0.0
            responsible_products = 0
            non_responsible_products = 0
            insufficient_failure_data_combinations = 0
            exponential_fit_success_count = 0
            exponential_fit_fail_count = 0

            for model_part_key, model_part_failures in failures_by_model_part.items():
                # 瑙ｆ瀽鍨嬪彿銆佹淳鐢熺爜鍜岄浂閮ㄤ欢缂栫爜
                product_model, product_config_code, part_code = model_part_key.split("_", 2)

                # 妫€鏌ユ晠闅滄暟閲忔槸鍚﹁冻澶燂紙闇€瑕?> 4 涓級
                if len(model_part_failures) <= 4:

                    # 灏濊瘯浣跨敤鎸囨暟鍒嗗竷鎷熷悎
                    try:
                        model_part_spare_quantity = await ScienceWarehouseService.exponential_fit_for_insufficient_data(
                            model_part_failures,
                            product_model,
                            product_config_code,
                            part_code,
                            time_interval_days,
                            input_date,
                        )

                        if model_part_spare_quantity > 0:
                            # 鎸囨暟鍒嗗竷鎷熷悎鎴愬姛
                            total_requirement += model_part_spare_quantity
                            responsible_products += len(
                                set([f.product_number for f in model_part_failures])
                            )
                            exponential_fit_success_count += 1
                        else:
                            # 鎸囨暟鍒嗗竷鎷熷悎澶辫触锛屼娇鐢ㄩ粯璁ゅ€?                            insufficient_failure_data_combinations += 1
                            non_responsible_products += len(
                                set([f.product_number for f in model_part_failures])
                            )
                            exponential_fit_fail_count += 1

                    except Exception as e:
                        # 鎸囨暟鍒嗗竷鎷熷悎寮傚父锛屼娇鐢ㄩ粯璁ゅ€?                        insufficient_failure_data_combinations += 1
                        non_responsible_products += len(
                            set([f.product_number for f in model_part_failures])
                        )
                        exponential_fit_fail_count += 1

                    continue

                # 鑾峰彇璇ュ瀷鍙?闆堕儴浠剁殑鎵€鏈変骇鍝佺紪鍙?                product_numbers = list(
                    set([f.product_number for f in model_part_failures])
                )

                # 浣跨敤宸茶繃婊ょ殑鏁呴殰鏁版嵁杩涜鎵撴爣澶勭悊
                tags = await part_strategy_service.part_tag_process_with_failures(
                    product_model,
                    part_code,
                    input_date,
                    model_part_failures,
                    product_config_code=product_config_code,
                )

                # 杩涜鎷熷悎
                fit_result = await part_fit_service.tag_fit(tags)

                # 鑾峰彇鏈€浣冲垎甯?                best_distribution = fit_result.best_distribution

                # 璁＄畻璇ュ瀷鍙?闆堕儴浠剁殑澶囦欢閲?                model_part_spare_quantity = (
                    await ScienceWarehouseService.calculate_spare_quantity_by_interval(
                        best_distribution,
                        time_interval_days,
                        model_part_failures,
                        input_date,
                    )
                )

                # 妫€鏌ユ瘡涓骇鍝佹槸鍚︾敱璇ュ簱鎴胯礋璐ｇ淮鎶?                for product_number in product_numbers:
                    maintenance_responsibility = (
                        await ScienceWarehouseService.check_maintenance_responsibility(
                            product_number, warehouse_code, spare_part_code
                        )
                    )

                    if maintenance_responsibility["responsible"]:
                        # 璇ュ簱鎴胯礋璐ｇ淮鎶わ紝璁″叆鎬婚渶姹?                        total_requirement += model_part_spare_quantity
                        responsible_products += 1
                    else:
                        # 璇ュ簱鎴夸笉璐熻矗缁存姢锛屼笉璁″叆鎬婚渶姹?                        non_responsible_products += 1

            return {
                "success": True,
                "quantity": max(1, math.ceil(total_requirement)),  # 鍚戜笂鍙栨暣涓旀渶灏忎负1
                "confidence": 0.8,
                "maintenance_analysis": {
                    "total_model_part_combinations": len(failures_by_model_part),
                    "responsible_products": responsible_products,
                    "non_responsible_products": non_responsible_products,
                    "insufficient_failure_data_combinations": insufficient_failure_data_combinations,
                    "exponential_fit_success_count": exponential_fit_success_count,
                    "exponential_fit_fail_count": exponential_fit_fail_count,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    async def calculate_spare_quantity_by_interval(
        best_distribution,
        time_interval_days: int,
        product_failures: List,
        input_date: date,
    ) -> float:
        """
        鍩轰簬鏃堕棿闂撮殧璁＄畻澶囦欢閲忥紙CDF宸€艰绠楋級
        鍙傝€?spare_service.py 涓殑璁＄畻閫昏緫
        """

        try:
            # 1. 鑾峰彇浜у搧淇℃伅锛堜粠绗竴涓晠闅滆褰曚腑鑾峰彇浜у搧鍨嬪彿锛?            if not product_failures:
                return 0.0

            product_model = product_failures[0].product_model
            product_config_code = getattr(product_failures[0], "product_config_code", None)

            # 2. 鑾峰彇浜у搧杩愯鍙傛暟
            async with async_db_session() as db:
                from backend.app.fit.schema.base_param import ProductParam
                from backend.app.fit.utils.convert_model import (
                    convert_to_pydantic_model,
                )
                from backend.app.datamanage.crud.crud_product import product_dao

                product_data = convert_to_pydantic_model(
                    await product_dao.get_by_model(
                        db, product_model, product_config_code=product_config_code
                    ),
                    ProductParam,
                )

            # 3. 璁＄畻姣忎釜浜у搧鐨勫浠堕噺
            result = 0.0
            product_list = {}

            # 4. 浠?despatch 鏁版嵁涓幏鍙栦骇鍝佸彂杩愭棩鏈熶俊鎭?            # 鑾峰彇鎵€鏈変骇鍝佺紪鍙?            product_numbers = list(set([f.product_number for f in product_failures]))

            # 浠?despatch 琛ㄤ腑鑾峰彇鍙戣繍鏃ユ湡
            async with async_db_session() as db:
                from backend.app.datamanage.crud.crud_despatch import despatch_dao

                # 鑾峰彇鎵€鏈夌浉鍏崇殑 despatch 鏁版嵁
                despatch_data = await despatch_dao.select_models(
                    db, identifier__in=product_numbers, repair_level__eq="鏂伴€?
                )

                # 鏋勫缓浜у搧缂栧彿鍒板彂杩愭棩鏈熺殑鏄犲皠
                product_despatch_map = {}
                for despatch in despatch_data:
                    if despatch.identifier and despatch.life_cycle_time:
                        product_despatch_map[despatch.identifier] = (
                            despatch.life_cycle_time
                        )

                # 涓烘瘡涓骇鍝佺紪鍙疯缃彂杩愭棩鏈?                for product_number in product_numbers:
                    if product_number not in product_list:
                        despatch_date = product_despatch_map.get(product_number)
                        if despatch_date:
                            product_list[product_number] = {"despatch": despatch_date}
                        else:
                            # 濡傛灉娌℃湁鎵惧埌鍙戣繍鏃ユ湡锛屼娇鐢ㄦ晠闅滃彂鐜版棩鏈熶綔涓鸿繎浼?                            # 杩欑鎯呭喌搴旇璁板綍璀﹀憡
                            first_failure = next(
                                (
                                    f
                                    for f in product_failures
                                    if f.product_number == product_number
                                ),
                                None,
                            )
                            if first_failure and first_failure.discovery_date:
                                parsed_date = parse_discovery_date(
                                    first_failure.discovery_date
                                )
                                if parsed_date:
                                    product_list[product_number] = {
                                        "despatch": parsed_date
                                    }
                                else:
                                    product_list[product_number] = {
                                        "despatch": input_date
                                    }
                            else:
                                product_list[product_number] = {"despatch": input_date}

            # 5. 璁＄畻姣忎釜浜у搧鐨勫浠堕噺
            for product_number, product_info in product_list.items():
                # 鑾峰彇鍙戣繍鏃ユ湡锛堝凡缁忔槸 date 瀵硅薄锛?                despatch_date = product_info["despatch"]

                # 璁＄畻鏃堕棿闂撮殧
                start_date = input_date
                end_date = input_date + timedelta(days=time_interval_days)

                # 杞崲涓鸿繍琛屾椂闂达紙鍙傝€?spare_service.py 鐨勯€昏緫锛?                xvals = [
                    (start_date - despatch_date).days
                    * product_data.year_days
                    * product_data.avg_worktime
                    / 365,
                    (end_date - despatch_date).days
                    * product_data.year_days
                    * product_data.avg_worktime
                    / 365,
                ]

                # 纭繚杩愯鏃堕棿涓烘鏁?                xvals = [max(0, x) for x in xvals]

                # 璁＄畻CDF宸€?                yvals = best_distribution.CDF(xvals=xvals, show_plot=False)
                calcu = yvals[1] - yvals[0]

                result += max(0.0, calcu)  # 纭繚涓嶄负璐熸暟

            return result

        except Exception as e:
            # 濡傛灉璁＄畻澶辫触锛岃繑鍥?
            return 0.0

    @staticmethod
    async def check_maintenance_responsibility(
        product_number: str, warehouse_code: str, spare_part_code: str
    ) -> Dict[str, Any]:
        """
        妫€鏌ヨ搴撴埧鏄惁璐熻矗缁存姢鎸囧畾浜у搧鐨勬寚瀹氬鍝?        """

        try:
            # 1. 鑾峰彇浜у搧鐨勯厤灞炰俊鎭?            allotment = await ScienceWarehouseService.get_allotment_by_product_number(
                product_number
            )
            if not allotment:
                return {
                    "responsible": False,
                    "reason": f"浜у搧缂栧彿 {product_number} 鏈壘鍒伴厤灞炰俊鎭?,
                }

            # 2. 妫€鏌ュ簱鎴挎槸鍚︽敮鎸佽浜у搧鐨勪簩绾ч厤灞?            warehouse_allotments = (
                await ScienceWarehouseService.get_warehouse_allotments(warehouse_code)
            )
            if allotment.allotment_two not in warehouse_allotments:
                return {
                    "responsible": False,
                    "reason": f"搴撴埧 {warehouse_code} 涓嶆敮鎸佷骇鍝?{product_number} 鐨勪簩绾ч厤灞?{allotment.allotment_two}",
                }

            # 3. 妫€鏌ュ簱鎴垮鍝佹竻鍗曚腑鏄惁鍖呭惈璇ュ鍝?            warehouse_spare = await ScienceWarehouseService.get_warehouse_spare(
                warehouse_code, spare_part_code
            )
            if not warehouse_spare:
                return {
                    "responsible": False,
                    "reason": f"搴撴埧 {warehouse_code} 鐨勫鍝佹竻鍗曚腑涓嶅寘鍚鍝?{spare_part_code}",
                }

            return {
                "responsible": True,
                "reason": f"搴撴埧 {warehouse_code} 璐熻矗缁存姢浜у搧 {product_number} 鐨勫鍝?{spare_part_code}",
                "allotment_info": {
                    "allotment_two": allotment.allotment_two,
                    "product_model": allotment.product_model,
                },
            }

        except Exception as e:
            return {"responsible": False, "reason": f"妫€鏌ョ淮鎶よ矗浠绘椂鍙戠敓閿欒: {str(e)}"}

    # 杈呭姪鏂规硶
    @staticmethod
    async def get_warehouse_allotments(warehouse_code: str) -> List[str]:
        """鑾峰彇搴撴埧鏀寔鐨勪簩绾ч厤灞炲垪琛?""
        async with async_db_session() as db:
            warehouses = await warehouse_dao.get_by_code(db, warehouse_code)
            if warehouses:
                # 鏀堕泦鎵€鏈夊簱鎴跨殑浜岀骇閰嶅睘锛屽幓閲?                allotments = set()
                for w in warehouses:
                    if w.allotment_two:
                        allotments.add(w.allotment_two)
                return list(allotments)
            return []

    @staticmethod
    async def get_models_using_spare(spare_part_code: str) -> List[str]:
        """鑾峰彇浣跨敤鎸囧畾澶囧搧鐨勪骇鍝佸瀷鍙峰垪琛?""
        async with async_db_session() as db:
            mappings = await part_spare_mapping_dao.get_by_spare_part_code(
                db, spare_part_code
            )
            return list(set([mapping.product_model for mapping in mappings]))

    @staticmethod
    async def get_products_by_allotment_two(allotment_two: str) -> List[str]:
        """鑾峰彇鎸囧畾浜岀骇閰嶅睘涓嬬殑鎵€鏈変骇鍝佺紪鍙?""
        async with async_db_session() as db:
            allotments = await allotment_dao.get_by_allotment_two(db, allotment_two)
            return [a.product_number for a in allotments]

    @staticmethod
    async def get_products_by_allotment_two_and_models(
        allotment_two: str, target_models: List[str]
    ) -> List[str]:
        """鑾峰彇鎸囧畾浜岀骇閰嶅睘涓嬩笖鍨嬪彿鍦ㄧ洰鏍囧垪琛ㄤ腑鐨勪骇鍝佺紪鍙凤紙浼樺寲鐗堟湰锛?""
        async with async_db_session() as db:
            allotments = await allotment_dao.get_by_allotment_two_and_models(
                db, allotment_two, target_models
            )
            return [a.product_number for a in allotments]

    @staticmethod
    async def get_model_by_product_number(product_number: str) -> str:
        """鏍规嵁浜у搧缂栧彿鑾峰彇浜у搧鍨嬪彿"""
        async with async_db_session() as db:
            allotment = await allotment_dao.get_by_product_number(db, product_number)
            return allotment.product_model if allotment else None

    @staticmethod
    async def calculate_total_run_time_for_products(
        product_numbers: List[str], product_model: str, product_config_code: str | None = None
    ) -> float:
        """璁＄畻鐗瑰畾浜у搧缂栧彿鍒楄〃鐨勬€昏繍琛屾椂闂?""
        async with async_db_session() as db:
            # 鑾峰彇浜у搧杩愯鍙傛暟
            product = await product_dao.get_by_model(
                db, product_model, product_config_code=product_config_code
            )
            if not product:
                return 0.0

            # 鑾峰彇杩欎簺浜у搧缂栧彿鐨勫彂杩愭暟鎹?            despatchs = await despatch_dao.select_models(
                db, identifier__in=product_numbers, repair_level__eq="鏂伴€?
            )

            if not despatchs:
                return 0.0

            # 璁＄畻鎬昏繍琛屾椂闂?            now = date.today()
            total_hours = 0
            for despatch in despatchs:
                dispatch_date = despatch.life_cycle_time
                if isinstance(dispatch_date, str):
                    dispatch_date = dateutils.validate_and_parse_date(dispatch_date)
                # 璁＄畻鏃ユ湡宸?                date_diff = (now - dispatch_date).days
                hours = dateutils.run_time(
                    date_diff, product.year_days, product.avg_worktime
                )
                total_hours += hours

            return total_hours

    @staticmethod
    async def exponential_fit_for_insufficient_data(
        model_part_failures: List,
        product_model: str,
        product_config_code: str | None,
        part_code: str,
        time_interval_days: int,
        input_date: date,
    ) -> float:
        """
        褰撴晠闅滄暟鎹笉瓒?涓椂锛屼娇鐢ㄦ寚鏁板垎甯冩嫙鍚堣绠楀浠堕噺
        鍙傝€?part_fit_service.py 涓殑 none_tag_fit 鏂规硶
        """
        try:
            # 鑾峰彇璇ュ瀷鍙?闆堕儴浠剁殑鎵€鏈変骇鍝佺紪鍙?            product_numbers = list(set([f.product_number for f in model_part_failures]))

            # 璁＄畻杩欎簺浜у搧鐨勬€昏繍琛屾椂闂?            total_run_time = (
                await ScienceWarehouseService.calculate_total_run_time_for_products(
                    product_numbers, product_model, product_config_code
                )
            )

            if total_run_time == 0:
                return 0.0

            # 璁＄畻鏁呴殰鏁伴噺
            failure_count = len(model_part_failures)

            # 璁＄畻鎸囨暟鍒嗗竷鐨刲ambda鍙傛暟
            if failure_count > 0:
                # 瀛樺湪鏁呴殰锛岃绠楁寚鏁板垎甯冨叕寮? 位 = n / T
                lambda_param = failure_count / total_run_time
            else:
                # 涓嶅瓨鍦ㄦ晠闅滐紝璁＄畻鎸囨暟鍒嗗竷鍏紡: 位 = t/-ln(1/e)
                lambda_param = -(math.log(1 / math.e)) / total_run_time

            # 璁＄畻澶囦欢閲忥紙浣跨敤鎸囨暟鍒嗗竷鐨凜DF锛?            # 鑾峰彇浜у搧杩愯鍙傛暟鐢ㄤ簬鏃堕棿杞崲
            async with async_db_session() as db:
                product = await product_dao.get_by_model(
                    db, product_model, product_config_code=product_config_code
                )
                if not product:
                    return 0.0

                # 璁＄畻鏃堕棿闂撮殧鐨勮繍琛屾椂闂?                start_date = input_date
                end_date = input_date + timedelta(days=time_interval_days)

                # 杞崲涓鸿繍琛屾椂闂?                start_run_time = 0  # 浠庡綋鍓嶆椂闂村紑濮?                end_run_time = (
                    time_interval_days * product.year_days * product.avg_worktime / 365
                )

                # 璁＄畻鎸囨暟鍒嗗竷鐨凜DF宸€?                # P(X <= end) - P(X <= start)
                cdf_end = 1 - math.exp(-lambda_param * end_run_time)
                cdf_start = 1 - math.exp(-lambda_param * start_run_time)
                spare_quantity = cdf_end - cdf_start

                return max(0.0, spare_quantity)

        except Exception as e:
            return 0.0

    @staticmethod
    async def get_failures_by_product_number(product_number: str) -> List:
        """鏍规嵁浜у搧缂栧彿鑾峰彇鏁呴殰鏁版嵁"""
        async with async_db_session() as db:
            return await failure_dao.get_by_product_number(db, product_number)

    @staticmethod
    async def get_part_spare_mapping(
        product_model: str,
        product_config_code: str,
        original_part_code: str,
    ):
        """鑾峰彇閮ㄤ欢涓庡鍝佹槧灏勫叧绯?""
        async with async_db_session() as db:
            return await part_spare_mapping_dao.get_by_original_part_code(
                db, product_model, product_config_code, original_part_code
            )

    @staticmethod
    async def get_allotment_by_product_number(product_number: str):
        """鏍规嵁浜у搧缂栧彿鑾峰彇閰嶅睘淇℃伅"""
        async with async_db_session() as db:
            return await allotment_dao.get_by_product_number(db, product_number)

    @staticmethod
    async def get_warehouse_spare(warehouse_code: str, spare_part_code: str):
        """鑾峰彇搴撴埧澶囧搧淇℃伅"""
        async with async_db_session() as db:
            return await warehouse_inventory_dao.get_by_warehouse_and_part(
                db, warehouse_code, spare_part_code
            )

    @staticmethod
    async def save_calculation_results(
        calculation_id: str,
        results: Dict[str, Any],
        statistics: Dict[str, Any],
        time_interval_days: int,
        input_date: date,
        product_model: str | None = None,
        product_config_code: str | None = None,
    ):
        """
        淇濆瓨璁＄畻缁撴灉鍒版暟鎹簱
        """
        async with async_db_session() as db:
            # 1. 娓呯┖璇ユ壒娆＄殑鍘嗗彶鏁版嵁
            await science_warehouse_result_dao.clear_by_calculation_id(
                db, calculation_id
            )
            # 缁熻琛ㄧ浉鍏抽€昏緫宸茬Щ闄?            # await science_warehouse_statistics_dao.clear_by_calculation_id(
            #     db, calculation_id
            # )

            # 2. 鍑嗗缁撴灉鏁版嵁
            result_data = []
            for warehouse_code, spare_parts in results.items():
                # 鑾峰彇搴撴埧鍚嶇О
                warehouse_name = await ScienceWarehouseService.get_warehouse_name(
                    warehouse_code
                )

                for spare_part_code, spare_info in spare_parts.items():
                    result_data.append(
                        {
                            "calculation_id": calculation_id,
                            "product_model": product_model,
                            "product_config_code": product_config_code,
                            "warehouse_code": warehouse_code,
                            "warehouse_name": warehouse_name or warehouse_code,
                            "spare_part_code": spare_part_code,
                            "spare_part_name": spare_info["part_name"],
                            "required_quantity": spare_info["required_quantity"],
                            "calculation_method": spare_info["calculation_method"],
                            "time_interval_days": time_interval_days,
                            "input_date": input_date,
                            "created_time": date.today(),
                            "confidence": spare_info["confidence"],
                            "max_failure_count": 0,  # 鏃х増鏈湇鍔′笉璁＄畻姝ゅ瓧娈碉紝璁句负0
                        }
                    )

            # 3. 鎵归噺淇濆瓨缁撴灉鏁版嵁
            if result_data:
                await science_warehouse_result_dao.bulk_create(db, result_data)

            # 缁熻琛ㄧ浉鍏抽€昏緫宸茬Щ闄わ紝鍙繚鐣欐牳蹇冭绠楃粨鏋?            # # 4. 淇濆瓨缁熻淇℃伅
            # from backend.app.calcu.model.science_warehouse_statistics import (
            #     ScienceWarehouseStatistics,
            # )
            # ... (缁熻琛ㄥ垱寤洪€昏緫宸叉敞閲?

    @staticmethod
    async def get_warehouse_name(warehouse_code: str) -> str:
        """鑾峰彇搴撴埧鍚嶇О"""
        async with async_db_session() as db:
            warehouses = await warehouse_dao.get_by_code(db, warehouse_code)
            if warehouses:
                # 濡傛灉鏈夊涓簱鎴匡紝杩斿洖绗竴涓殑鍚嶇О
                return warehouses[0].name
            return None

    @staticmethod
    async def convert_to_api_format(results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        灏嗗唴閮ㄨ绠楃粨鏋滆浆鎹负API杈撳嚭鏍煎紡

        :param results: 鍐呴儴璁＄畻缁撴灉
        :return: API鏍煎紡鐨勬暟鎹垪琛?        """
        api_data = []

        for warehouse_code, spare_parts in results.items():
            # 鑾峰彇搴撴埧鍚嶇О
            warehouse_name = await ScienceWarehouseService.get_warehouse_name(
                warehouse_code
            )

            for spare_part_code, spare_info in spare_parts.items():
                # 鏍规嵁浣犵殑API鏍煎紡瑕佹眰
                api_item = {
                    "factor": "G002",  # 宸ュ巶缂栫爜鍥哄畾涓篏002
                    "code": warehouse_code,  # 搴撴埧缂栫爜浣滀负code
                    "warehouse": warehouse_name
                    or warehouse_code,  # 搴撴埧鍚嶇О锛屽鏋滄病鏈夊垯浣跨敤缂栫爜
                    "part": spare_part_code,  # 澶囧搧缂栫爜浣滀负part
                    "number": spare_info["required_quantity"],  # 闇€姹傛暟閲?                }
                api_data.append(api_item)

        return api_data

    @staticmethod
    async def get_calculation_results_by_id(
        calculation_id: str,
    ) -> "ScienceWarehouseDetailsResponse":
        """
        鏍规嵁璁＄畻鎵规ID鑾峰彇璇︾粏璁＄畻缁撴灉锛堝寘鍚粺璁′俊鎭級
        """
        async with async_db_session() as db:
            # 鑾峰彇缁撴灉鏁版嵁
            results = await science_warehouse_result_dao.select_models(
                db, calculation_id__eq=calculation_id
            )

            # 缁熻琛ㄧ浉鍏抽€昏緫宸茬Щ闄?            # statistics = await science_warehouse_statistics_dao.select_model(
            #     db, calculation_id__eq=calculation_id
            # )
            statistics = None

            # 杞崲涓哄唴閮ㄦ牸寮?            results_dict = {}
            for result in results:
                if result.warehouse_code not in results_dict:
                    results_dict[result.warehouse_code] = {}

                results_dict[result.warehouse_code][result.spare_part_code] = {
                    "part_name": result.spare_part_name,
                    "required_quantity": result.required_quantity,
                    "calculation_method": result.calculation_method,
                    "confidence": result.confidence,
                    "max_failure_count": getattr(result, "max_failure_count", 0),
                }

            # 瀵煎叆Schema绫?            from backend.app.calcu.schema.science_warehouse import (
                ScienceWarehouseDetailsResponse,
            )

            return ScienceWarehouseDetailsResponse(
                calculation_id=calculation_id,
                results=results_dict,
                statistics={},  # 缁熻琛ㄥ凡绉婚櫎锛岃繑鍥炵┖瀛楀吀
            )

    @staticmethod
    async def get_calculation_results_for_api(
        calculation_id: str,
    ) -> List[Dict[str, Any]]:
        """
        鏍规嵁璁＄畻鎵规ID鑾峰彇API鏍煎紡鐨勮绠楃粨鏋?
        :param calculation_id: 璁＄畻鎵规ID
        :return: API鏍煎紡鐨勬暟鎹垪琛?        """
        async with async_db_session() as db:
            # 鑾峰彇缁撴灉鏁版嵁
            results = await science_warehouse_result_dao.select_models(
                db, calculation_id__eq=calculation_id
            )

            if not results:
                return []

            # 杞崲涓哄唴閮ㄦ牸寮?            results_dict = {}
            for result in results:
                if result.warehouse_code not in results_dict:
                    results_dict[result.warehouse_code] = {}

                results_dict[result.warehouse_code][result.spare_part_code] = {
                    "part_name": result.spare_part_name,
                    "required_quantity": result.required_quantity,
                    "calculation_method": result.calculation_method,
                    "confidence": result.confidence,
                }

            # 杞崲涓篈PI鏍煎紡
            api_data = await ScienceWarehouseService.convert_to_api_format(results_dict)
            return api_data

    @staticmethod
    async def get_latest_calculation_results() -> List[Dict[str, Any]]:
        """
        鑾峰彇鏈€鏂颁竴鎵规鐨勮绠楃粨鏋滐紝鐢ㄤ簬鍓嶇灞曠ず

        :return: 鏈€鏂版壒娆＄殑璁＄畻缁撴灉鍒楄〃
        """
        async with async_db_session() as db:
            # 缁熻琛ㄥ凡绉婚櫎锛屾敼涓轰粠缁撴灉琛ㄨ幏鍙栨渶鏂扮殑calculation_id
            # 1. 鑾峰彇鏈€鏂扮殑缁撴灉璁板綍锛堟寜鑷ID鍊掑簭锛岀‘淇濆敮涓€鎬э級
            latest_result = await science_warehouse_result_dao.select_model(
                db, order_by="id", desc=True
            )

            if not latest_result:
                return []

            # 2. 鏍规嵁鏈€鏂扮粨鏋滆褰曠殑calculation_id鑾峰彇缁撴灉鏁版嵁
            return await ScienceWarehouseService.get_calculation_results_for_api(
                latest_result.calculation_id
            )

    @staticmethod
    async def get_latest_calculation_results_detailed() -> List[Dict[str, Any]]:
        """
        鑾峰彇鏈€鏂颁竴鎵规鐨勮缁嗚绠楃粨鏋滐紝鍖呭惈鏇村瀛楁淇℃伅

        :return: 鏈€鏂版壒娆＄殑璇︾粏璁＄畻缁撴灉鍒楄〃
        """
        async with async_db_session() as db:
            # 缁熻琛ㄥ凡绉婚櫎锛屾敼涓轰粠缁撴灉琛ㄨ幏鍙栨渶鏂扮殑calculation_id
            # 1. 鑾峰彇鏈€鏂扮殑缁撴灉璁板綍锛堟寜鑷ID鍊掑簭锛岀‘淇濆敮涓€鎬э級
            latest_result = await science_warehouse_result_dao.select_model(
                db, order_by="id", desc=True
            )

            if not latest_result:
                return []

            # 2. 鑾峰彇璇︾粏鐨勭粨鏋滄暟鎹?            results = await science_warehouse_result_dao.select_models(
                db, calculation_id__eq=latest_result.calculation_id
            )

            if not results:
                return []

            # 3. 杞崲涓鸿缁嗘牸寮?            detailed_results = []
            for result in results:
                detailed_item = {
                    "calculation_id": result.calculation_id,
                    "product_model": getattr(result, "product_model", None),
                    "product_config_code": getattr(result, "product_config_code", None),
                    "warehouse_code": result.warehouse_code,
                    "warehouse_name": result.warehouse_name,
                    "spare_part_code": result.spare_part_code,
                    "spare_part_name": result.spare_part_name,
                    "required_quantity": result.required_quantity,
                    "calculation_method": result.calculation_method,
                    "confidence": result.confidence,
                    "time_interval_days": result.time_interval_days,
                    "input_date": (
                        result.input_date.isoformat() if result.input_date else None
                    ),
                    "created_time": (
                        result.created_time.isoformat() if result.created_time else None
                    ),
                    "max_failure_count": getattr(result, "max_failure_count", 0),
                }
                detailed_results.append(detailed_item)

            return detailed_results

    @staticmethod
    async def get_select(
        calculation_id: Optional[str] = None,
        product_model: Optional[str] = None,
        product_config_code: Optional[str] = None,
        warehouse_code: Optional[str] = None,
        spare_part_code: Optional[str] = None,
        calculation_method: Optional[str] = None,
        time_range: Optional[list[str]] = None,
    ):
        """
        鑾峰彇绉戝搴撳瓨璁＄畻缁撴灉鐨勬煡璇㈡潯浠?
        :param calculation_id: 璁＄畻鎵规ID锛堟敮鎸佹ā绯婂尮閰嶏級
        :param warehouse_code: 搴撴埧缂栫爜锛堢簿纭尮閰嶏級
        :param spare_part_code: 澶囧搧缂栫爜锛堢簿纭尮閰嶏級
        :param calculation_method: 璁＄畻鏂规硶锛堢簿纭尮閰嶏級
        :param time_range: 鍒涘缓鏃堕棿鑼冨洿 [寮€濮嬫棩鏈? 缁撴潫鏃ユ湡]
        :return: 鏌ヨ鏉′欢
        """
        from sqlalchemy import and_, or_, select
        from backend.app.calcu.model.science_warehouse_result import (
            ScienceWarehouseResult,
        )

        conditions = []

        # 鍥哄畾鏉′欢锛歳equired_quantity蹇呴』澶т簬0
        conditions.append(ScienceWarehouseResult.required_quantity > 0)
        conditions.append(ScienceWarehouseResult.required_quantity >= ScienceWarehouseResult.max_failure_count)

        if calculation_id:
            # 璁＄畻鎵规ID鏀寔妯＄硦鍖归厤锛堝洜涓虹敤鎴锋墜鍔ㄨ緭鍏ワ級
            conditions.append(
                ScienceWarehouseResult.calculation_id.like(f"%{calculation_id}%")
            )

        if product_model:
            conditions.append(ScienceWarehouseResult.product_model == product_model)

        if product_config_code is not None:
            conditions.append(
                ScienceWarehouseResult.product_config_code == product_config_code
            )

        if warehouse_code:
            # 搴撴埧缂栫爜绮剧‘鍖归厤锛堜笅鎷夋閫夋嫨锛?            conditions.append(ScienceWarehouseResult.warehouse_code == warehouse_code)

        if spare_part_code:
            # 澶囧搧缂栫爜绮剧‘鍖归厤锛堜笅鎷夋閫夋嫨锛?            conditions.append(ScienceWarehouseResult.spare_part_code == spare_part_code)

        if calculation_method:
            # 璁＄畻鏂规硶绮剧‘鍖归厤锛堜笅鎷夋閫夋嫨锛?            conditions.append(
                ScienceWarehouseResult.calculation_method == calculation_method
            )

        if time_range:
            conditions.append(
                ScienceWarehouseResult.created_time.between(
                    time_range[0], time_range[1]
                )
            )

        return (
            select(ScienceWarehouseResult)
            .where(and_(*conditions))
            .order_by(ScienceWarehouseResult.required_quantity.desc())
        )

    @staticmethod
    async def get_warehouse_code_name_pairs() -> Sequence[List[str]]:
        """
        鑾峰彇搴撴埧缂栫爜鍜屽悕绉扮殑鍒楄〃锛堝幓閲嶏級

        :return: [[搴撴埧缂栫爜, 搴撴埧鍚嶇О], ...] 鐨勫垪琛?        """
        async with async_db_session() as db:
            return await science_warehouse_result_dao.get_warehouse_code_name_pairs(db)

    @staticmethod
    async def get_spare_part_code_name_pairs(
        warehouse_code: str | None = None,
    ) -> Sequence[List[str]]:
        """
        鏍规嵁搴撴埧缂栫爜鑾峰彇澶囧搧缂栫爜鍜屽悕绉扮殑鍒楄〃锛堢骇鑱旂瓫閫夛級

        :param warehouse_code: 搴撴埧缂栫爜锛堝彲閫夛紝鐢ㄤ簬绾ц仈绛涢€夛級
        :return: [[澶囧搧缂栫爜, 澶囧搧鍚嶇О], ...] 鐨勫垪琛?        """
        async with async_db_session() as db:
            return await science_warehouse_result_dao.get_spare_part_code_name_pairs(
                db, warehouse_code
            )

    @staticmethod
    async def get_calculation_methods() -> Sequence[str]:
        """
        鑾峰彇鎵€鏈夊敮涓€鐨勮绠楁柟娉?
        :return: 璁＄畻鏂规硶鍒楄〃
        """
        async with async_db_session() as db:
            return await science_warehouse_result_dao.get_distinct_calculation_methods(
                db
            )

    @staticmethod
    async def get_latest_calculation_statistics() -> Dict[str, Any]:
        """
        鑾峰彇鏈€鏂颁竴鎵规鐨勭粺璁′俊鎭紙缁熻琛ㄥ凡绉婚櫎锛岃繑鍥炵┖瀛楀吀锛?
        :return: 鏈€鏂版壒娆＄殑缁熻淇℃伅
        """
        # 缁熻琛ㄥ凡绉婚櫎锛岃繑鍥炵┖瀛楀吀
        return {}


science_warehouse_service: ScienceWarehouseService = ScienceWarehouseService()
