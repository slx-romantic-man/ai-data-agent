# 贡献指南

感谢你对 AI Data Agent 的兴趣！我们欢迎各种形式的贡献，包括但不限于：

- 🐛 报告 Bug
- 💡 提交新功能建议
- 📝 完善文档
- 🔧 提交代码改进
- 🎨 改进 UI/UX

## 开发环境搭建

### 1. 克隆仓库

```bash
git clone https://github.com/slx-romantic-man/ai-data-agent.git
cd ai-data-agent
```

### 2. 安装 Python 依赖

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install ruff mypy pytest pytest-asyncio httpx
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写必要的配置项
```

### 4. 启动开发服务器

```bash
# 后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端（新终端）
cd ../frontend
python -m http.server 8080
```

## 代码规范

### Python

我们使用以下工具保证代码质量：

- **ruff** — 代码格式化和 lint（替代 black + flake8 + isort）
- **mypy** — 静态类型检查
- **pytest** — 单元测试

```bash
cd backend

# 格式化代码
ruff format app/

# 检查代码风格
ruff check app/

# 类型检查
mypy app/ --ignore-missing-imports

# 运行测试
pytest tests/ -v
```

### 提交规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

Type 类型：

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码含义）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

示例：

```bash
git commit -m "feat(agent): add support for parallel tool execution"
git commit -m "fix(auth): prevent user_id override in chat endpoint"
git commit -m "docs(readme): update deployment instructions"
```

## 提交 PR 流程

1. **Fork 本仓库** 到自己的 GitHub 账号
2. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/issue-description
   ```
3. **开发并提交代码**
   - 确保代码通过 `ruff check` 和 `mypy` 检查
   - 为新功能添加测试
   - 更新相关文档
4. **推送到你的 Fork**
   ```bash
   git push origin feature/your-feature-name
   ```
5. **创建 Pull Request**
   - 填写 PR 模板中的所有必填项
   - 关联相关的 Issue
   - 等待 CI 检查通过
   - 等待 Code Review

## 代码审查标准

- 代码是否清晰可读？
- 是否有适当的类型注解？
- 是否包含必要的测试？
- 是否更新了相关文档？
- 是否引入了安全漏洞？
- 是否有重复代码可以抽象？

## 问题反馈

- **Bug 报告**: 使用 [Bug Report Template](https://github.com/slx-romantic-man/ai-data-agent/issues/new?template=bug_report.yml)
- **功能建议**: 使用 [Feature Request Template](https://github.com/slx-romantic-man/ai-data-agent/issues/new?template=feature_request.yml)

## 开发注意事项

### Agent 核心链路修改

Agent 核心链路涉及以下文件，修改时请保持清晰的节点职责分离：

- `backend/app/agent/graph.py` — 工作流编排
- `backend/app/agent/nodes/*.py` — 节点实现
- `backend/app/agent/tools/*.py` — 工具实现
- `backend/app/agent/prompts/*.py` — Prompt 模板

### 添加新工具

1. 在 `backend/app/agent/tools/` 下新建类继承 `BaseTool`
2. 在 `backend/app/agent/router/tool_router.py` 中注册
3. 在 `executor_node.py` 中确保路由覆盖
4. 添加对应的单元测试

### 数据库变更

如需修改数据库模型：
1. 修改 `backend/app/access/database/models.py`
2. 生成 Alembic migration（即将支持）
3. 更新相关 Pydantic Schema

## 社区行为准则

请查看 [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)。

## 许可证

通过提交 PR，你同意你的贡献将在 [MIT License](./LICENSE) 下发布。
