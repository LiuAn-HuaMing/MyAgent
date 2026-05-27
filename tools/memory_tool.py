"""记忆工具 —— 持久化存储用户偏好和重要信息"""

import json
import os
import yaml
from datetime import datetime


def _get_memory_path() -> str:
    """获取 memory.json 路径"""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        workspace = config.get("workspace_dir", "workspace")
    except Exception:
        workspace = "workspace"
    os.makedirs(workspace, exist_ok=True)
    return os.path.join(workspace, "memory.json")


def _load_memories() -> dict:
    """加载所有记忆"""
    path = _get_memory_path()
    if not os.path.exists(path):
        return {"memories": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"memories": []}


def _save_memories(data: dict):
    """保存记忆到文件"""
    with open(_get_memory_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_memory_context() -> str:
    """启动时调用：将记忆转为 system prompt 片段"""
    data = _load_memories()
    mems = data.get("memories", [])
    if not mems:
        return ""

    lines = ["\n\n## 关于用户的记忆（跨会话持久化）"]
    for i, m in enumerate(mems, 1):
        lines.append(f"{i}. {m['key']}: {m['value']}")
    return "\n".join(lines)


# ============================================================
# 工具定义
# ============================================================

SAVE_DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "save_memory",
        "description": "保存一条关于用户的记忆，跨会话持久化。当用户明确要求记住某事，或你了解到用户的重要偏好/习惯/背景信息时使用。不要记忆琐碎的测试内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "记忆的主题，如 '编程水平'、'回答偏好'、'常用工具'"
                },
                "value": {
                    "type": "string",
                    "description": "记忆的具体内容，如 'Python 学了1个月，会基础语法'"
                }
            },
            "required": ["key", "value"]
        }
    }
}


def save_memory(key: str, value: str) -> str:
    """保存一条记忆"""
    data = _load_memories()
    mems = data.get("memories", [])

    # 更新已有 key 还是新增
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for m in mems:
        if m["key"] == key:
            m["value"] = value
            m["time"] = now
            _save_memories(data)
            return f"🧠 已更新记忆: [{key}] → {value}"

    mems.append({"key": key, "value": value, "time": now})
    _save_memories(data)
    return f"🧠 已保存记忆: [{key}] → {value}"


LIST_DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "list_memories",
        "description": "列出所有已保存的用户记忆。当你想了解之前记住了什么时使用。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


def list_memories() -> str:
    """列出所有记忆"""
    data = _load_memories()
    mems = data.get("memories", [])
    if not mems:
        return "📭 还没有保存任何记忆。"

    lines = [f"🧠 已保存的记忆 ({len(mems)} 条):\n"]
    for i, m in enumerate(mems, 1):
        lines.append(f"{i}. [{m['key']}] {m['value']} ({m.get('time', '?')})")
    return "\n".join(lines)


DELETE_DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "delete_memory",
        "description": "删除指定主题的记忆。当用户说'忘掉关于XX的事'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "要删除的记忆主题"
                }
            },
            "required": ["key"]
        }
    }
}


def delete_memory(key: str) -> str:
    """删除一条记忆"""
    data = _load_memories()
    mems = data.get("memories", [])
    before = len(mems)
    data["memories"] = [m for m in mems if m["key"] != key]

    if len(data["memories"]) == before:
        return f"📭 没有找到主题为 '{key}' 的记忆"

    _save_memories(data)
    return f"🗑️ 已删除记忆: [{key}]"
