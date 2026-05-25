"""工具注册中心 —— 统一管理所有工具，支持通过 config.yaml 开关"""
import yaml
import os
from tools import calculator, time_tool, file_reader, file_writer

# 所有可用工具的定义
ALL_TOOLS = {
    "calculator":      (calculator.calculator,      calculator.DESCRIPTION),
    "get_current_time": (time_tool.get_current_time, time_tool.DESCRIPTION),
    "read_file":       (file_reader.read_file,      file_reader.DESCRIPTION),
    "write_file":      (file_writer.write_file,     file_writer.DESCRIPTION),
}

# 从 config.yaml 读取启用的工具
def load_tools(config_path: str = "config.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    tool_settings = config.get("tools", {})
    functions = {}
    descriptions = []

    for name, (func, desc) in ALL_TOOLS.items():
        if tool_settings.get(name, False):
            functions[name] = func
            descriptions.append(desc)

    return functions, descriptions

# 便捷：直接加载
TOOL_FUNCTIONS, TOOL_DESCRIPTIONS = load_tools()
