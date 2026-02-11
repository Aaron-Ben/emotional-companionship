# 情感陪伴 AI 系统

一个基于 FastAPI + React 的情感陪伴 AI 系统，提供智能对话、角色定制、日记记录、工具调用等功能。

## 功能特性

### 💬 双模式对话
- **RPG 风格对话**：沉浸式角色扮演体验
- **传统聊天模式**：经典消息列表界面
- **流式响应**：实时交互体验
- **语音输入**：支持中英日韩粤语识别
- **语音合成**：TTS 语音输出

### 🎭 角色定制
- 支持自定义 AI 角色性格、行为偏好
- 角色模板系统，快速创建不同类型的陪伴角色
- 用户个性化偏好设置

### 🔧 工具调用系统 (VCPToolBox 模式)
- **插件化架构**：模块化扩展功能，支持多种协议
  - **stdio 协议**：通过子进程执行外部插件（如 DeepMemo Rust 插件）
  - **direct 协议**：直接调用 Python 插件（如 RAG 日记检索）
- **自动工具检测**：AI 响应中的工具调用标记自动检测和执行
- **工具调用格式**：`<<<[TOOL_REQUEST]>>>...<<<[END_TOOL_REQUEST]>>>`
- **工具结果注入**：执行结果自动注入下一轮对话

### 内置插件
1. **DeepMemo（深度回忆）**
   - 基于向量数据库的语义检索
   - 支持时间范围查询（如"三天前"、"上周"）
   - 智能标签关联和上下文理解

2. **RAGDailyPlugin（日记检索）**
   - 基于用户日记的 RAG 检索
   - 支持时间表达式解析
   - 自动分块处理长文本

### 📝 智能日记
- **AI 自动触发**：每次对话后 AI 自动评估是否值得记录
  - 智能判断对话重要性
  - 只记录有意义的对话内容
- **智能提取**：
  - 从对话中提取结构化日记内容
  - 自动生成对话主题、关键信息、感受
  - 自动添加相关标签
- **日记管理**：
  - 基于文件系统存储
  - 支持创建、更新、删除日记
  - AI 可以主动修正和补充已有日记
- **记忆集成**：
  - 后续对话自动参考相关日记内容
  - AI 能够记住与用户的重要时刻

### 📊 日志系统
- **文件日志记录**：所有对话和工具调用自动记录到文件
- **按日期归档**：
  - 当天日志：`data/logs/today.txt`
  - 历史日志：`data/logs/YYYY-MM-DD.txt`
- **实时写入**：日志实时刷新，方便查看
- **日志 API**：
  - `GET /api/v1/chat/logs/today` - 获取今日日志
  - `GET /api/v1/chat/logs/list` - 列出所有日志文件
  - `GET /api/v1/chat/logs/{date}` - 获取指定日期日志

### 🎨 精美 UI
- 动漫风格主题设计
- RPG 风格对话界面
- 响应式布局，支持移动端

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: SQLite + SQLAlchemy 2.0
- **LLM & Embedding**: OpenRouter
- **插件系统**: 自定义插件管理器，支持 stdio/direct 协议
- **语音识别**: Sherpa-ONNX SenseVoice
- **语音合成**: Genie-TTS (GPT-SoVITS)
- **Python**: 3.13+

### 前端
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **状态管理**: React Hooks

## 项目结构

