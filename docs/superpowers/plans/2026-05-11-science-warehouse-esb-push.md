# Science Warehouse ESB Push Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a manual-review-first science warehouse push flow that sends only reviewed rows from a dedicated push table to external business systems through ESB.

**Architecture:** Keep `calcu_science_warehouse_result` as the algorithm output and export source. Add a mirror push table for reviewed import data, a push log table for ESB traceability, an ESB client wrapper, and a Celery task triggered by `POST /calcu/science-warehouse/push/{calculation_id}`. The push service reads only the push table and never falls back to the calculation result table.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy async ORM, `sqlalchemy-crud-plus`, Celery, `httpx.AsyncClient`, pytest.

---

## Requirements Baseline

- Business users export rows from `calcu_science_warehouse_result`, review or modify them offline, then import reviewed rows into a new push table.
- Push trigger uses `calculation_id`; the implementation must query the push table by `calculation_id`.
- ESB is called by HTTP POST with JSON body, UTF-8, standard ESB headers, and synchronous response handling.
- ESB headers must include `Content-Type`, `requestId`, `trackId`, `sourceSystem`, `serviceName`, and `requestTime`.
- ESB response headers should be recorded when available: `statusFlag`, `requestId`, `esbCode`, and `esbDesc`.
- ESB document recommends request payloads stay under 100KB and not exceed 1MB, so the implementation must chunk payloads by byte size before sending.
- Push status and ESB responses belong to push logs, not the push result table.

## File Structure

Create:

- `backend/app/calcu/model/science_warehouse_push_result.py`  
  SQLAlchemy model for reviewed rows ready to push.

- `backend/app/calcu/model/science_warehouse_push_log.py`  
  SQLAlchemy model for one ESB push attempt per chunk.

- `backend/app/calcu/crud/crud_science_warehouse_push_result.py`  
  Query, count, and batch read helpers for push rows.

- `backend/app/calcu/crud/crud_science_warehouse_push_log.py`  
  Create/update helpers for push logs.

- `backend/app/calcu/service/science_warehouse_esb_client.py`  
  ESB header generation, byte-size chunking, and HTTP call wrapper.

- `backend/app/calcu/service/science_warehouse_push_service.py`  
  Orchestrates loading push rows, chunking, ESB calls, and log updates.

- `backend/app/calcu/tests/test_science_warehouse_push_contract.py`  
  Unit tests for schemas, chunking, payload construction, and route contract.

- `backend/alembic/versions/20260511_fix_science_warehouse_result_and_push_tables.py`  
  Migration for removing source-dimension columns from the science warehouse result table and creating the push result and push log tables. If the project continues not to use checked-in Alembic versions, convert this migration into the team's current database change process while preserving the same table definitions.

Modify:

- `backend/app/calcu/model/__init__.py`  
  Export the two new models so metadata discovery can include them.

- `backend/app/calcu/schema/science_warehouse.py`  
  Add push request, push task response, push item, and push summary schemas.

- `backend/app/calcu/api/v1/calcu/science_warehouse.py`  
  Add the internal push endpoint.

- `backend/app/task/tasks/science_warehouse_task/tasks.py`  
  Add `science_warehouse_push_task`.

- `backend/app/task/tasks/science_warehouse_task/__init__.py`  
  Export `science_warehouse_push_task`.

- `backend/core/conf.py`  
  Add ESB configuration with safe defaults and environment overrides.

- `backend/app/calcu/tests/test_calcu_identity_contract.py`  
  Update the task export contract after the push task is added.

## Data Model

### Push Result Table

Table name: `calcu_science_warehouse_push_result`

Use the same business columns as the corrected `ScienceWarehouseResult`, plus import metadata. The push table must stay at the final `warehouse + spare_part` result dimension and must not store `product_model` or `product_config_code`; those are source dimensions used only inside the calculation chain.

Recommended model shape:

```python
class ScienceWarehousePushResult(Base):
    """科学库存待推送结果。"""

    __tablename__ = "calcu_science_warehouse_push_result"

    id: Mapped[id_key] = mapped_column(init=False)
    calculation_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="计算批次ID")
    warehouse_code: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="库房编码")
    warehouse_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="库房名称")
    spare_part_code: Mapped[str] = mapped_column(String(255), nullable=False, index=True, comment="备品编码")
    spare_part_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="备品名称")
    max_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="最大滚动故障次数")
    required_quantity: Mapped[int] = mapped_column(Integer, nullable=False, comment="需求数量")
    calculation_method: Mapped[str] = mapped_column(String(50), nullable=False, comment="计算方法")
    time_interval_days: Mapped[int] = mapped_column(Integer, nullable=False, comment="时间间隔（天）")
    input_date: Mapped[date] = mapped_column(Date, nullable=False, comment="计算截止日期")
    source_created_time: Mapped[date | None] = mapped_column(Date, nullable=True, comment="原结果创建日期")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5, comment="置信度")
    imported_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, comment="导入时间")
```

