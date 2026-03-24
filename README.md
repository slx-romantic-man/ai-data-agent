# AI Data Agent (企业级 API 数据中台)

AI Data Agent 是一款基于 ReAct 推理框架的企业级智能数据分析助手。它能够理解自然语言指令，通过智能路由调用企业内部 API 获取数据，并提供流式推理过程、自动数据清洗、可视化分析及 Excel 导出等全链路能力。

## 🌟 核心特性

- **自然语言查询**: 告别 SQL 和繁琐的 API 参数，直接用自然语言提问（如：“查询最近七天订单统计”）。
- **流式推理展示**: 实时展示 AI 的 "Thought-Action-Observation" 思考过程，带来打字机式的极致交互体验。
- **智能 API 路由**: 自动从预配置的 API 库中选择最合适的端点，支持参数自动提取与映射。
- **动态日期计算**: 自动注入系统当前日期，AI 会基于此精准口算"昨天"、"上周"等时间范围，确保查询准确。
- **万无一失的导出**: 自动对 API 返回的复杂嵌套 JSON 进行解构与平整化，支持一键导出格式专业的 Excel 报表。
- **会话持久化**: 基于本地 JSON 的会话存储，实现跨重启的上下文记忆，支持多轮追问。

## 🚀 快速启动

### 1. 安装环境

```bash
# 安装后端依赖
cd backend
pip install -r requirements.txt
```

### 2. 配置环境

复制 `.env.example` 为 `.env` 并配置您的 LLM 密钥：

```env
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key_here
LLM_MODEL=qwen-plus
LLM_API_BASE=https://coding.dashscope.aliyuncs.com/v1
```

### 3. 启动服务

```bash
# 启动后端服务 (默认端口 8002)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

## 🛠️ API 接口说明

### 1. 认证接口

- `POST /api/v1/auth/login`: 用户登录，获取 JWT Token。
- `GET /api/v1/auth/me`: 获取当前用户信息。

### 2. 对话接口 (核心)

- `POST /api/v1/chat/stream` (推荐): SSE 流式接口，实时返回思考过程与结果。
- `POST /api/v1/chat`: 标准同步接口，生成完成后一次性返回结果。

### 3. 会话管理

- `GET /api/v1/chat/history`: 获取历史通话列表。
- `GET /api/v1/chat/sessions/{id}`: 获取特定会话的详细内容。

### 4. 数据导出

- `POST /api/v1/export`: 触发数据导出流程。
- `GET /api/v1/export/{filename}`: 下载生成的 Excel 文件。

## 📂 项目结构

```text
ai-data-agent/
├── .env                      # 环境配置文件
├── .env.example              # 环境配置示例
├── README.md                 # 项目说明文档
├── backend/                  # 后端应用
│   ├── app/                  # 应用核心代码
│   │   ├── api/              # API 层 (含会话持久化与 SSE 逻辑)
│   │   ├── agent/            # Agent 核心
│   │   │   ├── core/         # ReAct 推理引擎 & 流式解析器
│   │   │   ├── tools/        # API 调用、数据分析、Excel 导出工具
│   │   │   └── prompts/      # 动态 Prompt 模板 (含日期自动注入)
│   │   ├── config/           # LLM 及外部 API 注册配置
│   │   └── models/           # Pydantic 数据模型
│   ├── data/                 # 数据存储目录
│   ├── exports/              # 导出文件目录
│   ├── logs/                 # 日志文件
│   ├── scripts/              # 数据库迁移脚本
│   ├── tests/                # 单元测试
│   ├── sessions.json         # 会话持久化文件
│   └── requirements.txt      # Python 依赖
├── frontend/                 # 前端静态资源
│   ├── css/                  # 样式文件
│   ├── js/                   # JavaScript 文件
│   └── index.html            # 主页面
└── docs/                     # 项目文档
```

## 📖 配置 API 路由

在 `backend/app/config/api_config.py` 中，您可以轻松注册新的企业接口：

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

系统内置 RBAC 权限控制，AI 在调用 API 时会自动携带用户的 UserContext，确保：

1. **角色隔离**: 不同角色仅能调用其授权范围内的 API 模块。
2. **参数审计**: 所有 API 调用参数都经过 AI 二次校验，防止非法查询。
3. **敏感脱敏**: 对 API 返回的手机号、身份证等敏感字段进行自动屏蔽处理。

## 📜 开源协议

MIT License
