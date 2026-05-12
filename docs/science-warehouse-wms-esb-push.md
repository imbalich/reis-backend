# 科学库存结果推送（REIS -> ESB -> WMS）说明

## 1. 文档目的

本文档说明当前系统中“科学库存结果推送到 WMS”的实现与联调方式，作为后续部署、联调与运维排障的统一依据。

适用范围：

- REIS 内部触发科学库存推送
- 通过 ESB 总线转发到 WMS（或其它接收方）
- 推送日志追踪与失败判定

## 2. 推送总体流程

1. 科学库存计算结果生成后，业务人员在数据库层面对推送表数据进行导入/调整。
2. 调用 REIS 内部接口触发推送（按 `calculation_id`）。
3. 后端提交 Celery 任务，不阻塞接口请求。
4. 推送服务按批次读取推送表，组装业务报文。
5. 按报文字节大小分包后，通过 ESB HTTP 接口逐包发送。
6. 每个分包写入推送日志表，记录 requestId/trackId、ESB 返回和错误信息。
7. 任务返回汇总状态：`success` / `failed` / `partial_success`。

## 3. 关键接口

### 3.1 REIS 内部触发接口

- 方法：`POST`
- 路径：`/api/v1/calcu/science-warehouse/push/{calculation_id}`
- 说明：触发指定计算批次的推送任务

请求体示例：

```json
{
  "push_reason": "月度库存需求推送"
}
```

成功响应示例（任务提交成功）：

```json
{
  "code": 200,
  "msg": "成功",
  "data": {
    "task_id": "celery-task-id",
    "task_name": "science_warehouse_push_task",
    "calculation_id": "SW_1234567890",
    "message": "科学库存推送任务已提交"
  }
}
```

## 4. ESB 对接实现

### 4.1 配置项（`backend/core/conf.py`）

- `SCIENCE_WAREHOUSE_ESB_URL`：ESB 网关地址
- `SCIENCE_WAREHOUSE_ESB_SOURCE_SYSTEM`：来源系统标识（sourceSystem）
- `SCIENCE_WAREHOUSE_ESB_SERVICE_NAME`：ESB 服务名（serviceName）
- `SCIENCE_WAREHOUSE_ESB_TIMEOUT_SECONDS`：调用超时（秒）
- `SCIENCE_WAREHOUSE_ESB_MAX_PAYLOAD_BYTES`：单包最大字节数（UTF-8）

### 4.2 ESB 请求头

按 ESB 规范发送以下头信息：

- `Content-Type: application/json`
- `requestId`：UUID，全局唯一消息流水号
- `trackId`：链路追踪号
- `sourceSystem`：来源系统编码
- `serviceName`：ESB 服务名
- `requestTime`：`yyyy-MM-dd HH:mm:ss`

### 4.3 业务请求体

推送 body 结构：

```json
{
  "push_source": "REIS系统",
  "push_time": "2026-05-12T17:00:00",
  "push_reason": "月度库存需求推送",
  "calculation_id": "SW_1234567890",
  "results": [
    {
      "calculation_id": "SW_1234567890",
      "warehouse_code": "GK27",
      "warehouse_name": "新乡机务段库",
      "spare_part_code": "CNR0000231122",
      "spare_part_name": "备品名称",
      "max_failure_count": 5,
      "required_quantity": 10
    }
  ]
}
```

## 5. 分包与成功判定

### 5.1 分包策略

- 按完整 JSON payload 的 UTF-8 字节数分包。
- 若单条记录已超过单包大小限制，则直接报错。
- 当前默认阈值为 `100KB`（可配置）。

### 5.2 成功判定规则

单包推送成功条件：

- HTTP 状态码为 `200`
- 且 ESB 响应头 `statusFlag` 不存在或为 `"1"`

以下情况记为失败：

- HTTP 非 200
- `statusFlag = "0"`
- 网络异常/超时/请求异常

## 6. 数据表说明

### 6.1 推送数据表

- 表名：`calcu_science_warehouse_push_result`
- 用途：存放待推送数据（按 `calculation_id` 读取）

### 6.2 推送日志表

- 表名：`calcu_science_warehouse_push_log`
- 用途：记录每个分包的推送状态与上下文
- 关键字段：
  - `push_status`（running/success/failed）
  - `request_id`
  - `track_id`
  - `service_name`
  - `esb_status_flag`
  - `esb_code`
  - `esb_desc`
  - `response_body`
  - `error_message`

## 7. 联调建议（部署后）

1. 确认 ESB 配置项已按环境配置（地址、sourceSystem、serviceName）。
2. 准备一批测试数据写入 `calcu_science_warehouse_push_result`（同一 `calculation_id`）。
3. 调用内部触发接口发起推送。
4. 在 REIS 日志表按 `calculation_id` + `request_id` + `track_id` 查看分包结果。
5. 在 ESB 平台用 `requestId/trackId` 检索请求链路并核对返回码。
6. 在 WMS 侧确认收到数据并返回 200。

## 8. 参考来源（已整合进本文）

- `backend/app/calcu/WMS接口文档-科学库存计算结果推送接口文档.pdf`
- `backend/app/calcu/ESB文档及实例.docx`
- `backend/app/calcu/ESB标准规范最新.pptx`

上述历史文件已由本说明统一吸收，后续以本文为准维护。
