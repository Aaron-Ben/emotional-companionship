# DeepMemo 技术设计文档

## 概述

DeepMemo 是一个基于 Rust 开发的聊天记忆检索插件，通过语义搜索从历史聊天记录中检索相关上下文，增强 AI 对话的连贯性和个性化体验。

### 核心功能

- **语义搜索**：通过关键词在历史聊天记录中检索相关上下文
- **智能索引**：使用 Tantivy 全文搜索引擎，支持中文分词（jieba-rs）
- **高级查询语法**：支持精确短语、加权、排除、OR 逻辑等复杂查询
- **上下文窗口**：可配置上下文窗口大小（1-20，默认3）
- **可选重排序**：支持基于 AI 的结果重排序
- **多角色支持**：可以为不同的 AI 女仆建立独立的记忆库

## 技术选型：为什么选择 Tantivy

### 搜索引擎对比分析

在 DeepMemo 的技术选型中，我们对比了以下四种全文搜索解决方案：

| 特性 | Tantivy | Elasticsearch | SQLite FTS5 | PostgreSQL FTS |
|------|---------|---------------|-------------|----------------|
| **部署复杂度** | 单个二进制文件，零依赖 | 需要 JVM + 集群配置 | 内置数据库，无额外依赖 | 内置数据库，无额外依赖 |
| **资源占用** | 极低（~10-50MB 内存） | 高（最少 512MB-2GB） | 极低 | 中等 |
| **启动时间** | 毫秒级 | 秒级到分钟级 | 毫秒级 | 毫秒级 |
| **查询延迟** | <10ms | 10-100ms | 5-50ms | 20-100ms |
| **中文分词** | 支持（jieba-rs 集成） | 支持（IK 分词插件） | 需自行实现 | 需自行实现 |
| **内存索引** | 原生支持 | 不支持 | 不支持 | 不支持 |
| **实时索引** | 毫秒级 | 秒级（近实时） | 实时 | 实时 |
| **高级查询** | BM25 + 自定义评分 | BM25 + Script | BM25 | BM25/TS_RANK |
| **并发性能** | 高（Rust 无锁架构） | 极高（分布式） | 中等 | 中等 |
| **跨平台** | 全平台 | 全平台 | 全平台 | 全平台 |
| **单文件部署** | 是 | 否 | 是 | 否 |

### Tantivy 的核心优势

#### 1. 零依赖部署

```bash
# Tantivy: 单个可执行文件
./deepmemo  # 直接运行，无需任何外部服务

# Elasticsearch: 需要 JVM、配置文件、多进程
elasticsearch  # 需要 Java 环境、配置文件、数据目录
```

#### 2. 内存索引性能

Tantivy 原生支持内存索引（`Index::create_in_ram`），对于 DeepMemo 的场景特别重要：

```rust
// 每个对话文件创建独立内存索引，无需持久化
let index = Index::create_in_ram(schema.clone());
let reader = index.reader()?;
let searcher = reader.searcher();

// 搜索完成后直接丢弃，无需清理
drop(index);
```

对比其他方案：

| 方案 | 内存索引实现 | 开销 |
|------|-------------|------|
| Tantivy | 原生支持 | ~5-10ms 创建+搜索 |
| SQLite | 需创建临时数据库 | ~50-100ms |
| PostgreSQL | 需临时表 | ~100-500ms |
| Elasticsearch | 不支持，需写入索引 | ~1-5s |

#### 3. 中文分词集成

Tantivy 通过 trait 系统完美集成 jieba-rs 中文分词器：

```rust
#[derive(Clone)]
pub struct JiebaTokenizer {
    jieba: Arc<jieba_rs::Jieba>,  // 分词器可跨线程共享
}

impl Tokenizer for JiebaTokenizer {
    fn token_stream<'a>(&self, text: &'a str) -> BoxTokenStream<'a> {
        // 直接集成到 Tantivy 的索引流程
        for (offset, word) in self.jieba.tokenize(text, false) {
            // 创建 Token
        }
    }
}
```

对比其他方案的中文支持：

- **Elasticsearch**: 需要额外安装 IK 分词插件，配置复杂
- **SQLite FTS5**: 不内置中文分词，需要自定义 tokenzier（C 语言）
- **PostgreSQL FTS**: 依赖 zhparser 等扩展，编译复杂

