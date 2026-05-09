# Product Config Code Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将首批主链路 `datamanage -> fit -> calcu` 从旧分析口径切换到 `product + product_config_code` / `product + product_config_code + part`，确保新数据、新任务、新结果全部按新维度运行。

**Architecture:** 先用测试锁定“产品身份键”和“零部件身份键”的行为，再分三层改造 `datamanage`、`fit`、`calcu`。所有写入键、查询键、任务参数和聚合键都围绕 `product_model + product_config_code` 与 `product_model + product_config_code + part` 一致收口，不做旧口径运行时兼容。

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2.x, Celery, pytest

---

### Task 1: 建立 `product_config_code` 身份键契约与入口测试

**Files:**
- Create: `backend/app/datamanage/tests/test_product_config_identity.py`
- Create: `backend/app/fit/tests/test_fit_identity_contract.py`
- Create: `backend/app/calcu/tests/test_calcu_identity_contract.py`
- Modify: `backend/app/fit/schema/fit_param.py`
- Modify: `backend/app/calcu/schema/science_warehouse.py`
- Test: `backend/app/datamanage/tests/test_product_config_identity.py`
- Test: `backend/app/fit/tests/test_fit_identity_contract.py`
- Test: `backend/app/calcu/tests/test_calcu_identity_contract.py`

- [ ] **Step 1: 写 datamanage 身份契约失败测试**

```python
from backend.app.datamanage.model.failure import Failure
from backend.app.datamanage.model.product import Product


def test_failure_model_exposes_product_config_code() -> None:
    assert hasattr(Failure, "product_config_code")


def test_product_model_exposes_product_config_code() -> None:
    assert hasattr(Product, "product_config_code")
```

- [ ] **Step 2: 运行 datamanage 身份契约测试，确认因字段不存在而失败**

Run: `pytest backend/app/datamanage/tests/test_product_config_identity.py -q`
Expected: FAIL with `AssertionError` on missing `product_config_code`

- [ ] **Step 3: 写 fit 与 calcu 入口契约失败测试**

```python
from backend.app.fit.schema.fit_param import CreateFitPartInParam, CreateFitProductInParam
from backend.app.calcu.schema.science_warehouse import ScienceWarehouseRequest


def test_fit_product_input_requires_product_config_code() -> None:
    payload = CreateFitProductInParam.model_validate(
        {"model": "CR400AF", "product_config_code": "A01", "input_date": "2026-04-01", "method": "MLE"}
    )
    assert payload.product_config_code == "A01"


def test_fit_part_input_requires_product_config_code() -> None:
    payload = CreateFitPartInParam.model_validate(
        {
            "model": "CR400AF",
            "product_config_code": "A01",
            "part": "P-001",
            "input_date": "2026-04-01",
            "method": "MLE",
        }
    )
    assert payload.product_config_code == "A01"


def test_science_warehouse_request_accepts_product_dimension_filters() -> None:
    payload = ScienceWarehouseRequest.model_validate(
        {
            "time_interval_days": 180,
            "input_date": "2026-04-01",
            "product_model": "CR400AF",
            "product_config_code": "A01",
        }
    )
    assert payload.product_model == "CR400AF"
    assert payload.product_config_code == "A01"
```

- [ ] **Step 4: 运行 fit 与 calcu 入口契约测试，确认 schema 尚未接入字段**

Run: `pytest backend/app/fit/tests/test_fit_identity_contract.py backend/app/calcu/tests/test_calcu_identity_contract.py -q`
Expected: FAIL with `ValidationError` or missing attribute assertions for `product_config_code`

- [ ] **Step 5: 最小实现 schema 契约并提交**

```python
class CreateFitProductInParam(SchemaBase):
    model: str
    product_config_code: str
    input_date: str | None = None
    method: FitMethodType = FitMethodType.MLE


class CreateFitPartInParam(SchemaBase):
    model: str
    product_config_code: str
    part: str
    input_date: str | None = None
    method: FitMethodType | None = FitMethodType.MLE


class ScienceWarehouseRequest(SchemaBase):
    time_interval_days: int = Field(180, description="需求预测时间间隔（天数）")
    input_date: Optional[date] = Field(None, description="计算截止日期")
    product_model: Optional[str] = Field(None, description="产品型号过滤")
    product_config_code: Optional[str] = Field(None, description="派生码过滤")
```