### Push Log Table

Table name: `calcu_science_warehouse_push_log`

Recommended fields:

```python
class ScienceWarehousePushLog(Base):
    """科学库存推送日志。"""

    __tablename__ = "calcu_science_warehouse_push_log"

    id: Mapped[id_key] = mapped_column(init=False)
    calculation_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="计算批次ID")
    push_reason: Mapped[str] = mapped_column(String(500), nullable=False, comment="推送原因")
    push_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True, comment="推送状态")
    chunk_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="分包序号")
    chunk_total: Mapped[int] = mapped_column(Integer, nullable=False, comment="分包总数")
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, comment="本次分包记录数")
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="ESB消息流水号")
    track_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="ESB链路追踪号")
    service_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="ESB服务名")
    payload_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, comment="请求体字节数")
    esb_status_flag: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="ESB状态标识")
    esb_code: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="ESB响应码")
    esb_desc: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="ESB响应描述")
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True, comment="响应体")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="异常信息")
    pushed_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="推送完成时间")
```

Use these status values consistently:

- `running`
- `success`
- `failed`

Aggregate endpoint responses can derive `partial_success` when some chunk logs succeeded and some failed.

## Task 1: Schema Contract

**Files:**

- Modify: `backend/app/calcu/schema/science_warehouse.py`
- Create: `backend/app/calcu/tests/test_science_warehouse_push_contract.py`

- [ ] **Step 1: Add failing tests for push schemas**

Add tests:

```python
from backend.app.calcu.schema.science_warehouse import (
    ScienceWarehousePushRequest,
    ScienceWarehousePushTaskResponse,
)


def test_science_warehouse_push_request_requires_reason() -> None:
    payload = ScienceWarehousePushRequest.model_validate(
        {"push_reason": "月度库存审查完成后推送"}
    )
    assert payload.push_reason == "月度库存审查完成后推送"


def test_science_warehouse_push_task_response_contract() -> None:
    payload = ScienceWarehousePushTaskResponse.model_validate(
        {
            "task_id": "celery-task-id",
            "task_name": "science_warehouse_push_task",
            "calculation_id": "SW_123",
            "message": "科学库存推送任务已提交",
        }
    )
    assert payload.calculation_id == "SW_123"
```

- [ ] **Step 2: Run schema tests and verify failure**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py -q
```

Expected: fails because `ScienceWarehousePushRequest` and `ScienceWarehousePushTaskResponse` do not exist.

- [ ] **Step 3: Add schemas**

Add these classes to `backend/app/calcu/schema/science_warehouse.py`:

```python
class ScienceWarehousePushRequest(SchemaBase):
    """科学库存推送请求。"""

    push_reason: str = Field(..., max_length=500, description="推送原因")


class ScienceWarehousePushTaskResponse(SchemaBase):
    """科学库存推送任务提交响应。"""

    task_id: str = Field(..., description="Celery任务ID")
    task_name: str = Field(..., description="Celery任务名称")
    calculation_id: str = Field(..., description="计算批次ID")
    message: str = Field(..., description="提示信息")
```

- [ ] **Step 4: Run schema tests and verify pass**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py -q
```

Expected: pass.

## Task 2: Database Models and Migration

**Files:**

- Create: `backend/app/calcu/model/science_warehouse_push_result.py`
- Create: `backend/app/calcu/model/science_warehouse_push_log.py`
- Modify: `backend/app/calcu/model/__init__.py`
- Create: `backend/alembic/versions/20260511_add_science_warehouse_push_tables.py`
- Test: `backend/app/calcu/tests/test_science_warehouse_push_contract.py`

- [ ] **Step 1: Add model import tests**

Add:

