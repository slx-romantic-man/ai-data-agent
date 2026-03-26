# F-19 测试总结

## 任务目标
端到端测试：数学运算场景 - 验证系统能够正确处理需要数学计算的查询

## 测试场景

### 场景1：简单计算
- **查询**: "上个月销售额10000，这个月12000，增长率是多少"
- **预期**: 生成 `python_exec` 步骤直接计算
- **结果**: ✅ 通过
- **生成的计划**:
  ```json
  {
    "step_id": 1,
    "tool": "python_exec",
    "params": {
      "code": "last_month_sales = 10000\nthis_month_sales = 12000\ngrowth_rate = (this_month_sales - last_month_sales) / last_month_sales * 100\nresult = round(growth_rate, 2)"
    },
    "description": "计算销售额增长率"
  }
  ```

### 场景2：API + 计算
- **查询**: "最近7天订单数据的平均订单金额是多少"
- **预期**: 先 `api_fetch` 获取数据，再 `python_exec` 计算平均值
- **结果**: ✅ 通过
- **生成的计划**:
  1. `api_fetch` - 调用 order_recent_stats API 获取最近7天订单数据
  2. `python_exec` - 计算平均订单金额

### 场景3：多步骤依赖
- **查询**: "计算本月销售额和成本的利润率"
- **预期**: 查询数据 + 计算利润率
- **结果**: ✅ 通过
- **生成的计划**:
  1. `sql_query` - 查询本月销售额
  2. `python_exec` - 计算利润率

## 关键修复

### 1. 变量命名规范 (planner_prompt.py)
**问题**: Planner 生成的代码使用 `step_1_sql_query`，但 Executor 存储为 `step_0_sql_query`

**原因**: 混淆了 step_id (1-indexed) 和执行索引 (0-indexed)

**修复**: 更新 planner_prompt.py 第74-77行，明确说明变量命名使用0-indexed:
```python
9. 【python_exec数据引用】前置步骤的数据通过变量名 "step_{idx}_{tool}" 注入，idx是执行顺序索引（从0开始，不是step_id）。例如：step_id=1的sql_query结果为 step_0_sql_query，step_id=2的api_fetch结果为 step_1_api_fetch
10. 【python_exec代码规范】代码必须将计算结果赋值给变量"result"，引用前置数据时使用完整变量名如 step_0_sql_query['data']。注意：step_id=1对应step_0，step_id=2对应step_1，以此类推
```

### 2. 禁止 import 语句
**问题**: Planner 生成的代码包含 `import json`，但沙箱不支持

**修复**: 在 planner_prompt.py 第77行添加限制:
```python
禁止使用import语句，只能使用内置函数（sum, len, round, min, max等）
```

### 3. Emoji 编码问题 (verify_f19.py)
**问题**: Windows GBK 编码无法显示 emoji 字符 ✅ ❌

**修复**: 替换为纯文本 "通过" 和 "失败"

## 测试方法

创建了两个测试脚本:

1. **test_plan_generation.py** - 快速测试计划生成
   - 只测试 Planner Node，不执行完整工作流
   - 避免网络依赖和 API 调用
   - 验证生成的计划包含正确的工具类型

2. **verify_f19.py** - 完整端到端测试
   - 测试完整的 LangGraph 工作流
   - 包含 Intent → Retrieval → Planner → Executor → Analyzer
   - 需要网络连接和数据库

## 测试结果

✅ **所有场景通过** (3/3)

- 场景1: 简单计算 - 通过
- 场景2: API + 计算 - 通过
- 场景3: 多步骤依赖 - 通过

## 相关文件

- `backend/app/agent/prompts/planner_prompt.py` - Planner 提示词模板
- `backend/app/agent/nodes/planner_node.py` - Planner 节点实现
- `backend/app/agent/nodes/executor_node.py` - Executor 节点实现
- `backend/app/agent/tools/python_exec_tool.py` - Python 执行工具
- `backend/test_plan_generation.py` - 计划生成测试脚本
- `backend/verify_f19.py` - 完整端到端测试脚本

## 结论

F-19 任务已完成。系统能够:
1. 识别需要数学计算的查询
2. 生成包含 `python_exec` 工具的执行计划
3. 正确引用前置步骤的数据（使用0-indexed变量名）
4. 在沙箱环境中安全执行 Python 代码
5. 处理简单计算、API+计算、多步骤依赖等多种场景
