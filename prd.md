# PRD - macOS Desktop Word/Phrase/Article Capture and Learning Tool

## 1. Background and Goal
Build a macOS compatible desktop tool for English learning (Intel and Apple Silicon). The tool runs with user permissions, supports a global hotkey, captures words/phrases/articles from any desktop app (selection first, clipboard fallback), calls a large-model API for parsing/enrichment, checks duplicates, and provides a learning interface with audio playback and Ebbinghaus-based study scheduling. Data is stored locally first, with future export and cloud sync. Phrase/Article automatically include grammar structure highlights and notes on save.

## 2. Target Users
- English learners who read content in apps or browsers and want quick capture and study.

## 3. Scope
### In Scope (MVP)
- Global hotkey to open tool.
- Selection capture across desktop apps (clipboard is a fallback).
- Support capture types: word, phrase, article (full text).
- LLM API integration on capture: word/phrase/article parsing and enrichment.
- Duplicate check: exact match by entry text.
- Local storage (SQLite).
- Basic learning UI: list, detail view.
- Grammar analysis as a sub-feature of Phrase/Article (auto structure highlighting + notes).

### Out of Scope (Later)
- Local/offline LLM.
- Cloud sync, multi-device.
- Rich statistics dashboard.
- Advanced duplicate detection (lemmatization/fuzzy).

## 4. Core User Flows
1) Capture from selection/clipboard
- User selects text or copies text -> tool captures selection or clipboard -> identifies word/phrase/article -> calls LLM to parse/enrich -> shows confirmation popup -> user clicks Save to store record.

2) Quick access
- User presses global hotkey -> tool starts listening in silent mode without popping up.

3) Learning
- User opens an entry -> reads details -> manages tags/relations.

4) Grammar analysis (Phrase/Article only)
- On save, tool automatically calls grammar analysis -> generates structure highlights + notes -> shows results in Phrase/Article detail.

## 5. Functional Requirements
### 5.1 Capture & Ingestion
- Monitor clipboard changes (fallback).
- Capture selected text across apps (fallback to clipboard if selection is not accessible).
- Auto-detect content type:
  - Word: single token
  - Phrase: short multi-word chunk
  - Article: longer text block
- Ignore non-English or overly long noise (threshold configurable).
- Show confirmation popup after LLM enrichment; user chooses Save or Discard.
- Duplicate detection by exact text match (default is to skip save on duplicate).

### 5.2 LLM Processing
- Word: translation (POS grouped), part_of_speech, IPA (UK/US), phonetics (US/UK), word roots, tense/forms, common meanings, related terms, definition.
- Phrase/Article: translation, structure breakdown, grammar notes, key terms.

### 5.3 Storage
- Local SQLite database.
- Tables for entries, reviews, metadata.

### 5.4 Grammar Analysis (Phrase/Article)
- Auto-triggered on capture save (no manual action).
- Parse structure: highlight S/V/O and clause boundaries.
- Display highlights and grammar notes in Phrase/Article detail.

### 5.5 Tags & Related Terms
- Tags saved via input.
- Related terms selected from existing word entries via search.
- Related terms shown in detail view.

## 6. Non-Functional Requirements
- macOS compatibility (Intel and Apple Silicon).
- Must run with user permissions; global hotkey and selection capture require Accessibility permission.
- Local-first storage; no network sync required in MVP.
- Latency: LLM response within acceptable range; allow async queue.

## 7. Tech Stack
- UI: Qt via Python (PySide6 or PyQt6).
- Data: SQLite (local).
- Hotkey: macOS global hotkey library (Python).
- Selection/Clipboard: Accessibility API + clipboard fallback.
- LLM: OpenAI-compatible SDK (Volcengine Ark).

## 8. Risks & Considerations
- macOS Accessibility permission prompts for selection capture.
- OS updates may affect selection APIs.
- LLM latency/timeout.

## 9. Open Questions
- Article duplicate rules (full-text exact match vs hash/title).
- LLM prompt tuning for stable JSON output.

---
# Data Model (Draft)

## SQLite Tables

