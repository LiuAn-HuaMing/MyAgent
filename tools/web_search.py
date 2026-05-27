"""联网搜索工具 —— Bing 搜索，国内可用，无需 API Key"""

import requests
from bs4 import BeautifulSoup

DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "在互联网上搜索信息。当需要查找最新资料、事实信息、新闻或你不确定的内容时使用此工具。返回标题、链接和摘要。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，用简洁的语言描述你要查的内容"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量，默认5条，最多10条",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}

# 模拟浏览器，避免被 Bing 拦截
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}


def web_search(query: str, max_results: int = 5) -> str:
    """在 Bing 上搜索并返回格式化结果"""
    max_results = min(max_results, 10)

    try:
        url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Bing 搜索结果在 <li class="b_algo"> 中
        results = []
        for item in soup.select("li.b_algo"):
            title_tag = item.select_one("h2 a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            snippet_tag = item.select_one(".b_caption p")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            if len(snippet) > 200:
                snippet = snippet[:200] + "..."

            results.append({"title": title, "href": href, "body": snippet})

            if len(results) >= max_results:
                break

    except Exception as e:
        return f"搜索失败: {e}"

    if not results:
        return f"未找到关于 '{query}' 的相关结果。"

    lines = [f"🔍 搜索 '{query}' 的结果 ({len(results)} 条):\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   🔗 {r['href']}")
        lines.append(f"   📝 {r['body']}")
        lines.append("")

    return "\n".join(lines)