```python
from backend.app.calcu.model.science_warehouse_push_result import ScienceWarehousePushResult
from backend.app.calcu.model.science_warehouse_push_log import ScienceWarehousePushLog


def test_science_warehouse_push_model_table_names() -> None:
    assert ScienceWarehousePushResult.__tablename__ == "calcu_science_warehouse_push_result"
    assert ScienceWarehousePushLog.__tablename__ == "calcu_science_warehouse_push_log"
```

- [ ] **Step 2: Run model tests and verify failure**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_science_warehouse_push_model_table_names -q
```

Expected: import failure because the models do not exist.

- [ ] **Step 3: Create both model files**

Implement the push result and push log models using the fields in the Data Model section. Import `date` and `datetime` from `datetime`, `Date`, `DateTime`, `Float`, `Integer`, `String`, and `Text` from SQLAlchemy, and `Base`, `id_key` from `backend.common.model`.

- [ ] **Step 4: Export models**

Update `backend/app/calcu/model/__init__.py`:

```python
from backend.app.calcu.model.science_warehouse_result import ScienceWarehouseResult
from backend.app.calcu.model.science_warehouse_statistics import ScienceWarehouseStatistics
from backend.app.calcu.model.science_warehouse_push_result import ScienceWarehousePushResult
from backend.app.calcu.model.science_warehouse_push_log import ScienceWarehousePushLog
```

- [ ] **Step 5: Add migration**

Create an Alembic revision that creates both tables and indexes for:

- `calculation_id`
- `warehouse_code`
- `spare_part_code`
- `push_status`
- `request_id`
- `track_id`

The migration must also drop both tables in `downgrade()`.

- [ ] **Step 6: Run model tests**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_science_warehouse_push_model_table_names -q
```

Expected: pass.

## Task 3: Push Result and Log CRUD

**Files:**

- Create: `backend/app/calcu/crud/crud_science_warehouse_push_result.py`
- Create: `backend/app/calcu/crud/crud_science_warehouse_push_log.py`
- Test: `backend/app/calcu/tests/test_science_warehouse_push_contract.py`

- [ ] **Step 1: Add DAO contract tests**

Add:

```python
from backend.app.calcu.crud.crud_science_warehouse_push_result import science_warehouse_push_result_dao
from backend.app.calcu.crud.crud_science_warehouse_push_log import science_warehouse_push_log_dao


def test_science_warehouse_push_daos_use_expected_models() -> None:
    assert science_warehouse_push_result_dao.model.__tablename__ == "calcu_science_warehouse_push_result"
    assert science_warehouse_push_log_dao.model.__tablename__ == "calcu_science_warehouse_push_log"
```

- [ ] **Step 2: Run DAO tests and verify failure**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_science_warehouse_push_daos_use_expected_models -q
```

Expected: import failure.

- [ ] **Step 3: Implement push result DAO**

Create `CRUDScienceWarehousePushResult(CRUDPlus[ScienceWarehousePushResult])` with:

```python
async def get_by_calculation_id(self, db: AsyncSession, calculation_id: str) -> list[ScienceWarehousePushResult]:
    return await self.select_models(db, calculation_id__eq=calculation_id)


async def count_by_calculation_id(self, db: AsyncSession, calculation_id: str) -> int:
    stmt = select(func.count()).select_from(self.model).where(self.model.calculation_id == calculation_id)
    result = await db.execute(stmt)
    return int(result.scalar_one())
```

Expose:

```python
science_warehouse_push_result_dao = CRUDScienceWarehousePushResult(ScienceWarehousePushResult)
```

- [ ] **Step 4: Implement push log DAO**

Create `CRUDScienceWarehousePushLog(CRUDPlus[ScienceWarehousePushLog])` with:

```python
async def create_log(self, db: AsyncSession, data: dict[str, Any]) -> ScienceWarehousePushLog:
    log = ScienceWarehousePushLog(**data)
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def update_log(self, db: AsyncSession, log: ScienceWarehousePushLog, data: dict[str, Any]) -> ScienceWarehousePushLog:
    for key, value in data.items():
        setattr(log, key, value)
    await db.commit()
    await db.refresh(log)
    return log
```

Expose:

```python
science_warehouse_push_log_dao = CRUDScienceWarehousePushLog(ScienceWarehousePushLog)
```

- [ ] **Step 5: Run DAO tests**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_science_warehouse_push_daos_use_expected_models -q
```

Expected: pass.

## Task 4: ESB Client and Chunking

**Files:**

- Modify: `backend/core/conf.py`
- Create: `backend/app/calcu/service/science_warehouse_esb_client.py`
- Test: `backend/app/calcu/tests/test_science_warehouse_push_contract.py`

