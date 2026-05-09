# AI Data Agent — 智能数据分析平台

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3.12-blue.svg" alt="Python 3.12"></a>
  <a href="#"><img src="https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg" alt="FastAPI"></a>
  <a href="#"><img src="https://img.shields.io/badge/LangGraph-0.2%2B-orange.svg" alt="LangGraph"></a>
  <a href="#"><img src="https://img.shields.io/badge/Vue-3-4FC08D.svg" alt="Vue 3"></a>
  <a href="#"><img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg" alt="Docker"></a>
</p>

<p align="center"><strong>用自然语言对话，完成复杂数据分析与 API 调用</strong></p>

---

## 🌟 项目简介

**AI Data Agent** 是一款企业级智能数据分析 Agent 系统。用户只需用自然语言描述需求，系统即可自动理解意图、检索相关 API、生成执行计划、调用数据工具，最终输出结构化分析报告。整个推理过程通过 SSE 流式实时推送，透明可观测。

> 💡 典型场景："查询最近 7 天销售额最高的 10 个客户，并分析他们的订单趋势" → Agent 自动拆解为多步计划，依次调用订单 API、执行 Python 分析、生成带图表的报告。

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🧠 **自然语言查询** | 用大白话查询数据库或 API，AI 自动转译为 SQL / API 调用 |
| 🔗 **API 智能检索** | 基于向量相似度 + LLM 精排，从海量 API 中召回最相关的接口 |
| 📊 **数据分析与可视化** | 内置 Python 执行环境（Pandas/NumPy），支持 Chart.js 图表渲染 |
| 📤 **Excel 导出** | 一键将分析结果导出为多 Sheet Excel，支持样式定制 |
| 🔐 **三级权限控制** | 角色级 / 行级过滤 / 列级脱敏，企业级数据安全 |
| ✅ **人工审批网关** | 敏感操作自动触发审批流，非管理员需管理员批准后方可执行 |
| 💬 **多轮对话持久化** | 基于 LangGraph Checkpointer，会话状态自动保存，支持随时恢复 |
| 🌊 **流式推理展示** | SSE 实时推送每个节点的执行状态，推理过程一目了然 |

## 🏗️ 架构概览

```
┌─────────────┐     ┌─────────────────────────────────────────────────────────────┐     ┌──────────┐
│   用户输入   │────▶│                        LangGraph 工作流                      │────▶│ 分析结果  │
└─────────────┘     ├─────────┬───────────┬─────────┬──────────┬───────────────────┤     └──────────┘
                    │ 意图澄清 │  API 检索  │ 全局规划 │ 人工审批 │      执行器       │
                    │ Intent  │ Retrieval │ Planner │  Gateway │     Executor      │
                    └────┬────┴─────┬─────┴────┬────┴────┬─────┴─────────┬─────────┘
                         │          │          │         │               │
                         ▼          ▼          ▼         ▼               ▼
                    条件完备?   向量+LLM   结构化计划  非管理员?      循环执行各步骤
                    缺失则反问  Top-10 API JSON Plan  API调用需审批  SQL/API/Python
```

### 节点职责

1. **Intent Clarification（意图澄清）** — 判断查询条件是否完备，缺失则反问用户补充
2. **API Retrieval（API 检索）** — 两阶段检索：Embedding 向量召回候选 API → LLM 精排 Top-10
3. **Planner（全局规划）** — 生成结构化 JSON 执行计划，精确到每一步的工具和参数
4. **审批网关** — 基于用户角色自动判断是否需要人工审批，支持批准/拒绝
5. **Executor（执行器）** — 按计划循环执行每一步，结果隔离存储到 `data_context`
6. **Analyzer（终局分析）** — 综合所有步骤数据，生成最终洞察报告

## 🛠️ 技术栈

