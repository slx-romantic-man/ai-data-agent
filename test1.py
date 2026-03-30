import requests
import json

# 1. 配置参数
BASE_URL = "https://api-us.aiznt.com"
API_KEY = "sk-nDmxSZRAxKgypZVBG7u9oIPwSVz6CnHiyIammWKn7lDqFCT9"  # <--- 请在这里填入你的真实 API KEY

# 2. 拼接完整的 URL
url = f"{BASE_URL}/v1/messages"

# 3. 设置请求体 (Payload)
payload = {
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "messages": [
        {
            "role": "user",
            "content": "say 1"
        }
    ],
    "stream": False
}

# 4. 设置请求头 (Headers)
headers = {
    'Accept': 'application/json',
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json',
    # 如果你的服务商确实要求发送 X-Response-Id，可以取消下面这行的注释
    # 'X-Response-Id': 'msg_01RYWY1Esd6aQJsezmETjW4B' 
}

# 5. 发送请求
try:
    response = requests.post(url, headers=headers, json=payload)
    
    # 打印响应状态码 (200 表示成功)
    print(f"状态码: {response.status_code}")
    
    # 打印返回的 JSON 内容
    if response.status_code == 200:
        print("响应结果:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print("请求失败，错误详情:")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"发生网络错误: {e}")