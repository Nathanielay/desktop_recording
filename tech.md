# 技术方案

## 技术概述
- 运行环境：macOS（Intel 与 Apple Silicon），桌面常驻后台服务 + 可选主窗口。
- 技术栈：Python + Qt（PySide6 或 PyQt6），SQLite 本地存储。
- 交互方式：全局快捷键触发选区采集（剪贴板兜底）；检测到英文后自动调用 LLM 解析并入库；短语/文章自动生成语法结构与说明并在详情展示。
- 模型接口：火山引擎 Ark OpenAI SDK（base_url: `https://ark.cn-beijing.volces.com/api/v3`）。
- 音频：MVP 不包含播放；后续接入词典音频。

## 数据库设计
- 数据库：SQLite（单文件）。
- 主要表：
  - entries：词条/短语/文章主体与大模型补全字段（词性、音标、词根、结构拆解、关键术语等）。
  - reviews：艾宾浩斯复习状态与下次复习时间。
  - review_logs：复习操作日志。
  - settings：简单键值配置。
- 关键索引：
  - entries.text 唯一索引，用于精确查重。
  - reviews.next_review_at 索引，用于生成今日待学列表。
- 参考 `prd.md` 中 SQL 草案作为建表依据。
- tags、related_terms、structure_breakdown 等复杂字段以 JSON 字符串存储。

## 数据字段约定
- translation：按词性分行输出（`v.`/`n.`/`adj.`）。
- ipa：固定格式 `UK: /.../; US: /.../`，UI 转为 `英 [..]` / `美 [..]`。
- tense_form：中文标签数组（如 `复数`/`过去式` 等）。

## 后端设计
- 分层结构：
  - services：剪贴板、热键、选区采集、LLM、音频、复习调度、语法解析。
  - data：SQLite 访问与仓储（Entry/Review）。
  - utils：文本清洗、时间工具。
- 核心流程：
  1) 热键触发后优先读取选区文本（失败则监听剪贴板）。
  2) 检测英文文本后调用 LLM，获取翻译/词性/音标/词根/结构拆解/关键术语等。
  3) 精确查重并写入数据库。
  4) 语法解析（短语/文章）：解析句子结构，生成结构高亮与语法说明并展示。
- LLM 接口封装：
  - 统一 JSON schema 输出，字段名固定。
  - 解析失败时保留 raw_llm 原文，其他字段置空。
  - 失败/超时通过状态栏提示，不阻塞 UI。

## LLM 调用细节
- SDK：`openai>=1.0`，使用 `OpenAI(base_url, api_key)`。
- 消息结构：`messages=[{"role":"user","content":[{"type":"text","text": prompt}]}]`。
- 超时：通过 `LLM_TIMEOUT` 控制（默认 60s）。
- 关键环境变量：
  - `ARK_API_KEY` / `LLM_API_KEY`
  - `LLM_MODEL`（默认 `doubao-seed-1-6-lite-251015`）
  - `LLM_BASE_URL`（默认 Ark base_url）
  - `LLM_TIMEOUT`、`LLM_REASONING_EFFORT`

## 前端设计
- 交互组件：
  - 主窗口：列表 + 详情分栏。
  - 语法展示：结构高亮、语法说明（短语/文章详情页内）。
- 视图：
  - Word / Phrase / Article 列表。
  - 详情页：Word 字段与短语/文章结构高亮。
- 空态与错误态：
  - 无词条/无文章/无待学提示。
  - LLM/数据库错误提示与重试。

## 标签与关联词
- 标签：输入框保存为 JSON 数组。
- 关联词：搜索 Word 条目，下拉选择并保存关联 ID。
- 关联词展示：ID 转为文本显示在详情中。

## 安全与性能
- 权限：全局热键与选区采集需要无障碍权限。
- 数据安全：本地 SQLite 文件，不上传；后续同步需用户授权。
- 性能：
  - 选区采集/剪贴板监听 + 轻量文本判定。
  - LLM 调用在 QThread 异步执行，避免阻塞 UI。
  - 查询走索引，避免全表扫描。

## 部署与运行
- 打包：建议使用 PyInstaller 或 Nuitka 生成 macOS 可执行程序。
- 运行模式：
  - 后台常驻监听（托盘图标可选）。
  - 主窗口按需打开，不与热键冲突。
- 配置：LLM API Key、热键、阈值存放于 settings 表或配置文件。

## 后续扩展
- 本地/离线大模型切换。
- 词典音频接入与发音缓存。
- 高级查重（词形还原、模糊匹配）。
- 统计面板与学习数据可视化。
- 多端同步与导出。
- 语法解析模板扩展与规则库管理。

## 数据同步方案
- 阶段一：本地导出 JSON/CSV。
- 阶段二：上传到云数据库（用户授权）。
- 冲突策略：以时间戳或版本号合并，默认保留最新。
- 同步粒度：entries + reviews + review_logs。
