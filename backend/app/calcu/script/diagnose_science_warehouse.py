#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科学库存单零部件诊断脚本（只读，不写任何业务表）

把"现网科学库存口径"和"Aaron 对齐口径"逐环节拆开，输出每个库房、每个派生码、
每台产品（一辆车可配多台，按配属表产品编号计）、每个零件位置的中间结果，便于人工核对差异出在哪一步。

用法（在仓库根目录）：
    .venv\\Scripts\\python.exe backend/app/calcu/script/diagnose_science_warehouse.py ^
        --model YGZN2Q271 --part Z500000189932 ^
        --env deploy/backend/docker-compose/.env.server

口径说明：
    新服务结果    直接调用修复后的 ScienceWarehouseServiceChange（use_cached_fit=False，只读），应与 V1_对齐_BIC 基本一致
    V0_现网口径   复刻修复前 science_warehouse_service_change 的逻辑：
                  按产品(台)计 1 份、不乘 BOM；寿命起点=最早新造发运日期（缺失才用故障表生产日期）；
                  运行参数不带派生码；分布取 fit_part 表中已入库结果（老/新算法混存）。
    V1_对齐_W2P   Aaron 现场拟合的 Weibull_2P；按零件位置计（=乘 BOM）；
                  寿命起点=Aaron 的 life_cycle_time（发运日期与故障生产日期取早）；
                  F(t+Δ)-F(t)，t 为自寿命起点起算的累计运行小时。业务"单纯用 Weibull 测算"最接近此口径。
    V1_对齐_BIC   同 V1，但分布用 Aaron 现场拟合 BIC 最优分布（不一定是 Weibull）。
    V2_更换后寿命 同 V1_W2P，但 t 取 Aaron 标签中该位置最后一次更换后的当前寿命（suspense 标签）。
    V3_条件概率   同 V2，但用 [F(t+Δ)-F(t)] / [1-F(t)]（已存活到 t 条件下的失效概率）。
