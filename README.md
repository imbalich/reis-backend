# REIS 后端

可靠性与经济性集成系统（Reliability And Economical Integration System）的后端服务。面向国铁售后场景，提供主数据管理、寿命拟合、科学库存、可靠性分析及相关后台计算。

代码在 FastAPI 分层结构上演进，当前仓库以 REIS 业务为准，不再沿用上游模板的产品说明。

## 业务模块

接口统一挂在 `/api/v1` 下。

| 模块 | 路径前缀 | 作用 |
|------|----------|------|
| 认证与系统管理 | `/auth`、`/sys`、`/logs`、`/monitors` | 登录、权限、操作日志、运行监控 |
| 主数据 | `/datamanage` | 产品、故障、配属、库房、备品映射、发运等基础数据 |
| 寿命拟合 | `/fit` | 按产品型号、派生码和部件做寿命分布拟合 |
| Aaron 拟合 | `/fit-aaron` | 使用 Aaron 曲线的拟合链路 |
| 科学库存与备件计算 | `/calcu` | 科学库存、备件统计、可靠度指标、优化计算 |
| 敏感度 | `/sense` | 敏感度排序与预测 |
| 可靠性框图 | `/rbd` | 可靠性框图分析 |
| RCM | `/rcm` | 以可靠性为中心的维修分析 |
| 性能退化 | `/degrade` | 退化数据拟合 |
| 全寿命成本 | `/lcc` | 寿命周期成本与修程对比 |
| 等寿命 | `/lifetime` | 等寿命点与曲线 |
| 后台任务 | `/tasks` | Celery 任务结果与调度 |

科学库存推送到 WMS 的流程见 [docs/science-warehouse-wms-esb-push.md](docs/science-warehouse-wms-esb-push.md)。

## 代码分层

每个业务包按下面的层次组织：

| 层次 | 目录 | 职责 |
|------|------|------|
| 接口 | `api` | 路由、参数和响应 |
| 传输对象 | `schema` | 请求与响应结构 |
| 业务 | `service` | 计算与流程 |
| 数据访问 | `crud` | 数据库读写 |
| 模型 | `model` | 表结构 |

## 本地运行

依赖 Python 3.10 及以上，包管理使用 [uv](https://docs.astral.sh/uv/)。

```shell
uv sync --frozen
copy backend\.env.example backend\.env
```

按本机环境修改 `backend/.env` 中的数据库、Redis 和 RabbitMQ。开发环境 Celery 默认走 Redis，生产环境强制走 RabbitMQ。

在项目根目录启动：

```shell
uv run fba run
uv run fba celery worker
uv run fba celery beat
```

开发环境文档地址为 `http://127.0.0.1:8000/docs`。生产环境关闭 OpenAPI。

## 现网部署

现网使用 `docker-compose-reis.yml`。MySQL 和 Redis 部署在宿主机，不由该 compose 文件拉起。API 与 Celery 容器通过 `deploy/backend/docker-compose/.env.server` 读取连接信息，该文件挂载为容器内的 `/fba/backend/.env`。

```shell
docker compose -f docker-compose-reis.yml up -d --build
```

改环境变量后需要重启 `fba_server` 和 `fba_celery`，配置只在进程启动时读取。

## 相关说明

- 后端命令与脚本：[backend/README.md](backend/README.md)
- 后台任务：[backend/app/task/README.md](backend/app/task/README.md)
- 变更记录以 Git 历史为准，见 [CHANGELOG.md](CHANGELOG.md)
