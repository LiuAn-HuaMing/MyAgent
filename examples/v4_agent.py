"""V4: 配置化 + 文件工具 —— Agent 能读写文件了"""
import os
import json
import yaml
from openai import OpenAI
from dotenv import load_dotenv
from tools import TOOL_FUNCTIONS, TOOL_DESCRIPTIONS
from colorama import init, Fore, Style

init(autoreset=True)  # 每次 print 后自动重置颜色

load_dotenv()

# ============================================================
# 从 config.yaml 加载配置
# ============================================================
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

system_prompt = config["system_prompt"]
model_config = config.get("model", {})
workspace_dir = config.get("workspace_dir", "workspace")

# 确保工作目录存在
os.makedirs(workspace_dir, exist_ok=True)

# ============================================================
# 初始化
# ============================================================
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
)

model = os.getenv("DEEPSEEK_MODEL")
if not model:
    raise ValueError("请在 .env 中设置 DEEPSEEK_MODEL")

messages = [{"role": "system", "content": system_prompt}]

HELP_TEXT = """
命令列表：
  /help   显示此帮助信息
  /exit   退出程序
  /clear  清空对话历史
"""

print("=" * 40)
print("🤖 Agent V4（计算器 | 时间 | 文件读写 | 搜索 | 命令行）")
print(f"📁 工作目录: {workspace_dir}")
print("=" * 40)

# ============================================================
# 对话循环
# ============================================================
round_num = 1
while True:
    user_input = input(f"\n{Fore.GREEN}IN [{round_num}]: {Style.RESET_ALL}")

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

    messages.append({"role": "user", "content": user_input})

    # 循环处理工具调用
    used_tools = False
    final_msg = None  # 最后一次非流式响应（无工具调用时）
    while True:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DESCRIPTIONS,
            stream=False,
            reasoning_effort=model_config.get("reasoning_effort", "max"),
            extra_body={"thinking": {"type": "enabled"}},
        )

        msg = response.choices[0].message
        reasoning = getattr(msg, "reasoning_content", None)

        # 不需要工具 → 记下这条消息，退出循环
        if not msg.tool_calls:
            final_msg = msg
            break

        used_tools = True

        # 显示思考过程
        if reasoning:
            print(f"\nTHINK : {reasoning}")

        # 执行所有工具调用
        tool_results = []
        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            print(f"🔧 调用工具: {tool_name}({tool_args})")
            tool_func = TOOL_FUNCTIONS.get(tool_name)
            tool_result = tool_func(**tool_args) if tool_func else f"未知工具: {tool_name}"
            print(f"📊 工具返回: {tool_result}")
            tool_results.append((tool_call, tool_result))

        # 加入历史
        assistant_msg = {
            "role": "assistant",
            "content": msg.content,
            "tool_calls": msg.tool_calls
        }
        if reasoning:
            assistant_msg["reasoning_content"] = reasoning
        messages.append(assistant_msg)

        for tool_call, tool_result in tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })

    # 输出最终回答
    if used_tools:
        # 用过工具 → 流式输出（思考+回答一起展示）
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            reasoning_effort=model_config.get("reasoning_effort", "max"),
            extra_body={"thinking": {"type": "enabled"}},
        )

        answer = ""
        thinking_shown = False
        for chunk in stream:
            delta = chunk.choices[0].delta

            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                if not thinking_shown:
                    print("\nTHINK : ", end="", flush=True)
                    thinking_shown = True
                print(delta.reasoning_content, end="", flush=True)

            if delta.content:
                if thinking_shown:
                    print(f"\n\n{Fore.RED}OUT[{round_num}]: {Style.RESET_ALL}", end="", flush=True)
                    thinking_shown = False
                elif not answer:
                    print(f"{Fore.RED}OUT[{round_num}]: {Style.RESET_ALL}", end="", flush=True)
                print(delta.content, end="", flush=True)
                answer += delta.content

        print()
        messages.append({"role": "assistant", "content": answer})

    else:
        # 没用工具 → 直接用非流式结果（只想了1次）
        reasoning = getattr(final_msg, "reasoning_content", None)
        if reasoning:
            print(f"\nTHINK : {reasoning}")
        answer = final_msg.content or ""
        print(f"{Fore.RED}OUT[{round_num}]: {Style.RESET_ALL}{answer}")
        assistant_msg = {"role": "assistant", "content": answer}
        if reasoning:
            assistant_msg["reasoning_content"] = reasoning
        messages.append(assistant_msg)

    round_num += 1