### 1) entries
Stores words/phrases/articles.
- id (INTEGER, PK)
- entry_type (TEXT) -- word | phrase | article
- text (TEXT) -- exact captured text, used for exact match
- language (TEXT) -- default "en"
- translation (TEXT)
- phonetic_us (TEXT)
- phonetic_uk (TEXT)
- definition (TEXT) -- short gloss
- part_of_speech (TEXT) -- word only
- ipa (TEXT) -- word only
- word_roots (TEXT) -- JSON string
- tense_form (TEXT) -- JSON array
- common_meanings (TEXT) -- JSON array
- tags (TEXT) -- JSON array
- related_entry_ids (TEXT) -- JSON array
- grammar_notes (TEXT) -- phrase/article
- structure_breakdown (TEXT) -- JSON
- key_terms (TEXT) -- JSON
- audio_us_url (TEXT) -- optional
- audio_uk_url (TEXT) -- optional
- source_app (TEXT) -- optional
- raw_llm (TEXT) -- store raw response for debugging
- created_at (INTEGER)
- updated_at (INTEGER)

Indexes:
- UNIQUE(text) for exact duplicate check
- INDEX(entry_type)
- INDEX(created_at)

### 2) reviews
Tracks learning schedule and progress.
- id (INTEGER, PK)
- entry_id (INTEGER, FK -> entries.id)
- stage (INTEGER)
- next_review_at (INTEGER)
- last_review_at (INTEGER)
- status (TEXT) -- pending | learned | postponed
- created_at (INTEGER)
- updated_at (INTEGER)

### 3) review_logs
Tracks each review action.
- id (INTEGER, PK)
- entry_id (INTEGER, FK -> entries.id)
- action (TEXT) -- learn | postpone | skip
- reviewed_at (INTEGER)
- note (TEXT)

### 4) settings
Simple key/value settings.
- key (TEXT, PK)
- value (TEXT)

---
# Detailed Flow (Draft)

## 1) Selection/Clipboard Capture Pipeline
1. Read selected text via Accessibility API; if unavailable, listen to clipboard changes via QClipboard signal.
2. Normalize text: trim, collapse whitespace, remove leading/trailing quotes.
3. Detect type:
   - word: single token (letters + hyphen/quote)
   - phrase: 2–6 tokens, length below threshold
   - article: length above threshold
4. Reject if:
   - non-English ratio too high
   - too short/too long (configurable)
5. Call LLM API to enrich:
   - word: translation, part_of_speech, ipa, phonetics, roots, tense, common meanings, related terms
   - phrase/article: translation, structure breakdown, grammar notes, key terms
6. Show confirmation popup:
   - display text + translation/phonetics/definition
   - actions: Save / Discard
7. On Save:
   - exact duplicate check by `entries.text`
   - if not duplicate, store in `entries`, create `reviews` row
8. Notify UI and optionally toast.

## 2) Global Hotkey Flow
1. Register global hotkey on app start.
2. On hotkey:
   - start selection capture in silent mode (clipboard fallback)
   - do not show main window

## 3) Grammar Analysis Flow
1. User saves a Phrase/Article entry.
2. System auto-parses structure and generates highlights + notes.
3. Results are shown inside the Phrase/Article detail view.

---
# LLM Output Contract (Draft)

## API Request (Logical)
- Input: `text`, `entry_type` (word|phrase|article), `language` (en)
- Task: return word/phrase/article enrichment fields

## Expected JSON Response (Word)
```json
{
  "text": "original input text",
  "entry_type": "word",
  "translation": "v. ...\n n. ...",
  "part_of_speech": "noun/verb/...",
  "ipa": "UK: /.../; US: /.../",
  "phonetic_us": "US phonetic",
  "phonetic_uk": "UK phonetic",
  "word_roots": ["root1", "root2"],
  "tense_form": ["复数: ...", "第三人称单数: ...", "现在分词: ...", "过去式: ...", "过去分词: ..."],
  "common_meanings": ["meaning1", "meaning2"],
  "related_terms": ["term1", "term2"],
  "definition": "short English definition or usage",
  "confidence": 0.0
}
```

## Expected JSON Response (Phrase/Article)
```json
{
  "text": "original input text",
  "entry_type": "phrase",
  "translation": "v. ...\n n. ...",
  "structure_breakdown": [{"span": "...", "role": "clause/phrase"}],
  "grammar_notes": "short grammar explanation",
  "key_terms": [{"term": "...", "definition": "..."}],
  "confidence": 0.0
}
```

