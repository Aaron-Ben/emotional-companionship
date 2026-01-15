backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 应用入口
│   ├── config.py                  # 配置文件
│   ├── constants.py               # 常量定义
│   │
│   ├── api/                       # API 路由层
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py            # 对话相关接口
│   │   │   ├── user.py            # 用户相关接口
│   │   │   ├── memory.py          # 记忆相关接口
│   │   │   ├── emotion.py         # 情感相关接口
│   │   │   └── notification.py    # 通知相关接口
│   │   └── websocket.py           # WebSocket 处理
│   │
│   ├── core/                      # 核心模块
│   │   ├── __init__.py
│   │   ├── security.py            # 安全认证
│   │   ├── database.py            # 数据库连接
│   │   ├── cache.py               # Redis 缓存
│   │   └── llm_factory.py         # LLM 工厂模式
│   │
│   ├── services/                  # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── chat_service.py        # 对话服务（核心）
│   │   ├── memory_service.py      # 记忆管理服务
│   │   ├── emotion_service.py     # 情感识别服务
│   │   ├── user_service.py        # 用户管理服务
│   │   ├── llm_service.py         # LLM 集成服务
│   │   ├── embedding_service.py   # 向量嵌入服务
│   │   └── notification_service.py# 通知服务
│   │
│   ├── models/                    # 数据模型层
│   │   ├── __init__.py
│   │   ├── user.py                # 用户模型
│   │   ├── conversation.py        # 对话模型
│   │   ├── message.py             # 消息模型
│   │   ├── memory.py              # 记忆模型
│   │   ├── emotion.py             # 情感模型
│   │   └── notification.py        # 通知模型
│   │
│   ├── schemas/                   # Pydantic 模型（请求/响应）
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── message.py
│   │   ├── memory.py
│   │   └── emotion.py
│   │
│   ├── repositories/              # 数据访问层
│   │   ├── __init__.py
│   │   ├── user_repository.py
│   │   ├── conversation_repository.py
│   │   ├── message_repository.py
│   │   └── memory_repository.py
│   │
│   └── utils/                     # 工具函数
│       ├── __init__.py
│       ├── text_processing.py     # 文本处理
│       ├── time_utils.py          # 时间工具
│       └── logger.py              # 日志配置
│
├── migrations/                    # 数据库迁移
├── tests/                         # 测试用例
├── scripts/                       # 脚本文件
├── requirements.txt               # Python 依赖
└── .env.example                   # 环境变量示例