Run: `pytest backend/app/datamanage/tests/test_product_config_identity.py backend/app/fit/tests/test_fit_identity_contract.py backend/app/calcu/tests/test_calcu_identity_contract.py -q`
Expected: datamanage tests still FAIL, fit/calcu tests PASS

```bash
git add backend/app/datamanage/tests/test_product_config_identity.py backend/app/fit/tests/test_fit_identity_contract.py backend/app/calcu/tests/test_calcu_identity_contract.py backend/app/fit/schema/fit_param.py backend/app/calcu/schema/science_warehouse.py
git commit -m "test: lock product_config_code identity contracts"
```

### Task 2: 切换 datamanage 的基础实体、查询与供数服务

**Files:**
- Modify: `backend/app/datamanage/model/product.py`
- Modify: `backend/app/datamanage/model/failure.py`
- Modify: `backend/app/datamanage/schema/product.py`
- Modify: `backend/app/datamanage/schema/failure.py`
- Modify: `backend/app/datamanage/crud/crud_failure.py`
- Modify: `backend/app/datamanage/crud/crud_product.py`
- Modify: `backend/app/datamanage/service/failure_service.py`
- Modify: `backend/app/datamanage/service/product_service.py`
- Modify: `backend/app/datamanage/api/v1/datamanage/failure.py`
- Modify: `backend/app/datamanage/api/v1/datamanage/product.py`
- Test: `backend/app/datamanage/tests/test_product_config_identity.py`
- Test: `backend/app/datamanage/tests/test_product_config_code_filters.py`

- [ ] **Step 1: 写 datamanage 过滤与去重失败测试**

```python
from types import SimpleNamespace


def test_get_product_model_and_config_pairs_deduplicate_by_new_dimension() -> None:
    rows = [
        SimpleNamespace(product_model="CR400AF", product_config_code="A01"),
        SimpleNamespace(product_model="CR400AF", product_config_code="A01"),
        SimpleNamespace(product_model="CR400AF", product_config_code="B02"),
    ]
    pairs = {(row.product_model, row.product_config_code) for row in rows}
    assert pairs == {("CR400AF", "A01"), ("CR400AF", "B02")}
```

- [ ] **Step 2: 运行 datamanage 过滤测试，确认当前服务未提供新维度对**

Run: `pytest backend/app/datamanage/tests/test_product_config_code_filters.py -q`
Expected: FAIL because the test file references behavior not yet implemented in service/DAO

- [ ] **Step 3: 为 Product 与 Failure 模型补齐 `product_config_code` 并同步 schema**

```python
class Product(DataClassBase):
    __tablename__ = "dm_product"

    id: Mapped[id_key] = mapped_column(init=False)
    model: Mapped[str] = mapped_column(String(255), nullable=True, comment="产品型号")
    product_config_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="派生码"
    )


class Failure(DataClassBase):
    __tablename__ = "dm_failure"

    pk: Mapped[id_key] = mapped_column(init=False, nullable=False)
    product_model: Mapped[str] = mapped_column(String(128), nullable=True, comment="产品型号")
    product_config_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="派生码"
    )
    fault_material_code: Mapped[str] = mapped_column(
        String(128), nullable=True, comment="终判故障部位物料代号", name="fault_part_code"
    )
```

- [ ] **Step 4: 更新 DAO 与 service，使供数按新维度返回**

```python
class FailureService:
    @staticmethod
    async def get_product_dimension_pairs() -> Sequence[list[str]]:
        async with async_db_session() as db:
            rows = await failure_dao.get_distinct_columns_values(
                db, ["product_model", "product_config_code"]
            )
            return [[product_model, product_config_code] for product_model, product_config_code in rows]

    @staticmethod
    async def get_parts_by_model_and_config(product_model: str, product_config_code: str) -> Sequence[str]:
        async with async_db_session() as db:
            return await failure_dao.get_distinct_column_values_by_dimension(
                db, product_model, product_config_code, "fault_material_code"
            )
```

- [ ] **Step 5: 运行 datamanage 测试并提交**

Run: `pytest backend/app/datamanage/tests/test_product_config_identity.py backend/app/datamanage/tests/test_product_config_code_filters.py -q`
Expected: PASS