- [ ] **Step 1: Add chunking and header tests**

Add:

```python
from backend.app.calcu.service.science_warehouse_esb_client import (
    ScienceWarehouseEsbClient,
    chunk_payload_records,
)


def test_esb_headers_include_required_fields() -> None:
    headers = ScienceWarehouseEsbClient.build_headers(
        source_system="REIS",
        service_name="S_REIS_WMS_ScienceWarehousePush_S",
    )
    assert headers["Content-Type"] == "application/json"
    assert headers["sourceSystem"] == "REIS"
    assert headers["serviceName"] == "S_REIS_WMS_ScienceWarehousePush_S"
    assert "requestId" in headers
    assert "trackId" in headers
    assert "requestTime" in headers


def test_chunk_payload_records_respects_byte_limit() -> None:
    records = [{"spare_part_name": "A" * 200, "required_quantity": 1} for _ in range(10)]
    chunks = chunk_payload_records(records, base_payload={"calculation_id": "SW_123"}, max_bytes=900)
    assert len(chunks) > 1
    assert sum(len(chunk) for chunk in chunks) == 10
```

- [ ] **Step 2: Run client tests and verify failure**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_esb_headers_include_required_fields backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_chunk_payload_records_respects_byte_limit -q
```

Expected: import failure.

- [ ] **Step 3: Add ESB settings**

Add to `backend/core/conf.py`:

```python
    # Science warehouse ESB push
    SCIENCE_WAREHOUSE_ESB_URL: str = "http://172.30.9.40:18080/esb/comm/api"
    SCIENCE_WAREHOUSE_ESB_SOURCE_SYSTEM: str = "REIS"
    SCIENCE_WAREHOUSE_ESB_SERVICE_NAME: str = "S_REIS_WMS_ScienceWarehousePush_S"
    SCIENCE_WAREHOUSE_ESB_TIMEOUT_SECONDS: int = 35
    SCIENCE_WAREHOUSE_ESB_MAX_PAYLOAD_BYTES: int = 100 * 1024
```

- [ ] **Step 4: Implement chunking**

Implement `chunk_payload_records(records, base_payload, max_bytes)` so it:

- Serializes with `json.dumps(..., ensure_ascii=False)`.
- Computes byte size with `.encode("utf-8")`.
- Preserves record order.
- Raises `ValueError` if a single record exceeds `max_bytes` with the base payload.

- [ ] **Step 5: Implement ESB client**

Create `ScienceWarehouseEsbClient` with:

- `build_headers(source_system: str, service_name: str) -> dict[str, str]`
- `async post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout_seconds: int) -> EsbResponse`

`EsbResponse` can be a dataclass:

```python
@dataclass(frozen=True)
class EsbResponse:
    http_status: int
    headers: dict[str, str]
    body_text: str

    @property
    def success(self) -> bool:
        return self.http_status == 200 and self.headers.get("statusFlag") in (None, "1")
```

- [ ] **Step 6: Run client tests**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_esb_headers_include_required_fields backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_chunk_payload_records_respects_byte_limit -q
```

Expected: pass.

## Task 5: Push Service

**Files:**

- Create: `backend/app/calcu/service/science_warehouse_push_service.py`
- Test: `backend/app/calcu/tests/test_science_warehouse_push_contract.py`

- [ ] **Step 1: Add payload mapping test**

Add a unit test with simple fake row objects:

```python
from types import SimpleNamespace

from backend.app.calcu.service.science_warehouse_push_service import build_science_warehouse_push_payload


def test_build_science_warehouse_push_payload_maps_reviewed_rows() -> None:
    rows = [
        SimpleNamespace(
            calculation_id="SW_123",
            warehouse_code="GK27",
            warehouse_name="新乡机务段库",
            spare_part_code="CNR0000231122",
            spare_part_name="备品名称",
            max_failure_count=5,
            required_quantity=10,
        )
    ]
    payload = build_science_warehouse_push_payload(
        calculation_id="SW_123",
        push_reason="审查完成",
        rows=rows,
    )
    assert payload["push_source"] == "REIS系统"
    assert payload["calculation_id"] == "SW_123"
    assert payload["results"][0]["required_quantity"] == 10
```

