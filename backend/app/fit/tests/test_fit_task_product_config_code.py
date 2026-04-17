import asyncio

from backend.app.task.tasks.fit_task import tasks as fit_tasks


def test_product_fit_all_task_iterates_model_config_pairs(monkeypatch) -> None:
    captured: list[tuple[str, str | None, str | None, object]] = []

    async def _fake_get_product_dimension_pairs():
        return [["YJ90A1", "PS00"], ["YJ90A1", "PS01"], ["YJ90B", None]]

    async def _fake_create(*, obj):
        captured.append(
            (
                obj.model,
                obj.product_config_code,
                obj.input_date,
                obj.method,
            )
        )

    monkeypatch.setattr(
        fit_tasks.failure_service,
        "get_product_dimension_pairs",
        _fake_get_product_dimension_pairs,
    )
    monkeypatch.setattr(
        fit_tasks.product_fit_service,
        "create",
        _fake_create,
    )

    result = asyncio.run(
        fit_tasks.product_fit_all_task("2026-04-17", fit_tasks.FitMethodType.MLE)
    )

    assert "Processed 2 model-config pairs" in result
    assert captured == [
        ("YJ90A1", "PS00", "2026-04-17", fit_tasks.FitMethodType.MLE),
        ("YJ90A1", "PS01", "2026-04-17", fit_tasks.FitMethodType.MLE),
    ]


def test_part_fit_all_task_iterates_parts_by_model_and_config(monkeypatch) -> None:
    parts_requests: list[tuple[str, str | None]] = []
    captured: list[tuple[str, str | None, str, str | None, object]] = []

    async def _fake_get_product_dimension_pairs():
        return [["YJ90A1", "PS00"], ["YJ90A1", "PS01"]]

    async def _fake_get_parts_by_model(model, product_config_code=None):
        parts_requests.append((model, product_config_code))
        mapping = {
            ("YJ90A1", "PS00"): ["P-001", "P-002"],
            ("YJ90A1", "PS01"): ["P-003"],
        }
        return mapping[(model, product_config_code)]

    async def _fake_create(*, obj):
        captured.append(
            (
                obj.model,
                obj.product_config_code,
                obj.part,
                obj.input_date,
                obj.method,
            )
        )

    monkeypatch.setattr(
        fit_tasks.failure_service,
        "get_product_dimension_pairs",
        _fake_get_product_dimension_pairs,
    )
    monkeypatch.setattr(
        fit_tasks.failure_service,
        "get_parts_by_model",
        _fake_get_parts_by_model,
    )
    monkeypatch.setattr(
        fit_tasks.part_fit_service,
        "create",
        _fake_create,
    )

    result = asyncio.run(
        fit_tasks.part_fit_all_task("2026-04-17", fit_tasks.FitMethodType.MLE)
    )

    assert "Processed 2 model-config pairs" in result
    assert parts_requests == [("YJ90A1", "PS00"), ("YJ90A1", "PS01")]
    assert captured == [
        ("YJ90A1", "PS00", "P-001", "2026-04-17", fit_tasks.FitMethodType.MLE),
        ("YJ90A1", "PS00", "P-002", "2026-04-17", fit_tasks.FitMethodType.MLE),
        ("YJ90A1", "PS01", "P-003", "2026-04-17", fit_tasks.FitMethodType.MLE),
    ]


def test_part_fit_model_all_task_without_config_iterates_all_model_configs(monkeypatch) -> None:
    parts_requests: list[tuple[str, str | None]] = []
    captured: list[tuple[str, str | None, str]] = []

    async def _fake_get_product_dimension_pairs():
        return [["YJ90A1", "PS00"], ["YJ90A1", "PS01"], ["YJ90B", "PB00"]]

    async def _fake_get_parts_by_model(model, product_config_code=None):
        parts_requests.append((model, product_config_code))
        mapping = {
            ("YJ90A1", "PS00"): ["P-001"],
            ("YJ90A1", "PS01"): ["P-002"],
        }
        return mapping[(model, product_config_code)]

    async def _fake_create(*, obj):
        captured.append((obj.model, obj.product_config_code, obj.part))

    monkeypatch.setattr(
        fit_tasks.failure_service,
        "get_product_dimension_pairs",
        _fake_get_product_dimension_pairs,
    )
    monkeypatch.setattr(
        fit_tasks.failure_service,
        "get_parts_by_model",
        _fake_get_parts_by_model,
    )
    monkeypatch.setattr(
        fit_tasks.part_fit_service,
        "create",
        _fake_create,
    )

    result = asyncio.run(
        fit_tasks.part_fit_model_all_task(
            "YJ90A1",
            "2026-04-17",
            fit_tasks.FitMethodType.MLE,
        )
    )

    assert "Processed model YJ90A1, 2 total parts" in result
    assert parts_requests == [("YJ90A1", "PS00"), ("YJ90A1", "PS01")]
    assert captured == [("YJ90A1", "PS00", "P-001"), ("YJ90A1", "PS01", "P-002")]
