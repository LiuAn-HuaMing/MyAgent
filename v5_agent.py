"""V5: 记忆系统 —— Agent 能记住你，跨会话持久化"""
import os
import re
import json
import yaml
from openai import OpenAI
from dotenv import load_dotenv
from tools import TOOL_FUNCTIONS, TOOL_DESCRIPTIONS
from tools.memory_tool import load_memory_context, list_memories, save_memory, delete_memory
from colorama import init, Fore, Style

init(autoreset=True)

load_dotenv()


# ============================================================
# 工具函数：清洗模型误输出的 XML 格式工具调用
# ============================================================
def _clean_response(text: str) -> str:
    """去掉模型误当文本输出的 <function_calls> / <invoke> 等 XML"""
    if not text:
        return text
    # 匹配 <function_calls>...</function_calls> 整块
    text = re.sub(r'<function_calls>.*?</function_calls>', '', text, flags=re.DOTALL)
    # 匹配 <invoke name="...">...</invoke>
    text = re.sub(r'<invoke\b[^>]*>.*?</invoke>', '', text, flags=re.DOTALL)
    # 匹配零散的 parameter 标签
    text = re.sub(r'<parameter\b[^>]*>.*?</parameter>', '', text, flags=re.DOTALL)
    return text.strip()

# ============================================================
# 配置加载
# ============================================================
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

system_prompt = config["system_prompt"]
model_config = config.get("model", {})
workspace_dir = config.get("workspace_dir", "workspace")
os.makedirs(workspace_dir, exist_ok=True)

# ============================================================
# 🧠 记忆：启动时加载，注入 system prompt
# ============================================================
memory_context = load_memory_context()
if memory_context:
    system_prompt += memory_context

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
  /help      显示此帮助信息
  /exit      退出程序
  /clear     清空对话历史（记忆保留）
  /remember <主题>: <内容>   手动保存记忆
  /forget <主题>             删除记忆
  /memories  查看所有记忆
