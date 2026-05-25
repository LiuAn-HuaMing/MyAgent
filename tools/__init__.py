"""工具注册中心 —— 统一管理所有工具"""
from tools import calculator, weather, time_tool

# 工具函数映射：名称 → 函数
TOOL_FUNCTIONS = {
    "calculator": calculator.calculator,
    "get_weather": weather.get_weather,
    "get_current_time": time_tool.get_current_time,
}

# 工具描述列表：告诉 LLM 有哪些工具可用
TOOL_DESCRIPTIONS = [
    calculator.DESCRIPTION,
    weather.DESCRIPTION,
    time_tool.DESCRIPTION,
]