"""

import argparse
import asyncio
import os
import sys
import traceback
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))


def parse_args():
    parser = argparse.ArgumentParser(description="科学库存单零部件诊断（只读）")
    parser.add_argument("--model", required=True, help="产品型号，如 YGZN2Q271")
    parser.add_argument("--part", required=True, help="故障件(原装件)物料编码；若传的是备品编码也会自动识别")
    parser.add_argument("--input-date", default="2025-12-30", help="计算截止日期，默认 2025-12-30")
    parser.add_argument("--interval-days", type=int, default=180, help="预测时间窗口（天），默认 180")
    parser.add_argument("--env", default=None, help="环境变量文件路径，如 deploy/backend/docker-compose/.env.server")
    parser.add_argument("--out-dir", default=None, help="输出目录，默认 backend/app/calcu/script/output")
    return parser.parse_args()


def load_env_file(env_path: str) -> None:
    """在导入 backend 之前把 .env 写入进程环境变量，覆盖同名变量。"""
    path = Path(env_path)
    if not path.is_absolute():
        path = project_root / path
    if not path.exists():
        raise FileNotFoundError(f"env 文件不存在: {path}")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip("'").strip('"')


ARGS = parse_args()
if ARGS.env:
    load_env_file(ARGS.env)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from reliability.Distributions import Exponential_Distribution, Weibull_Distribution  # noqa: E402
from sqlalchemy import select  # noqa: E402

from backend.app.calcu.schema.distribute_param import DistributionParams  # noqa: E402
from backend.app.calcu.service.distribute_service import distribute_service  # noqa: E402
from backend.app.calcu.service.science_warehouse_service_change import (  # noqa: E402
    ScienceWarehouseServiceChange,
)
from backend.app.datamanage.crud.crud_failure import CRUDFailure, failure_dao  # noqa: E402
from backend.app.datamanage.crud.crud_product import product_dao  # noqa: E402
from backend.app.datamanage.model.allotment import Allotment  # noqa: E402
from backend.app.datamanage.model.despatch import Despatch  # noqa: E402
from backend.app.datamanage.model.part_spare_mapping import PartSpareMapping  # noqa: E402
from backend.app.datamanage.model.warehouse import Warehouse  # noqa: E402
from backend.app.datamanage.model.warehouse_inventory import WarehouseInventory  # noqa: E402
from backend.app.fit.crud.crud_fit_part import fit_part_dao  # noqa: E402
from backend.app.fit.schema.fit_param import FitCheckType, FitMethodType  # noqa: E402
from backend.app.fit.service.part_strategy_service import (  # noqa: E402
    part_strategy_service as old_part_strategy_service,
)
from backend.app.fit.utils.convert_model import (  # noqa: E402
    convert_to_pydantic_model,
    convert_to_total_quantity,
    get_ebom_tree_with_parents,
)
from backend.app.fit.utils.data_check_utils import datacheckutils  # noqa: E402
from backend.app.fit_aaron.service.part_fit_service import (  # noqa: E402
    PartFitService as AaronPartFitService,
)
from backend.app.fit_aaron.service.part_strategy_service import (  # noqa: E402
    part_strategy_service as aaron_part_strategy_service,
)
from backend.common.exception.errors import DataValidationError, FailureCheckError  # noqa: E402
from backend.common.product_config import normalize_product_config_code  # noqa: E402
from backend.database.db import async_db_session, async_engine  # noqa: E402

FIT_RESULT_COLUMNS = [
    "Distribution", "Alpha", "Beta", "Gamma", "Mu", "Sigma", "Lambda",
    "Log-likelihood", "AICc", "BIC", "AD",
]


def to_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        parsed = pd.to_datetime(value, errors="coerce")
    except Exception:
        return None
    return None if pd.isna(parsed) else parsed.date()


def cdf(distribution, x: float) -> float:
    return float(np.asarray(distribution.CDF(xvals=[x], show_plot=False)).ravel()[0])


def delta_f(distribution, t0: float, t1: float) -> float:
    t0, t1 = max(0.0, t0), max(0.0, t1)
    if distribution is None or t1 <= t0:
        return 0.0
    return max(0.0, cdf(distribution, t1) - cdf(distribution, t0))


def conditional_delta_f(distribution, t0: float, t1: float) -> float:
    t0, t1 = max(0.0, t0), max(0.0, t1)
    if distribution is None or t1 <= t0:
        return 0.0
    survive = 1.0 - cdf(distribution, t0)
    if survive <= 1e-12:
        return 0.0
    return max(0.0, (cdf(distribution, t1) - cdf(distribution, t0)) / survive)


def describe_distribution(distribution) -> str:
    if distribution is None:
        return "无"
    try:
        return str(distribution.param_title_long)
    except Exception:
        return repr(distribution)


# --------------------------------------------------------------------------- 数据读取


async def load_mappings(model: str, part: str) -> tuple[list[PartSpareMapping], str]:
    async with async_db_session() as db:
        rows = (
            await db.execute(
                select(PartSpareMapping).where(
                    PartSpareMapping.product_model == model,
                    PartSpareMapping.original_part_code == part,
                )
            )
        ).scalars().all()
        if rows:
            return list(rows), "original_part_code"
        rows = (
            await db.execute(
                select(PartSpareMapping).where(
                    PartSpareMapping.product_model == model,
                    PartSpareMapping.spare_part_code == part,
                )
            )
        ).scalars().all()
        return list(rows), "spare_part_code"


async def load_warehouses_for_spare(spare_part_code: str) -> list[WarehouseInventory]:
    async with async_db_session() as db:
        return list(
            (
                await db.execute(
                    select(WarehouseInventory).where(WarehouseInventory.part_code == spare_part_code)
                )
            ).scalars().all()
        )


async def load_warehouse_allotments(warehouse_code: str) -> list[str]:
    async with async_db_session() as db:
        rows = (
            await db.execute(select(Warehouse).where(Warehouse.code == warehouse_code))
        ).scalars().all()
    return sorted({r.allotment_two for r in rows if r.allotment_two is not None})


async def load_allotment_products(allotment_twos: list[str], model: str) -> list[Allotment]:
    if not allotment_twos:
        return []
    async with async_db_session() as db:
        return list(
            (
                await db.execute(
                    select(Allotment).where(
                        Allotment.allotment_two.in_(allotment_twos),
                        Allotment.product_model == model,
                    )
                )
            ).scalars().all()
        )


async def load_product_despatch_info(model: str, products: list[str]) -> dict[str, dict]:
    """每个产品编号：新造发运最早日期、派生码（现网口径不按型号过滤，这里两种都记录）。"""
    info: dict[str, dict] = {}
    if not products:
        return info
    async with async_db_session() as db:
        rows = (
            await db.execute(
                select(Despatch).where(
                    Despatch.identifier.in_(products),
                    Despatch.repair_level == "新造",
                )
            )
        ).scalars().all()
    for row in rows:
        if not row.identifier or not row.life_cycle_time:
            continue
        item = info.setdefault(
            row.identifier,
            {"despatch_date": None, "despatch_model": None, "despatch_config": None},
        )
        if item["despatch_date"] is None or row.life_cycle_time < item["despatch_date"]:
            item["despatch_date"] = row.life_cycle_time
            item["despatch_model"] = row.model
            item["despatch_config"] = normalize_product_config_code(row.product_config_code)
    return info


async def load_manufacturing_dates(model: str, products: list[str]) -> dict[str, date]:
    """复刻现网：发运缺失时取故障表最早 manufacturing_date。"""
    result: dict[str, date] = {}
    if not products:
        return result
    async with async_db_session() as db:
        rows = (
            await db.execute(
                select(failure_dao.model)
                .where(
                    failure_dao.model.product_model == model,
                    failure_dao.model.product_number.in_(products),
                    failure_dao.model.manufacturing_date.isnot(None),
                )
                .order_by(failure_dao.model.product_number, failure_dao.model.manufacturing_date)
            )
        ).scalars().all()
    for row in rows:
        if row.product_number in result:
            continue
        parsed = to_date(row.manufacturing_date)
        if parsed:
            result[row.product_number] = parsed
    return result


async def count_failures(model: str, part: str, input_date: date | None, config: str | None) -> int:
    async with async_db_session() as db:
        rows = await failure_dao.get_by_model_and_part(
            db, model, part, input_date, product_config_code=config
        )
    return len(rows)


async def count_window_failures(model: str, part: str, products: list[str], start: date, end: date) -> int:
    if not products:
        return 0
    async with async_db_session() as db:
        return await failure_dao.get_failure_count_by_model_and_part_in_products(
            db, model, part, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), products
        )


# --------------------------------------------------------------------------- 分布


async def current_system_distribution(model: str, part: str, input_date: date, config: str) -> dict:
    """
    复刻 ScienceWarehouseServiceChange.get_distribution_by_model_and_part，但不触发入库：
    1) 老打标通过 -> 读 fit_part（source False 再 True）的 BIC 第一条；
    2) 老打标 FailureCheckError -> 现网指数兜底（len(fit_part 记录) / 全车队运行时间）。
    """
    out = {"branch": None, "distribution": None, "detail": "", "fit_rows": []}
    try:
        await old_part_strategy_service.part_tag_process(
            model, part, input_date, product_config_code=config
        )
        out["branch"] = "老打标通过->读fit_part"
    except FailureCheckError as exc:
        out["branch"] = "老打标FailureCheckError->现网指数兜底"
        async with async_db_session() as db:
            rows = await fit_part_dao.get_by_model_and_part(db, model, part, input_date)
            t = await datacheckutils.total_run_time(db, model)
        if rows and t and t > 0:
            lam = len(rows) / t
            out["distribution"] = Exponential_Distribution(Lambda=lam)
            out["detail"] = f"{exc.msg}; lambda=len(fit_part记录={len(rows)})/t({t:.1f}h)={lam:.3e}"
        else:
            out["detail"] = f"{exc.msg}; fit_part记录={len(rows) if rows else 0}, t={t} -> 现网结果为跳过"
        return out
    except DataValidationError as exc:
        out["branch"] = "老打标DataValidationError->现网跳过"
        out["detail"] = exc.msg
        return out
    except Exception as exc:  # noqa: BLE001
        out["branch"] = "老打标异常->现网跳过"
        out["detail"] = f"{type(exc).__name__}: {exc}"
        return out

    for source in (False, True):
        async with async_db_session() as db:
            rows = await fit_part_dao.get_by_model_and_part(
                db, model, part, input_date,
                method=FitMethodType.MLE, check=FitCheckType.BIC,
                source=source, product_config_code=config,
            )
        if not rows:
            continue
        out["fit_rows"] = [
            {
                "source": int(bool(source)),
                "group_id": r.group_id,
                "created_time": r.created_time,
                "distribution": r.distribution,
                "alpha": r.alpha, "beta": r.beta, "gamma": r.gamma,
                "mu": r.mu, "sigma": r.sigma, "lambda": r.lambda_,
                "bic": r.bic, "product_config_code": r.product_config_code,
            }
            for r in rows
        ]
        params = convert_to_pydantic_model(rows[0], DistributionParams)
        out["distribution"] = await distribute_service.get_distribution_by_params(params)
        out["detail"] = (
            f"source={int(bool(source))}, group_id={rows[0].group_id}, "
            f"created_time={rows[0].created_time}, 选用={rows[0].distribution}"
        )
        return out
    out["detail"] = "fit_part 无该截止日期结果；现网会触发 Aaron 拟合入库后再读（本脚本不入库，V0 改用现场 Aaron BIC 最优代替）"
    return out


async def fresh_aaron_fit(model: str, part: str, input_date: date, config: str) -> dict:
    """现场跑 Aaron 打标 + Fit_Everything，只在内存中，不入库。"""
    out = {
        "tags": [], "error": None, "fit_table": pd.DataFrame(),
        "best": None, "best_name": None, "weibull": None, "exp_fallback": None,
    }
    try:
        out["tags"] = await aaron_part_strategy_service.part_tag_process(
            model, part, input_date, product_config_code=config
        )
    except FailureCheckError as exc:
        out["error"] = f"Aaron打标FailureCheckError: {exc.msg}"
        try:
            async with async_db_session() as db:
                lam = await AaronPartFitService.none_tag_fit(
                    db, model, part, input_date, product_config_code=config
                )
            out["exp_fallback"] = Exponential_Distribution(Lambda=lam)
        except Exception as inner:  # noqa: BLE001
            out["error"] += f"; Aaron指数兜底失败: {inner}"
        return out
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"Aaron打标失败: {type(exc).__name__}: {getattr(exc, 'msg', exc)}"
        return out

    failures = sum(1 for t in out["tags"] if t[-1] == "failure")
    if failures == 0:
        out["error"] = "Aaron标签中无 failure，无法拟合"
        return out
    try:
        fit = await AaronPartFitService.tag_fit(out["tags"], FitMethodType.MLE)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"Aaron拟合失败: {type(exc).__name__}: {exc}"
        return out

    table = fit.results.copy()
    out["fit_table"] = table[[c for c in FIT_RESULT_COLUMNS if c in table.columns]]
    out["best"] = fit.best_distribution
    out["best_name"] = fit.best_distribution_name
    alpha = getattr(fit, "Weibull_2P_alpha", None)
    beta = getattr(fit, "Weibull_2P_beta", None)
    if alpha is not None and beta is not None and not pd.isna(alpha) and not pd.isna(beta):
        out["weibull"] = Weibull_Distribution(alpha=float(alpha), beta=float(beta))
    return out


def build_unit_map(tags: list[list]) -> dict[str, list[dict]]:
    """
    tags: [identifier, identifier_index, life_cycle_time, fault, fault_day, fault_time, state]
    返回 产品编号 -> 零件位置列表（寿命起点、更换后当前寿命、历史失效次数）
    """
    units: dict[tuple, dict] = {}
    for tag in tags:
        identifier, identifier_index, life_start, _, _, fault_time, state = tag[:7]
        key = (identifier, identifier_index)
        unit = units.setdefault(
            key,
            {
                "identifier": identifier,
                "identifier_index": identifier_index,
                "life_start": to_date(life_start),
                "current_age_hours": 0.0,
                "history_failures": 0,
            },
        )
        if state == "failure":
            unit["history_failures"] += 1
        elif state == "suspense":
            unit["current_age_hours"] = float(fault_time or 0.0)
    by_product: dict[str, list[dict]] = defaultdict(list)
    for unit in units.values():
        by_product[unit["identifier"]].append(unit)
    return by_product


async def load_product_param(model: str, config: str | None):
    async with async_db_session() as db:
        row = await product_dao.get_by_model(db, model, product_config_code=config)
    if row is None:
        return None
    return {"year_days": float(row.year_days), "avg_worktime": float(row.avg_worktime),
            "config": getattr(row, "product_config_code", None)}


async def load_bom_quantity(model: str, config: str, part: str) -> int:
    async with async_db_session() as db:
        rows = await get_ebom_tree_with_parents(db, model, config, part)
    return convert_to_total_quantity(rows, part) if rows else 0


# --------------------------------------------------------------------------- 主流程


async def run() -> None:
    model, part = ARGS.model, ARGS.part
    input_date = to_date(ARGS.input_date)
    interval = ARGS.interval_days
    window_end = input_date + timedelta(days=interval)
    out_dir = Path(ARGS.out_dir) if ARGS.out_dir else Path(__file__).parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"diagnose_{model}_{part}_{stamp}.xlsx"
    log_lines: list[str] = []

    def note(text: str = "") -> None:
        print(text)
        log_lines.append(text)

    note(f"型号={model} 零部件={part} 截止日期={input_date} 窗口={interval}天 ({input_date} ~ {window_end})")

    # 1. 备品映射
    mappings, matched_by = await load_mappings(model, part)
    if not mappings:
        note("未找到备品映射，结束")
        return
    if matched_by == "spare_part_code":
        note(f"[提示] {part} 匹配的是备品编码，按映射对应的原装件计算")
    original_parts = sorted({m.original_part_code for m in mappings})
    if len(original_parts) > 1:
        note(f"[提示] 该备品对应多个原装件 {original_parts}，本脚本仅诊断第一个: {original_parts[0]}")
    fault_part = original_parts[0]
    mapping_rows = [
        {
            "product_model": m.product_model,
            "派生码(原值)": m.product_config_code,
            "派生码(规范化)": normalize_product_config_code(m.product_config_code),
            "original_part_code": m.original_part_code,
            "original_part_name": m.original_part_name,
            "spare_part_code": m.spare_part_code,
            "spare_part_name": m.spare_part_name,
        }
        for m in mappings
        if m.original_part_code == fault_part
    ]
    mapping_configs = sorted({r["派生码(规范化)"] for r in mapping_rows})
    spare_codes = sorted({r["spare_part_code"] for r in mapping_rows})
    seen_keys, kept_configs = set(), []
    for r in mapping_rows:
        key = (r["product_model"], r["original_part_code"], r["spare_part_code"])
        if key not in seen_keys:
            seen_keys.add(key)
            kept_configs.append((r["spare_part_code"], r["派生码(规范化)"]))
    note(f"映射派生码={mapping_configs}；备品={spare_codes}")
    note(f"现网去重(型号,故障件,备品)后实际只保留: {kept_configs}")

    # 2. 各派生码：失效数、BOM、运行参数、分布
    config_rows, fit_table_frames, db_fit_frames = [], [], []
    config_ctx: dict[str, dict] = {}
    param_no_config = await load_product_param(model, None)
    for config in mapping_configs:
        note(f"\n==== 派生码 {config} ====")
        failures_all = await count_failures(model, part=fault_part, input_date=None, config=config)
        failures_cut = await count_failures(model, fault_part, input_date, config)
        failures_any_config = await count_failures(model, fault_part, input_date, None)
        bom_qty = await load_bom_quantity(model, config, fault_part)
        param = await load_product_param(model, config)
        system = await current_system_distribution(model, fault_part, input_date, config)
        fresh = await fresh_aaron_fit(model, fault_part, input_date, config)
        unit_map = build_unit_map(fresh["tags"])
        note(f"故障数: 全部={failures_all}, 截止日前={failures_cut}, 截止日前(不分派生码)={failures_any_config}")
        note(f"BOM用量={bom_qty}；运行参数(带派生码)={param}；运行参数(现网不带派生码)={param_no_config}")
        note(f"现网分支={system['branch']}；{system['detail']}")
        note(f"现网分布={describe_distribution(system['distribution'])}")
        note(
            f"Aaron现场: tags={len(fresh['tags'])}, 位置数={sum(len(v) for v in unit_map.values())}, "
            f"failure={sum(1 for t in fresh['tags'] if t[-1] == 'failure')}, 错误={fresh['error']}"
        )
        note(f"Aaron BIC最优={fresh['best_name']} {describe_distribution(fresh['best'])}")
        note(f"Aaron Weibull_2P={describe_distribution(fresh['weibull'])}")

        if not fresh["fit_table"].empty:
            frame = fresh["fit_table"].copy()
            frame.insert(0, "派生码", config)
            fit_table_frames.append(frame)
        if system["fit_rows"]:
            frame = pd.DataFrame(system["fit_rows"])
            frame.insert(0, "派生码", config)
            db_fit_frames.append(frame)

        v0_dist = system["distribution"]
        v0_note = ""
        if v0_dist is None and system["branch"] == "老打标通过->读fit_part":
            v0_dist = fresh["best"]
            v0_note = "fit_part无结果,用Aaron BIC最优代替"
        weibull = fresh["weibull"] or fresh["exp_fallback"]
        bic_best = fresh["best"] or fresh["exp_fallback"]
        config_ctx[config] = {
            "param": param, "bom_qty": bom_qty, "unit_map": unit_map,
            "v0_dist": v0_dist, "weibull": weibull, "bic_best": bic_best,
        }

        hours_per_day = (param["year_days"] * param["avg_worktime"] / 365) if param else 0.0
        fleet = {"V1_W2P": 0.0, "V1_W2P_365天": 0.0, "V2": 0.0}
        for units in unit_map.values():
            for u in units:
                if not u["life_start"]:
                    continue
                age = (input_date - u["life_start"]).days * hours_per_day
                fleet["V1_W2P"] += delta_f(weibull, age, age + interval * hours_per_day)
                fleet["V1_W2P_365天"] += delta_f(weibull, age, age + 365 * hours_per_day)
                a2 = u["current_age_hours"]
                fleet["V2"] += delta_f(weibull, a2, a2 + interval * hours_per_day)
        config_rows.append(
            {
                "派生码": config,
                "故障数_全部": failures_all,
                "故障数_截止日前": failures_cut,
                "老门槛(>4条,不看截止日)通过": failures_all > 4,
                "BOM用量": bom_qty,
                "year_days(带派生码)": param and param["year_days"],
                "avg_worktime(带派生码)": param and param["avg_worktime"],
                "year_days(现网不带派生码)": param_no_config and param_no_config["year_days"],
                "avg_worktime(现网不带派生码)": param_no_config and param_no_config["avg_worktime"],
                "现网分支": system["branch"],
                "现网分布": describe_distribution(system["distribution"]),
                "现网分布说明": system["detail"],
                "V0实际所用分布": describe_distribution(v0_dist) + (f"（{v0_note}）" if v0_note else ""),
                "Aaron错误": fresh["error"],
                "Aaron_BIC最优": f"{fresh['best_name']} {describe_distribution(fresh['best'])}",
                "Aaron_Weibull_2P": describe_distribution(fresh["weibull"]),
                "Aaron标签数": len(fresh["tags"]),
                "全车队产品数(标签)": len(unit_map),
                "全车队位置数(标签)": sum(len(v) for v in unit_map.values()),
                f"全车队V1_W2P_{interval}天": round(fleet["V1_W2P"], 5),
                "全车队V1_W2P_365天": round(fleet["V1_W2P_365天"], 5),
                f"全车队V2_{interval}天": round(fleet["V2"], 5),
            }
        )
        note(
            f"全车队参考: V1_W2P_{interval}天={fleet['V1_W2P']:.5f}, "
            f"V1_W2P_365天={fleet['V1_W2P_365天']:.5f}, V2_{interval}天={fleet['V2']:.5f}"
        )

    # 3. 各库房
    warehouse_rows, product_rows, unit_rows = [], [], []
    service_cache: dict = {}
    v0_param = param_no_config
    v0_hpd = (v0_param["year_days"] * v0_param["avg_worktime"] / 365) if v0_param else 0.0
    for spare_code in spare_codes:
        v0_dist_by_kept = [c for s, c in kept_configs if s == spare_code]
        inventories = await load_warehouses_for_spare(spare_code)
        note(f"\n==== 备品 {spare_code}：{len(inventories)} 个库房 ====")
        for inv in inventories:
            allotment_twos = await load_warehouse_allotments(inv.warehouse_code)
            allot_rows = await load_allotment_products(allotment_twos, model)
            allot_by_product: dict[str, Allotment] = {}
            for row in allot_rows:
                allot_by_product.setdefault(row.product_number, row)
            products = sorted(allot_by_product)
            despatch_info = await load_product_despatch_info(model, products)
            manu_dates = await load_manufacturing_dates(
                model, [p for p in products if p not in despatch_info]
            )
            window_failures = await count_window_failures(model, fault_part, products, input_date, window_end)
            hist_start = input_date - timedelta(days=interval)
            hist_failures = await count_window_failures(model, fault_part, products, hist_start, input_date)

            totals = defaultdict(float)
            per_config_products = defaultdict(int)
            per_config_vehicles: dict[str, set] = defaultdict(set)
            per_config_units = defaultdict(int)
            unmatched = 0
            vehicles = {(allot_by_product[p].vehicle_type, allot_by_product[p].vehicle_number) for p in products}
            for product in products:
                allot = allot_by_product[product]
                dinfo = despatch_info.get(product, {})
                v0_start = dinfo.get("despatch_date") or manu_dates.get(product)
                v0_value = 0.0
                for kept_config in v0_dist_by_kept:
                    dist = config_ctx.get(kept_config, {}).get("v0_dist")
                    if dist is not None and v0_start:
                        age = (input_date - v0_start).days * v0_hpd
                        v0_value += delta_f(dist, age, age + interval * v0_hpd)
                totals["V0_现网口径"] += v0_value

                product_config = None
                units = []
                for config, ctx in config_ctx.items():
                    if product in ctx["unit_map"]:
                        product_config = config
                        units = ctx["unit_map"][product]
                        break
                row = {
                    "库房编码": inv.warehouse_code,
                    "库房名称": inv.warehouse_name,
                    "备品编码": spare_code,
                    "二级配属": allot.allotment_two,
                    "车号": allot.vehicle_number,
                    "车型": allot.vehicle_type,
                    "产品编号": product,
                    "配属表ps_code": allot.ps_code,
                    "发运表派生码": dinfo.get("despatch_config"),
                    "发运表型号": dinfo.get("despatch_model"),
                    "现网寿命起点": v0_start,
                    "现网寿命起点来源": "发运" if dinfo.get("despatch_date") else ("故障表生产日期" if v0_start else "无"),
                    "V0_现网口径": round(v0_value, 6),
                    "归属派生码(Aaron标签)": product_config,
                    "零件位置数": len(units),
                }
                if product_config is None:
                    unmatched += 1
                    row["备注"] = "不在映射任何派生码的 Aaron 标签中（无该派生码新造发运/故障记录），对齐口径不计"
                    product_rows.append(row)
                    continue

                ctx = config_ctx[product_config]
                hpd = (ctx["param"]["year_days"] * ctx["param"]["avg_worktime"] / 365) if ctx["param"] else 0.0
                per_config_products[product_config] += 1
                per_config_vehicles[product_config].add((allot.vehicle_type, allot.vehicle_number))
                per_config_units[product_config] += len(units)
                sums = defaultdict(float)
                for u in units:
                    age1 = (input_date - u["life_start"]).days * hpd if u["life_start"] else 0.0
                    age2 = u["current_age_hours"]
                    dt = interval * hpd
                    values = {
                        "V1_对齐_W2P": delta_f(ctx["weibull"], age1, age1 + dt),
                        "V1_对齐_BIC": delta_f(ctx["bic_best"], age1, age1 + dt),
                        "V2_更换后寿命": delta_f(ctx["weibull"], age2, age2 + dt),
                        "V3_条件概率": conditional_delta_f(ctx["weibull"], age2, age2 + dt),
                    }
                    for k, v in values.items():
                        sums[k] += v
                    unit_rows.append(
                        {
                            "库房编码": inv.warehouse_code,
                            "产品编号": product,
                            "车号": allot.vehicle_number,
                            "派生码": product_config,
                            "零件位置": u["identifier_index"],
                            "Aaron寿命起点": u["life_start"],
                            "截止日累计运行小时(自起点)": round(age1, 2),
                            "更换后当前寿命小时": round(age2, 2),
                            "历史失效次数": u["history_failures"],
                            **{k: round(v, 6) for k, v in values.items()},
                        }
                    )
                for k, v in sums.items():
                    totals[k] += v
                row.update({k: round(v, 6) for k, v in sums.items()})
                row["Aaron寿命起点(最早位置)"] = min((u["life_start"] for u in units if u["life_start"]), default=None)
                product_rows.append(row)

            service_result = await ScienceWarehouseServiceChange.single_warehouse_single_spare_calculate(
                time_interval_days=interval,
                input_date=input_date,
                warehouse_code=inv.warehouse_code,
                spare_part_code=spare_code,
                use_cached_fit=False,
                fit_context_cache=service_cache,
            )
            service_quantity = float(service_result.get("quantity") or 0)
            warehouse_rows.append(
                {
                    "库房编码": inv.warehouse_code,
                    "库房名称": inv.warehouse_name,
                    "备品编码": spare_code,
                    "新服务结果": service_quantity,
                    "新服务最大滚动故障数": service_result.get("max_failure_count"),
                    "新服务映射明细": str(service_result.get("statistics", {}).get("mapping_details")),
                    "二级配属": ",".join(allotment_twos),
                    "车辆数(按车型+车号去重)": len(vehicles),
                    "产品数(台,配属,不分派生码)": len(products),
                    "车辆数_按派生码": "; ".join(
                        f"{c}:{len(v)}" for c, v in sorted(per_config_vehicles.items())
                    ),
                    "产品数(台)_按派生码": "; ".join(
                        f"{c}:{n}" for c, n in sorted(per_config_products.items())
                    ),
                    "零件位置数_按派生码": "; ".join(f"{c}:{n}" for c, n in sorted(per_config_units.items())),
                    "未归属派生码产品数(台)": unmatched,
                    "V0_现网口径": round(totals["V0_现网口径"], 5),
                    "V1_对齐_W2P": round(totals["V1_对齐_W2P"], 5),
                    "V1_对齐_BIC": round(totals["V1_对齐_BIC"], 5),
                    "V2_更换后寿命": round(totals["V2_更换后寿命"], 5),
                    "V3_条件概率": round(totals["V3_条件概率"], 5),
                    f"前{interval}天实际故障数": hist_failures,
                    f"窗口内实际故障数({input_date}~{window_end})": window_failures,
                }
            )
            note(
                f"{inv.warehouse_code} {inv.warehouse_name}: 车={len(vehicles)} 产品(台)={len(products)} "
                f"派生码产品数={dict(per_config_products)} 位置={dict(per_config_units)} "
                f"新服务={service_quantity:.5f} V1_BIC={totals['V1_对齐_BIC']:.5f} "
                f"V0={totals['V0_现网口径']:.4f} V1_W2P={totals['V1_对齐_W2P']:.4f} "
                f"V2={totals['V2_更换后寿命']:.4f} 窗口实际故障={window_failures}"
            )

    # 4. 输出
    with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
        pd.DataFrame({"说明": [__doc__] + log_lines}).to_excel(writer, sheet_name="说明与日志", index=False)
        pd.DataFrame(mapping_rows).to_excel(writer, sheet_name="备品映射", index=False)
        pd.DataFrame(config_rows).to_excel(writer, sheet_name="派生码汇总", index=False)
        if fit_table_frames:
            pd.concat(fit_table_frames).to_excel(writer, sheet_name="Aaron现场拟合", index=False)
        if db_fit_frames:
            pd.concat(db_fit_frames).to_excel(writer, sheet_name="fit_part已入库", index=False)
        pd.DataFrame(warehouse_rows).to_excel(writer, sheet_name="库房汇总", index=False)
        pd.DataFrame(product_rows).to_excel(writer, sheet_name="产品明细(每台一行)", index=False)
        pd.DataFrame(unit_rows).to_excel(writer, sheet_name="零件位置明细", index=False)
    note(f"\n已输出: {out_file}")


async def main() -> None:
    try:
        await run()
    except Exception:
        traceback.print_exc()
        raise
    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