```
emotional-companionship/
├── backend/                      # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   └── v1/
│   │   │       ├── chat.py          # 对话接口（含日志端点）
│   │   │       ├── character.py     # 角色管理
│   │   │       ├── diary.py         # 日记接口
│   │   │       └── chat_history.py  # 对话历史接口
│   │   ├── config/            # 配置模块
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic 模型
│   │   ├── services/          # 业务逻辑
│   │   │   ├── chat_service.py         # 对话服务（含工具调用）
│   │   │   ├── character_service.py    # 角色服务
│   │   │   ├── llm.py                # LLM 服务（含超时配置）
│   │   │   ├── chat_history_service.py  # 对话历史服务
│   │   │   └── diary/                # 日记服务
│   │   ├── utils/            # 工具模块
│   │   │   ├── file_logger.py         # 文件日志记录
│   │   │   └── json.py               # JSON 工具
│   │   └── characters/       # 角色模块
│   │       ├── asr.py          # 语音识别
│   │       └── tts.py          # 语音合成
│   ├── plugins/           # 插件系统
│   │   ├── plugin.py              # 插件管理器
│   │   ├── tool_call_parser.py   # 工具调用解析器
│   │   ├── tool_executor.py      # 工具执行器
│   │   ├── deepmemo/            # DeepMemo 插件（Rust）
│   │   └── rag_daily/           # RAG 日记检索插件
│   ├── resources/        # 资源文件
│   │   ├── characters/     # 角色配置
│   │   │   ├── sister.yaml      # 基础角色
│   │   │   └── sister_v2.yaml  # 扩展角色示例
│   │   └── archetypes/     # 角色模板
│   │       ├── emotional_companion.yaml
│   │       ├── mentor.yaml
│   │       └── friend.yaml
│   └── main.py           # 应用入口
│
├── frontend/                  # 前端应用
│   └── src/
│       ├── components/      # React 组件
│       ├── pages/         # 页面组件
│       ├── hooks/         # 自定义 Hooks
│       ├── services/       # API 服务
│       └── types/         # TypeScript 类型
│
├── data/                  # 数据目录
│   ├── chat/           # 对话历史
│   ├── diary/          # 日记存储
│   └── logs/           # 日志文件（today.txt + YYYY-MM-DD.txt）
│
└── README.md            # 项目文档
```

## 快速开始

### 环境要求
- Python 3.13+
- Node.js 18+
- OpenRouter API Key

### 后端设置

1. 进入后端目录：
```bash
cd backend
```

2. 创建虚拟环境：
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置环境变量（复制 `.env.example` 到 `.env` 并填入你的 API Key）：
```env
# OpenRouter API Key (必需)
OPENROUTER_API_KEY=sk-or-v1-xxxxx

# API 配置
API_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=deepseek/deepseek-v3.2
EmbeddingModel=baai/bge-m3
```

5. 运行数据库迁移：
```bash
python migrate_extensions.py
```

6. 启动后端服务：
```bash
python -m uvicorn app.main:app --reload
```

后端将运行在 `http://localhost:8000`

### 前端设置

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 配置 API 地址（创建 `.env` 文件）：
```env
VITE_API_URL=http://localhost:8000
```

4. 启动开发服务器：
```bash
npm run dev
```

前端将运行在 `http://localhost:5173`

## API 文档

启动后端后，访问以下地址查看 API 文档：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 核心 API 端点

#### 对话
- `POST /api/v1/chat/` - 发送消息（流式响应）
- `POST /api/v1/chat/stream` - SSE 流式对话
- `POST /api/v1/chat/voice` - 语音识别
- `POST /api/v1/chat/tts` - 文字转语音
- `GET /api/v1/chat/tts/audio/{filename}` - 获取生成的语音文件
- `GET /api/v1/chat/logs/today` - 获取今日日志
- `GET /api/v1/chat/logs/list` - 列出所有日志文件
- `GET /api/v1/chat/logs/{date}` - 获取指定日期日志

#### 角色
- `GET /api/v1/character/` - 获取角色列表
- `GET /api/v1/character/{id}` - 获取角色详情
- `PUT /api/v1/character/preferences` - 更新用户偏好
- `GET /api/v1/character/preferences` - 获取用户偏好

#### 日记
- `GET /api/v1/diary/list` - 获取日记列表
- `GET /api/v1/diary/latest` - 获取最新日记
- `GET /api/v1/diary/names` - 获取日记本名称列表
- `POST /api/v1/diary/create` - 创建日记
- `POST /api/v1/diary/ai-update` - AI 更新日记（查找替换）
- `DELETE /api/v1/diary/{path}` - 删除日记

