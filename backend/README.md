# REIS 后端运行说明

在仓库根目录执行命令。应用入口是 `fba`，定义在 `pyproject.toml` 的 `[project.scripts]`。

## 准备环境

```shell
uv sync --frozen
```

复制 `backend/.env.example` 为 `backend/.env`，填写本机数据库、Redis 和 RabbitMQ。生产配置使用 `deploy/backend/docker-compose/.env.server`，不要把密码提交进 Git。

## 启动服务

```shell
uv run fba run
uv run fba celery worker
uv run fba celery beat
uv run fba celery flower
```

`fba run` 默认监听 `127.0.0.1:8000`。需要对外访问时指定主机和端口，例如 `uv run fba run --host 0.0.0.0 --port 8001`。

## 现网容器

`docker-compose-reis.yml` 构建并启动：

| 容器 | 作用 |
|------|------|
| `fba_server` | API，映射端口 `8001` |
| `fba_celery` | Worker、Beat 和 Flower，Flower 端口 `8555` |
| `fba_ui` | 前端 Nginx |
| `fba_rabbitmq` | 生产环境 Celery 消息代理 |

MySQL、Redis 使用宿主机实例。容器启动前会等待 `DATABASE_HOST` 对应的 3306 和 6379。

## 脚本

以下脚本位于 `backend/`，在 Windows 上优先使用上面的 `uv run fba` 命令。

| 脚本 | 用途 |
|------|------|
| `celery-start.sh` | 容器内同时启动 worker、beat 和 flower |
| `scripts/format.sh` | Ruff 格式检查 |
| `scripts/lint.sh` | pre-commit 检查 |
