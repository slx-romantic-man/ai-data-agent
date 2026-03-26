# AI Data Agent v4 (企业级 API 数据中台)

AI Data Agent 是一款基于 **LangGraph Plan-and-Execute** 架构的企业级智能数据分析助手。它能够理解自然语言指令，通过智能规划与执行调用企业内部 API 获取数据，并提供流式推理过程、状态持久化、人工审批网关及 Excel 导出等全链路能力。

## 🌟 核心特性

- **LangGraph 状态机**: 采用 Plan-and-Execute 模式，先规划后执行，确保复杂查询的确定性与可控性。
- **状态持久化**: 基于 SQLite Checkpointer 实现会话状态保存，支持多轮下钻对话无需重复查询。
- **数据隔离存储**: 所有 API 查询结果存入 `data_context` 字典，避免 Prompt 污染，最终统一分析。
- **人工审批网关**: 基于用户角色的条件审批，普通用户调用 API 时需人工批准，管理员直接执行。
- **智能 API 路由**: 自动从预配置的 API 库中选择最合适的端点，支持参数自动提取与映射。
- **流式推理展示**: 实时展示 AI 的节点流转过程，带来打字机式的极致交互体验。
- **动态日期计算**: 自动注入系统当前日期，AI 会基于此精准口算"昨天"、"上周"等时间范围。

## 🏗️ 架构升级 (v3 → v4)

| 维度 | v3 (ReAct) | v4 (LangGraph) |
|------|-----------|----------------|
| **推理引擎** | ReAct 循环 (最多10次迭代) | LangGraph 状态机 (Plan-and-Execute) |
| **状态管理** | 无状态 (仅依赖历史消息) | 持久化 AgentState (含结构化数据) |
| **执行流程** | 边想边做，易丢失目标 | 先规划完整计划，再按步骤执行 |
| **数据传递** | 拼接到 Prompt 导致污染 | 隔离存入 data_context 字典 |
| **审批机制** | 工具内部校验 | LangGraph interrupt_before 挂起 |

## 🚀 快速启动

### 方式一：一键启动 (推荐)

```bash
bash init.sh
```

该脚本会自动完成环境检查、依赖安装、服务启动和健康检查。

### 方式二：手动启动

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 配置 LLM_API_KEY

# 3. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### 访问应用

- **前端页面**: 打开 `frontend/index.html`
- **API 文档**: http://localhost:8002/docs
- **健康检查**: http://localhost:8002/health

## 🛠️ API 接口说明

### 1. 认证接口

- `POST /api/v1/auth/login`: 用户登录，获取 JWT Token
- `GET /api/v1/auth/me`: 获取当前用户信息

### 2. 对话接口 (核心)

- `POST /api/v1/chat/stream` (推荐): SSE 流式接口，实时返回节点流转过程
- `POST /api/v1/chat`: 标准同步接口，生成完成后一次性返回结果

**请求示例**:
```json
{
  "query": "查询最近七天订单统计",
  "session_id": "user123_20260326"
}
```

### 3. 人工审批接口 (新增)

- `POST /api/v1/chat/approve`: 批准执行计划并恢复流程
- `POST /api/v1/chat/reject`: 拒绝执行计划并终止流程

**审批请求示例**:
```json
{
  "session_id": "user123_20260326",
  "thread_id": "abc-def-123"
}
```

### 4. 会话管理

- `GET /api/v1/chat/history`: 获取历史会话列表
- `GET /api/v1/chat/sessions/{id}`: 获取特定会话的详细内容

### 5. 数据导出

- `POST /api/v1/export`: 触发数据导出流程
- `GET /api/v1/export/{filename}`: 下载生成的 Excel 文件

## 📂 项目结构