- [ ] **Step 2: Run payload test and verify failure**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_build_science_warehouse_push_payload_maps_reviewed_rows -q
```

Expected: import failure.

- [ ] **Step 3: Implement payload builder**

Create a pure function that maps reviewed push rows to the external contract from the WMS document:

```python
def build_science_warehouse_push_payload(
    calculation_id: str,
    push_reason: str,
    rows: Sequence[Any],
) -> dict[str, Any]:
    return {
        "push_source": "REIS系统",
        "push_time": datetime.now().replace(microsecond=0).isoformat(),
        "push_reason": push_reason,
        "calculation_id": calculation_id,
        "results": [
            {
                "calculation_id": row.calculation_id,
                "warehouse_code": row.warehouse_code,
                "warehouse_name": row.warehouse_name,
                "spare_part_code": row.spare_part_code,
                "spare_part_name": row.spare_part_name,
                "max_failure_count": row.max_failure_count,
                "required_quantity": row.required_quantity,
            }
            for row in rows
        ],
    }
```

- [ ] **Step 4: Implement service orchestration**

Create `ScienceWarehousePushService.push_by_calculation_id(calculation_id, push_reason)`.

Behavior:

- Open `async_db_session()`.
- Query `science_warehouse_push_result_dao.get_by_calculation_id`.
- If no rows, raise `DataNotFoundError` or `HTTPException` is mapped later by the API.
- Build base payload and chunk records with `settings.SCIENCE_WAREHOUSE_ESB_MAX_PAYLOAD_BYTES`.
- For each chunk, create a `running` log before the ESB call.
- Send ESB request using `ScienceWarehouseEsbClient.post_json`.
- Update the log to `success` if HTTP 200 and ESB header `statusFlag` is absent or `"1"`.
- Update the log to `failed` with `error_message` on HTTP, ESB, or network failure.
- Return a summary dictionary with `calculation_id`, `total_records`, `success_chunks`, `failed_chunks`, and `status`.

- [ ] **Step 5: Run payload test**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_build_science_warehouse_push_payload_maps_reviewed_rows -q
```

Expected: pass.

## Task 6: Celery Task

**Files:**

- Modify: `backend/app/task/tasks/science_warehouse_task/tasks.py`
- Modify: `backend/app/task/tasks/science_warehouse_task/__init__.py`
- Modify: `backend/app/calcu/tests/test_calcu_identity_contract.py`

- [ ] **Step 1: Update task export contract test**

Change the expected exports to:

```python
def test_science_warehouse_task_exports_main_calculation_and_push_flows() -> None:
    assert science_task_exports == [
        "science_warehouse_calculation_task",
        "science_warehouse_push_task",
    ]
```

- [ ] **Step 2: Run export test and verify failure**

Run:

```bash
pytest backend/app/calcu/tests/test_calcu_identity_contract.py::test_science_warehouse_task_exports_main_calculation_and_push_flows -q
```

Expected: failure because `science_warehouse_push_task` is not exported.

- [ ] **Step 3: Add Celery task**

Append to `backend/app/task/tasks/science_warehouse_task/tasks.py`:

```python
@celery_app.task(name="science_warehouse_push_task", base=TaskBase)
async def science_warehouse_push_task(calculation_id: str, push_reason: str) -> str:
    """后台任务: 推送人工审查后的科学库存结果到ESB。"""
    try:
        from backend.app.calcu.service.science_warehouse_push_service import science_warehouse_push_service

        result = await science_warehouse_push_service.push_by_calculation_id(
            calculation_id=calculation_id,
            push_reason=push_reason,
        )
        return (
            f"科学库存推送完成 - 计算批次ID: {result['calculation_id']}, "
            f"总记录数: {result['total_records']}, 状态: {result['status']}"
        )
    except Exception as e:
        return f"科学库存推送失败: {str(e)}"
```

- [ ] **Step 4: Export the task**

Update `backend/app/task/tasks/science_warehouse_task/__init__.py`:

```python
from backend.app.task.tasks.science_warehouse_task.tasks import (
    science_warehouse_calculation_task,
    science_warehouse_push_task,
)

__all__ = [
    "science_warehouse_calculation_task",
    "science_warehouse_push_task",
]
```

- [ ] **Step 5: Run export test**

Run:

```bash
pytest backend/app/calcu/tests/test_calcu_identity_contract.py::test_science_warehouse_task_exports_main_calculation_and_push_flows -q
```

Expected: pass.

## Task 7: API Endpoint

**Files:**

