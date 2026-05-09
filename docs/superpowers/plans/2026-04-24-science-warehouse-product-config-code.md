# Science Warehouse Product Config Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将科学库存主链路 `/calculate` 切换到 `product_model + product_config_code + original_part_code` 维度进行映射、拟合和兜底计算，并删除 `/calculate-v2` 废弃分支。

**Architecture:** 保持科学库存结果对象仍为 `warehouse + spare_part`，不改库房和库存表结构；只把派生码作为“需求来源维度”贯穿 `PartSpareMapping` 命中、故障分组、拟合调用、运行参数查询与兜底计算。最终每个 `型号 + 派生码 + 部件` 独立算量，再汇总到同一库房备品结果。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Pydantic, pytest, Celery

---

### Task 1: 锁定备品映射必须按派生码命中

**Files:**
- Modify: `backend/app/datamanage/crud/crud_part_spare_mapping.py`
- Create: `backend/app/calcu/tests/test_science_warehouse_mapping_dimension.py`
- Test: `backend/app/calcu/tests/test_science_warehouse_mapping_dimension.py`

- [ ] **Step 1: 写失败测试，锁定 PartSpareMapping 查询键必须包含 product_config_code**

```python
from types import SimpleNamespace

import pytest

from backend.app.calcu.service.science_warehouse_service import ScienceWarehouseService


@pytest.mark.asyncio
async def test_get_part_spare_mapping_passes_product_config_code(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    async def _fake_get_by_original_part_code(
        db, product_model: str, product_config_code: str | None, original_part_code: str
    ):
        captured["product_model"] = product_model
        captured["product_config_code"] = product_config_code
        captured["original_part_code"] = original_part_code
        return SimpleNamespace(spare_part_code="SP-001")

    monkeypatch.setattr(
        "backend.app.calcu.service.science_warehouse_service.part_spare_mapping_dao.get_by_original_part_code",
        _fake_get_by_original_part_code,
    )

    result = await ScienceWarehouseService.get_part_spare_mapping(
        "CR400AF", "A01", "P-001"
    )

    assert result.spare_part_code == "SP-001"
    assert captured == {
        "product_model": "CR400AF",
        "product_config_code": "A01",
        "original_part_code": "P-001",
    }
```

- [ ] **Step 2: 运行测试确认当前实现失败**

Run: `pytest backend/app/calcu/tests/test_science_warehouse_mapping_dimension.py -q`
Expected: FAIL，提示 `get_part_spare_mapping()` 参数个数不匹配，或 DAO 查询未收到 `product_config_code`

- [ ] **Step 3: 最小实现 DAO 与 service 新签名**

```python
# backend/app/datamanage/crud/crud_part_spare_mapping.py
async def get_by_original_part_code(
    self,
    db: AsyncSession,
    product_model: str,
    product_config_code: str | None,
    original_part_code: str,
) -> PartSpareMapping:
    stmt = select(self.model).where(
        self.model.product_model == product_model,
        self.model.product_config_code == product_config_code,
        self.model.original_part_code == original_part_code,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# backend/app/calcu/service/science_warehouse_service.py
@staticmethod
async def get_part_spare_mapping(
    product_model: str,
    product_config_code: str | None,
    original_part_code: str,
):
    async with async_db_session() as db:
        return await part_spare_mapping_dao.get_by_original_part_code(
            db,
            product_model,
            product_config_code,
            original_part_code,
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest backend/app/calcu/tests/test_science_warehouse_mapping_dimension.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/datamanage/crud/crud_part_spare_mapping.py backend/app/calcu/service/science_warehouse_service.py backend/app/calcu/tests/test_science_warehouse_mapping_dimension.py
git commit -m "feat: key science warehouse part mapping by product config"
```

### Task 2: 锁定主链路按 型号+派生码+部件 独立计算后再汇总

**Files:**
- Modify: `backend/app/calcu/service/science_warehouse_service.py`
- Create: `backend/app/calcu/tests/test_science_warehouse_dimension_aggregation.py`
- Test: `backend/app/calcu/tests/test_science_warehouse_dimension_aggregation.py`

- [ ] **Step 1: 写失败测试，锁定故障按 product_config_code 分组独立计算后求和**

```python
from types import SimpleNamespace

import pytest

from backend.app.calcu.service.science_warehouse_service import ScienceWarehouseService


@pytest.mark.asyncio
async def test_perform_spare_calculation_groups_by_product_config_code(monkeypatch) -> None:
    failures = [
        SimpleNamespace(
            product_model="CR400AF",
            product_config_code="A01",
            fault_material_code="P-001",
            product_number="001",
            discovery_date="2026-03-01",
        ),
        SimpleNamespace(
            product_model="CR400AF",
            product_config_code="B02",
            fault_material_code="P-001",
            product_number="002",
            discovery_date="2026-03-01",
        ),
    ] * 3

    calls: list[tuple[str, str | None, str]] = []

    async def _fake_part_tag_process_with_failures(
        model, part, input_date, model_part_failures, product_config_code=None
    ):
        calls.append((model, product_config_code, part))
        return [1, 2, 3, 4, 5]

    async def _fake_tag_fit(tags):
        class _Fit:
            best_distribution = object()

        return _Fit()

    async def _fake_calculate_spare_quantity_by_interval(
        best_distribution, time_interval_days, product_failures, input_date
    ) -> float:
        code = product_failures[0].product_config_code
        return 2.0 if code == "A01" else 3.0

    async def _fake_check_maintenance_responsibility(product_number, warehouse_code, spare_part_code):
        return {"responsible": True}

    monkeypatch.setattr(
        "backend.app.calcu.service.science_warehouse_service.part_strategy_service.part_tag_process_with_failures",
        _fake_part_tag_process_with_failures,
    )
    monkeypatch.setattr(
        "backend.app.calcu.service.science_warehouse_service.part_fit_service.tag_fit",
        _fake_tag_fit,
    )
    monkeypatch.setattr(
        ScienceWarehouseService,
        "calculate_spare_quantity_by_interval",
        _fake_calculate_spare_quantity_by_interval,
    )
    monkeypatch.setattr(
        ScienceWarehouseService,
        "check_maintenance_responsibility",
        _fake_check_maintenance_responsibility,
    )

    result = await ScienceWarehouseService.perform_spare_calculation_with_fit(
        failures=failures,
        time_interval_days=180,
        input_date=None,
        warehouse_code="WH-01",
        spare_part_code="SP-001",
    )

    assert ("CR400AF", "A01", "P-001") in calls
    assert ("CR400AF", "B02", "P-001") in calls
    assert result["success"] is True
    assert result["quantity"] == 5
```