#### 对话历史
- `POST /api/v1/chat_history/topics` - 创建新的对话历史
- `GET /api/v1/chat_history/topic/{topic_id}` - 获取特定对话历史
- `PUT /api/v1/chat_history/topic/{topic_id}` - 更新对话历史
- `DELETE /api/v1/chat_history/topic/{topic_id}` - 删除对话历史
- `GET /api/v1/chat_history/topics` - 获取所有对话历史

## 工具调用开发指南

### 工具调用格式

AI 需要使用工具时，按以下格式输出：

```
<<<[TOOL_REQUEST]>>>
tool_name:「始」插件名「末」,
参数1:「始」值1「末」,
参数2:「始」值2「末」
<<<[END_TOOL_REQUEST]>>>
```

### 插件清单

当前可用的插件：

| 插件名 | 协议 | 功能 | 配置 |
|---------|--------|------|------|
| DeepMemo | stdio | 向量语义检索 | `plugins/deepmemo/config.env` |
| RAGDailyPlugin | direct | 日记 RAG 检索 | `plugins/rag_daily/config.env` |

### 创建新插件

1. **Stdio 协议插件**（如 Rust/Go 实现）：
   - 创建插件目录：`plugins/your_plugin/`
   - 创建 `plugin-manifest.json`：
     ```json
     {
       "name": "YourPlugin",
       "displayName": "你的插件",
       "version": "1.0.0",
       "communication": {
         "protocol": "stdio",
         "timeout": 60000
       },
       "entryPoint": {
         "command": "./target/release/your_plugin"
       }
     }
     ```
   - 可选：创建 `config.env` 配置文件

2. **Direct 协议插件**（Python 实现）：
   - 创建插件目录：`plugins/your_plugin/`
   - 创建 `plugin-manifest.json`：
     ```json
     {
       "name": "YourPlugin",
       "displayName": "你的插件",
       "version": "1.0.0",
       "communication": {
         "protocol": "direct"
       },
       "entryPoint": {
         "script": "main.py"
       },
       "capabilities": {
         "invocationCommands": [
           {
             "command": "ToolName",
             "description": "工具描述",
             "example": "{\"param\": \"value\"}"
           }
         ]
       }
     }
     ```
   - 实现 `main.py`：
     ```python
     async def initialize(config, dependencies):
         # 初始化逻辑
         pass

     async def process_tool_call(args):
         # 工具调用处理
         return {"status": "success", "result": "..."}
     ```

## 配置说明

### 环境变量 (.env)

| 变量 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `OPENROUTER_API_KEY` | OpenRouter API Key (LLM + Embedding) | - | ✅ |
| `API_URL` | OpenRouter API 地址 | `https://openrouter.ai/api/v1` | ❌ |
| `OPENROUTER_MODEL` | LLM 模型名称 | `anthropic/claude-3.5-sonnet` | ❌ |

### 角色配置

角色配置文件位于 `backend/app/resources/characters/`：
- **基础角色**：传统配置，无需修改即可运行
- **扩展角色**：添加扩展功能配置，启用高级特性

### 角色模板

预设模板位于 `backend/app/resources/archetypes/`：
- **emotional_companion**：情感陪伴者，注重情感连接
- **mentor**：导师，注重指导和知识分享
- **friend**：朋友，轻松平等的交流

### 添加新角色

1. 在 `backend/app/resources/characters/` 创建新的 YAML 文件
2. 从模板复制或从头定义
3. 可选：添加扩展功能配置
4. 重启后端服务自动加载

## 日志说明

日志文件位于 `data/logs/` 目录：

- **today.txt**：当天的日志（实时追加）
- **YYYY-MM-DD.txt**：历史日志（自动归档）

日志内容包括：
- 对话信息
- 工具调用检测和执行
- 插件执行结果
- 错误和异常信息

查看日志示例：
```bash
# 查看今天的日志
curl http://localhost:8000/api/v1/chat/logs/today

# 列出所有日志
curl http://localhost:8000/api/v1/chat/logs/list
```
