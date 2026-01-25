# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack emotional companionship AI system with customizable characters, intelligent chat, and auto-generated diary system. The system uses LLMs (Qwen/DashScope or DeepSeek) to provide contextual conversations and automatically generates diary entries based on conversation events and emotional analysis.

## Development Commands

### Backend (FastAPI)

```bash
cd backend

# Setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run development server
python -m uvicorn app.main:app --reload

# Run all tests
pytest tests/ -v

# Run unit tests only (no integration)
pytest tests/ -v -m "not integration"

# Linting (optional, allowed to fail in CI)
pip install flake8
flake8 app/ tests/ --max-line-length=120
```

### Frontend (React + Vite)

```bash
cd frontend

# Setup
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint
```

### Environment Variables

**Backend `.env`** (create in `backend/`):
```
DASHSCOPE_API_KEY=your_qwen_api_key    # OR
DEEPSEEK_API_KEY=your_deepseek_api_key
LLM_PROVIDER=qwen|deepseek             # Optional, defaults to deepseek
DATABASE_URL=sqlite:///./emotional_companionship.db
```

**Frontend `.env`** (create in `frontend/`):
```
VITE_API_URL=http://localhost:8000
```

## Architecture

### Backend Structure

- **`app/api/v1/`** - API endpoints (chat, character, diary, temporal)
- **`app/models/`** - SQLAlchemy ORM models
- **`app/services/`** - Business logic layer
  - **`services/llms/`** - LLM provider integrations (Qwen, DeepSeek)
  - **`services/diary/`** - Simplified diary system with AI assessment
  - **`services/temporal/`** - Future timeline system
- **`app/schemas/`** - Pydantic request/response schemas
- **`app/main.py`** - FastAPI application entry point

### Frontend Structure

- **`src/components/`** - Reusable React components
  - `chat/` - Chat interface components
  - `character/` - Character selection
  - `diary/` - Diary display
  - `ui/` - Common UI components
- **`src/pages/ChatPage.tsx`** - Main chat interface
- **`src/hooks/`** - Custom React hooks (useChat.ts, useCharacter.ts)
- **`src/services/`** - API client services
- **`src/types/`** - TypeScript type definitions

### Key Data Flow

1. **Chat Flow**: Frontend sends message → `chat_service.py` → LLM API → streaming response with AI assessment → async diary extraction if worth recording → temporal event extraction → response to frontend
2. **Diary Generation**: AI evaluates conversation worthiness during chat → if worth recording → `diary/core_service.py` extracts from actual conversation → quality check → SQLite storage
3. **Character System**: YAML files in `backend/app/resources/characters/` loaded at startup → `character_service.py` serves character data
4. **Temporal Timeline**: Chat mentions future time → `temporal/extractor.py` extracts time expressions → `temporal/normalizer.py` normalizes to absolute datetime → SQLite storage via `temporal/retriever.py`

### Diary System Architecture

**Simplified, prompt-based diary system:**

Located in `app/services/diary/`:
- **`core_service.py`** - Unified diary generation from conversations
- **`assessor.py`** - AI-powered conversation assessment
- **`tag_service.py`** - High-density tag generation
- **`quality.py`** - Content quality validation
- **`prompts/`** - External prompt templates for easy iteration

**Flow:**
```
Chat → AI评估值得记录？ → 提取日记（含Tag） → 质量检查 → 保存SQLite
              ↓
         不值得记录 → 结束
```

**Diary Format:**
```
【对话主题】简述本次对话的核心内容

【对话记录】
哥哥：...
我：...

【关键信息】
- 要点1
- 要点2

【我的感受】

Tag: 关键词1, 关键词2
```

### Temporal Timeline System

**Future timeline with time precision support:**

Located in `app/services/temporal/`:
- **`models.py`** - Data models (FutureEvent, EventStatus, etc.)
- **`extractor.py`** - LLM-based time expression extraction from conversations
- **`normalizer.py`** - Chinese time expression normalization to absolute datetime
  - Supports: "明天下午3点" → "2025-01-26 15:00"
  - Supports: "后天9点" → "2025-01-27 09:00"
  - Supports: "15:30" → "2025-01-25 15:30" (today)
  - Time-of-day defaults: 上午9点, 下午3点, 晚上8点
- **`retriever.py`** - Event CRUD operations with database
- **`prompt.py`** - Prompt templates for timeline operations

**Flow:**
```
Chat → 提取时间表达 → 归一化为绝对时间 → 存储SQLite → 可视化展示
              ↓
        LLM识别未来事件
```

**Time Format:**
- With time: `YYYY-MM-DD HH:MM` (e.g., "2025-01-26 15:30")
- Date only: `YYYY-MM-DD` (e.g., "2025-01-26")

**Frontend Components:**
- `FutureTimeline.tsx` - S-curve timeline visualization
  - Expandable/collapsible daily events (default: 3 visible)
  - Dynamic row height calculation
  - Click events to view details

**Database Table (`future_events`):**
```sql
CREATE TABLE future_events (
    id VARCHAR PRIMARY KEY,
    character_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT,
    event_date VARCHAR NOT NULL,  -- YYYY-MM-DD or YYYY-MM-DD HH:MM
    source_conversation TEXT,
    tags JSON DEFAULT '[]',
    status VARCHAR NOT NULL,  -- pending/completed/cancelled
    created_at DATETIME NOT NULL,
    updated_at DATETIME
);
```

### LLM Integration

- **`services/llms/qwen.py`** - Qwen/DashScope API integration
- **`services/llms/deepseek.py`** - DeepSeek API integration
- Provider selected via `LLM_PROVIDER` env var or defaults to deepseek

## Important Notes

- **Multi-user support**: Data isolated by `user_id`
- **Diary storage**: SQLite-only (single source of truth)
- **Character configs**: YAML files auto-loaded from `backend/app/resources/characters/`
- **API docs**: Available at `http://localhost:8000/docs` (Swagger UI) when backend is running
- **CI runs**: On push/PR to main/develop branches via GitHub Actions
- **Python version**: 3.13+
- **Node version**: 18+

## Adding New Characters

Create YAML file in `backend/app/resources/characters/` with:
- Basic info (name, age, personality)
- Behavior preferences (initiative level, topic preferences)
- Speaking style (catchphrases, tone)
- Relationship settings

Character service auto-loads on restart.

## Database Schema

**Diary Table (`diaries`):**
```sql
CREATE TABLE diaries (
    id VARCHAR PRIMARY KEY,
    character_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    date VARCHAR NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR NOT NULL,  -- knowledge/topic/emotional/milestone
    emotions JSON DEFAULT '[]',
    tags JSON DEFAULT '[]',
    created_at DATETIME NOT NULL,
    updated_at DATETIME
);
```

If you need to migrate from an old schema with `trigger_type`, run:
```sql
ALTER TABLE diaries ADD COLUMN category VARCHAR;
UPDATE diaries SET category =
  CASE
    WHEN trigger_type = 'important_event' THEN 'milestone'
    WHEN trigger_type = 'daily_summary' THEN 'topic'
    WHEN trigger_type = 'emotional_fluctuation' THEN 'emotional'
    ELSE 'topic'
  END;
-- Then recreate table without old columns
```
