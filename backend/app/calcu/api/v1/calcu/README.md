# 科学库存计算 API 使用说明

## 概述

科学库存计算 API 提供了完整的科学库存需求计算功能，包括计算执行、结果查询和 API 格式输出。

## API 接口

### 1. 执行科学库存计算

**接口地址**: `POST /calcu/science-warehouse/calculate`

**请求参数**:

```json
{
  "time_interval_days": 180,
  "input_date": "2024-01-01"
}
```

**响应格式**:

```json
{
  "code": 200,
  "msg": "科学库存计算成功",
  "data": {
    "calculation_id": "SW_1234567890",
    "statistics": {
      "total_warehouse_spares": 100,
      "calculated_spares": 80,
      "default_spares": 20
    },
    "calculation_period": {
      "time_interval_days": 180,
      "input_date": "2024-01-01"
    }
  }
}
```

### 2. 获取 API 格式计算结果

**接口地址**: `GET /calcu/science-warehouse/results/{calculation_id}/api`

**响应格式**:

```json
{
  "code": 200,
  "msg": "获取计算结果成功",
  "data": {
    "data": [
      {
        "factor": "G002",
        "code": "GK27",
        "warehouse": "新乡机务段库",
        "part": "CNR0000231122",
        "number": 10
      },
      {
        "factor": "G002",
        "code": "GK28",
        "warehouse": "北京机务段库",
        "part": "CNR0000231133",
        "number": 3
      }
    ]
  }
}
```

### 3. 获取详细计算结果

**接口地址**: `GET /calcu/science-warehouse/results/{calculation_id}/details`

**响应格式**:

```json
{
  "code": 200,
  "msg": "获取详细计算结果成功",
  "data": {
    "calculation_id": "SW_1234567890",
    "results": {
      "G002": {
        "GK27": {
          "part_name": "备品名称",
          "required_quantity": 10,
          "calculation_method": "fitted",
          "confidence": 0.8
        }
      }
    },
    "statistics": {
      "total_warehouse_spares": 100,
      "calculated_spares": 80,
      "default_spares": 20
    }
  }
}
```

### 4. 计算并直接返回 API 格式结果

**接口地址**: `POST /calcu/science-warehouse/calculate-and-get-api`

**请求参数**: 同接口 1

**响应格式**: 同接口 2

## 使用场景

### 场景 1: 后台管理系统

```python
# 1. 执行计算
response = await calculate_science_warehouse_requirements(request)
calculation_id = response.data.calculation_id

# 2. 显示统计信息
statistics = response.data.statistics
print(f"总备品数: {statistics.total_warehouse_spares}")
print(f"成功计算: {statistics.calculated_spares}")
```

### 场景 2: 外部系统集成

```python
# 直接获取API格式结果
response = await calculate_and_get_api_results(request)
api_data = response.data.data

# 推送给外部系统
for item in api_data:
    external_system.push({
        "factor": item.factor,
        "code": item.code,
        "warehouse": item.warehouse,
        "part": item.part,
        "number": item.number
    })
```

### 场景 3: 分步调用

```python
# 1. 执行计算
calc_response = await calculate_science_warehouse_requirements(request)
calculation_id = calc_response.data.calculation_id

# 2. 获取API格式结果
api_response = await get_calculation_results_for_api(calculation_id)
api_data = api_response.data.data
```

## Schema 层优势

1. **类型安全**: 使用 Pydantic 提供完整的类型检查和验证
2. **文档自动生成**: FastAPI 自动生成 OpenAPI 文档
3. **统一格式**: 符合项目统一的响应格式规范
4. **易于维护**: 清晰的 schema 定义，便于后续维护和扩展
5. **IDE 支持**: 完整的代码提示和类型检查