"""

print("=" * 45)
print("🤖 Agent V5（8个工具 + 🧠 记忆系统）")
print(f"📁 工作目录: {workspace_dir}")
if memory_context:
    print("🧠 已加载历史记忆")
print("=" * 45)

# ============================================================
# 对话循环
# ============================================================
round_num = 1
while True:
    user_input = input(f"\n{Fore.GREEN}IN [{round_num}]: {Style.RESET_ALL}")

    if user_input.startswith("/"):
        cmd = user_input[1:].lower()
        parts = cmd.split(None, 1)

        if parts[0] in ["exit", "quit"]:
            print("👋 再见！记忆已保存。")
            break

        elif parts[0] in ["help", "?"]:
            print(HELP_TEXT)
            continue

        elif parts[0] == "clear":
            messages = [messages[0]]
            round_num = 1
            print("✅ 对话历史已清空（记忆保留）")
            continue

        elif parts[0] == "remember":
            if len(parts) < 2 or ":" not in parts[1]:
                print("格式: /remember <主题>: <内容>\n例如: /remember 编程水平: Python 学了1个月")
            else:
                key, value = parts[1].split(":", 1)
                print(save_memory(key.strip(), value.strip()))
            continue

        elif parts[0] == "forget":
            if len(parts) < 2:
                print("格式: /forget <主题>\n例如: /forget 编程水平")
            else:
                print(delete_memory(parts[1].strip()))
            continue

        elif parts[0] == "memories":
            print(list_memories())
            continue

        else:
            print(f"未知命令: {user_input}，输入 /help 查看可用命令")
            continue

    if not user_input:
        continue

    messages.append({"role": "user", "content": user_input})

    # ========================================
    # 工具调用循环
    # ========================================
    used_tools = False
    final_msg = None
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

        if not msg.tool_calls:
            final_msg = msg
            break

        used_tools = True

        if reasoning:
            print(f"\nTHINK : {reasoning}")

        tool_results = []
        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            print(f"🔧 调用工具: {tool_name}({tool_args})")
            tool_func = TOOL_FUNCTIONS.get(tool_name)
            tool_result = tool_func(**tool_args) if tool_func else f"未知工具: {tool_name}"
            print(f"📊 工具返回: {tool_result}")
            tool_results.append((tool_call, tool_result))

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

    # ========================================
    # 输出最终回答
    # ========================================
    if used_tools:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            reasoning_effort=model_config.get("reasoning_effort", "max"),
            extra_body={"thinking": {"type": "enabled"}},
        )

        answer = ""
        thinking_shown = False
        # XML 拦截缓冲区：模型可能把 tool call 当文本输出，实时屏蔽
        xml_buf = ""       # 疑似 XML 区域的缓冲
        in_xml = False     # 是否正在 XML 区域内

        for chunk in stream:
            delta = chunk.choices[0].delta

            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                if thinking_shown:
                    # 已在打印思考内容，直接继续
                    print(delta.reasoning_content, end="", flush=True)
                else:
                    print("\nTHINK : ", end="", flush=True)
                    thinking_shown = True
                    print(delta.reasoning_content, end="", flush=True)

            if delta.content:
                if thinking_shown:
                    print(f"\n\n{Fore.RED}OUT[{round_num}]: {Style.RESET_ALL}", end="", flush=True)
                    thinking_shown = False
                elif not answer:
                    print(f"{Fore.RED}OUT[{round_num}]: {Style.RESET_ALL}", end="", flush=True)

                text = delta.content
                i = 0
                while i < len(text):
                    if not in_xml:
                        # 正常模式：检测 XML 起始
                        idx_func = text.find("<function_calls>", i)
                        idx_invoke = text.find("<invoke", i)
                        first_xml = min(idx_func if idx_func >= 0 else len(text),
                                        idx_invoke if idx_invoke >= 0 else len(text))

                        if first_xml < len(text):
                            # 先输出 XML 之前的正常文字
                            print(text[i:first_xml], end="", flush=True)
                            answer += text[i:first_xml]
                            in_xml = True
                            xml_buf = text[first_xml:]
                            i = len(text)  # 当前 chunk 剩余全进缓冲
                        else:
                            print(text[i:], end="", flush=True)
                            answer += text[i:]
                            i = len(text)
                    else:
                        # XML 模式：缓冲直到找到闭合标签
                        xml_buf += text[i:]
                        i = len(text)
                        # 检查是否 XML 结束了
                        if "</function_calls>" in xml_buf or "</invoke>" in xml_buf:
                            # XML 块结束，丢弃缓冲
                            end_tag = max(xml_buf.find("</function_calls>"),
                                          xml_buf.find("</invoke>"))
                            if end_tag >= 0:
                                end_pos = end_tag + len("</function_calls>") if "</function_calls>" in xml_buf else end_tag + len("</invoke>")
                                # 检查闭合标签后还有没有正常文字
                                after = xml_buf[end_pos:]
                                xml_buf = ""
                                in_xml = False
                                if after:
                                    # 重新处理剩余部分
                                    text = after
                                    i = 0
                                    continue

        # 如果循环结束时还在 XML 里，丢弃缓冲
        if xml_buf and not in_xml:
            answer += _clean_response(xml_buf)

        print()
        answer = _clean_response(answer)
        messages.append({"role": "assistant", "content": answer})

    else:
        reasoning = getattr(final_msg, "reasoning_content", None)
        if reasoning:
            print(f"\nTHINK : {reasoning}")
        answer = _clean_response(final_msg.content or "")
        print(f"{Fore.RED}OUT[{round_num}]: {Style.RESET_ALL}{answer}")
        assistant_msg = {"role": "assistant", "content": answer}
        if reasoning:
            assistant_msg["reasoning_content"] = reasoning
        messages.append(assistant_msg)

    round_num += 1