```text
ai-data-agent-v4/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── nodes/              # LangGraph 节点实现
│   │   │   │   ├── intent_node.py      # 意图澄清节点
│   │   │   │   ├── retrieval_node.py   # API 检索节点
│   │   │   │   ├── planner_node.py     # 全局规划师节点
│   │   │   │   ├── executor_node.py    # 执行器节点
│   │   │   │   └── analyzer_node.py    # 终局分析节点
│   │   │   ├── tools/              # 工具实现
│   │   │   ├── prompts/            # Prompt 模板
│   │   │   ├── state.py            # AgentState 定义
│   │   │   └── graph.py            # LangGraph 工作流图
│   │   ├── api/                    # API 层
│   │   ├── config/                 # 配置管理
│   │   └── models/                 # 数据模型
│   ├── data/                       # SQLite 数据库
│   ├── exports/                    # 导出文件
│   └── requirements.txt
├── frontend/                       # 前端静态资源
├── docs/                          # 项目文档
│   └── architecture-v4.md         # v4 架构详细设计
├── init.sh                        # 一键启动脚本
├── feature_list.json              # 功能清单
└── README.md
```

## 🔄 工作流程说明

### 节点流转图

```
用户查询 → Intent Node → Retrieval Node → Planner Node
                                              ↓
                                         [审批网关]
                                              ↓
                                        Executor Node → Analyzer Node → 返回结果
                                              ↑______________|
                                           (循环执行多步骤)
```

### 核心节点说明

1. **Intent Node**: 判断查询条件是否完备，缺失则反问，完备则提取过滤条件
2. **Retrieval Node**: 向量召回 + LLM 精排，检索 Top-10 相关 API
3. **Planner Node**: 生成 JSON 格式的执行计划（包含多个步骤）
4. **审批网关**: 根据用户角色决定是否需要人工审批
5. **Executor Node**: 按计划逐步执行，调用 API/SQL 工具，结果存入 data_context
6. **Analyzer Node**: 综合 data_context 中的所有数据，生成最终分析报告

## 💾 状态持久化

系统使用 LangGraph 的 `AsyncSqliteSaver` 实现状态持久化：

- **存储位置**: `backend/data/checkpoints.db`
- **存储内容**: AgentState (包含 messages, plan, data_context 等)
- **业务价值**: 支持多轮下钻，第二轮追问时无需重新查询，直接复用第一轮数据

**多轮对话示例**:
```
第一轮: "查询华东地区销售数据"
→ 系统查询并保存到 data_context

第二轮: "为什么上海的销售额下降了" (使用相同 session_id)
→ 系统从 checkpoint 恢复 data_context，直接分析无需重新查询
```

## 🛡️ 人工审批网关

基于用户角色的条件审批机制：

- **管理员 (role=admin)**: 直接执行，无需审批
- **普通用户 (role=user)**: 调用 API 时触发审批流程

**审批流程**:
1. Planner 生成计划后，系统检测到需要审批
2. 推送 `approval_required` 事件到前端，展示审批卡片
3. 用户点击"批准"或"拒绝"
4. 调用 `/api/v1/chat/approve` 或 `/api/v1/chat/reject`
5. 系统恢复执行或终止流程

## 📖 配置 API 路由

在 `backend/app/config/api_config.py` 中注册新的企业接口：

```python
self.register_api("sales", APIConfig(
    name="销售API",
    base_url="http://api.internal/sales",
    endpoints={
        "stats": APIEndpointConfig(
            path="/stats",
            method="GET",
            params_mapping={"start_date": "begin", "end_date": "end"}
        )
    }
))
```

## 🛡️ 数据安全与权限

系统内置 RBAC 权限控制：

1. **角色隔离**: 不同角色仅能调用其授权范围内的 API 模块
2. **参数审计**: 所有 API 调用参数都经过 AI 二次校验
3. **敏感脱敏**: 对 API 返回的手机号、身份证等敏感字段进行自动屏蔽
4. **审批网关**: 普通用户调用高危 API 需要人工审批

## 📚 更多文档

- [v4 架构详细设计](docs/architecture-v4.md)
- [API 文档](http://localhost:8002/docs)
- [功能清单](feature_list.json)

## 📜 开源协议

MIT License
