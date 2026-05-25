"""文件写入工具"""
import os


def write_file(filepath: str, content: str) -> str:
    """将内容写入文件"""
    filepath = os.path.normpath(filepath)

    # 确保目录存在
    dirpath = os.path.dirname(filepath)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        size_kb = os.path.getsize(filepath) / 1024
        return f"✅ 已写入: {filepath} ({size_kb:.1f} KB)"

    except Exception as e:
        return f"错误: {e}"


DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "将内容写入文件。当用户要求保存内容、创建文件时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "要写入的文件路径，如 C:/Projects/note.txt"
                },
                "content": {
                    "type": "string",
                    "description": "要写入文件的文本内容"
                }
            },
            "required": ["filepath", "content"]
        }
    }
}
