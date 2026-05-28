"""V6: 对话保存与恢复 —— 退出时保存，启动时恢复，真正连续对话"""
import os
import re
import json
import uuid
import yaml
from openai import OpenAI
from dotenv import load_dotenv
from tools import TOOL_FUNCTIONS, TOOL_DESCRIPTIONS
from datetime import datetime
from tools.memory_tool import load_memory_context, list_memories, save_memory, delete_memory
from colorama import init, Fore, Style

init(autoreset=True)

load_dotenv()


# ============================================================
# 工具函数：检测并解析模型误输出的 XML 工具调用
# ============================================================
def _extract_xml_tool_calls(text: str) -> tuple[str, list]:
    if not text:
        return text, []

    tool_calls = []
    invoke_pattern = r'<invoke\s+name="([^"]+)"\s*>(.*?)</invoke>'
    for match in re.finditer(invoke_pattern, text, re.DOTALL):
        tool_name = match.group(1)
        params_block = match.group(2)
        args = {}
        param_pattern = r'<parameter\s+name="([^"]+)"[^>]*>(.*?)</parameter>'
        for pm in re.finditer(param_pattern, params_block, re.DOTALL):
            args[pm.group(1)] = pm.group(2)
        if tool_name and args:
            tool_calls.append((tool_name, args))

    clean = re.sub(r'<function_calls>.*?</function_calls>', '', text, flags=re.DOTALL)
    clean = re.sub(r'<invoke\b[^>]*>.*?</invoke>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<parameter\b[^>]*>.*?</parameter>', '', clean, flags=re.DOTALL)
    clean = clean.strip()
    return clean, tool_calls


def _clean_response(text: str) -> str:
    clean, _ = _extract_xml_tool_calls(text)
    return clean


# ============================================================
# 💾 会话管理：每个会话独立存档
# ============================================================
sessions_dir = None
manifest_path = None

def _init_sessions():
    global sessions_dir, manifest_path
    sessions_dir = os.path.join(workspace_dir, "conversations")
    manifest_path = os.path.join(sessions_dir, "sessions.json")
    os.makedirs(sessions_dir, exist_ok=True)

def _load_manifest() -> list:
    if not os.path.exists(manifest_path):
        return []
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []

def _save_manifest(manifest: list) -> None:
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

def _session_path(session_id: str) -> str:
    return os.path.join(sessions_dir, f"{session_id}.json")

def _serialize_tool_calls(tool_calls) -> list | None:
    """将 OpenAI tool_calls 对象转为可 JSON 序列化的 dict 列表"""
    if not tool_calls:
        return None
    result = []
    for tc in tool_calls:
        if hasattr(tc, 'id'):  # OpenAI SDK 返回的对象
            result.append({
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            })
        else:  # XML 工具构造的，已经是 dict
            result.append(tc)
    return result

def save_current_session(session_id: str, title: str, messages: list) -> None:
    """保存当前会话到独立文件"""
    path = _session_path(session_id)
    save_data = []
    for msg in messages[1:]:  # 跳过 messages[0]（system prompt）
        item = {"role": msg["role"], "content": msg.get("content")}
        if msg.get("tool_calls"):
            item["tool_calls"] = _serialize_tool_calls(msg["tool_calls"])
        if msg.get("tool_call_id"):
            item["tool_call_id"] = msg["tool_call_id"]
        if msg.get("reasoning_content"):
            item["reasoning_content"] = msg["reasoning_content"]
        save_data.append(item)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    # 更新 manifest
    manifest = _load_manifest()
    user_count = sum(1 for m in messages if m["role"] == "user")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for s in manifest:
        if s["id"] == session_id:
            s["title"] = title
            s["messages"] = f"{user_count} 轮"
            s["updated_at"] = now
            break
    else:
        manifest.append({
            "id": session_id,
            "title": title,
            "messages": f"{user_count} 轮",
            "created_at": now,
            "updated_at": now,
        })
    _save_manifest(manifest)

