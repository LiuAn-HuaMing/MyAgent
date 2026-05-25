"""V2: 循环多轮对话 —— 像网页版一样持续聊天"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
)

model = os.getenv("DEEPSEEK_MODEL")
if not model:
    raise ValueError("请在 .env 中设置 DEEPSEEK_MODEL")

# 🆕 对话历史列表，先放入 system 提示设定 AI 人设
messages = [
    {"role": "system", "content": "你是一个友好的AI助手，用中文回答问题。"}
]

HELP_TEXT = """
命令列表：
  /help   显示此帮助信息
  /exit   退出程序
  /clear  清空对话历史
  /stats  查看 Token 用量
"""

# 🆕 Token 估算（参考 DeepSeek 官方文档：中文≈0.6t/字，英文≈0.3t/字）
def estimate_tokens(text: str) -> int:
    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other = len(text) - chinese
    return int(chinese * 0.6 + other * 0.3)

# 累计统计
total_prompt_tokens = estimate_tokens(messages[0]["content"])
total_answer_tokens = 0

print("=" * 40)
print("🤖 对话助手（输入 /help 查看命令）")
print("=" * 40)

# 🆕 while True：不再只聊一次，而是循环聊下去
round_num = 1
while True:
    user_input = input(f"\nIN [{round_num}]: ")

    # / 开头的系统命令
    if user_input.startswith("/"):
        cmd = user_input[1:].lower()
        if cmd in ["exit", "quit"]:
            print("👋 再见！")
            break
        elif cmd in ["help", "?"]:
            print(HELP_TEXT)
            continue
        elif cmd == "clear":
            messages = [messages[0]]
            round_num = 1
            total_prompt_tokens = estimate_tokens(messages[0]["content"])
            total_answer_tokens = 0
            print("✅ 对话历史已清空")
            continue
        elif cmd == "stats":
            total = total_prompt_tokens + total_answer_tokens
            cache_hit = total_prompt_tokens - estimate_tokens(messages[-2]["content"]) if len(messages) >= 2 else 0
            print(f"\n📊 当前用量估算：")
            print(f"   历史消息数 : {len(messages)} 条")
            print(f"   累计输入   : ~{total_prompt_tokens} tokens")
            print(f"   累计输出   : ~{total_answer_tokens} tokens")
            print(f"   合计       : ~{total} tokens")
            print(f"   💡 前缀缓存自动生效，历史部分仅约 1/10 价格")
            continue
        else:
            print(f"未知命令: {user_input}，输入 /help 查看可用命令")
            continue

    if not user_input:
        continue

    # 🆕 把用户输入加入历史（而非直接放进 messages 参数里）
    messages.append({"role": "user", "content": user_input})

    # 流式调用，实时看到思考和回答过程
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        reasoning_effort="max",
        extra_body={"thinking": {"type": "enabled"}}
    )

    # 收集完整回答，同时实时打印
    answer = ""
    thinking_shown = False
    for chunk in stream:
        delta = chunk.choices[0].delta

        # 思考过程（灰色，不存入历史）
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            if not thinking_shown:
                print("\nTHINK : ", end="", flush=True)
                thinking_shown = True
            print(delta.reasoning_content, end="", flush=True)

        # 正式回答
        if delta.content:
            if thinking_shown:
                print(f"\n\nOUT[{round_num}]: ", end="", flush=True)
                thinking_shown = False
            print(delta.content, end="", flush=True)
            answer += delta.content

    print()  # 换行

    if not answer:
        answer = "(模型未返回内容)"

    # 🆕 Token 统计
    prompt_tokens = estimate_tokens(user_input)
    answer_tokens = estimate_tokens(answer)
    total_prompt_tokens += prompt_tokens
    total_answer_tokens += answer_tokens
    print(f"  [本轮: 入~{prompt_tokens}t, 出~{answer_tokens}t | 累计: ~{total_prompt_tokens + total_answer_tokens}t]")

    # 🆕 把 AI 回复也加入历史，下一轮就能"记住"
    messages.append({"role": "assistant", "content": answer})

    round_num += 1
