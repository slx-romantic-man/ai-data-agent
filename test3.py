import os
from anthropic import Anthropic

# 1. 配置必要的环境变量
# 注意：这一步最关键，它将请求重定向到 MiniMax 的服务器，而不是 Anthropic 官方服务器
os.environ["ANTHROPIC_BASE_URL"] = "https://api.minimaxi.com/anthropic"
os.environ["ANTHROPIC_API_KEY"] = "sk-cp-b9-yITc2R_pY9ckBiaRro13OUaABhnPov_zs4Xv5eX-lfokaKyVVv1ZdOBO4mWh8ObE4nrONzVAFbYOKd9tKENZNbLnJkaY1Bs67PTHHXK1_rfYapcSUbLg"

# 2. 初始化客户端
client = Anthropic()

# 3. 发起调用
try:
    response = client.messages.create(
        model="MiniMax-M2.7",  # 支持 MiniMax-M2.7, MiniMax-M2.5 等
        max_tokens=1000,
        system="你是一个乐于助人的 AI 助手。",
        messages=[
            {
                "role": "user",
                "content": "你好，请简单介绍一下你自己。"
            }
        ]
    )

    # 4. 获取并打印结果
    # MiniMax 的返回内容包含 text 和可能的 thinking (思维链)
    for block in response.content:
        if block.type == "text":
            print(f"回答内容:\n{block.text}")
        elif block.type == "thinking":
            print(f"思考过程:\n{block.thinking}")

except Exception as e:
    print(f"调用出错: {e}")