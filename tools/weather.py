"""天气查询工具 —— 模拟数据"""

def get_weather(city: str) -> str:
    """查询城市天气（模拟数据）"""
    weather_data = {
        "北京": "晴天 ☀️，25°C，湿度 40%",
        "上海": "多云 ⛅，28°C，湿度 65%",
        "深圳": "阵雨 🌧️，30°C，湿度 80%",
        "杭州": "阴天 ☁️，22°C，湿度 55%",
        "成都": "小雨 🌧️，20°C，湿度 70%",
        "广州": "雷阵雨 ⛈️，32°C，湿度 85%",
    }
    return weather_data.get(city, f"抱歉，暂无「{city}」的天气数据")


DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的天气信息。当用户询问天气时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如：北京、上海、深圳"
                }
            },
            "required": ["city"]
        }
    }
}