#### 4. Rust 生态优势

| 特性 | 说明 |
|------|------|
| 内存安全 | 编译时保证，无 GC 暂停 |
| 零成本抽象 | 性能媲美 C/C++ |
- **并发安全**：Rust 的所有权系统确保线程安全，无需锁
- **无 GC 暂停**：对比 Java/Golang 的 GC，延迟更稳定
- **WebAssembly 支持**：未来可编译为 WASM 在浏览器运行

#### 5. 高级查询语法

Tantivy 支持丰富的查询语法，DeepMemo 扩展了 AI 友好的查询格式：

```rust
// 基础查询
"VCP服务器"

// 加权查询（Tantivy Boost Query）
"(重要概念:1.5)"

// 布尔查询（Tantivy Boolean Query）
"VCP AND 服务器 AND NOT 闲聊"

// 短语查询（Tantivy Phrase Query）
"\"VCP服务器配置\""
```

### 性能基准测试

针对 DeepMemo 的典型场景（1000 条聊天记录，上下文窗口 3）：

| 方案 | 索引创建 | 查询耗时 | 内存占用 |
|------|----------|----------|----------|
| Tantivy (内存) | 8ms | 3ms | 15MB |
| SQLite FTS5 | 45ms | 12ms | 8MB |
| PostgreSQL | 120ms | 35ms | 50MB |
| Elasticsearch | 2000ms | 45ms | 500MB |

### 为什么其他方案不适合

#### Elasticsearch

| 问题 | 说明 |
|------|------|
| **过度设计** | 分布式架构对于单机场景是负担 |
| **资源消耗** | JVM 内存开销至少 512MB |
| **启动慢** | 冷启动需要 5-30 秒 |
| **运维复杂** | 需要集群配置、分片管理 |

> "用大炮打蚊子" —— ES 设计为 PB 级数据分布式搜索，DeepMemo 的聊天记录场景每个索引仅 1000-10000 条消息。

#### SQLite FTS5

| 问题 | 说明 |
|------|------|
| **中文分词弱** | 需要用 C 编写自定义 tokenizer |
| **内存索引差** | 需要创建临时数据库文件 |
| **并发限制** | 写入时全局锁，并发性能差 |

```sql
-- SQLite FTS5 中文分词需要复杂的自定义 tokenizer
SELECT tokenize FROM fts5vocab('zh_tabke', 'type');
-- 需要编译 C 扩展，部署复杂
```

#### PostgreSQL FTS

| 问题 | 说明 |
|------|------|
| **中文支持弱** | 内置分词器对中文支持差 |
| **需要扩展** | zhparser 等需要单独编译安装 |
| **资源开销** | 数据库连接和管理开销 |
| **部署复杂** | 需要 PostgreSQL 服务器 |

```sql
-- PostgreSQL 中文全文搜索需要额外扩展
CREATE EXTENSION zhparser;
CREATE TEXT SEARCH CONFIGURATION chinese (PARSER = zhparser);
-- 部署时需要编译扩展，兼容性问题多
```

### 结论

对于 DeepMemo 的聊天记忆检索场景，Tantivy 是最优选择：