def load_session_messages(session_id: str) -> list:
    """加载指定会话的消息（不含 system prompt）"""
    path = _session_path(session_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        print("⚠️ 会话存档损坏")
        return []

def delete_session_file(session_id: str) -> None:
    """删除指定会话"""
    path = _session_path(session_id)
    if os.path.exists(path):
        os.remove(path)
    manifest = _load_manifest()
    manifest = [s for s in manifest if s["id"] != session_id]
    _save_manifest(manifest)


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
# 💾 会话：初始化，创建新会话
# ============================================================
_init_sessions()
current_session_id = uuid.uuid4().hex[:8]
current_session_title = "(未命名)"
messages = [{"role": "system", "content": system_prompt}]
round_num = 1

HELP_TEXT = """
命令列表：
  /help /?                    显示此帮助信息
  /exit /quit                 保存并退出
  /save [标题]                手动保存当前会话（可附带标题）
  /new [标题]                 保存当前会话并开始新会话
  /sessions                   查看所有已保存的会话
  /load <ID>                  加载指定会话（自动保存当前）
  /delete <ID>                删除指定会话
  /clear                      清空当前会话对话
  /clearall confirm           删除全部会话存档（需输入 confirm 确认）
  /title <标题>               设置当前会话标题
  /history [N]                查看当前会话对话历史（可选最近 N 轮）
  /remember <主题>: <内容>    手动保存记忆
  /forget <主题>              删除记忆
  /memories                   查看所有记忆
"""

print("=" * 50)
print("🤖 Agent V6（多会话管理 + 🧠 记忆）")
print(f"📁 工作目录: {workspace_dir}")
print(f"💬 会话 ID: {current_session_id}（新会话）")
if memory_context:
    print("🧠 已加载历史记忆")
manifest = _load_manifest()
if manifest:
    print(f"💾 已有 {len(manifest)} 个存档会话，输入 /sessions 查看")
print("=" * 50)

# ============================================================
# 初始化 OpenAI 客户端
# ============================================================
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
)

model = os.getenv("DEEPSEEK_MODEL")
if not model:
    raise ValueError("请在 .env 中设置 DEEPSEEK_MODEL")

