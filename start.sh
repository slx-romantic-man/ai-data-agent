#!/bin/bash
set -e

# AI Data Agent — 生产环境启动脚本
# 特性：所有应用配置从 .env 文件读取，改 .env + podman restart 即可生效

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
CONTAINER_NAME="ai-data-agent-backend"
IMAGE="localhost/ai-data-agent-backend:latest"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env not found at $ENV_FILE"
    exit 1
fi

# 如果容器已存在，先删除（确保环境变量不残留）
if podman ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping and removing existing container..."
    podman stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    podman rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
fi

echo "Starting container with .env mounted..."
podman run -d \
    --name "$CONTAINER_NAME" \
    -p 8000:8000 \
    -v "${ENV_FILE}:/app/.env:ro" \
    -v "${PROJECT_DIR}/data:/app/data" \
    -v "${PROJECT_DIR}/logs:/app/logs" \
    "$IMAGE" \
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

echo "Syncing ALL modified backend code..."
# 核心修改文件列表（来自 git diff）
FILES=(
    "app/agent/core/data_analyzer.py"
    "app/agent/graph.py"
    "app/agent/nodes/analyzer_node.py"
    "app/agent/nodes/intent_planner_node.py"
    "app/agent/nodes/retrieval_node.py"
    "app/agent/prompts/intent_planner_prompt.py"
    "app/agent/tools/api_fetch_tool.py"
    "app/agent/tools/python_exec_tool.py"
    "app/api/dependencies.py"
    "app/api/v1/__init__.py"
    "app/api/v1/api_management.py"
    "app/api/v1/auth.py"
    "app/api/v1/chat.py"
    "app/api/v1/mock_api.py"
    "app/config/api_config.py"
    "app/config/embedding_config.py"
    "app/config/settings.py"
    "app/main.py"
    "app/models/api_permission.py"
    "app/services/api_permission_service.py"
    "app/services/api_retrieval_service.py"
    "app/services/suggestion_service.py"
    "app/services/user_service.py"
)

for f in "${FILES[@]}"; do
    src="${PROJECT_DIR}/backend/$f"
    if [ -f "$src" ]; then
        podman cp "$src" "${CONTAINER_NAME}:/app/$f"
    else
        echo "WARNING: $src not found"
    fi
done

# 清除 Python 缓存
echo "Clearing Python cache..."
podman exec "$CONTAINER_NAME" find /app/app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "Restarting with updated code..."
podman restart "$CONTAINER_NAME"
sleep 6

# 健康检查
for i in 1 2 3; do
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        echo ""
        echo "========================================"
        echo "  Container started successfully."
        echo "========================================"
        echo ""
        echo "To change config:"
        echo "  1. Edit ${ENV_FILE}"
        echo "  2. Run: podman restart ${CONTAINER_NAME}"
        echo ""
        exit 0
    fi
    sleep 2
done

echo "WARNING: Health check failed, check logs:"
podman logs "$CONTAINER_NAME" | tail -20
exit 1
