# AI 日记 API 使用说明

## 概述

新增的 AI 日记 API 让 AI 主动创建和更新日记，类似 VCPToolBox DailyNote 插件功能。

## 新增 API 端点

### 1. POST /api/v1/diary/ai-create - AI 创建日记

允许 AI 根据提供的参数创建新日记。

**请求示例：**

```json
{
    "character_id": "sister_001",
    "date": "2025-01-23",
    "content": "今天哥哥陪我玩了一整天，我们去了公园，看到了好多花。哥哥还给我买了冰淇淋，是草莓味的，好甜！",
    "category": "emotional",
    "tag": "开心, 约会, 温暖"
}
```

或者将标签放在内容末尾：

```json
{
    "character_id": "sister_001",
    "date": "2025-01-23",
    "content": "今天哥哥陪我玩了一整天，我们去了公园，看到了好多花。哥哥还给我买了冰淇淋，是草莓味的，好甜！\n\nTag: 开心, 约会, 温暖",
    "category": "emotional"
}
```

**参数说明：**
- `character_id` (必填): 角色ID
- `date` (必填): 日记日期，格式 YYYY-MM-DD
- `content` (必填): 日记内容，支持在末尾添加 `Tag: xxx, xxx`
- `category` (可选): 日记分类，默认 `topic`
  - 可选值: `knowledge`, `topic`, `emotional`, `milestone`
- `tag` (可选): 独立标签字段，如果提供会覆盖 content 中的 Tag 行

**响应示例：**

```json
{
    "diary": {
        "id": "diary_sister_001_user_default_20250123_143052_123456",
        "character_id": "sister_001",
        "user_id": "user_default",
        "date": "2025-01-23",
        "content": "今天哥哥陪我玩了一整天，我们去了公园，看到了好多花。哥哥还给我买了冰淇淋，是草莓味的，好甜！\n\nTag: 开心, 约会, 温暖",
        "category": "emotional",
        "emotions": ["开心", "温暖"],
        "tags": ["开心", "约会", "温暖"],
        "created_at": "2025-01-23T14:30:52.123456",
        "updated_at": null
    },
    "message": "日记创建成功"
}
```

### 2. POST /api/v1/diary/ai-update - AI 更新日记

通过查找和替换内容来更新日记，类似 VCPToolBox 的 update 命令。

**请求示例：**

```json
{
    "target": "哥哥还给我买了冰淇淋，是草莓味的，好甜！",
    "replace": "哥哥还给我买了冰淇淋，是巧克力味的，特别浓郁！",
    "character_id": "sister_001"
}
```

**参数说明：**
- `target` (必填): 要查找和替换的旧内容，至少 15 个字符
- `replace` (必填): 替换的新内容
- `character_id` (可选): 角色ID，用于指定搜索范围，如果未指定则搜索所有角色的日记

**响应示例：**

```json
{
    "message": "Successfully edited diary file: diary_sister_001_user_default_20250123_143052_123456",
    "diary_id": "diary_sister_001_user_default_20250123_143052_123456",
    "old_content": "哥哥还给我买了冰淇淋，是草莓味的，好甜！",
    "new_content": "哥哥还给我买了冰淇淋，是巧克力味的，特别浓郁！"
}
```

**错误响应（未找到匹配内容）：**

```json
{
    "detail": "Target content not found in any diary files."
}
```

## 与 VCPToolBox DailyNote 的对比

| 功能 | VCPToolBox DailyNote | Emotional Companionship |
|------|---------------------|------------------------|
| 创建方式 | 文件系统 | SQLite 数据库 |
| 标签处理 | Content 末尾或独立 Tag 参数 | 相同 |
| 更新方式 | 查找替换文件内容 | 查找替换数据库记录 |
| 安全检查 | 路径穿越、target 最小长度 | target 最小长度 (15 字符) |
| 角色隔离 | 文件夹分类 | character_id 字段 |

## 使用场景

### 1. AI 主动记录重要事件

当 AI 判断对话中包含值得记录的内容时，可以调用 `ai-create` 创建日记：

```
系统提示：今天的对话很重要，需要记录日记
AI 调用：POST /api/v1/diary/ai-create
{
    "character_id": "sister_001",
    "date": "2025-01-23",
    "content": "今天哥哥跟我说他涨工资了，看到他那么开心我也好高兴...",
    "category": "milestone",
    "tag": "涨工资, 开心, 重要"
}
```

### 2. AI 修正之前的日记

当 AI 发现之前的日记有错误时，可以调用 `ai-update` 修正：

```
系统提示：之前的日记记录有误
AI 调用：POST /api/v1/diary/ai-update
{
    "target": "哥哥去了北京出差",
    "replace": "哥哥去了上海出差",
    "character_id": "sister_001"
}
```

### 3. AI 追加补充信息

当 AI 想要给已有日记添加更多细节时：

```
AI 调用：POST /api/v1/diary/ai-update
{
    "target": "我们去了公园",
    "replace": "我们去了朝阳公园，天气特别好，阳光明媚",
    "character_id": "sister_001"
}
```

## API 测试

可以使用 Swagger UI 测试这些端点：

1. 启动后端服务
2. 访问 http://localhost:8000/docs
3. 找到 `/api/v1/diary/ai-create` 和 `/api/v1/diary/ai-update` 端点进行测试
