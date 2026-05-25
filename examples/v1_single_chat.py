"""V1: 单次对话 —— 发消息 → 收回复"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv() # 加载 .env 文件中的环境变量

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
) # 初始化 OpenAI 客户端

model = os.getenv("DEEPSEEK_MODEL") # 从环境变量获取模型名称
if not model:
    raise ValueError("请在 .env 中设置 DEEPSEEK_MODEL")

print("=" * 40)
print("🤖 对话助手")
print("=" * 40)

question = input("\nIN [1]: ") # 获取用户输入的问题

response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": question}]
) # 调用 API，发送用户消息并获取回复

answer = response.choices[0].message.content # 从 API 响应中提取模型回复的内容  

print(f"OUT[1]: {answer}") # 输出模型回复
