# REIS 后台任务

长时间计算通过 Celery 执行，避免阻塞 API。任务代码在 `backend/app/task/tasks`，每个子目录包含 `tasks.py`，由 Celery 自动发现。

## 现有任务

| 目录 | 任务 |
|------|------|
| `science_warehouse_task` | 科学库存计算、审查后经 ESB 推送 WMS |
| `spare_statistics_task` | 备件预测与故障次数批量统计 |
| `fit_task` | 寿命拟合 |
| `sense_task` | 敏感度计算 |
| `lifetime_task` | 等寿命计算 |
| `rcm_task` | RCM 计算 |
| `db_log` | 操作日志异步落库 |

## 消息代理

`CELERY_BROKER` 可选 `redis` 或 `rabbitmq`。`ENVIRONMENT=prod` 时固定使用 RabbitMQ。本地调试可以使用 Redis。

生产环境 Flower 随 `fba_celery` 容器启动，映射端口 `8555`。

## 新增任务

1. 在 `backend/app/task/tasks` 下新建 Python 包。
2. 在包内添加 `tasks.py`，并用 `@celery_app.task` 注册任务。
3. 在对应业务 API 中调用 `task.delay(...)` 提交任务。
