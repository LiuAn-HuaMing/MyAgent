"""天气查询工具 —— 基于 wttr.in，全球免费，无需 API Key"""

import requests

DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的当前天气。返回温度、天气状况、湿度、风速等信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，支持中文（如 北京）或英文（如 Beijing）、拼音（如 shanghai）"
                }
            },
            "required": ["city"]
        }
    }
}


def get_weather(city: str) -> str:
    """查询城市天气（wttr.in 免费 API）"""
    try:
        # 获取简洁文本格式天气
        url = f"https://wttr.in/{city}?format=4&m&lang=zh"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        text = resp.text.strip()

        if not text or "Unknown" in text:
            return f"❌ 未找到城市 '{city}' 的天气信息"

        return f"🌤️ {text}"

    except requests.Timeout:
        return f"⏱️ 天气查询超时: {city}"
    except Exception as e:
        return f"❌ 天气查询失败: {e}"
