# MyAgent 学习笔记

> 从零开始，用 Python 构建一个 LLM Agent 的完整过程。

---

## V1：单次对话 (`examples/v1_single_chat.py`)

**目标：** 跑通 DeepSeek API，理解最基本的"发消息→收回复"。

**学到的东西：**
- `OpenAI(...)` 创建客户端，DeepSeek 兼容 OpenAI 格式
- `client.chat.completions.create()` 是真正发 HTTP 请求的方法
- `messages` 列表里每条消息有 `role`（user/assistant/system）和 `content`
- `response.choices[0].message.content` 提取回复文本
- `temperature` 控制随机性
- `.env` 管理密钥，`python-dotenv` 加载配置

**核心代码量：** ~25 行

---

## V2：循环多轮对话 (`examples/v2_loop_chat.py`)

**目标：** 像网页版一样持续聊天，能记住上下文。

**V1 → V2 关键改动：**
- `while True` 循环替代一次性执行
- `messages` 列表存全部历史（system + user + assistant），每次全量发送
- 这就是"记忆"的最简单形态——一个不断增长的 Python 列表
- 加了 `/exit`、`/clear`、`/help` 系统命令
- 流式输出 + 思考过程实时显示（`stream=True`）
- Token 估算统计（中文字符 × 0.6，英文 × 0.3）

**学到的东西：**
- 对话记忆 = 把历史消息存在列表里，每次全发
- DeepSeek 前缀缓存让长对话不会太贵
- 流式输出改善等待体验
- f-string 比 `+` 拼接更安全

**核心代码量：** ~90 行

---

## V3：工具调用 (`examples/v3_with_tools.py`)

**目标：** Agent 不仅能聊天，还能"做事"——调计算器、查时间。

**V2 → V3 关键改动：**
- `tools/` 包：每个工具一个文件（函数 + JSON Schema 描述）
- `tools/__init__.py` 注册中心，统一管理 TOOL_FUNCTIONS 和 TOOL_DESCRIPTIONS
- API 调用加 `tools=TOOL_DESCRIPTIONS` 参数
- 非流式调用检查 `msg.tool_calls`，有则执行工具
- 工具调用和结果用 `role: "assistant"` + `role: "tool"` 加入历史
- `while True` 循环处理多次工具调用

**踩过的坑：**
- `^` 在 Python 里是异或，需要转成 `**`（幂运算）
- DeepSeek 思考模式下 `reasoning_content` 必须传回，否则 400 错误
- 模型可能连续调多次工具，需要循环处理

**核心代码量：** ~140 行

---

## V4：配置化 + 工具生态 (`examples/v4_agent.py`)

**目标：** 代码与配置分离，Agent 能读写文件、联网搜索、执行代码。

**V3 → V4 关键改动：**
- `config.yaml`：system prompt、工具开关、模型参数全外置
- 文件沙箱：`write_file` 限定在 `workspace_dir` + `allowed_paths` 内，`read_file` 全开放
- 命令行工具：`run_command`，展示命令 + 说明 + 输入 `confirm` 才执行
- 联网搜索：`web_search`（Bing 抓取）+ `read_webpage`（网页全文阅读）
- 天气查询：`get_weather`（wttr.in 真实数据）
- Python 执行：`run_python`（子进程沙箱，15s 超时），替代了旧 calculator
- IN/OUT 着色：绿色输入、红色输出（colorama）
- 双重思考修复：无工具时直接用非流式结果，省一次 API 调用

**踩过的坑：**
- DuckDuckGo 国内不可用，改用 Bing 抓取
- API vs 本地函数都是"接口约定"（DESCRIPTION 就是菜单）
- 推理模式下 `temperature` 无效，只认 `reasoning_effort`
- 确认词用 `confirm` 而非简单 `y`，防止误触

**核心代码量：** ~180 行

---

## V5：记忆系统 (`v5_agent.py`)  🆕

**目标：** Agent 跨会话记住用户偏好和重要信息。

**V4 → V5 关键改动：**
- `memory.json` 持久化存储（workspace 目录）
- 三个记忆工具：`save_memory`、`list_memories`、`delete_memory`
- 启动时加载记忆，注入 system prompt："关于用户，你知道：..."
- 手动记忆：`/remember 主题: 内容`、`/forget 主题`、`/memories`
- 自动记忆：Agent 在对话中学到重要信息时主动保存
- `/clear` 只清对话历史，不删记忆

**学到的东西：**
- 记忆 ≠ 对话历史。记忆是跨会话的，对话历史是本次的
- system prompt 注入是让 Agent "知道"记忆的最简单方式
- Agent 判断"该不该记"需要 system prompt 约束（不记琐碎测试）
- JSON 文件作轻量级数据库够用

**核心代码量：** ~190 行

---

## 项目结构演进

```
V4:                           V5:
MyAgent/                      MyAgent/
├── .env                      ├── .env
├── config.yaml               ├── config.yaml
├── v4_agent.py  (→examples)  ├── v5_agent.py        ← 当前主文件
├── examples/                 ├── examples/
│   ├── v1_single_chat.py     │   ├── v1_single_chat.py
│   ├── v2_loop_chat.py       │   ├── v2_loop_chat.py
│   ├── v3_with_tools.py      │   ├── v3_with_tools.py
│   ├── v4_agent.py           │   └── v4_agent.py
│   └── NOTES.md              │   └── NOTES.md
├── tools/                    ├── tools/
│   ├── __init__.py           │   ├── __init__.py
│   ├── time_tool.py          │   ├── time_tool.py
│   ├── file_reader.py        │   ├── weather_tool.py
│   ├── file_writer.py        │   ├── file_reader.py
│   ├── web_search.py         │   ├── file_writer.py
│   ├── web_reader.py         │   ├── web_search.py
│   ├── shell_tool.py         │   ├── web_reader.py
│   └── python_runner.py      │   ├── shell_tool.py
├── workspace/                │   ├── python_runner.py
    └── (Agent 的文件)        │   └── memory_tool.py  🆕
                              └── workspace/
                                  ├── memory.json     🆕
                                  └── (Agent 的文件)
```

---

## 工具进化史

| 版本 | 工具数 | 工具列表 |
|------|:---:|------|
| V3 | 2 | calculator, get_current_time |
| V4 | 8 | get_current_time, get_weather, read_file, write_file, web_search, read_webpage, run_command, run_python |
| V5 | 11 | V4的8个 + save_memory, list_memories, delete_memory |

---

## 核心技术概念总结

| 概念 | 实现方式 | 版本 |
|------|----------|:---:|
| **对话记忆** | `messages` 列表，每轮追加 | V2 |
| **工具调用** | Python 函数 + JSON Schema 描述 | V3 |
| **推理模式** | `reasoning_effort` + thinking mode | V3 |
| **配置分离** | YAML 文件，改行为不改代码 | V4 |
| **文件沙箱** | 写入白名单目录，读取全开放 | V4 |
| **联网搜索** | Bing HTML 抓取 + 网页全文 | V4 |
| **命令安全** | 展示 + 说明 + `confirm` 确认 | V4 |
| **代码执行** | 子进程沙箱 + 15s 超时 | V4 |
| **跨会话记忆** | JSON 文件 + system prompt 注入 | V5 |
| **安全** | `.env` 存密钥，`.gitignore` 防泄露 | V1 |