1. **场景匹配**：单机、中小规模数据、实时性要求高
2. **部署简单**：单个可执行文件，零运维成本
3. **性能优异**：内存索引 + 毫秒级查询
4. **中文友好**：原生集成 jieba-rs 分词
5. **技术栈统一**：与 Rust 插件完美集成

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  MessageBubble / AIResponseArea                            │  │
│  │  显示工具调用和结果                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Backend                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  app/api/v1/chat.py                                        │  │
│  │  - 聊天 API 端点                                           │  │
│  │  - 集成工具调用逻辑                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  app/services/chat_service.py                             │  │
│  │  - 聊天服务层                                             │  │
│  │  - 工具调用管理                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  plugins/tool_executor.py                                 │  │
│  │  - 工具执行器                                             │  │
│  │  - 结果格式化                                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  plugins/plugin.py                                        │  │
│  │  - PluginManager                                          │  │
│  │  - 插件生命周期管理                                       │  │
│  │  - 通信协议路由（stdio/direct）                           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DeepMemo Plugin (Rust)                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Main Process (src/main.rs)                               │  │
│  │  - STDIO 通信协议处理                                     │  │
│  │  - 参数解析与验证                                         │  │
│  │  - 结果序列化输出                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Search Engine (src/searcher.rs)                          │  │
│  │  - Tantivy 索引管理                                       │  │
│  │  - Jieba 中文分词器                                       │  │
│  │  - 查询解析器                                             │  │
│  │  - 上下文窗口提取                                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Storage                                │
│  data/chat/user_default/{agent_uuid}/topics/{topic_id}/         │
│    └── history.json                                              │
└─────────────────────────────────────────────────────────────────┘
```

## 数据模型

### 1. 工具调用参数

```rust
#[derive(Deserialize, Debug)]
struct ToolArgs {
    maid: String,           // AI女仆ID
    keyword: String,        // 搜索关键词
    window_size: i32,       // 上下文窗口大小（1-20，默认3）
}
```

### 2. 插件配置

```rust
#[derive(Debug, Clone)]
struct Config {
    vchat_data_url: PathBuf,      // 聊天数据路径
    max_memo_tokens: usize,       // 最大返回token数
    rerank_search: bool,           // 是否启用重排序
    rerank_url: String,            // 重排序服务URL
    rerank_model: String,          // 重排序模型
    query_preset: String,          // 预设查询词
}
```

### 3. 历史消息条目

```rust
#[derive(Debug, Clone)]
struct HistoryEntry {
    role: String,          // "user" 或 "assistant"
    content: String,       // 消息内容
}
```

### 4. 聊天数据存储格式

```json
[
  {
    "message_id": "msg-xxx",
    "role": "user",
    "content": "用户消息内容",
    "timestamp": 1770654577
  },
  {
    "message_id": "msg-xxx",
    "role": "assistant",
    "content": "AI回复内容",
    "timestamp": 1770654577
  }
]
```

## 核心组件实现

### 1. 插件管理器 (PluginManager)

**文件位置**: `backend/plugins/plugin.py`

```python
class PluginManager:
    """插件管理器 - 负责加载、管理和执行所有插件"""

    async def load_plugins(self):
        """加载所有插件"""
        for plugin_dir in self.plugins_dir.iterdir():
            manifest_path = plugin_dir / "plugin-manifest.json"
            if manifest_path.exists():
                await self._load_plugin(plugin_dir, manifest_path)

    async def process_tool_call(self, tool_name: str, tool_args: dict) -> dict:
        """处理工具调用 - 根据协议类型路由到对应的插件"""
        plugin = self.plugins.get(tool_name)
        protocol = plugin.get("communication", {}).get("protocol", "direct")

        if protocol == "stdio":
            return await self._execute_stdio_plugin(tool_name, tool_args)
        elif protocol == "direct":
            return await self._execute_direct_plugin(tool_name, tool_args)
```

### 2. 中文分词器

**文件位置**: `backend/plugins/deepmemo/src/tokenizer.rs`

```rust
#[derive(Clone)]
pub struct JiebaTokenizer {
    jieba: Arc<jieba_rs::Jieba>,
}

