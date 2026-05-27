"""天气查询工具 —— 基于 wttr.in，全球免费，无需 API Key，支持3天预报"""

import requests

DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市今天及未来2天的天气。返回温度、天气状况、风力等信息。",
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
    """查询城市天气，返回今天 + 未来2天预报"""
    try:
        # 使用 JSON 格式获取结构化数据
        url = f"https://wttr.in/{city}?format=j1&m&lang=zh"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # 当前天气
        current = data.get("current_condition", [{}])[0]
        if not current:
            return f"❌ 未找到城市 '{city}' 的天气信息"

        temp = current.get("temp_C", "?")
        desc = current.get("weatherDesc", [{}])[0].get("value", "未知")
        humidity = current.get("humidity", "?")
        wind = current.get("winddir16Point", "?") + " " + current.get("windspeedKmph", "?") + "km/h"

        lines = [f"🌤️ {city} 天气"]
        lines.append(f"   今天: {desc}  🌡️{temp}°C  湿度{humidity}%  风{wind}")

        # 未来2天预报
        forecasts = data.get("weather", [])
        day_names = ["明天", "后天"]
        for i, day in enumerate(forecasts[1:3]):  # 跳过今天，取后2天
            date = day.get("date", "?")
            high = day.get("maxtempC", "?")
            low = day.get("mintempC", "?")
            # 取白天的天气描述
            hourly = day.get("hourly", [])
            day_desc = "未知"
            for h in hourly:
                if h.get("weatherDesc"):
                    day_desc = h["weatherDesc"][0]["value"]
                    break
            lines.append(f"   {day_names[i]} ({date}): {day_desc}  🌡️{low}~{high}°C")

        return "\n".join(lines)

    except requests.Timeout:
        return f"⏱️ 天气查询超时: {city}"
    except Exception as e:
        return f"❌ 天气查询失败: {e}"