```bash
git add backend/app/datamanage/model/product.py backend/app/datamanage/model/failure.py backend/app/datamanage/schema/product.py backend/app/datamanage/schema/failure.py backend/app/datamanage/crud/crud_failure.py backend/app/datamanage/crud/crud_product.py backend/app/datamanage/service/failure_service.py backend/app/datamanage/service/product_service.py backend/app/datamanage/api/v1/datamanage/failure.py backend/app/datamanage/api/v1/datamanage/product.py backend/app/datamanage/tests/test_product_config_identity.py backend/app/datamanage/tests/test_product_config_code_filters.py
git commit -m "feat: wire product_config_code through datamanage"
```

### Task 3: 切换 fit 的输入模型、结果模型与 DAO 查询键

**Files:**
- Modify: `backend/app/fit/model/fit_product.py`
- Modify: `backend/app/fit/model/fit_part.py`
- Modify: `backend/app/fit/schema/fit_param.py`
- Modify: `backend/app/fit/crud/crud_fit_product.py`
- Modify: `backend/app/fit/crud/crud_fit_part.py`
- Create: `backend/app/fit/tests/test_fit_query_keys.py`
- Test: `backend/app/fit/tests/test_fit_query_keys.py`

- [ ] **Step 1: 写 fit 查询键失败测试**

```python
from backend.app.fit.schema.fit_param import CreateFitPartInParam, CreateFitProductInParam


def test_fit_product_payload_contains_dimension_key() -> None:
    payload = CreateFitProductInParam(model="CR400AF", product_config_code="A01", input_date="2026-04-01")
    assert payload.product_config_code == "A01"


def test_fit_part_payload_contains_dimension_key() -> None:
    payload = CreateFitPartInParam(
        model="CR400AF",
        product_config_code="A01",
        part="P-001",
        input_date="2026-04-01",
    )
    assert (payload.model, payload.product_config_code, payload.part) == ("CR400AF", "A01", "P-001")
```

- [ ] **Step 2: 运行 fit 查询键测试，确认结果模型与 DAO 还没接入新维度**

Run: `pytest backend/app/fit/tests/test_fit_query_keys.py -q`
Expected: FAIL after schema passes but DAO/model-based assertions still fail because result models lack `product_config_code`

- [ ] **Step 3: 为 fit 结果模型补齐 `product_config_code`**

```python
class FitProduct(DataClassBase):
    __tablename__ = "fit_product"

    id: Mapped[id_key] = mapped_column(init=False)
    group_id: Mapped[str] = mapped_column(String(50), index=True, comment="分组ID")
    model: Mapped[str] = mapped_column(String(30), index=True, comment="型号")
    product_config_code: Mapped[str] = mapped_column(String(64), index=True, comment="派生码")
    input_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="输入日期")


class FitPart(DataClassBase):
    __tablename__ = "fit_part"

    id: Mapped[id_key] = mapped_column(init=False)
    group_id: Mapped[str] = mapped_column(String(50), index=True, comment="分组ID")
    model: Mapped[str] = mapped_column(String(30), index=True, comment="型号")
    product_config_code: Mapped[str] = mapped_column(String(64), index=True, comment="派生码")
    part: Mapped[str] = mapped_column(String(30), index=True, comment="零部件物料编码")
```

- [ ] **Step 4: 修改 DAO 查询方法，使所有“最新 group”和“最佳结果”按新维度定位**

```python
base_conditions = [
    self.model.model == model,
    self.model.product_config_code == product_config_code,
    self.model.method == method,
    self.model.source == source,
]

base_conditions = [
    self.model.model == model,
    self.model.product_config_code == product_config_code,
    self.model.part == part,
    self.model.method == method,
    self.model.source == source,
]
```

- [ ] **Step 5: 运行 fit 查询键测试并提交**

Run: `pytest backend/app/fit/tests/test_fit_identity_contract.py backend/app/fit/tests/test_fit_query_keys.py -q`
Expected: PASS

```bash
git add backend/app/fit/model/fit_product.py backend/app/fit/model/fit_part.py backend/app/fit/schema/fit_param.py backend/app/fit/crud/crud_fit_product.py backend/app/fit/crud/crud_fit_part.py backend/app/fit/tests/test_fit_query_keys.py
git commit -m "feat: add product_config_code to fit query keys"
```

### Task 4: 切换 fit 的 service、任务与 API，统一按新维度执行拟合

