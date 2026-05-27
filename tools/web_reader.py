"""网页内容抓取工具 —— 读取网页全文（文本内容）"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

DESCRIPTION = {
    "type": "function",
    "function": {
        "name": "read_webpage",
        "description": "读取指定网页的文本内容。适合在搜索后深入阅读某篇文章、查阅文档、抓取信息。返回页面中的纯文本。",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要读取的网页完整URL，如 https://docs.python.org/3/whatsnew/3.13.html"
                }
            },
            "required": ["url"]
        }
    }
}


def read_webpage(url: str) -> str:
    """抓取网页并提取纯文本内容"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        # 尝试自动检测编码
        resp.encoding = resp.apparent_encoding or "utf-8"

        soup = BeautifulSoup(resp.text, "html.parser")

        # 移除无用标签
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # 提取文本
        text = soup.get_text(separator="\n", strip=True)

        # 压缩多余空行
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # 限制长度
        max_chars = 5000
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n...(内容过长，已截断，共 {len(text)} 字符)"

        return f"🌐 {url}\n\n{text}"

    except requests.Timeout:
        return f"⏱️ 请求超时: {url}"
    except requests.HTTPError as e:
        return f"❌ HTTP 错误 ({resp.status_code}): {url}"
    except requests.ConnectionError:
        return f"❌ 无法连接到: {url}"
    except Exception as e:
        return f"❌ 读取失败: {e}"
