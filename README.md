# AI Data Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangGraph-0.2%2B-orange?logo=langchain&logoColor=white" alt="LangGraph">
  <img src="https://img.shields.io/badge/Vue-3-4FC08D?logo=vue.js&logoColor=white" alt="Vue 3">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker">
  <br>
  <img src="https://img.shields.io/github/license/slx-romantic-man/ai-data-agent?color=blue" alt="License">
  <img src="https://img.shields.io/badge/Tests-In%20Progress-yellow" alt="Tests">
  <img src="https://img.shields.io/badge/Coverage-Building-yellow" alt="Coverage">
</p>

<p align="center"><strong>🤖 用自然语言对话，完成复杂数据分析与 API 调用</strong></p>

<p align="center">
  <a href="https://github.com/slx-romantic-man/ai-data-agent/stargazers"><img src="https://img.shields.io/github/stars/slx-romantic-man/ai-data-agent?style=social" alt="Stars"></a>
  <a href="https://github.com/slx-romantic-man/ai-data-agent/forks"><img src="https://img.shields.io/github/forks/slx-romantic-man/ai-data-agent?style=social" alt="Forks"></a>
</p>

---

## 🌟 项目简介

**AI Data Agent** 是一款企业级智能数据分析 Agent 系统，基于 **LangGraph** 的 Plan-and-Execute 模式构建。用户只需用自然语言描述需求，系统即可自动：

1. 🧠 **理解意图** — 判断查询条件是否完备，缺失则反问
2. 🔗 **检索 API** — 向量召回 + LLM 精排，找到最相关的数据接口
3. 📋 **全局规划** — 生成结构化 JSON 执行计划
4. ✅ **审批网关** — 敏感操作自动触发人工审批
5. ⚡ **执行计划** — 调用 SQL / API / Python 工具完成数据获取与分析
6. 📊 **生成洞察** — 综合所有数据输出结构化分析报告

整个推理过程通过 **SSE 流式实时推送**，每一步状态透明可观测。

> 💡 **典型场景**："查询最近 7 天销售额最高的 10 个客户，并分析他们的订单趋势" → Agent 自动拆解为多步计划，依次调用订单 API、执行 Python 分析、生成带图表的报告。

## 🎬 快速预览

```
用户：分析最近 7 天各渠道订单转化率和客单价

Agent 推理过程（SSE 实时推送）：
[Intent]     已提取条件：时间范围=最近7天，分析维度=渠道
[Retrieval]  召回相关 API: orders_api, channel_api (Top-2)
[Planner]    生成 3 步执行计划：
             Step 1: api_fetch 获取订单数据
             Step 2: python_exec 按渠道聚合计算转化率
             Step 3: analysis 生成洞察报告
[Executor]   Step 1/3 完成 → 获取 12,456 条订单记录
[Executor]   Step 2/3 完成 → 转化率: 官网 3.2% | APP 5.1% | 小程序 2.8%
[Analyzer]   最近7天各渠道表现：APP 转化率最高（5.1%），...
```

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🧠 **自然语言查询** | 用大白话查询数据库或 API，AI 自动转译为 SQL / API 调用 |
| 🔗 **API 智能检索** | 基于 Embedding 向量相似度 + LLM 精排，从海量 API 中召回最相关的接口 |
| 📊 **数据分析与可视化** | 内置受限 Python 执行环境（Pandas/NumPy），支持 Chart.js 图表渲染 |
| 📤 **Excel 导出** | 一键将分析结果导出为多 Sheet Excel，支持样式定制 |
| 🔐 **三级权限控制** | 角色级 / 行级过滤 / 列级脱敏，企业级数据安全 |
| ✅ **人工审批网关** | 敏感操作自动触发审批流，非管理员需管理员批准后方可执行 |
| 💬 **多轮对话持久化** | 基于 LangGraph Checkpointer，会话状态自动保存，支持随时恢复 |
| 🌊 **流式推理展示** | SSE 实时推送每个节点的执行状态，推理过程一目了然 |
| 🔌 **可插拔工具系统** | 新增工具只需继承 BaseTool，3 步即可完成扩展 |

