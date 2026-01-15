frontend/
├── src/
│   ├── __init__.py
│   ├── main.tsx                   # 应用入口
│   ├── App.tsx                    # 根组件
│   ├── vite.config.ts             # Vite 配置
│   │
│   ├── assets/                    # 静态资源
│   │   ├── images/
│   │   └── icons/
│   │
│   ├── components/                # 公共组件
│   │   ├── __init__.py
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx
│   │   │   └── Loading.tsx
│   │   └── layout/
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       └── Footer.tsx
│   │
│   ├── features/                  # 功能模块组件
│   │   ├── chat/                  # 对话模块
│   │   │   ├── ChatWindow.tsx     # 对话窗口
│   │   │   ├── ChatInput.tsx      # 输入框
│   │   │   ├── MessageBubble.tsx  # 消息气泡
│   │   │   ├── MessageList.tsx    # 消息列表
│   │   │   └── TypingIndicator.tsx# 打字指示器
│   │   │
│   │   ├── memory/                # 记忆模块
│   │   │   ├── MemoryCard.tsx     # 记忆卡片
│   │   │   ├── MemoryTimeline.tsx # 记忆时间线
│   │   │   └── MemoryForm.tsx     # 记忆表单
│   │   │
│   │   ├── emotion/               # 情感模块
│   │   │   ├── EmotionBadge.tsx   # 情感标签
│   │   │   ├── EmotionChart.tsx   # 情感图表
│   │   │   └── EmotionIndicator.tsx# 情感指示器
│   │   │
│   │   ├── profile/               # 个人中心
│   │   │   ├── Avatar.tsx         # 头像
│   │   │   ├── Settings.tsx       # 设置
│   │   │   └── Personality.tsx    # 个性设置
│   │   │
│   │   └── notification/          # 通知模块
│   │       ├── NotificationItem.tsx
│   │       └── NotificationList.tsx
│   │
│   ├── pages/                     # 页面组件
│   │   ├── __init__.py
│   │   ├── Home.tsx               # 首页
│   │   ├── Chat.tsx               # 对话页
│   │   ├── Memory.tsx             # 记忆页
│   │   ├── Profile.tsx            # 个人中心
│   │   └── Settings.tsx           # 设置页
│   │
│   ├── hooks/                     # 自定义 Hooks
│   │   ├── __init__.py
│   │   ├── useChat.ts             # 对话相关
│   │   ├── useMemory.ts           # 记忆相关
│   │   ├── useEmotion.ts          # 情感相关
│   │   ├── useWebSocket.ts        # WebSocket
│   │   └── useLocalStorage.ts     # 本地存储
│   │
│   ├── services/                  # API 服务
│   │   ├── __init__.py
│   │   ├── api.ts                 # API 基础配置
│   │   ├── chatService.ts         # 对话服务
│   │   ├── userService.ts         # 用户服务
│   │   ├── memoryService.ts       # 记忆服务
│   │   ├── emotionService.ts      # 情感服务
│   │   └── websocketService.ts    # WebSocket 服务
│   │
│   ├── stores/                    # 状态管理
│   │   ├── __init__.py
│   │   ├── chatStore.ts           # 对话状态
│   │   ├── userStore.ts           # 用户状态
│   │   ├── memoryStore.ts         # 记忆状态
│   │   └── emotionStore.ts        # 情感状态
│   │
│   ├── types/                     # TypeScript 类型定义
│   │   ├── __init__.py
│   │   ├── user.ts
│   │   ├── message.ts
│   │   ├── conversation.ts
│   │   ├── memory.ts
│   │   └── emotion.ts
│   │
│   ├── utils/                     # 工具函数
│   │   ├── __init__.py
│   │   ├── format.ts              # 格式化工具
│   │   ├── validate.ts            # 验证工具
│   │   └── constants.ts           # 常量
│   │
│   └── styles/                    # 全局样式
│       ├── main.css               # 主样式文件
│       └── tailwind.css           # Tailwind 入口
│
├── tailwind.config.js             # Tailwind 配置
├── tsconfig.json                  # TypeScript 配置
└── package.json                   # 依赖配置