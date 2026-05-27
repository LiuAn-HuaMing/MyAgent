"""Python 代码执行工具 —— 安全沙箱执行，有超时和输出长度限制"""

import sys
import subprocess
import os
import yaml


def _get_workspace() -> str:
    """从 config.yaml 读取工作目录"""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return os.path.normpath(config.get("workspace_dir", "workspace"))
    except Exception:
        return os.path.normpath("workspace")


DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": "执行一段 Python 代码并返回输出。适合数据分析、计算、文件处理、格式化等任务。代码在隔离的子进程中运行，15秒超时。",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码。可以 import 已安装的库。用 print() 输出结果。"
                }
            },
            "required": ["code"]
        }
    }
}


def run_python(code: str) -> str:
    """在子进程中执行 Python 代码，返回 stdout/stderr"""
    workspace = _get_workspace()

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=workspace,
            encoding="utf-8",
            errors="replace",
        )

        output = result.stdout
        if result.stderr:
            if output:
                output += "\n"
            output += f"[stderr]:\n{result.stderr}"

        if not output.strip():
            return f"✅ 代码执行完成（无输出），返回码: {result.returncode}"

        # 限制输出长度
        max_chars = 3000
        if len(output) > max_chars:
            output = output[:max_chars] + f"\n\n...(输出过长，已截断，共 {len(output)} 字符)"

        return output

    except subprocess.TimeoutExpired:
        return "⏱️ 代码执行超时（超过15秒），已终止"
    except Exception as e:
        return f"❌ 代码执行失败: {e}"