## 🏗️ 架构概览

```mermaid
graph TD
    A[用户输入] --> B[Intent Clarification<br/>意图澄清]
    B -->|条件完备| C[API Retrieval<br/>向量召回+LLM精排]
    B -->|条件缺失| D[反问用户补充]
    C --> E[Planner<br/>生成JSON执行计划]
    E --> F{审批网关}
    F -->|需审批| G[等待人工批准]
    G -->|批准| H[Executor<br/>按步骤执行]
    F -->|免审批| H
    H -->|步骤未完成| H
    H -->|全部完成| I[Analyzer<br/>终局分析]
    I --> J[输出洞察报告]
```

### 数据流

```
用户输入 "查询最近7天订单统计"
    ↓
Intent Node: 提取 {start_date: "2024-03-19", end_date: "2024-03-26"}
    ↓
Retrieval Node: 召回 orders_api (Top-1)
    ↓
Planner Node: 生成计划
  [
    {step: 1, tool: "api_fetch", api_id: "orders_api", params: {...}},
    {step: 2, tool: "python_exec", code: "sum(data['amount'])", data_refs: ["step_1_orders_api"]}
  ]
    ↓
[审批网关] ← 普通用户需审批
    ↓
Executor Node (Step 1): 调用 api_fetch_tool → data_context["step_1_api_fetch"] = {...}
    ↓
Executor Node (Step 2): 调用 python_exec_tool → data_context["step_2_python_exec"] = 123456
    ↓
Analyzer Node: "最近7天订单总额为 ¥123,456"
    ↓
返回给用户
```

## 🛠️ 技术栈