### 后端
- **框架**: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **Agent 引擎**: [LangGraph](https://langchain-ai.github.io/langgraph/)（Plan-and-Execute 模式）
- **ORM**: [SQLAlchemy 2.0](https://docs.sqlalchemy.org/)（异步支持）
- **数据库**: MySQL / PostgreSQL（业务数据）+ SQLite（状态持久化）+ [Qdrant](https://qdrant.tech/)（向量存储）
- **LLM**: OpenAI / 阿里云 / 任何兼容 OpenAI API 的模型
- **Embedding**: OpenAI Embedding 或 [Sentence Transformers](https://www.sbert.net/)（本地模型）
- **安全**: JWT 认证、RestrictedPython 代码沙箱、参数化 SQL 防注入

### 前端
- **框架**: [Vue 3](https://vuejs.org/)（CDN 引入，无构建步骤）
- **样式**: [Tailwind CSS](https://tailwindcss.com/)
- **图表**: [Chart.js](https://www.chartjs.org/)
- **Markdown 渲染**: [Marked](https://marked.js.org/) + [DOMPurify](https://github.com/cure53/DOMPurify)（XSS 防护）
- **DOM 更新**: [Morphdom](https://github.com/patrick-steele-idem/morphdom)（局部 Diff）

### 部署
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **监控**: 内置 Health Check 端点

## 🚀 快速开始

### 环境要求
- Docker >= 20.10
- Docker Compose >= 2.0
- 或 Podman + podman-compose

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/ai-data-agent.git
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
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
LLM_MODEL=gpt-4

# 数据库（必填）
DATABASE_URL=mysql+aiomysql://user:password@mysql:3306/ai_data_agent

# JWT（必填）
JWT_SECRET_KEY=your-strong-jwt-secret
API_AUTH_ENCRYPTION_KEY=your-encryption-key

# Embedding（可选，默认使用本地模型）
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your-embedding-key
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
| `http://your-server-ip/` | 前端界面 |
| `http://your-server-ip/docs` | API 文档（Swagger UI）|
| `http://your-server-ip/health` | 健康检查 |

## 📁 项目结构

```
ai-data-agent/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── agent/              # LangGraph Agent 核心
│   │   │   ├── nodes/          # 工作流节点（意图/检索/规划/执行/分析）
│   │   │   ├── tools/          # 工具实现（SQL/API/Python/导出）
│   │   │   ├── prompts/        # Prompt 模板
│   │   │   ├── state.py        # AgentState 状态定义
│   │   │   └── graph.py        # LangGraph 工作流图
│   │   ├── api/v1/             # REST API 路由
│   │   ├── access/             # 数据访问层（数据库/权限/元数据）
│   │   ├── services/           # 业务服务层
│   │   ├── config/             # 配置管理
│   │   └── main.py             # FastAPI 入口
│   ├── data/                   # 数据存储（SQLite/Qdrant）
│   ├── scripts/                # 初始化与迁移脚本
│   ├── requirements.txt        # Python 依赖
│   └── Dockerfile
├── frontend/                   # Vue 3 前端
│   ├── index.html              # 入口页面
│   ├── css/                    # 样式文件
│   ├── js/                     # JS 模块（API/状态/工具/各功能页）
│   └── lib/                    # 第三方库
├── data/                       # 生产环境数据卷映射
├── logs/                       # 日志目录
├── docker-compose.yml          # Docker Compose 配置
├── deploy.sh                   # 生产部署脚本
├── start.sh                    # Podman 启动脚本
├── nginx.conf                  # Nginx 配置
└── docs/                       # 文档
```

## 🔧 开发指南

### 本地开发启动

```bash
# 1. 创建虚拟环境
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. 前端直接用浏览器打开 frontend/index.html
# 或使用任意静态服务器：python -m http.server 8080
```

### 注册 API 到系统

系统支持将企业内部 API 注册为 Agent 可调用的工具：

```bash
# 方式1：通过管理后台 UI 注册
# 方式2：使用脚本批量注册
cd scripts
python register_mock_apis_to_db.py
```

### 添加新工具

在 `backend/app/agent/tools/` 下新建工具类，继承 `BaseTool`，然后在 `executor_node.py` 中添加路由即可。

## 🔒 安全设计

- **SQL 注入防护**: 所有 SQL 查询使用 SQLAlchemy 参数化执行
- **代码沙箱**: Python Exec Tool 基于 RestrictedPython，禁止危险操作（文件写入、网络请求、导入未知模块）
- **数据脱敏**: 列级权限自动对敏感字段（如手机号、身份证）进行掩码处理
- **行级过滤**: 基于用户部门/角色自动追加 `WHERE` 条件
- **审批审计**: 所有审批操作记录到数据库，支持事后追溯
- **Token 安全**: JWT 认证 + API 配置加密存储

## 🎯 使用示例

### 示例 1：自然语言查数据库

```
用户：查询本月销售额超过 10 万的客户，按金额降序排列

Agent:
[Intent] 已提取条件：时间范围=本月，筛选条件=销售额>10万，排序=降序
[Retrieval] 召回相关 API: sales_query_api (score: 0.95)
[Planner] 生成计划:
  Step 1: 调用 sales_query_api 查询本月销售数据
  Step 2: 筛选金额>10万的记录
  Step 3: 按金额降序排列
[Executor] 执行中...
[Analyzer] 本月共有 23 位客户销售额超过 10 万元，TOP 3 为：...
```

### 示例 2：API 调用 + Python 分析

```
用户：分析最近 7 天订单量的趋势

Agent:
[Planner] 生成计划:
  Step 1: 调用 orders_api 获取最近 7 天订单
  Step 2: Python 代码按日期聚合统计
  Step 3: 生成趋势图表数据
[Analyzer] 最近 7 天订单量呈上升趋势，日均 156 单，周三达到峰值 203 单...
```

## 📸 界面预览

> 前端采用深色主题设计，支持响应式布局，核心页面包括：
> - 💬 对话页面：类 ChatGPT 的流式对话体验，支持 Markdown 和图表渲染
> - 🔌 API 管理：注册、测试、管理企业 API
> - 👤 用户管理：角色配置与权限分配
> - 📜 历史记录：查看过往对话与分析结果

## 🤝 参与贡献

我们欢迎各种形式的贡献，包括但不限于：

- 提交 Issue 反馈 Bug 或建议
- 提交 Pull Request 改进代码
- 完善文档和教程
- 分享使用案例

### 提交 PR 流程

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

## 📄 许可证

[MIT License](../LICENSE) © AI Data Agent Team

## 🙏 致谢

本项目基于以下优秀开源项目构建：

- [LangChain / LangGraph](https://github.com/langchain-ai/langgraph) — Agent 工作流框架
- [FastAPI](https://github.com/tiangolo/fastapi) — 现代 Python Web 框架
- [Vue.js](https://github.com/vuejs/core) — 渐进式前端框架
- [Qdrant](https://github.com/qdrant/qdrant) — 向量数据库
- [Sentence Transformers](https://github.com/UKPLab/sentence-transformers) — 文本嵌入模型

---

<p align="center">
  如果本项目对你有帮助，请 ⭐ Star 支持我们！
</p>
