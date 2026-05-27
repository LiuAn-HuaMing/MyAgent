"""文件读取工具 —— 可读取任意路径（读取不会造成破坏）"""

import os
import yaml


def _get_workspace() -> str:
    """从 config.yaml 读取工作目录，用于解析相对路径"""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return os.path.normpath(config.get("workspace_dir", "workspace"))
    except Exception:
        return os.path.normpath("workspace")


def read_file(filepath: str) -> str:
    """读取文本文件的内容（任意路径均可读取）"""
    # 相对路径 → 相对于 workspace
    if not os.path.isabs(filepath):
        filepath = os.path.normpath(os.path.join(_get_workspace(), filepath))
    else:
        filepath = os.path.normpath(filepath)

    if not os.path.exists(filepath):
        return f"错误: 文件不存在 —— {filepath}"

    if not os.path.isfile(filepath):
        return f"错误: 路径不是文件 —— {filepath}"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        max_chars = 5000
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n...(文件过长，已截断，共 {len(content)} 字符)"

        size_kb = os.path.getsize(filepath) / 1024
        return f"📄 {filepath} ({size_kb:.1f} KB):\n\n{content}"

    except UnicodeDecodeError:
        return f"错误: 无法以 UTF-8 编码读取文件（可能是二进制文件） —— {filepath}"
    except PermissionError:
        return f"错误: 没有权限读取文件 —— {filepath}"
    except Exception as e:
        return f"错误: {e}"


DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取指定文件的内容。可读取任意路径的文本文件。当用户想看某个文件内容时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "文件路径，支持绝对路径（如 C:/Users/xxx/file.txt）或相对于工作目录的路径（如 'readme.txt'）"
                }
            },
            "required": ["filepath"]
        }
    }
}
