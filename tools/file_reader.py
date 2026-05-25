"""文件读取工具"""
import os


def read_file(filepath: str) -> str:
    """读取文本文件的内容"""
    # 安全检查：路径标准化
    filepath = os.path.normpath(filepath)

    if not os.path.exists(filepath):
        return f"错误: 文件不存在 —— {filepath}"

    if not os.path.isfile(filepath):
        return f"错误: 路径不是文件 —— {filepath}"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 限制返回长度，避免 token 爆炸
        max_chars = 5000
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n...(文件过长，已截断，共 {len(content)} 字符)"

        size_kb = os.path.getsize(filepath) / 1024
        return f"📄 {filepath} ({size_kb:.1f} KB):\n\n{content}"

    except UnicodeDecodeError:
        return f"错误: 无法以 UTF-8 编码读取文件 —— {filepath}"
    except Exception as e:
        return f"错误: {e}"


DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取指定文件的内容。当用户想看某个文件内容时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "文件的完整路径，如 C:/Projects/readme.txt"
                }
            },
            "required": ["filepath"]
        }
    }
}
