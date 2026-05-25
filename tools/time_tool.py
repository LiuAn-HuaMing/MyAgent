"""时间工具 —— 获取当前日期和时间"""
from datetime import datetime


def get_current_time(timezone: str = "local") -> str:
    """获取当前日期和时间"""
    now = datetime.now()
    weekday_map = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekday_map[now.weekday()]
    return f"{now.year}年{now.month}月{now.day}日 星期{weekday} {now.hour:02d}:{now.minute:02d}:{now.second:02d}"


DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "获取当前的日期和时间。当用户询问现在几点、今天几号时使用。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}