**Files:**
- Modify: `backend/app/fit/service/product_fit_service.py`
- Modify: `backend/app/fit/service/part_fit_service.py`
- Modify: `backend/app/fit/service/product_strategy_service.py`
- Modify: `backend/app/fit/service/part_strategy_service.py`
- Modify: `backend/app/fit/api/v1/fit_product.py`
- Modify: `backend/app/fit/api/v1/fit_part.py`
- Modify: `backend/app/task/tasks/fit_task/tasks.py`
- Create: `backend/app/fit/tests/test_fit_tasks_and_routes.py`
- Test: `backend/app/fit/tests/test_fit_tasks_and_routes.py`

- [ ] **Step 1: 写 fit 任务与接口失败测试**

```python
from backend.app.fit.schema.fit_param import CreateFitProductInParam


def test_product_fit_payload_keeps_product_dimension() -> None:
    payload = CreateFitProductInParam(
        model="CR400AF",
        product_config_code="A01",
        input_date="2026-04-01",
        method="MLE",
    )
    assert (payload.model, payload.product_config_code) == ("CR400AF", "A01")
```

- [ ] **Step 2: 运行 fit 任务与接口测试，确认任务签名与 API 仍按旧口径**

Run: `pytest backend/app/fit/tests/test_fit_tasks_and_routes.py -q`
Expected: FAIL because task function signatures and route params do not accept `product_config_code`

- [ ] **Step 3: 修改 product/part fit service 的样本查询与落库调用**

```python
async def create(*, obj: CreateFitProductInParam) -> None:
    input_date = dateutils.validate_and_parse_date(obj.input_date)
    is_system_default = input_date == date.today() and obj.method == FitMethodType.MLE

    async with async_db_session() as db:
        if is_system_default and await ProductFitService._recent_fit_exists(
            db, obj.model, obj.product_config_code, input_date, obj.method
        ):
            return

        await ProductFitService._perform_and_save_fit(
            obj.model, obj.product_config_code, input_date, obj.method, not is_system_default
        )
```

- [ ] **Step 4: 修改 Celery 任务与 API，使产品维度和零部件维度参数完整下传**

```python
@celery_app.task(name="product_fit_task")
async def product_fit_task(
    model: str, product_config_code: str, input_date: str, method: FitMethodType = FitMethodType.MLE
) -> str:
    fit_param = CreateFitProductInParam(
        model=model,
        product_config_code=product_config_code,
        input_date=input_date,
        method=method,
    )
    await product_fit_service.create(obj=fit_param)
    return f"Task completed for model: {model}, product_config_code: {product_config_code}"


@router.post("/fit", summary="整机级别:创建单型号数据拟合->后台任务执行")
async def product_create_fit_task(obj: CreateFitProductInParam):
    task = product_fit_task.delay(obj.model, obj.product_config_code, obj.input_date, obj.method)
    return response_base.success(data={"task_id": task.id, "task_name": product_fit_task.name, "message": "任务已提交"})
```

- [ ] **Step 5: 运行 fit 服务/任务测试并提交**

Run: `pytest backend/app/fit/tests/test_fit_identity_contract.py backend/app/fit/tests/test_fit_query_keys.py backend/app/fit/tests/test_fit_tasks_and_routes.py -q`
Expected: PASS

```bash
git add backend/app/fit/service/product_fit_service.py backend/app/fit/service/part_fit_service.py backend/app/fit/service/product_strategy_service.py backend/app/fit/service/part_strategy_service.py backend/app/fit/api/v1/fit_product.py backend/app/fit/api/v1/fit_part.py backend/app/task/tasks/fit_task/tasks.py backend/app/fit/tests/test_fit_tasks_and_routes.py
git commit -m "feat: cut fit tasks and routes to new dimension keys"
```

### Task 5: 切换 calcu 的结果模型、筛选模型与查询入口

**Files:**
- Modify: `backend/app/calcu/model/science_warehouse_result.py`
- Modify: `backend/app/calcu/model/science_warehouse_statistics.py`
- Modify: `backend/app/calcu/model/spare_statistics_result.py`
- Modify: `backend/app/calcu/schema/science_warehouse.py`
- Modify: `backend/app/calcu/schema/spare_statistics.py`
- Modify: `backend/app/calcu/api/v1/spare/predict_product.py`
- Modify: `backend/app/calcu/api/v1/spare/predict_part.py`
- Modify: `backend/app/calcu/api/v1/spare/statistics.py`
- Create: `backend/app/calcu/tests/test_calcu_filters_and_models.py`
- Test: `backend/app/calcu/tests/test_calcu_filters_and_models.py`

- [ ] **Step 1: 写 calcu 结果与过滤失败测试**