- Modify: `backend/app/calcu/api/v1/calcu/science_warehouse.py`
- Test: `backend/app/calcu/tests/test_science_warehouse_push_contract.py`

- [ ] **Step 1: Add route contract test**

Add:

```python
from backend.app.calcu.api.v1.calcu.science_warehouse import router as science_router


def test_science_warehouse_exposes_push_route() -> None:
    paths = {route.path for route in science_router.routes}
    assert "/push/{calculation_id}" in paths
```

- [ ] **Step 2: Run route test and verify failure**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_science_warehouse_exposes_push_route -q
```

Expected: failure because the route does not exist.

- [ ] **Step 3: Add endpoint imports**

Add imports:

```python
from backend.app.calcu.schema.science_warehouse import (
    ScienceWarehousePushRequest,
    ScienceWarehousePushTaskResponse,
)
from backend.app.task.tasks.science_warehouse_task.tasks import science_warehouse_push_task
```

- [ ] **Step 4: Add endpoint**

Add to `backend/app/calcu/api/v1/calcu/science_warehouse.py`:

```python
@router.post("/push/{calculation_id}", summary="推送人工审查后的科学库存结果 -> 后台任务执行")
async def push_science_warehouse_results(
    calculation_id: str,
    request: ScienceWarehousePushRequest,
) -> ResponseSchemaModel[ScienceWarehousePushTaskResponse]:
    try:
        task = science_warehouse_push_task.delay(
            calculation_id=calculation_id,
            push_reason=request.push_reason,
        )
        return response_base.success(
            data={
                "task_id": task.id,
                "task_name": science_warehouse_push_task.name,
                "calculation_id": calculation_id,
                "message": "科学库存推送任务已提交",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推送任务提交失败: {str(e)}")
```

- [ ] **Step 5: Run route test**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py::test_science_warehouse_exposes_push_route -q
```

Expected: pass.

## Task 8: Full Verification

**Files:**

- Verify all files touched by Tasks 1-7.

- [ ] **Step 1: Run focused tests**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_push_contract.py backend/app/calcu/tests/test_calcu_identity_contract.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run existing science warehouse tests**

Run:

```bash
pytest backend/app/calcu/tests/test_science_warehouse_dimension_aggregation.py backend/app/calcu/tests/test_science_warehouse_mapping_dimension.py -q
```

Expected: all tests pass; push changes must not affect calculation behavior.

- [ ] **Step 3: Run lint diagnostics in Cursor**

Use IDE lint diagnostics for the created and modified files. Fix only issues introduced by this implementation.

- [ ] **Step 4: Manual API smoke check**

With a development database containing rows in `calcu_science_warehouse_push_result`, call:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/calcu/science-warehouse/push/SW_123" \
  -H "Content-Type: application/json" \
  -d "{\"push_reason\":\"月度库存审查完成后推送\"}"
```

Expected response shape:

```json
{
  "code": 200,
  "msg": "成功",
  "data": {
    "task_id": "celery-task-id",
    "task_name": "science_warehouse_push_task",
    "calculation_id": "SW_123",
    "message": "科学库存推送任务已提交"
  }
}
```

## Operational Notes

- The import process for `calcu_science_warehouse_push_result` can be implemented separately if the current system already has a generic import path. This push plan assumes reviewed rows already exist in the push table.
- The push service must not silently read from `calcu_science_warehouse_result`. Empty push table data is a business validation failure because it means reviewed data has not been imported.
- Use `calculation_id` as the business boundary. Use `request_id` and `track_id` as ESB trace keys.
- If ESB returns HTTP 200 but `statusFlag` is `"0"`, record the chunk as `failed`.
- If one chunk fails and another succeeds, return aggregate status `partial_success` in the service summary while keeping each log row as `success` or `failed`.
- Keep the WMS payload contract compatible with the existing PDF: `push_source`, `push_time`, `push_reason`, `calculation_id`, and `results`.

## Self-Review

- Spec coverage: The plan covers the new push table, push log table, ESB headers, chunking, Celery task, internal API, and tests.
- Open-value scan: No unresolved values are required for implementation; ESB URL, source system, service name, timeout, and byte limit have concrete defaults and remain environment-overridable.
- Type consistency: `calculation_id`, `push_reason`, `request_id`, `track_id`, `service_name`, chunk fields, and status values are named consistently across schemas, models, services, task, and API.
- Scope check: This plan implements push from an already populated push table. Spreadsheet import or UI review workflow is intentionally outside this implementation unit.
