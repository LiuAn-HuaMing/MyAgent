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
# 工具函数：检测并解析模型误输出的 XML 工具调用
# ============================================================
def _extract_xml_tool_calls(text: str) -> tuple[str, list]:
    """
    从文本中提取 XML 格式的工具调用，返回 (清洗后文本, 工具调用列表)
    工具调用列表每项为 (tool_name, dict_of_args)
    """
    if not text:
        return text, []

    tool_calls = []
    # 匹配所有 <invoke name="xxx">...</invoke> 块
    invoke_pattern = r'<invoke\s+name="([^"]+)"\s*>(.*?)</invoke>'
    for match in re.finditer(invoke_pattern, text, re.DOTALL):
        tool_name = match.group(1)
        params_block = match.group(2)

        args = {}
        # 匹配 <parameter name="xxx" ...>value</parameter>
        param_pattern = r'<parameter\s+name="([^"]+)"[^>]*>(.*?)</parameter>'
        for pm in re.finditer(param_pattern, params_block, re.DOTALL):
            args[pm.group(1)] = pm.group(2)

        if tool_name and args:
            tool_calls.append((tool_name, args))

    # 清洗掉所有 XML 标签
    clean = re.sub(r'<function_calls>.*?</function_calls>', '', text, flags=re.DOTALL)
    clean = re.sub(r'<invoke\b[^>]*>.*?</invoke>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<parameter\b[^>]*>.*?</parameter>', '', clean, flags=re.DOTALL)
    clean = clean.strip()

    return clean, tool_calls


def _clean_response(text: str) -> str:
    """仅清洗 XML，不解析（兼容旧逻辑）"""
    clean, _ = _extract_xml_tool_calls(text)
    return clean

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
  /help                       显示此帮助信息
  /exit                       退出程序
  /clear                      清空对话历史（记忆保留）
  /remember <主题>: <内容>     手动保存记忆
  /forget <主题>               删除记忆
  /memories                   查看所有记忆
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
skip_input = False  # XML 工具执行后跳过 input，直接处理工具结果
while True:
    if not skip_input:
        user_input = input(f"\n{Fore.GREEN}IN [{round_num}]: {Style.RESET_ALL}")
    else:
        user_input = None
    skip_input = False

    if user_input and user_input.startswith("/"):
        cmd = user_input[1:].lower()
        parts = cmd.split(None, 1)
        # 只有 / 没有命令名 → 报错
        if not parts or not parts[0]:
            print("输入 /help 查看可用命令")
            continue

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
    # 保存原始答案，以便后续提取 XML 工具调用
    raw_answer = ""

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
        xml_buf = ""
        in_xml = False

        for chunk in stream:
            delta = chunk.choices[0].delta

            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                if thinking_shown:
                    print(delta.reasoning_content, end="", flush=True)
                else:
                    print("\nTHINK : ", end="", flush=True)
                    thinking_shown = True
                    print(delta.reasoning_content, end="", flush=True)

            if delta.content:
                raw_answer += delta.content  # 保存原始内容（含 XML）

                if thinking_shown:
                    print(f"\n\n{Fore.RED}OUT[{round_num}]: {Style.RESET_ALL}", end="", flush=True)
                    thinking_shown = False
                elif not answer:
                    print(f"{Fore.RED}OUT[{round_num}]: {Style.RESET_ALL}", end="", flush=True)

                text = delta.content
                i = 0
                while i < len(text):
                    if not in_xml:
                        idx_func = text.find("<function_calls>", i)
                        idx_invoke = text.find("<invoke", i)
                        first_xml = min(idx_func if idx_func >= 0 else len(text),
                                        idx_invoke if idx_invoke >= 0 else len(text))

                        if first_xml < len(text):
                            print(text[i:first_xml], end="", flush=True)
                            answer += text[i:first_xml]
                            in_xml = True
                            xml_buf = text[first_xml:]
                            i = len(text)
                        else:
                            print(text[i:], end="", flush=True)
                            answer += text[i:]
                            i = len(text)
                    else:
                        xml_buf += text[i:]
                        i = len(text)
                        if "</function_calls>" in xml_buf or "</invoke>" in xml_buf:
                            end_tag = max(xml_buf.find("</function_calls>"),
                                          xml_buf.find("</invoke>"))
                            if end_tag >= 0:
                                end_pos = end_tag + (len("</function_calls>") if "</function_calls>" in xml_buf else len("</invoke>"))
                                after = xml_buf[end_pos:]
                                xml_buf = ""
                                in_xml = False
                                if after:
                                    text = after
                                    i = 0
                                    continue

        if xml_buf and not in_xml:
            answer += _clean_response(xml_buf)

        print()

    else:
        reasoning = getattr(final_msg, "reasoning_content", None)
        if reasoning:
            print(f"\nTHINK : {reasoning}")
        raw_answer = final_msg.content or ""
        answer = raw_answer
        print(f"{Fore.RED}OUT[{round_num}]: {Style.RESET_ALL}{_clean_response(answer)}")

    # ========================================
    # 检测并执行模型 XML 输出的工具调用
    # ========================================
    clean_answer, xml_tool_calls = _extract_xml_tool_calls(raw_answer)

    if xml_tool_calls:
        import uuid
        # 保存清洗后的回答
        messages.append({"role": "assistant", "content": clean_answer or None})
        # 执行 XML 工具
        for t_name, t_args in xml_tool_calls:
            func = TOOL_FUNCTIONS.get(t_name)
            result = func(**t_args) if func else f"未知工具: {t_name}"
            print(f"🔧 XML工具: {t_name}({t_args}) → {result}")
            # 构造正规 tool_call 格式加入历史
            cid = f"xml_{uuid.uuid4().hex[:8]}"
            messages.append({
                "role": "assistant", "content": None,
                "tool_calls": [{"id": cid, "type": "function",
                                "function": {"name": t_name,
                                             "arguments": json.dumps(t_args, ensure_ascii=False)}}]
            })
            messages.append({"role": "tool", "tool_call_id": cid, "content": result})
        # 重新进入处理循环（跳过 input，直接处理工具结果）
        skip_input = True
        continue

    # ========================================
    # 正常：保存回答到历史
    # ========================================
    answer = _clean_response(answer)
    assistant_msg = {"role": "assistant", "content": answer}
    if not used_tools:
        reasoning = getattr(final_msg, "reasoning_content", None)
        if reasoning:
            assistant_msg["reasoning_content"] = reasoning
    messages.append(assistant_msg)

    round_num += 1