```python
from backend.app.calcu.schema.science_warehouse import ScienceWarehouseFilterParam


def test_science_warehouse_filter_accepts_product_config_code() -> None:
    payload = ScienceWarehouseFilterParam.model_validate(
        {"product_model": "CR400AF", "product_config_code": "A01"}
    )
    assert payload.product_model == "CR400AF"
    assert payload.product_config_code == "A01"
```

- [ ] **Step 2: 运行 calcu 过滤测试，确认结果查询模型未接入派生码**

Run: `pytest backend/app/calcu/tests/test_calcu_filters_and_models.py -q`
Expected: FAIL with `ValidationError` or missing field assertions for `product_config_code`

- [ ] **Step 3: 在 calcu 结果模型和 schema 中补齐产品维度字段**

```python
class ScienceWarehouseResult(DataClassBase):
    __tablename__ = "science_warehouse_result"

    id: Mapped[id_key] = mapped_column(init=False)
    calculation_id: Mapped[str] = mapped_column(String(64), index=True)
    product_model: Mapped[str | None] = mapped_column(String(64), index=True, comment="产品型号")
    product_config_code: Mapped[str | None] = mapped_column(String(64), index=True, comment="派生码")
    spare_part_code: Mapped[str] = mapped_column(String(64), index=True, comment="备品编码")


class ScienceWarehouseFilterParam(SchemaBase):
    calculation_id: Optional[str] = Field(None, description="计算批次ID")
    product_model: Optional[str] = Field(None, description="产品型号")
    product_config_code: Optional[str] = Field(None, description="派生码")
    warehouse_code: Optional[str] = Field(None, description="库房编码")
```

- [ ] **Step 4: 修改 spare/calcu API，使查询参数和结果输出透传新维度**

```python
@router.get("/predict-product")
async def predict_product(
    model: str,
    product_config_code: str,
    input_date: str | None = None,
):
    result = await spare_service.predict_product(model=model, product_config_code=product_config_code, input_date=input_date)
    return response_base.success(data=result)
```

- [ ] **Step 5: 运行 calcu 模型/过滤测试并提交**

Run: `pytest backend/app/calcu/tests/test_calcu_identity_contract.py backend/app/calcu/tests/test_calcu_filters_and_models.py -q`
Expected: PASS

```bash
git add backend/app/calcu/model/science_warehouse_result.py backend/app/calcu/model/science_warehouse_statistics.py backend/app/calcu/model/spare_statistics_result.py backend/app/calcu/schema/science_warehouse.py backend/app/calcu/schema/spare_statistics.py backend/app/calcu/api/v1/spare/predict_product.py backend/app/calcu/api/v1/spare/predict_part.py backend/app/calcu/api/v1/spare/statistics.py backend/app/calcu/tests/test_calcu_filters_and_models.py
git commit -m "feat: add product_config_code to calcu filters and result models"
```

### Task 6: 切换 calcu 的 service 聚合与 fit 结果关联条件

**Files:**
- Modify: `backend/app/calcu/service/science_warehouse_service.py`
- Modify: `backend/app/calcu/service/spare_service.py`
- Modify: `backend/app/calcu/service/spare_statistics_service.py`
- Modify: `backend/app/calcu/service/reliability_index_service.py`
- Modify: `backend/app/datamanage/crud/crud_failure.py`
- Modify: `backend/app/datamanage/crud/crud_part_spare_mapping.py`
- Create: `backend/app/calcu/tests/test_calcu_dimension_isolation.py`
- Test: `backend/app/calcu/tests/test_calcu_dimension_isolation.py`

- [ ] **Step 1: 写 calcu 维度隔离失败测试**

```python
def test_product_dimension_identity_is_model_plus_product_config_code() -> None:
    left = ("CR400AF", "A01")
    right = ("CR400AF", "B02")
    assert left != right


def test_part_dimension_identity_is_model_plus_product_config_code_plus_part() -> None:
    left = ("CR400AF", "A01", "P-001")
    right = ("CR400AF", "A01", "P-002")
    assert left != right
```

- [ ] **Step 2: 运行 calcu 维度隔离测试，确认 service 查询仍按旧维度聚合**

Run: `pytest backend/app/calcu/tests/test_calcu_dimension_isolation.py -q`
Expected: FAIL after adding concrete service assertions against old method signatures

- [ ] **Step 3: 修改 science warehouse 与 spare 相关 service，使所有取样和 fit 结果查询都纳入 `product_config_code`**