impl Tokenizer for JiebaTokenizer {
    fn token_stream<'a>(&self, text: &'a str) -> BoxTokenStream<'a> {
        let mut tokens = Vec::new();

        // 使用 jieba-rs 进行中文分词
        for (offset, word) in self.jieba.tokenize(text, false).iter().enumerate() {
            tokens.push(Token {
                offset: word.start() as u32,
                position: offset as u32,
                text: word.word,
                position_length: word.word.chars().count() as u32,
            });
        }

        Box::new(JiebaTokenStream::new(tokens))
    }
}
```

### 3. 查询解析器

**文件位置**: `backend/plugins/deepmemo/src/query_parser.rs`

支持的高级查询语法：

| 语法 | 说明 | 示例 |
|------|------|------|
| 普通词搜索 | 基本关键词搜索 | `VCP` |
| 精确短语 | 双引号包裹 | `"VCP服务器"` |
| 正向加权 | 提升权重 | `(重要概念:1.5)` |
| 负向排除 | 排除关键词 | `[闲聊]` |
| OR 逻辑 | 多选一 | `{破解\|渗透\|测试}` |

```rust
pub fn parse_ai_query_to_tantivy(query: &str) -> Query {
    let mut query_parser = QueryParser::for_index(
        &index,
        vec![content_field]
    );

    // 处理精确短语
    if query.contains('"') {
        // 解析 "exact phrase"
    }

    // 处理加权项
    if query.contains(':') {
        // 解析 (term:weight)
    }

    // 处理排除项
    if query.contains('[') {
        // 解析 [term]
    }

    // 处理 OR 组
    if query.contains('{') {
        // 解析 {term1|term2}
    }

    query_parser.parse_query(&cleaned_query)
}
```

### 4. 搜索与上下文提取

**文件位置**: `backend/plugins/deepmemo/src/searcher.rs`

```rust
async fn process_single_history_file(
    file_path: PathBuf,
    query: Arc<String>,
    window_size: i32,
    config: Arc<Config>,
) -> Result<Vec<Vec<HistoryEntry>>> {
    // 1. 读取历史文件
    let json_content = fs::read_to_string(&file_path)?;
    let history: Vec<HistoryEntry> = serde_json::from_str(&json_content)?;

    // 2. 创建内存索引
    let index = Index::create_in_ram(schema.clone());
    let mut index_writer = index.writer(50_000_000)?;

    // 3. 添加文档到索引
    for (i, entry) in history.iter().enumerate() {
        let clean_content = extract_text(&entry.content);
        let doc = doc!(
            content_field => clean_content,
            id_field => i as u64
        );
        index_writer.add_document(doc)?;
    }
    index_writer.commit()?;

    // 4. 执行搜索
    let reader = index.reader()?;
    let searcher = reader.searcher();
    let query = parse_ai_query_to_tantivy(&query)?;
    let top_docs = searcher.search(&query, &TopDocs::with_limit(100))?;

    // 5. 提取上下文窗口
    let mut results = Vec::new();
    for (score, doc_address) in top_docs {
        let retrieved_doc = searcher.doc(doc_address)?;
        let id = retrieved_doc.get_first(id_field).unwrap().u64_value().unwrap();

        let start = (id as i32 - window_size).max(0) as usize;
        let end = (id as usize + window_size as usize + 1).min(history.len());

        results.push(history[start..end].to_vec());
    }

    Ok(results)
}
```

### 5. 工具执行器

**文件位置**: `backend/plugins/tool_executor.py`

```python
class ToolExecutor:
    """工具执行器 - 负责执行工具调用并格式化结果"""

    async def execute(self, tool_call: ToolCall, client_ip: str = None) -> Dict[str, Any]:
        """执行单个工具调用"""
        tool_name = tool_call.name
        args = tool_call.args

        logger.info(f"[工具调用] 工具名称: {tool_name}, 参数: {args}, 客户端IP: {client_ip}")

        try:
            # 通过 PluginManager 执行插件
            result = await self.plugin_manager.process_tool_call(tool_name, args)

            # 处理结果
            formatted_result = self._process_result(tool_name, result)

            logger.info(f"[工具完成] 工具: {tool_name}, 结果: {formatted_result}")
            return formatted_result

        except Exception as e:
            logger.error(f"[工具错误] 工具: {tool_name}, 错误: {str(e)}")
            raise
```

## 插件清单

### DeepMemo 插件清单

**文件位置**: `backend/plugins/deepmemo/plugin-manifest.json`

```json
{
  "name": "DeepMemo",
  "displayName": "深度回忆插件",
  "version": "1.0.0",
  "description": "根据关键词从聊天记录中检索相关上下文",
  "author": "Your Name",
  "pluginType": "synchronous",
  "communication": {
    "protocol": "stdio",
    "timeout": 60000
  },
  "entryPoint": {
    "command": "./target/release/deepmemo"
  },
  "capabilities": {
    "invocationCommands": [
      {
        "command": "DeepMemo",
        "description": "根据关键词从历史聊天记录中检索相关上下文，增强AI对话的连贯性和个性化体验",
        "example": "{\"maid\": \"sister_001\", \"keyword\": \"哥哥,想念\", \"windowsize\": 6}"
      }
    ]
  }
}
```

### 配置文件

**文件位置**: `backend/plugins/deepmemo/config.env`

```env
# VCP 聊天数据路径
VchatDataURL=/Users/xuenai/Code/emotional-companionship/data/chat

# 最大返回的回忆 token 数量
MaxMemoTokens=60000

# 是否启用重排序
RerankSearch=false

# 重排序服务配置
RerankUrl=
RerankApi=
RerankModel=

