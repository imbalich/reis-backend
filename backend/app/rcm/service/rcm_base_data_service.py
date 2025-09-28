#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : rcm_base_data_service.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/01/XX XX:XX
@Desc    : RCM基础数据服务类
"""

from typing import Sequence, List, Dict, Any
from datetime import datetime, date
import pandas as pd
import io

from sqlalchemy import Select

from backend.database.db import async_db_session
from backend.app.rcm.crud.crud_rcm_base_data import rcm_base_data_dao
from backend.app.rcm.schema.rcm_base_data import (
    RcmExcelImportRow,
    RcmExcelImportResponse,
    GetRcmBaseDataDetails,
    GetRcmBaseDataListResponse,
    RcmBaseDataFilterParam,
)


class RcmBaseDataService:
    """RCM基础数据服务类"""

    async def get_select(
        self,
        product_model: str | None = None,
        component_name: str | None = None,
        component_material_code: str | None = None,
        failure_mode: str | None = None,
        is_key_component: bool | None = None,
        is_consumable_part: bool | None = None,
    ) -> Select:
        """
        获取RCM基础数据查询语句

        :param product_model: 产品型号
        :param component_name: 部件名称
        :param component_material_code: 零部件物料编码
        :param failure_mode: 故障模式
        :param is_key_component: 是否关键部件
        :param is_consumable_part: 是否耗损型部件
        :return: 查询语句
        """
        return await rcm_base_data_dao.get_select(
            product_model=product_model,
            component_name=component_name,
            component_material_code=component_material_code,
            failure_mode=failure_mode,
            is_key_component=is_key_component,
            is_consumable_part=is_consumable_part,
        )

    async def get_product_models(self) -> Sequence[str]:
        """
        获取所有产品型号

        :return: 产品型号列表
        """
        async with async_db_session() as db:
            return await rcm_base_data_dao.get_product_models(db)

    async def get_component_names_by_model(self, product_model: str) -> Sequence[str]:
        """
        根据产品型号获取部件名称列表

        :param product_model: 产品型号
        :return: 部件名称列表
        """
        async with async_db_session() as db:
            return await rcm_base_data_dao.get_component_names_by_model(
                db, product_model
            )

    async def get_failure_modes_by_model(self, product_model: str) -> Sequence[str]:
        """
        根据产品型号获取故障模式列表

        :param product_model: 产品型号
        :return: 故障模式列表
        """
        async with async_db_session() as db:
            return await rcm_base_data_dao.get_failure_modes_by_model(db, product_model)

    async def import_from_excel(self, excel_content: bytes) -> RcmExcelImportResponse:
        """
        从Excel导入RCM基础数据（完全覆盖）

        Excel格式要求：
        - Sheet名称：RCM基础数据
        - 表头：产品型号、派生码、部件名称、零部件物料编码、故障模式、来源、是否关键部件、是否耗损型部件、故障率预计值、增加预防性维修的、改进前LCC、改进后LCC、状态是否可在线、故障率变化趋势是否达到预警值、创建人、更新时间
        - 第一行为表头，从第二行开始为数据
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(
                io.BytesIO(excel_content), sheet_name="配置表", engine="openpyxl"
            )

            # 验证列名
            expected_columns = [
                "产品型号",
                "派生码",
                "部件名称",
                "零部件物料编码",
                "故障模式",
                "来源",
                "是否关键部件",
                "是否耗损型部件",
                "故障率预计值",
                "增加预防性维修的LCC",
                "改进前LCC",
                "改进后LCC",
                "状态是否可在线监控",
                "故障率变化趋势是否达到预警值",
                "创建人",
                "更新时间",
            ]
            if not all(col in df.columns for col in expected_columns):
                missing_cols = [
                    col for col in expected_columns if col not in df.columns
                ]
                return RcmExcelImportResponse(
                    total_rows=0,
                    success_rows=0,
                    failed_rows=0,
                    errors=[f"Excel文件格式错误：缺少必要的列 {missing_cols}"],
                )

            # 处理数据
            total_rows = len(df)
            success_rows = 0
            failed_rows = 0
            errors = []
            rcm_data = []

            for index, row in df.iterrows():
                try:
                    # 验证必填字段
                    if (
                        pd.isna(row["产品型号"])
                        or pd.isna(row["部件名称"])
                        or pd.isna(row["零部件物料编码"])
                    ):
                        failed_rows += 1
                        error_msg = (
                            f"第{index+2}行：产品型号、部件名称、零部件物料编码为必填项"
                        )
                        errors.append(error_msg)
                        continue

                    # 获取数据
                    product_model = str(row["产品型号"]).strip()
                    derivative_code = (
                        str(row["派生码"]).strip()
                        if not pd.isna(row["派生码"])
                        else None
                    )
                    component_name = str(row["部件名称"]).strip()
                    component_material_code = str(row["零部件物料编码"]).strip()
                    failure_mode = (
                        str(row["故障模式"]).strip()
                        if not pd.isna(row["故障模式"])
                        else None
                    )
                    source = (
                        str(row["来源"]).strip() if not pd.isna(row["来源"]) else None
                    )
                    created_by = (
                        str(row["创建人"]).strip()
                        if not pd.isna(row["创建人"])
                        else None
                    )

                    # 处理布尔值字段
                    is_key_component = None
                    if not pd.isna(row["是否关键部件"]):
                        value = str(row["是否关键部件"]).strip().lower()
                        if value in ["是", "true", "1", "yes"]:
                            is_key_component = True
                        elif value in ["否", "false", "0", "no"]:
                            is_key_component = False

                    is_consumable_part = None
                    if not pd.isna(row["是否耗损型部件"]):
                        value = str(row["是否耗损型部件"]).strip().lower()
                        if value in ["是", "true", "1", "yes"]:
                            is_consumable_part = True
                        elif value in ["否", "false", "0", "no"]:
                            is_consumable_part = False

                    # 处理数值字段
                    estimated_failure_rate = None
                    if not pd.isna(row["故障率预计值"]):
                        try:
                            estimated_failure_rate = float(row["故障率预计值"])
                        except (ValueError, TypeError):
                            errors.append(f"第{index+2}行：故障率预计值格式不正确")

                    preventive_maintenance_cost = None
                    if not pd.isna(row["增加预防性维修的LCC"]):
                        try:
                            preventive_maintenance_cost = float(
                                row["增加预防性维修的LCC"]
                            )
                        except (ValueError, TypeError):
                            errors.append(
                                f"第{index+2}行：增加预防性维修的LCC格式不正确"
                            )

                    lcc_before_improvement = None
                    if not pd.isna(row["改进前LCC"]):
                        try:
                            lcc_before_improvement = float(row["改进前LCC"])
                        except (ValueError, TypeError):
                            errors.append(f"第{index+2}行：改进前LCC格式不正确")

                    lcc_after_improvement = None
                    if not pd.isna(row["改进后LCC"]):
                        try:
                            lcc_after_improvement = float(row["改进后LCC"])
                        except (ValueError, TypeError):
                            errors.append(f"第{index+2}行：改进后LCC格式不正确")

                    # 处理状态字段
                    is_online_status = None
                    if not pd.isna(row["状态是否可在线监控"]):
                        value = str(row["状态是否可在线监控"]).strip().lower()
                        if value in ["是", "true", "1", "yes"]:
                            is_online_status = True
                        elif value in ["否", "false", "0", "no"]:
                            is_online_status = False

                    is_trend_rate_limit = None
                    if not pd.isna(row["故障率变化趋势是否达到预警值"]):
                        value = str(row["故障率变化趋势是否达到预警值"]).strip().lower()
                        if value in ["是", "true", "1", "yes"]:
                            is_trend_rate_limit = True
                        elif value in ["否", "false", "0", "no"]:
                            is_trend_rate_limit = False

                    # 处理更新时间
                    changed_time = None
                    if not pd.isna(row["更新时间"]):
                        try:
                            if isinstance(row["更新时间"], str):
                                changed_time = datetime.strptime(
                                    row["更新时间"], "%Y-%m-%d"
                                ).date()
                            else:
                                changed_time = row["更新时间"].date()
                        except:
                            errors.append(f"第{index+2}行：更新时间格式不正确，已忽略")

                    # 构建数据
                    rcm_record = {
                        "product_model": product_model,
                        "derivative_code": derivative_code,
                        "component_name": component_name,
                        "component_material_code": component_material_code,
                        "failure_mode": failure_mode,
                        "source": source,
                        "is_key_component": is_key_component,
                        "is_consumable_part": is_consumable_part,
                        "estimated_failure_rate": estimated_failure_rate,
                        "preventive_maintenance_cost": preventive_maintenance_cost,
                        "lcc_before_improvement": lcc_before_improvement,
                        "lcc_after_improvement": lcc_after_improvement,
                        "is_online_status": is_online_status,
                        "is_trend_rate_limit": is_trend_rate_limit,
                        "created_by": created_by,
                        "changed_time": changed_time,
                    }

                    rcm_data.append(rcm_record)
                    success_rows += 1

                except Exception as e:
                    failed_rows += 1
                    error_msg = str(e)
                    if "NOT NULL constraint failed" in error_msg:
                        errors.append(f"第{index+2}行：必填字段不能为空")
                    elif (
                        "Data too long" in error_msg
                        or "String data, right truncated" in error_msg
                    ):
                        errors.append(f"第{index+2}行：数据长度超出限制")
                    else:
                        errors.append(f"第{index+2}行：{error_msg}")

            # 如果数据有效，执行数据库操作
            if rcm_data:
                async with async_db_session() as db:
                    # 清空现有数据
                    await rcm_base_data_dao.clear_all(db)
                    # 批量创建新数据
                    await rcm_base_data_dao.bulk_create(db, rcm_data)

            return RcmExcelImportResponse(
                total_rows=total_rows,
                success_rows=success_rows,
                failed_rows=failed_rows,
                errors=errors,
            )

        except Exception as e:
            return RcmExcelImportResponse(
                total_rows=0,
                success_rows=0,
                failed_rows=0,
                errors=[f"Excel处理失败：{str(e)}"],
            )


rcm_base_data_service = RcmBaseDataService()
