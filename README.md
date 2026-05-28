# 🤖 MyAgent

从零开始用 Python 构建的 LLM Agent，支持工具调用、跨会话记忆、多会话管理和对话压缩。用于学习Python，AI Agent与Vibe Coding -- 0行代码纯手写完成。

## ✨ 功能

- **11 个内置工具**：时间、天气、文件读写、网页搜索、命令行、Python 执行、记忆管理
- **🧠 跨会话记忆**：Agent 能记住你的偏好和重要信息，下次对话仍然记得
- **💬 多会话管理**：每个话题独立存档，随时切换继续聊
- **📦 对话压缩**：长对话自动总结旧消息，节省 tokens
- **🔒 安全执行**：命令行需手动确认，文件操作有沙箱限制
- **⚙️ 配置驱动**：改 YAML 不改代码，工具可按需开关

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置密钥

在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=你的API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
```

### 3. 运行

```bash
python v6_agent.py
```

## 🎮 命令一览

| 命令 | 作用 |
|------|------|
| `/help` | 显示帮助 |
| `/exit` | 保存并退出 |
| `/save [标题]` | 保存当前会话 |
| `/new [标题]` | 开始新会话 |
| `/sessions` | 查看所有会话 |
| `/load <ID>` | 加载指定会话 |
| `/delete <ID>` | 删除指定会话 |
| `/title <标题>` | 设置会话标题 |
| `/clear` | 清空当前会话 |
| `/clearall confirm` | 删除全部会话 |
| `/history [N]` | 查看对话历史 |
| `/remember 主题: 内容` | 保存记忆 |
| `/forget 主题` | 删除记忆 |
| `/memories` | 查看所有记忆 |

## 🛠️ 内置工具

| 工具 | 功能 |
|------|------|
| `get_current_time` | 获取当前时间 |
| `get_weather` | 查询城市天气 |
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件 |
| `web_search` | 关键词搜索 |
| `read_webpage` | 阅读网页全文 |
| `run_command` | 执行命令行（需确认） |
| `run_python` | 运行 Python 代码 |
| `save_memory` | 保存记忆 |
| `list_memories` | 列出记忆 |
| `delete_memory` | 删除记忆 |

## 📁 项目结构

```
MyAgent/
├── v6_agent.py              # 当前主程序
├── config.yaml              # 配置文件
├── requirements.txt         # 依赖
├── .env                     # API 密钥（不提交）
├── tools/                   # 工具包
│   ├── __init__.py
│   ├── time_tool.py
│   ├── weather_tool.py
│   ├── file_reader.py
│   ├── file_writer.py
│   ├── web_search.py
│   ├── web_reader.py
│   ├── shell_tool.py
│   ├── python_runner.py
│   └── memory_tool.py
├── examples/                # 各版本示例 + 学习笔记
│   ├── NOTES.md
│   ├── v1_single_chat.py
│   ├── v2_loop_chat.py
│   ├── v3_with_tools.py
│   ├── v4_agent.py
│   └── v5_agent.py
└── workspace/               # 运行时数据（不提交）
    ├── conversations/       # 会话存档
    └── memory.json          # 记忆数据
```

## 🔧 配置

编辑 `config.yaml` 调整行为：

```yaml
system_prompt: "..."      # 系统提示词
model:
  reasoning_effort: "max" # low / medium / max
tools:                    # 工具开关
  get_current_time: true
  ...
compression:              # 对话压缩
  enabled: true
  max_messages: 30
  keep_recent: 12
workspace_dir: "..."      # 工作目录
allowed_paths: [...]     # 允许访问的额外目录
```

## 📖 学习笔记

从 V1 到 V6 的完整演进过程记录在 [`examples/NOTES.md`](examples/NOTES.md)，包含每版本的改动、踩坑和经验总结。

## 📄 License

MIT
