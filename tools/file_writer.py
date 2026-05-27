"""文件写入工具 —— 限定在 workspace_dir 范围内"""

import os
import yaml


def _get_allowed_dirs() -> list:
    """从 config.yaml 读取所有允许的目录（workspace + allowed_paths）"""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception:
        return [os.path.normpath("workspace")]

    dirs = [os.path.normpath(config.get("workspace_dir", "workspace"))]
    for p in config.get("allowed_paths", []) or []:
        dirs.append(os.path.normpath(p))
    return dirs


def _safe_path(filepath: str) -> str:
    """将路径约束在允许的目录内，拒绝越界访问"""
    allowed = _get_allowed_dirs()

    if os.path.isabs(filepath):
        resolved = os.path.normpath(filepath)
    else:
        resolved = os.path.normpath(os.path.join(allowed[0], filepath))

    for d in allowed:
        if resolved.startswith(d + os.sep) or resolved == d:
            return resolved

    raise PermissionError(
        f"🚫 安全限制: 禁止访问允许目录外的路径!\n"
        f"   请求: {filepath}\n"
        f"   解析: {resolved}\n"
        f"   允许范围: {allowed}"
    )


def write_file(filepath: str, content: str) -> str:
    """将内容写入文件（仅限 workspace_dir 内）"""
    try:
        filepath = _safe_path(filepath)
    except PermissionError as e:
        return str(e)

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
        "description": "将内容写入文件。只能写入工作目录（workspace_dir）内的文件。当用户要求保存内容、创建文件时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "文件路径，可以是相对于工作目录的路径，如 'note.txt' 或 'output/result.txt'"
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
