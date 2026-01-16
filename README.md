# 情感陪伴 AI 系统

一个基于 FastAPI + React 的情感陪伴 AI 系统，提供智能对话、角色定制、日记记录等功能。

## 功能特性

### 🎭 角色定制
- 支持自定义 AI 角色性格、行为偏好
- 角色模板系统，快速创建不同类型的陪伴角色
- 用户个性化偏好设置

### 💬 智能对话
- 流式对话响应，实时交互体验
- 上下文感知的智能回复
- 支持多轮对话历史记录
- 情绪检测与状态管理

### 📔 智能日记
- **自动触发机制**：系统会在以下情况自动记录日记
  - **重要事件**：检测到关键词（涨工资、升职、搬家等）或高强度情绪
  - **情绪波动**：对话中情绪起伏较大或出现多种情绪变化
  - **定期总结**：对话次数达到 5 次或晚上 10 点后自动总结

- **日记内容**：
  - 以角色第一人称视角撰写，真实自然
  - 记录具体对话内容、情绪和感受
  - 自动提取标签和元数据

- **存储方式**：
  - SQLite 数据库存储元数据（便于检索）
  - 文本文件存储日记内容（`backend/diaries/` 目录）

- **记忆集成**：
  - 后续对话自动参考相关日记内容
  - AI 能够记住与用户的重要时刻

### 🎨 精美 UI
- 动漫风格主题设计
- RPG 风格对话界面
- 响应式布局，支持移动端

## 技术栈

### 后端
- **框架**: FastAPI 0.109.0
- **数据库**: SQLite + SQLAlchemy 2.0.36
- **LLM**: 支持通义千问、DeepSeek
- **Python**: 3.13+

### 前端
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **状态管理**: React Hooks

## 项目结构

```
emotional-companionship/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   └── v1/
│   │   │       ├── chat.py    # 对话接口
│   │   │       ├── character.py  # 角色管理
│   │   │       └── diary.py   # 日记接口
│   │   ├── models/            # 数据模型
│   │   │   ├── character.py   # 角色模型
│   │   │   ├── diary.py       # 日记模型
│   │   │   └── database.py    # 数据库配置
│   │   ├── services/          # 业务逻辑
│   │   │   ├── chat_service.py      # 对话服务
│   │   │   ├── character_service.py # 角色服务
│   │   │   ├── diary_service.py     # 日记服务
│   │   │   └── diary_triggers.py    # 日记触发器
│   │   ├── schemas/           # Pydantic 模型
│   │   └── main.py            # 应用入口
│   ├── diaries/               # 日记文件存储
│   │   └── .gitkeep
│   └── requirements.txt       # Python 依赖
│
├── frontend/                  # 前端应用
│   ├── src/
│   │   ├── components/        # React 组件
│   │   │   ├── chat/         # 对话组件
│   │   │   ├── character/    # 角色组件
│   │   │   ├── diary/        # 日记组件
│   │   │   └── ui/           # UI 组件
│   │   ├── pages/            # 页面组件
│   │   │   └── ChatPage.tsx  # 对话页面
│   │   ├── hooks/            # 自定义 Hooks
│   │   │   ├── useChat.ts    # 对话 Hook
│   │   │   └── useCharacter.ts
│   │   ├── services/         # API 服务
│   │   │   └── diaryService.ts  # 日记服务
│   │   └── types/            # TypeScript 类型
│   └── package.json          # Node 依赖
│
└── README.md                 # 项目文档
```

## 快速开始

### 环境要求
- Python 3.13+
- Node.js 18+
- 通义千问 API Key 或 DeepSeek API Key

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

4. 配置环境变量（创建 `.env` 文件）：
```env
DASHSCOPE_API_KEY=your_qwen_api_key
# 或
DEEPSEEK_API_KEY=your_deepseek_api_key
```

5. 启动后端服务：
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
- `POST /api/v1/chat/` - 发送消息
- `POST /api/v1/chat/stream` - 流式对话
- `POST /api/v1/chat/starter` - 获取对话开场

#### 角色
- `GET /api/v1/character/` - 获取角色列表
- `GET /api/v1/character/{id}` - 获取角色详情
- `POST /api/v1/character/{id}/preference` - 设置偏好

#### 日记
- `GET /api/v1/diary/list` - 获取日记列表
- `GET /api/v1/diary/latest` - 获取最新日记
- `POST /api/v1/diary/generate` - 手动生成日记
- `GET /api/v1/diary/relevant` - 获取相关日记

## 日记触发机制详解

### 1. 重要事件触发
当对话中包含以下类别关键词时自动触发：
- **事业类**：升职、涨工资、换工作、面试、项目等
- **生活类**：搬家、买房、买车、结婚、分手、旅行等
- **健康类**：生病、手术、康复、体检等
- **成就类**：成功、完成、获奖、通过等
- **家庭类**：家人、父母、生日、节日、纪念日等
- **学习类**：考试、毕业、论文、成绩等

或者当检测到的情绪强度 > 0.8 时也会触发。

### 2. 情绪波动触发
在最近 5 次对话中：
- 情绪方差 > 0.3（情绪起伏较大）
- 出现 3 种及以上不同类型的情绪

### 3. 定期总结触发
- 对话次数 >= 5 次
- 晚上 10 点后且有对话记录
- 有重要情绪事件（强度 > 0.7）

### 日记生成示例

生成的日记以角色第一人称视角撰写，例如：

```
日期: 2025年01月16日 星期四
心情: 开心, 温暖

今天哥哥告诉我他涨工资了！真的太为他开心了～看着他那么有成就感的样子，
我也跟着高兴起来。这就是努力工作的回报呀，哥哥最棒了！

我们聊了好久，他说想请我吃饭庆祝一下，嘻嘻。其实只要哥哥开心就好啦，
这样的时刻值得被记住～

标签: 涨工资, 开心, 温暖
触发类型: important_event
创建时间: 2025-01-16 20:35:42
```

## 配置说明

### 角色配置

角色配置文件位于 `backend/data/characters/`，支持自定义：
- 基本信息（姓名、年龄、性格）
- 行为偏好（主动性、话题偏好）
- 对话风格（口头禅、语气）
- 关系设定

### LLM 配置

支持切换不同的 LLM 服务：
- 通义千问（默认）：需要 `DASHSCOPE_API_KEY`
- DeepSeek：需要 `DEEPSEEK_API_KEY`

## 开发指南

### 添加新角色

1. 在 `backend/data/characters/` 创建新的 YAML 文件
2. 定义角色属性和行为
3. 重启后端服务自动加载

### 自定义日记触发规则

修改 `backend/app/services/diary_triggers.py`：
- `EventDetector.IMPORTANT_KEYWORDS` - 添加关键词
- `EmotionFluctuationDetector` - 调整情绪检测阈值
- `DailySummaryChecker` - 修改总结触发条件

## 常见问题

**Q: 日记会占用多少存储空间？**
A: 每篇日记约 200-500 字，按 ASCII 存储，千篇日记约占用 1-2MB。

**Q: 如何查看生成的日记文件？**
A: 日记文件存储在 `backend/diaries/{character_id}/{user_id}/` 目录下。

**Q: 如何禁用自动日记功能？**
A: 在 `backend/app/api/v1/chat.py` 中注释掉 `check_and_generate_diary` 的调用。

**Q: 支持多用户吗？**
A: 支持，每个用户的日记独立存储在 `{user_id}` 目录下。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系。