### Rules
- `translation` must be POS grouped in multi-line format.
- `ipa` must be formatted as `UK: /.../; US: /.../`.
- `tense_form` must be an array of Chinese-labeled forms.
- Arrays stored as JSON strings.

---
# UI Details (Draft)

## Main Window Layout
- Top bar: capture status indicator.
- Left nav: Word / Phrase / Article tabs.
- Right panel: detail view with structure highlight for Phrase/Article.

## List View (Word / Phrase / Article)
- Text (primary)
- Translation (secondary, single line)

## Detail View
- Title: entry text
- Translation block
- Word-only: part of speech, IPA, US/UK phonetics, roots, tense, common meanings, related terms, tags
- Phrase/Article: structure breakdown, grammar notes, key terms, structure highlight

---
# SQLite Schema (Draft SQL)

```sql
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_type TEXT NOT NULL,
  text TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'en',
  translation TEXT DEFAULT '',
  phonetic_us TEXT DEFAULT '',
  phonetic_uk TEXT DEFAULT '',
  definition TEXT DEFAULT '',
  part_of_speech TEXT DEFAULT '',
  ipa TEXT DEFAULT '',
  word_roots TEXT DEFAULT '',
  tense_form TEXT DEFAULT '',
  common_meanings TEXT DEFAULT '',
  tags TEXT DEFAULT '',
  related_entry_ids TEXT DEFAULT '',
  grammar_notes TEXT DEFAULT '',
  structure_breakdown TEXT DEFAULT '',
  key_terms TEXT DEFAULT '',
  audio_us_url TEXT DEFAULT '',
  audio_uk_url TEXT DEFAULT '',
  source_app TEXT DEFAULT '',
  raw_llm TEXT DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_text ON entries(text);
CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at);
```

---
# Module & Class Structure (Draft)

## Suggested Structure
- app/
  - main.py
  - ui/
    - main_window.py
  - services/
    - selection_service.py
    - clipboard_service.py
    - llm_service.py
    - grammar_service.py
  - data/
    - db.py
    - entry_repo.py
  - utils/
    - text_detect.py

## Key Responsibilities
- selection_service: capture selected text on macOS.
- clipboard_service: capture clipboard as fallback.
- llm_service: call LLM and parse JSON.
- grammar_service: parse sentence structure and generate highlights.
- entry_repo: SQLite CRUD and duplicate check.

---
# PRD - macOS 桌面划词/短语/文章采集与学习工具（中文）

## 1. 背景与目标
构建一款兼容 macOS（Intel 与 Apple Silicon）的英语学习桌面工具。工具以用户权限运行，支持全局快捷键，支持任意应用内选区采集（剪贴板兜底），自动识别单词/短语/文章并调用大模型解析与补全，进行精确去重并入库展示。短语/文章保存后自动生成语法结构高亮与说明。数据本地存储，后续可扩展导出与同步。

## 2. 目标用户
- 在应用或网页中阅读英语内容并希望快速采集与学习的用户。

## 3. 范围
### 范围内（MVP）
- 全局快捷键打开工具。
- 选区采集（剪贴板兜底）。
- 支持采集类型：单词、短语、文章。
- 采集后自动调用 LLM 解析补全并入库。
- 文本完全匹配去重。
- 本地存储（SQLite）。
- 基础列表与详情展示。
- 短语/文章自动语法结构高亮与说明。

### 范围外（后续）
- 本地/离线模型。
- 云同步、多端。
- 统计面板与高级复习算法。

## 4. 核心需求
### 4.1 采集与入库
- 选区优先，剪贴板兜底。
- 自动识别 Word / Phrase / Article。
- 捕获后自动调用 LLM 解析并入库。
- 精确去重。

### 4.2 Word 解析字段
- 翻译（按词性分组）。
- 词性、IPA（英/美）、美/英音标。
- 词根拆解、时态/形态、常用释义。
- 标签与关联词。

### 4.3 Phrase / Article 解析字段
- 中英文翻译。
- 结构拆解与语法说明。
- 关键术语释义。
- 结构高亮展示（主干/从句）。

