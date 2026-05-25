"""V3: 工具调用 —— Agent 能"做事"了"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from tools import TOOL_FUNCTIONS, TOOL_DESCRIPTIONS

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
)

model = os.getenv("DEEPSEEK_MODEL")
if not model:
    raise ValueError("请在 .env 中设置 DEEPSEEK_MODEL")

messages = [
    {"role": "system", "content": "你是一个有用的AI助手。你可以使用工具来计算数学、获取时间。其他问题直接回答。请用中文回复。"}
]

HELP_TEXT = """
命令列表：
  /help   显示此帮助信息
  /exit   退出程序
  /clear  清空对话历史
"""

print("=" * 40)
print("🤖 Agent 助手（支持工具调用 | 输入 /help 查看命令）")
print("=" * 40)

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
            print("✅ 对话历史已清空")
            continue
        else:
            print(f"未知命令: {user_input}，输入 /help 查看可用命令")
            continue

    if not user_input:
        continue

    # 把用户输入加入历史
    messages.append({"role": "user", "content": user_input})

    # 循环处理工具调用（模型可能多次调工具）
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DESCRIPTIONS,
            stream=False,
            reasoning_effort="max",
            extra_body={"thinking": {"type": "enabled"}},
        )

        msg = response.choices[0].message

        # 显示思考过程（即使要调工具也先展示）
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            print(f"\nTHINK : {reasoning}", end="", flush=True)

        # 模型不需要工具 → 退出循环，准备流式回答
        if not msg.tool_calls:
            # 如果有思考但没有回答，先换行
            if reasoning and not msg.content:
                print()
            break

        # 如果有思考，换行后再显示工具调用
        if reasoning:
            print()

        # 模型需要工具 → 逐个执行
        tool_results = []
        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            print(f"\n🔧 调用工具: {tool_name}({tool_args})")

            tool_func = TOOL_FUNCTIONS.get(tool_name)
            tool_result = tool_func(**tool_args) if tool_func else f"未知工具: {tool_name}"

            print(f"📊 工具返回: {tool_result}")
            tool_results.append((tool_call, tool_result))

        # 把工具调用加入历史
        assistant_msg = {
            "role": "assistant",
            "content": msg.content,
            "tool_calls": msg.tool_calls
        }
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            assistant_msg["reasoning_content"] = reasoning
        messages.append(assistant_msg)

        # 把工具结果加入历史
        for tool_call, tool_result in tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })

    # 流式输出最终回答
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        reasoning_effort="max",
        extra_body={"thinking": {"type": "enabled"}},
    )

    # 收集并实时打印回答
    answer = ""
    thinking_shown = False
    for chunk in stream:
        delta = chunk.choices[0].delta

        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            if not thinking_shown:
                print("THINK : ", end="", flush=True)
                thinking_shown = True
            print(delta.reasoning_content, end="", flush=True)

        if delta.content:
            if thinking_shown:
                print(f"\nOUT[{round_num}]: ", end="", flush=True)
                thinking_shown = False
            elif not answer:
                print(f"OUT[{round_num}]: ", end="", flush=True)
            print(delta.content, end="", flush=True)
            answer += delta.content

    print()

    if not answer:
        answer = "(模型未返回内容)"

    messages.append({"role": "assistant", "content": answer})
    round_num += 1