# ============================================================
# 对话循环
# ============================================================
processing_tools = False
while True:
    if not processing_tools:
        user_input = input(f"\n{Fore.GREEN}IN [{round_num}]: {Style.RESET_ALL}")
    else:
        user_input = None

    if user_input and user_input.startswith("/"):
        cmd = user_input[1:].lower()
        parts = cmd.split(None, 1)
        if not parts or not parts[0]:
            print("输入 /help 查看可用命令")
            continue

        if parts[0] in ["exit", "quit"]:
            save_current_session(current_session_id, current_session_title, messages)
            print("👋 再见！当前会话已保存。")
            break

        elif parts[0] in ["help", "?"]:
            print(HELP_TEXT)
            continue

        elif parts[0] == "save":
            if len(parts) > 1 and parts[1].strip():
                current_session_title = parts[1].strip()
            save_current_session(current_session_id, current_session_title, messages)
            user_msgs = sum(1 for m in messages if m["role"] == "user")
            print(f"💾 会话 {current_session_id} 已保存（{user_msgs} 轮）- {current_session_title}")
            continue

        elif parts[0] == "new":
            # 保存当前会话，然后开始新会话
            if len(messages) > 1:
                save_current_session(current_session_id, current_session_title, messages)
            title = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "(未命名)"
            current_session_id = uuid.uuid4().hex[:8]
            current_session_title = title
            messages = [{"role": "system", "content": system_prompt}]
            round_num = 1
            print(f"✅ 已保存，开始新会话: {current_session_id}（{title}）")
            continue

        elif parts[0] == "sessions":
            manifest = _load_manifest()
            if not manifest:
                print("📭 暂无已保存的会话")
            else:
                print(f"\n📋 已保存的会话（共 {len(manifest)} 个）：")
                print("─" * 60)
                for s in sorted(manifest, key=lambda x: x.get("updated_at", ""), reverse=True):
                    marker = " ← 当前" if s["id"] == current_session_id else ""
                    print(f"  [{s['id']}] {s['title']}  |  {s['messages']}  |  {s['updated_at']}{marker}")
                print("─" * 60)
            continue

        elif parts[0] == "load":
            if len(parts) < 2:
                print("格式: /load <会话ID>\n先用 /sessions 查看可用会话")
                continue
            target_id = parts[1].strip()
            target_msgs = load_session_messages(target_id)
            if not target_msgs:
                print(f"❌ 会话 {target_id} 不存在或为空")
                continue
            # 保存当前会话
            if len(messages) > 1:
                save_current_session(current_session_id, current_session_title, messages)
            # 读取会话标题
            manifest = _load_manifest()
            title = "(未命名)"
            for s in manifest:
                if s["id"] == target_id:
                    title = s["title"]
                    break
            current_session_id = target_id
            current_session_title = title
            messages = [{"role": "system", "content": system_prompt}] + target_msgs
            round_num = sum(1 for m in target_msgs if m["role"] == "user") + 1
            print(f"✅ 已加载会话: {target_id}（{title}），{round_num - 1} 轮对话")
            continue

        elif parts[0] == "delete":
            if len(parts) < 2:
                print("格式: /delete <会话ID>\n先用 /sessions 查看可用会话")
                continue
            target_id = parts[1].strip()
            delete_session_file(target_id)
            if target_id == current_session_id:
                current_session_id = uuid.uuid4().hex[:8]
                current_session_title = "(未命名)"
                messages = [{"role": "system", "content": system_prompt}]
                round_num = 1
            print(f"✅ 会话 {target_id} 已删除")
            continue

        elif parts[0] == "clear":
            messages = [messages[0]]
            round_num = 1
            print("✅ 当前会话对话已清空")
            continue

        elif parts[0] == "clearall":
            if len(parts) < 2 or parts[1].strip().lower() != "confirm":
                print("⚠️ 此操作将删除全部会话存档！请输入 /clearall confirm 确认")
            else:
                manifest = _load_manifest()
                count = len(manifest)
                for s in manifest:
                    delete_session_file(s["id"])
                current_session_id = uuid.uuid4().hex[:8]
                current_session_title = "(未命名)"
                messages = [{"role": "system", "content": system_prompt}]
                round_num = 1
                print(f"✅ 已删除 {count} 个会话存档")
            continue

        elif parts[0] == "title":
            if len(parts) < 2 or not parts[1].strip():
                print(f"当前标题: {current_session_title}\n格式: /title <新标题>")
            else:
                current_session_title = parts[1].strip()
                print(f"✅ 会话标题已设为: {current_session_title}")
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

        elif parts[0] == "history":
            # 查看对话历史，可选 /history N 只看最近 N 轮
            limit = None
            if len(parts) > 1:
                try:
                    limit = int(parts[1])
                except ValueError:
                    print("格式: /history [N]，N 为数字")
                    continue
            # 提取所有 user/assistant 对话轮次（跳过 system 和 tool 消息）
            rounds = []
            current_round = []
            for m in messages[1:]:  # 跳过 system prompt
                role = m.get("role")
                content = m.get("content", "")
                if not content:
                    continue
                if role == "user":
                    if current_round:
                        rounds.append(current_round)
                    # 截断过长内容
                    preview = content[:80] + "..." if len(content) > 80 else content
                    current_round = [(Fore.GREEN + "👤 用户" + Style.RESET_ALL, preview)]
                elif role == "assistant":
                    preview = content[:120] + "..." if len(content) > 120 else content
                    current_round.append((Fore.RED + "🤖 助手" + Style.RESET_ALL, preview))
            if current_round:
                rounds.append(current_round)

            if not rounds:
                print("📜 暂无对话历史")
                continue

            total = len(rounds)
            if limit and limit > 0:
                rounds = rounds[-limit:]
                print(f"\n📜 对话历史（最近 {min(limit, total)} / 共 {total} 轮）：")
            else:
                print(f"\n📜 对话历史（共 {total} 轮）：")
            print("─" * 50)
            for i, rnd in enumerate(rounds):
                idx = total - len(rounds) + i + 1
                for speaker, text in rnd:
                    print(f"[{idx}] {speaker}: {text}")
                print()
            print("─" * 50)
            continue

        elif parts[0] == "memories":
            print(list_memories())
            continue

        else:
            print(f"未知命令: {user_input}，输入 /help 查看可用命令")
            continue

    if not user_input:
        if processing_tools:
            processing_tools = False
        else:
            continue

    if user_input:
        messages.append({"role": "user", "content": user_input})
        # 自动用首条消息作为会话标题
        if current_session_title == "(未命名)" and len(messages) == 2:
            current_session_title = user_input[:30] + ("..." if len(user_input) > 30 else "")
            print(f"💬 会话自动标题: {current_session_title}")

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
                raw_answer += delta.content

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
        messages.append({"role": "assistant", "content": clean_answer or None})
        for t_name, t_args in xml_tool_calls:
            func = TOOL_FUNCTIONS.get(t_name)
            result = func(**t_args) if func else f"未知工具: {t_name}"
            print(f"🔧 XML工具: {t_name}({t_args}) → {result}")
            cid = f"xml_{uuid.uuid4().hex[:8]}"
            messages.append({
                "role": "assistant", "content": None,
                "tool_calls": [{"id": cid, "type": "function",
                                "function": {"name": t_name,
                                             "arguments": json.dumps(t_args, ensure_ascii=False)}}]
            })
            messages.append({"role": "tool", "tool_call_id": cid, "content": result})
        processing_tools = True
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