### 4.4 标签与关联词
- 标签输入后保存。
- 关联词通过搜索词库的 Word 下拉选择并保存。
- 保存后在详情中展示关联词。

## 5. 数据要求
### 5.1 条目字段（摘要）
- entry_type, text, translation
- part_of_speech, ipa, phonetic_us, phonetic_uk
- word_roots, tense_form, common_meanings
- tags, related_entry_ids
- grammar_notes, structure_breakdown, key_terms
- raw_llm, created_at, updated_at

### 5.2 翻译格式
- translation 按词性分行输出：
  - `v. ...`
  - `n. ...`

### 5.3 IPA 格式
- `UK: /.../; US: /.../`

## 6. 用户流程
1) 选区或复制文本。
2) 自动调用 LLM 解析。
3) 入库并展示列表。
4) 查看详情并管理标签/关联词。

## 7. 页面/功能
### 7.1 主窗口
- 左侧 Tab：Word / Phrase / Article。
- 右侧详情：短语/文章展示结构高亮。

### 7.2 详情区
- Word：词性、IPA、音标、词根、时态、常用释义、关联词、标签。
- Phrase/Article：结构拆解、语法说明、关键术语、结构高亮。

## 8. 边界场景
- 无文本：提示无法采集。
- 非英文：提示忽略。
- 超时：提示失败并保留 raw_llm。
- 重复：提示重复不入库。

---
# 中文版 SQL 草案

```sql
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_type TEXT NOT NULL,
  text TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'en',
  translation TEXT DEFAULT '',
  phonetic_us TEXT DEFAULT '',
  phonetic_uk TEXT DEFAULT '',
  definition TEXT DEFAULT '',
  part_of_speech TEXT DEFAULT '',
  ipa TEXT DEFAULT '',
  word_roots TEXT DEFAULT '',
  tense_form TEXT DEFAULT '',
  common_meanings TEXT DEFAULT '',
  tags TEXT DEFAULT '',
  related_entry_ids TEXT DEFAULT '',
  grammar_notes TEXT DEFAULT '',
  structure_breakdown TEXT DEFAULT '',
  key_terms TEXT DEFAULT '',
  audio_us_url TEXT DEFAULT '',
  audio_uk_url TEXT DEFAULT '',
  source_app TEXT DEFAULT '',
  raw_llm TEXT DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_text ON entries(text);
CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at);
```

---
# 中文版 LLM 输出协议

## 请求
- 输入：`text`，`entry_type`（word|phrase|article），`language`（en）
- 任务：返回条目解析字段（JSON）

## 返回示例（单词）
```json
{
  "text": "original input text",
  "entry_type": "word",
  "translation": "v. ...\n n. ...",
  "part_of_speech": "noun/verb/...",
  "ipa": "UK: /.../; US: /.../",
  "phonetic_us": "US phonetic",
  "phonetic_uk": "UK phonetic",
  "word_roots": ["root1", "root2"],
  "tense_form": ["复数: ...", "第三人称单数: ...", "现在分词: ...", "过去式: ...", "过去分词: ..."],
  "common_meanings": ["meaning1", "meaning2"],
  "related_terms": ["term1", "term2"],
  "definition": "short English definition or usage",
  "confidence": 0.0
}
```

## 返回示例（短语/文章）
```json
{
  "text": "original input text",
  "entry_type": "phrase",
  "translation": "v. ...\n n. ...",
  "structure_breakdown": [{"span": "...", "role": "clause/phrase"}],
  "grammar_notes": "short grammar explanation",
  "key_terms": [{"term": "...", "definition": "..."}],
  "confidence": 0.0
}
```

## 规则
- translation 必须按词性分行输出。
- ipa 必须为 `UK: /.../; US: /.../`。
- tense_form 必须为中文标签数组。
- 数组字段以 JSON 字符串存储。

---
# 中文版 UI 线框图

### 主窗口
```
------------------------------------------------
| Word | Phrase | Article                       |
|----------------------------------------------|
| [列表]              | [详情]                 |
|                     | 词条/短语/文章详情     |
|                     | 结构高亮（短语/文章）  |
------------------------------------------------
```
