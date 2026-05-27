"""命令行工具 —— 三重保障：展示命令 + 用户确认 + 可开关"""

import subprocess
import shlex

DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": '在终端执行一条命令行指令。执行前会先展示命令并等待用户输入「确认」后才真正运行。可用于查看文件、运行脚本、管理项目等。',
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的终端命令，如 'dir'、'python --version'、'git status' 等"
                },
                "explanation": {
                    "type": "string",
                    "description": "用中文解释这个命令会做什么，让用户了解后再决定是否确认执行"
                }
            },
            "required": ["command", "explanation"]
        }
    }
}


def run_command(command: str, explanation: str) -> str:
    """执行命令行指令，需用户确认"""

    # ============================================
    # 第 1 步：展示命令 + 说明
    # ============================================
    print(f"\n{'=' * 50}")
    print(f"💻 命令 : {command}")
    print(f"📝 说明 : {explanation}")
    print(f"{'=' * 50}")
    print("⚠️  输入 [确认] 来执行，输入其他任意内容则跳过")

    # ============================================
    # 第 2 步：等待用户输入
    # ============================================
    try:
        confirm = input(">>> ").strip()
    except (EOFError, KeyboardInterrupt):
        return "❌ 已取消"

    if confirm != "确认":
        return f"⏭️ 已跳过: 用户输入了 '{confirm}' 而非 '确认'"

    # ============================================
    # 第 3 步：执行命令
    # ============================================
    print(f"🔄 正在执行: {command}")
    try:
        # shell=True 支持管道、重定向等，但需谨慎
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]:\n{result.stderr}"

        # 截断过长输出
        if len(output) > 2000:
            output = output[:2000] + "\n... (输出过长，已截断)"

        return output if output.strip() else f"✅ 命令执行成功（无输出），返回码: {result.returncode}"

    except subprocess.TimeoutExpired:
        return "⏱️ 命令执行超时（超过30秒），已终止"
    except Exception as e:
        return f"❌ 命令执行失败: {e}"
