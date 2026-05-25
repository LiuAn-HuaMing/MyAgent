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

## V4：配置化 + 文件工具 (`v4_agent.py`)

**目标：** 代码与配置分离，Agent 能读写真实文件。

**V3 → V4 关键改动：**
- `config.yaml`：system prompt、工具开关、模型参数全外置
- 文件读写工具：`read_file`、`write_file`
- `tools/__init__.py` 支持从 config.yaml 动态加载工具
- `workspace/` 作为 Agent 的文件操作目录

**学到的东西：**
- 配置与代码分离是正规项目的基础
- 文件工具让 Agent 有实际生产力
- `pyyaml` 读取 YAML 配置

**核心代码量：** ~150 行（主文件）+ 配置文件

---

## 项目结构演进

```
V1-V2:          V3:                  V4:
MyAgent/        MyAgent/             MyAgent/
├── .env        ├── .env             ├── .env
├── v1_*.py     ├── v3_*.py          ├── config.yaml 🆕
├── v2_*.py     └── tools/           ├── v4_agent.py
                   ├── __init__.py    ├── examples/
                   ├── calculator.py  │   ├── v1_*.py
                   ├── weather.py     │   ├── v2_*.py
                   └── time_tool.py   │   └── v3_*.py
                                      ├── tools/
                                      │   ├── __init__.py
                                      │   ├── calculator.py
                                      │   ├── time_tool.py
                                      │   ├── file_reader.py
                                      │   └── file_writer.py
                                      └── workspace/
```

---

## 核心技术概念总结

| 概念 | 实现方式 |
|------|----------|
| **记忆** | `messages` 列表，每轮追加 user + assistant |
| **工具** | Python 函数 + JSON Schema 描述 |
| **推理** | `reasoning_effort` + thinking mode |
| **配置** | YAML 文件，改行为不改代码 |
| **安全** | `.env` 存密钥，`.gitignore` 防泄露 |