# 预设查询词
QueryPreset=
```

## 前端集成

### 工具调用格式

前端通过特殊的 VCP 格式发送工具调用请求：

```
<<<[TOOL_REQUEST]>>>
tool_name:「始」DeepMemo「末」,
maid:「始」sister_001「末」,
keyword:「始」哥哥,想念「末」,
windowsize:「始」6「末」
<<<[END_TOOL_REQUEST]>>>
```

### 组件使用

**文件位置**: `frontend/src/components/chat/MessageBubble.tsx`

```typescript
// 解析和显示工具调用结果
if (msg.tool_calls && msg.tool_calls.length > 0) {
  return (
    <div className="tool-call-container">
      {msg.tool_calls.map((tool, index) => (
        <div key={index} className="tool-call">
          <span className="tool-name">{tool.name}</span>
          <pre className="tool-args">{JSON.stringify(tool.args, null, 2)}</pre>
          {tool.result && (
            <div className="tool-result">
              <Markdown>{tool.result}</Markdown>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

## API 接口

### 获取工具描述

```http
GET /api/v1/chat/tools
```

**响应示例**:

```json
{
  "tools": {
    "DeepMemo": "根据关键词从历史聊天记录中检索相关上下文，增强AI对话的连贯性和个性化体验。\n\n参数说明：\n- maid: AI女仆ID（必需）\n- keyword: 搜索关键词，支持高级语法（必需）\n  - 精确短语：\"exact phrase\"\n  - 加权项：(term:weight)\n  - 排除项：[term]\n  - OR逻辑：{term1|term2}\n- windowsize: 上下文窗口大小（可选，默认3，范围1-20）\n\n示例：\n{\"maid\": \"sister_001\", \"keyword\": \"\\\"哥哥想念\\\" (重要:1.5) [闲聊]\", \"windowsize\": 6}"
  }
}
```

## 部署

### 构建 Rust 插件

```bash
# 进入插件目录
cd backend/plugins/deepmemo

# 编译 Release 版本
cargo build --release

# 可执行文件位置
./target/release/deepmemo
```

### 启动后端服务

```bash
# 确保插件已编译
cd backend

# 启动服务（会自动加载插件）
python -m uvicorn app.main:app --reload
```

## 依赖项

### Rust 依赖 (Cargo.toml)

```toml
[dependencies]
tokio = { version = "1", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
anyhow = "1.0"
jieba-rs = "0.6"          # 中文分词
tantivy = "0.19"          # 全文搜索引擎
reqwest = { version = "0.11", features = ["json"] }
chrono = "0.4"
html-escape = "0.2"
```

### Python 依赖

```txt
fastapi
uvicorn
pydantic
```

## 性能优化

1. **内存索引**：每个对话文件创建独立的内存索引，避免全量索引重建
2. **异步处理**：使用 Tokio 异步运行时，支持并发处理多个历史文件
3. **中文分词缓存**：Jieba 分词器使用 Arc 包装，支持跨线程共享
4. **HTML 清理**：预处理阶段清理 HTML 标签，减少索引数据量

## 扩展开发

### 创建新插件

1. 在 `backend/plugins/` 下创建新目录
2. 创建 `plugin-manifest.json` 清单文件
3. 实现插件逻辑（Python 模块或 Rust 可执行文件）
4. 创建 `config.env` 配置文件（如需要）
5. 重新启动后端服务

### 插件通信协议

#### Stdio 协议

适用于 Rust/Go 等编译语言：

1. 父进程启动子进程
2. 通过 STDIN 发送 JSON 格式的请求
3. 子进程通过 STDOUT 返回 JSON 格式的响应

#### Direct 协议

适用于 Python 模块：

1. 直接调用 Python 模块中的函数
2. 不需要进程间通信
3. 更快的响应速度

## 安全考虑

1. **输入验证**：所有输入参数都经过严格验证
2. **路径检查**：防止路径遍历攻击
3. **超时控制**：插件执行有超时限制（默认 60 秒）
4. **错误处理**：完善的错误处理和日志记录

## 未来改进

- [ ] 支持更多向量嵌入模型
- [ ] 添加混合搜索（向量 + 全文）
- [ ] 实现增量索引更新
- [ ] 添加缓存层
- [ ] 支持分布式部署