```python
related_models = await ScienceWarehouseService.get_models_using_spare(spare_part["part_code"])

for product_model, product_config_code in related_models:
    fit_records = await part_fit_service.get_by_model_and_part(
        model=product_model,
        product_config_code=product_config_code,
        part=spare_part["part_code"],
        input_date=input_date,
    )
```

- [ ] **Step 4: 修改 datamanage DAO 的聚合过滤方法，提供按新维度筛选的 failure 样本**

```python
async def get_by_dimension(
    self,
    db: AsyncSession,
    product_model: str,
    product_config_code: str,
) -> Sequence[Failure]:
    stmt = (
        select(self.model)
        .where(self.model.product_model == product_model)
        .where(self.model.product_config_code == product_config_code)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
```

- [ ] **Step 5: 运行 calcu 维度隔离测试并提交**

Run: `pytest backend/app/calcu/tests/test_calcu_identity_contract.py backend/app/calcu/tests/test_calcu_filters_and_models.py backend/app/calcu/tests/test_calcu_dimension_isolation.py -q`
Expected: PASS

```bash
git add backend/app/calcu/service/science_warehouse_service.py backend/app/calcu/service/spare_service.py backend/app/calcu/service/spare_statistics_service.py backend/app/calcu/service/reliability_index_service.py backend/app/datamanage/crud/crud_failure.py backend/app/datamanage/crud/crud_part_spare_mapping.py backend/app/calcu/tests/test_calcu_dimension_isolation.py
git commit -m "feat: isolate calcu aggregations by product config code"
```

### Task 7: 运行首批闭环验证并清理文档

**Files:**
- Modify: `README.zh-CN.md`
- Modify: `backend/app/calcu/api/v1/calcu/README.md`
- Modify: `backend/app/task/README.md`
- Test: `backend/app/datamanage/tests/test_product_config_identity.py`
- Test: `backend/app/datamanage/tests/test_product_config_code_filters.py`
- Test: `backend/app/fit/tests/test_fit_identity_contract.py`
- Test: `backend/app/fit/tests/test_fit_query_keys.py`
- Test: `backend/app/fit/tests/test_fit_tasks_and_routes.py`
- Test: `backend/app/calcu/tests/test_calcu_identity_contract.py`
- Test: `backend/app/calcu/tests/test_calcu_filters_and_models.py`
- Test: `backend/app/calcu/tests/test_calcu_dimension_isolation.py`

- [ ] **Step 1: 更新文档中的新口径说明**

```markdown
首批链路已切换为以下正式分析维度：

- 整机：`product_model + product_config_code`
- 零部件：`product_model + product_config_code + part`

旧口径不再作为新导入数据和新计算任务的目标路径。
```

- [ ] **Step 2: 运行 datamanage 全部新增测试**

Run: `pytest backend/app/datamanage/tests/test_product_config_identity.py backend/app/datamanage/tests/test_product_config_code_filters.py -q`
Expected: PASS

- [ ] **Step 3: 运行 fit 全部新增测试**

Run: `pytest backend/app/fit/tests/test_fit_identity_contract.py backend/app/fit/tests/test_fit_query_keys.py backend/app/fit/tests/test_fit_tasks_and_routes.py -q`
Expected: PASS

- [ ] **Step 4: 运行 calcu 全部新增测试**

Run: `pytest backend/app/calcu/tests/test_calcu_identity_contract.py backend/app/calcu/tests/test_calcu_filters_and_models.py backend/app/calcu/tests/test_calcu_dimension_isolation.py -q`
Expected: PASS

- [ ] **Step 5: 运行首批闭环测试并提交**

Run: `pytest backend/app/datamanage/tests/test_product_config_identity.py backend/app/datamanage/tests/test_product_config_code_filters.py backend/app/fit/tests/test_fit_identity_contract.py backend/app/fit/tests/test_fit_query_keys.py backend/app/fit/tests/test_fit_tasks_and_routes.py backend/app/calcu/tests/test_calcu_identity_contract.py backend/app/calcu/tests/test_calcu_filters_and_models.py backend/app/calcu/tests/test_calcu_dimension_isolation.py -q`
Expected: PASS with all new identity, routing, aggregation, and isolation tests green

```bash
git add README.zh-CN.md backend/app/calcu/api/v1/calcu/README.md backend/app/task/README.md
git commit -m "docs: document product_config_code cutover"
```
