"""计算器工具 —— 安全地计算数学表达式"""

def calculator(expression: str) -> str:
    """计算数学表达式，返回结果字符串"""
    try:
        # 只允许安全的数学运算
        result = eval(expression, {"__builtins__": {}}, {})
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算出错: {e}"


# 工具描述（告诉 LLM 怎么用这个工具）
DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "计算数学表达式。当用户需要数学计算时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '3+5*2' 或 '(100+200)/3'"
                }
            },
            "required": ["expression"]
        }
    }
}