### 后端
| 技术 | 用途 |
|------|------|
| [FastAPI](https://fastapi.tiangolo.com/) | 现代 Python Web 框架 |
| [LangGraph](https://langchain-ai.github.io/langgraph/) | Agent 工作流编排（Plan-and-Execute） |
| [SQLAlchemy 2.0](https://docs.sqlalchemy.org/) | 异步 ORM |
| [Qdrant](https://qdrant.tech/) | 向量数据库（API 检索） |
| [Pydantic v2](https://docs.pydantic.dev/) | 数据验证与序列化 |

### 前端
| 技术 | 用途 |
|------|------|
| [Vue 3](https://vuejs.org/) | 响应式前端框架（CDN 引入） |
| [Tailwind CSS](https://tailwindcss.com/) | 原子化 CSS |
| [Chart.js](https://www.chartjs.org/) | 数据可视化 |
| [Marked](https://marked.js.org/) + [DOMPurify](https://github.com/cure53/DOMPurify) | Markdown 渲染 + XSS 防护 |

### 部署
| 技术 | 用途 |
|------|------|
| [Docker](https://www.docker.com/) | 容器化部署 |
| [Nginx](https://nginx.org/) | 反向代理 + 静态资源 |

## 🚀 快速开始

### 环境要求
- Docker >= 20.10
- Docker Compose >= 2.0

### 1. 克隆仓库

```bash
git clone https://github.com/slx-romantic-man/ai-data-agent.git
cd ai-data-agent
```

### 2. 配置环境变量

```bash
cp .env.example .env.production
# 编辑 .env.production，填写你的 LLM API Key、数据库地址等
```

关键配置项：

```bash
# LLM（必填）
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-api-key
LLM_MODEL=gpt-4

# 数据库（必填）
DATABASE_URL=mysql+aiomysql://user:password@mysql:3306/ai_data_agent

# JWT（必填）
JWT_SECRET_KEY=your-strong-jwt-secret
API_AUTH_ENCRYPTION_KEY=your-encryption-key
```

### 3. 一键部署

```bash
chmod +x deploy.sh
./deploy.sh
```

或手动使用 Docker Compose：

```bash
docker compose up -d --build
```

### 4. 访问服务

| 地址 | 说明 |
|------|------|
| `http://localhost/` | 前端界面 |
| `http://localhost/docs` | API 文档（Swagger UI）|
| `http://localhost/health` | 健康检查 |

> 默认演示账号：admin / admin123

## 📁 项目结构

```
ai-data-agent/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── agent/              # LangGraph Agent 核心
│   │   │   ├── nodes/          # 工作流节点
│   │   │   ├── tools/          # 工具实现
│   │   │   ├── prompts/        # Prompt 模板
│   │   │   └── graph.py        # 工作流图定义
│   │   ├── api/v1/             # REST API 路由
│   │   ├── access/             # 数据访问层
│   │   ├── services/           # 业务服务层
│   │   └── config/             # 配置管理
│   ├── data/                   # 数据存储
│   ├── scripts/                # 初始化脚本
│   └── tests/                  # 测试套件（建设中）
├── frontend/                   # Vue 3 前端
│   ├── index.html
│   ├── css/
│   └── js/
├── examples/                   # 使用示例
├── docs/                       # 详细文档
├── docker-compose.yml
├── deploy.sh
├── Makefile
└── pyproject.toml
```

## 🔧 开发指南

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt
pip install -e ".[dev]"        # 安装开发依赖（ruff、mypy、pytest 等）

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env

# 3. 启动开发服务器
make dev                          # 或: uvicorn app.main:app --reload

# 4. 运行测试
make test                         # 运行全部测试
make test-cov                     # 带覆盖率报告

# 5. 代码检查
make lint                         # ruff 代码检查
make format                       # ruff 代码格式化
make typecheck                    # mypy 类型检查
```

更多开发细节请查看 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 🔒 安全设计

- **SQL 注入防护**: SQLAlchemy 参数化查询
- **代码沙箱**: RestrictedPython 限制危险操作
- **数据脱敏**: 列级权限自动掩码敏感字段
- **行级过滤**: 基于用户部门/角色自动追加 `WHERE` 条件
- **审批审计**: 所有审批操作记录到数据库，支持事后追溯
- **Token 安全**: JWT 认证 + API 配置加密存储

发现安全漏洞？请查看 [SECURITY.md](./SECURITY.md) 了解报告流程。

## 📖 文档

- [📘 架构设计文档](./ARCHITECTURE.md)
- [🚀 快速开始](./docs/README.md)
- [🤝 贡献指南](./CONTRIBUTING.md)
- [📋 变更日志](./CHANGELOG.md)
- [🔒 安全政策](./SECURITY.md)

## 🛣️ 路线图

- [x] LangGraph Plan-and-Execute 工作流
- [x] API 向量检索 + LLM 精排
- [x] 三级权限控制（角色/行/列）
- [x] 人工审批网关
- [x] SSE 流式推理展示
- [ ] Alembic 数据库迁移
- [ ] API 限流与熔断增强
- [ ] 多模态支持（图表生成）
- [ ] 分布式执行（并行步骤）

## 🤝 参与贡献

我们欢迎各种形式的贡献！请查看 [CONTRIBUTING.md](./CONTRIBUTING.md) 了解：

- 🐛 如何报告 Bug
- 💡 如何提交功能建议
- 🔧 开发环境搭建
- 📝 代码提交规范

## 📄 许可证

[MIT License](./LICENSE) © AI Data Agent Contributors

## 🙏 致谢

本项目基于以下优秀开源项目构建：

- [LangChain / LangGraph](https://github.com/langchain-ai/langgraph) — Agent 工作流框架
- [FastAPI](https://github.com/tiangolo/fastapi) — 现代 Python Web 框架
- [Vue.js](https://github.com/vuejs/core) — 渐进式前端框架
- [Qdrant](https://github.com/qdrant/qdrant) — 向量数据库

---

<p align="center">
  如果本项目对你有帮助，请 ⭐ <a href="https://github.com/slx-romantic-man/ai-data-agent">Star</a> 支持我们！
</p>