- [ ] **Step 2: 运行测试确认当前实现失败**

Run: `pytest backend/app/calcu/tests/test_science_warehouse_dimension_aggregation.py -q`
Expected: FAIL，提示只有一个分组被调用，或 `product_config_code` 未透传

- [ ] **Step 3: 修改主链路映射、分组、拟合与兜底透传**

```python
# backend/app/calcu/service/science_warehouse_service.py
mapping = await ScienceWarehouseService.get_part_spare_mapping(
    failure.product_model,
    getattr(failure, "product_config_code", None),
    failure.fault_material_code,
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


tags = await part_strategy_service.part_tag_process_with_failures(
    product_model,
    part_code,
    input_date,
    model_part_failures,
    product_config_code=product_config_code,
)
```

- [ ] **Step 4: 补一条兜底测试，锁定运行参数查询也带 product_config_code**

```python
@pytest.mark.asyncio
async def test_exponential_fit_for_insufficient_data_uses_product_config_code(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    async def _fake_get_by_model(db, model, product_config_code=None):
        captured["model"] = model
        captured["product_config_code"] = product_config_code
        return SimpleNamespace(year_days=365, avg_worktime=10)

    monkeypatch.setattr(
        "backend.app.calcu.service.science_warehouse_service.product_dao.get_by_model",
        _fake_get_by_model,
    )
```

- [ ] **Step 5: 实现兜底链路 product_config_code 透传**

```python
# backend/app/calcu/service/science_warehouse_service.py
total_run_time = await ScienceWarehouseService.calculate_total_run_time_for_products(
    product_numbers,
    product_model,
    product_config_code,
)

product = await product_dao.get_by_model(
    db,
    product_model,
    product_config_code=product_config_code,
)
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest backend/app/calcu/tests/test_science_warehouse_mapping_dimension.py backend/app/calcu/tests/test_science_warehouse_dimension_aggregation.py -q`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add backend/app/calcu/service/science_warehouse_service.py backend/app/calcu/tests/test_science_warehouse_dimension_aggregation.py
git commit -m "feat: split science warehouse demand by product config"
```

### Task 3: 清理 `/calculate-v2` 废弃方案

**Files:**
- Modify: `backend/app/calcu/api/v1/calcu/science_warehouse.py`
- Modify: `backend/app/task/tasks/science_warehouse_task/tasks.py`
- Delete or Stop Referencing: `backend/app/calcu/service/science_warehouse_service_change.py`
- Test: `pytest backend/app/calcu/tests/test_science_warehouse_mapping_dimension.py backend/app/calcu/tests/test_science_warehouse_dimension_aggregation.py -q`

- [ ] **Step 1: 删除 API 中 `/calculate-v2` 入口与无用 import**

```python
from backend.app.task.tasks.science_warehouse_task.tasks import (
    science_warehouse_calculation_task,
    science_warehouse_calculation_and_api_task,
)

# 删除 calculate_science_warehouse_requirements_v2 路由函数
```

- [ ] **Step 2: 删除任务中的 v2 废弃任务与无用 service 引用**

```python
from backend.app.calcu.service.science_warehouse_service import (
    science_warehouse_service,
)

# 删除 ScienceWarehouseServiceChange import
# 删除 science_warehouse_calculation_v2_task
```

- [ ] **Step 3: 删除废弃 service 文件或至少移除所有引用**

```bash
git rm backend/app/calcu/service/science_warehouse_service_change.py
```

- [ ] **Step 4: 运行主链路相关测试确认清理未破坏功能**

Run: `pytest backend/app/calcu/tests/test_science_warehouse_mapping_dimension.py backend/app/calcu/tests/test_science_warehouse_dimension_aggregation.py backend/app/calcu/tests/test_calcu_identity_contract.py -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/calcu/api/v1/calcu/science_warehouse.py backend/app/task/tasks/science_warehouse_task/tasks.py backend/app/calcu/tests/test_calcu_identity_contract.py
git commit -m "chore: remove abandoned science warehouse v2 flow"
```

## Self-Review

- Spec coverage:
  - `PartSpareMapping` 按 `model + product_config_code + part` 命中：Task 1
  - 科学库存按 `型号 + 派生码 + 部件` 独立拟合、最终按库房备品求和：Task 2
  - `/calculate-v2` 废弃方案清理：Task 3
- Placeholder scan:
  - 已移除 `TODO/TBD/类似 Task N` 占位表述；每个任务都给出明确文件、测试与命令
- Type consistency:
  - 全计划统一使用 `product_config_code`
  - 统一以 `get_part_spare_mapping(product_model, product_config_code, original_part_code)` 为 service 层签名
  - 统一以 `part_strategy_service.part_tag_process_with_failures(..., product_config_code=...)` 为拟合透传入口
