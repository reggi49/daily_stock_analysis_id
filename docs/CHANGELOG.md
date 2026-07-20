# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

> For user-friendly release highlights, see the [GitHub Releases](https://github.com/ZhuLinsen/daily_stock_analysis/releases) page.

## [Unreleased]
- [Repair] Telegram Push press before sending Markdown The converted text is strictly 3000 character chunking，Avoid long report triggers `message is too long`。
- [Improve] GitHub Actions Daily analysis workflow completion TickFlow Data source environment variable mapping，and converge README Data Source Stability Explained to Complete Guide。
- [Repair] WebUI Explicit on startup `--host` / `--port` no longer be `.env` in `WEBUI_HOST` / `WEBUI_PORT` Cover，Not passed on CLI The parsed runtime configuration is uniformly used for parameters.。
- [Improve] GitHub Actions: Daily analysis workflow（`00-daily-analysis.yml`）Added DingTalk notification environment variable mapping，Supports direct use of DingTalk robots in cloud scheduled tasks。
- [Repair] Web Changed to the home screen snapshot of the position page `include_realtime=false` Quick valuation，Skip ticket-by-ticket real-time market price prefetching and then display the position list first，Avoid long periods of blank waiting when external real-time market sources slow down。
- [Repair] Fixed the task status interface to separate legitimate emotions when rebuilding the report action field. `0` Treat it as a null value problem，Ensure that low-scoring reports can be corrected into sell recommendations based on scoring criteria。
- [Repair] Repair Agent Streaming replies are displayed as“（No content）”question，Instead prompt for streaming response interruption and preserve user messages，Avoid false positives for empty answers。
- [Repair] Fix desktop `WEBUI_HOST=*` / `WEBUI_HOST=[::]` Will be passed to the port detection and backend startup as it is, causing the problem of being unable to monitor.，Before starting, they are normalized to `0.0.0.0` / `::`。
- [Improve] `STOCK_LIST` Optional stock analysis supports Chinese commas、comma、semicolon、Common paste delimiters such as spaces and newlines，runtime、Scheduled hot refresh、CLI `--stocks`、Web Save and customize settings API Unified identification，And standardize it as an English comma when writing back。
- [Improve] New `NEWS_INTEL_AUTO_FETCH_ENABLED` single switch，Individual stock analysis after opening、Agent Analysis and market review meeting fail-open Automatically initialize and refresh RSS/Atom/NewsNow local information pool。
- [Improve] Web AI Added main stock context to suggestion page，Reuse recent analysis and stock index candidates，and improved zero-sample description of performance statistics。
- [Improve] Supplement the layout convergence of this settings page：Change the mobile category navigation to a horizontal scrolling list and ensure that the setting content is visible on the first screen，The desktop version retains classification descriptions and tightens field layout levels and spacing，Improve first-screen efficiency and configurable information density。
- [Documentation] in README Supplementary market data source configuration instructions in Quick Start（TUSHARE_TOKEN / Longbridge），It is still possible to leave when it is clearly not configured. AkShare、Baostock、YFinance Wait for the free source，The relevant prompts in the log do not affect the operation.。Synchronous updatesdocsChinese and English copies below README

<!-- New entry format：- [Type] Description（Type value：new features/Improve/Repair/Documentation/test/chore）-->
<!-- Each separate line is appended to the end of this paragraph，No category title required，Minimal conflicts when merging -->
- [new features] Feishu Push adds new file upload capability：`FeishuSender.send_feishu_file(file_path)` Pass App Bot SDK (`im.v1.file.create`) Upload files and send file messages；Webhook Mode fallback to sending file content text；New `FEISHU_SEND_AS_FILE=true` Configuration switches，After turning it on, Feishu will send reports in the form of files instead of text messages.。
<!-- 新条目格式：- [类型] 描述（类型取值：新功能/改进/修复/文档/测试/chore）-->
<!-- 每条独立一行追加到本段末尾，无需分类标题，合并时冲突最小 -->

## [3.27.0] - 2026-07-19

### 发布亮点

- feat: 新增 Codex App Server single-agent 问股实验原型，并保持 LiteLLM、Multi Agent、普通报告和定时任务等默认链路不变。
- feat: Web AI 建议页支持保存基于历史报告快照重算的决策风格信号，补齐去重、续期、失效和可审计 guardrail 语义。
- feat: 引入多策略观点结构化输出第一阶段契约，覆盖观点标准化、基础冲突检测、聚合元数据和报告兼容边界。
- improve: 报告页明确展示输入数据状态、来源、异常影响、处理建议和诊断码，并区分页面资讯与本次分析输入。
- fix: 修复 MiniMax 推理内容污染最终 JSON、字符串 `<think>` 包装兼容及多 Agent 风险覆盖后结论未按最终信号收敛的issue。
- fix: 补齐美股实时行情 PE/PB 估值字段、多市场工具描述和 macOS Gatekeeper 安装排障说明。

### 新功能

- 新增 #1743 Phase 6 Codex App Server single-agent 问股实验原型，仅开放三个既有Read-only Tool Surface 工具；默认 LiteLLM、Multi Agent、Deep Research、普通报告、定时任务与 Phase 1/2 `codex_cli` 路径保持不变。
- Web AI 建议页支持确认保存基于历史报告快照重算的决策风格信号，以 created/existing/refreshed 区分新建、原样复用和既有记录续期或维度补齐，并复用 profile-aware 去重与失效语义。
- 多策略观点结构化输出第一版新增策略观点标准化、基础冲突检测与聚合 metadata，作为 #1964 的阶段性基础契约；本版本不声明完成并发执行、完整策略调度 MVP 或前端完整多语言展示。

### 改进

- Codex Settings page only checks configuration、命令和所需协议是否允许尝试，用户保存后可直接提问；Chat 以服务端 `accepted` 事件提交issue并按实际 backend 停止。
- Web 报告页输入数据块沿用状态、来源、Warning和说明字段，在说明中补充异常影响、处理建议与诊断码，并区分报告页资讯和本次分析输入。
- 更新 Anspire 数据源的项目展示信息，并将 `get_stock_info` 工具说明从 A 股限定修正为覆盖 A 股、港股和美股。

### 修复

- 修复 MiniMax 分析与渠道 JSON 测试把推理内容和最终文本拼接后导致结果无法解析、无法持久化的issue；字符串Response仅剥离开头完整的 `<think>` 包装，并保留 JSON 内容中的同名字面标签。
- 修正多 Agent 内部 runtime facts 的 timeout 归因，并让 risk application 覆盖后的 dashboard 决策字段及一句话核心结论基于 post-risk signal 完成 finalization。
- 收敛多策略综合器语义：正确处理 Signal 枚举、缺失 signal、有效 opinion_count 和 deterministic synthesis，并兼容历史与外部 dashboard 的宽松字段形状。
- Codex 问股只接受 App Server 明确完成的终态回答，并统一整体时限、累计输出、事件、工具预算和进程回收边界。
- `codex_cli` 普通分析显式固定无人值守批准策略与Read-only沙箱，避免新版 Codex 在非交互任务中因请求人工批准而中断。
- yfinance 美股实时行情补齐 `pe_ratio` 和 `pb_ratio`，供估值分析和下游报告使用。

### 文档

- 补充 macOS 未签名、未公证 DMG 被 Gatekeeper 拦截时的架构选择、安全排查与官方安装包临时放行步骤。

## [3.26.1] - 2026-07-12

### 发布亮点

- feat: Web 首页新增历史、自选与今日工作区，支持批量分析、今日覆盖判断和评分排行。
- feat: 新增 A 股市场结构与题材主线上下文，并贯通报告、Agent、DecisionSignal 与 Web 展示。
- feat: 飞书支持文件形式推送报告，多 Agent 支持子 Agent 独立超时钳位。
- feat: 补齐内部 DSA Tool Surface、DecisionAgent 分歧摘要和 DecisionSignal profile 契约。
- fix: 统一报告动作口径，修复按股票代码批量删除历史记录和通知理由静默截断issue。
- fix: 改进 Web、桌面端、数据源缓存及发行包资源的稳定性。

### 新功能

- 新增 A 股市场结构与题材主线上下文，并在报告、Agent、DecisionSignal 和 Web 市场位置卡中复用。
- 飞书推送新增文件上传能力：`FeishuSender.send_feishu_file(file_path)` 通过 App Bot SDK (`im.v1.file.create`) 上传文件并发送文件消息；Webhook 模式回退为发送文件内容文本；新增 `FEISHU_SEND_AS_FILE=true` 配置开关，开启后飞书以文件形式发送报告而非文字消息。
- 多 Agent 编排 Pipeline 新增子 Agent 独立超时钳位：支持 6 个环境变量为 TechnicalAgent、IntelAgent、RiskAgent、DecisionAgent、PortfolioAgent、SkillAgent 各自配置独立硬上限，互不挤占配额；默认 0 表示关闭钳位。

### 改进

- 为 multi-agent DecisionAgent 增加内部低敏分歧摘要输入管线，作为 #1904 P1 解释输出的前置 plumbing；不改变 public API、dashboard schema 或最终解释字段。
- GitHub Actions 每日分析工作流补齐 TickFlow 数据源环境变量映射，并收敛 README 数据源稳定性说明到完整指南。
- Web 首页个股栏新增历史 / 自选 / Today's switch，保留历史分析默认视图，并支持在自选页一键分析全部或仅分析今日未覆盖股票、在今日页按评分查看当天分析排行；分块提交部分失败时保留已确认计数、停止后续提交并刷新任务列表。
- GitHub Actions 每日分析工作流新增钉钉通知环境变量映射，支持在云端定时任务中直接使用钉钉机器人。
- `STOCK_LIST` 自选股解析支持中文逗号、顿号、分号、空格和换行等常见粘贴分隔符，运行时、定时热刷新、CLI `--stocks`、Web 设置保存和自选 API 统一识别，并在写回时规范为英文逗号。
- 新增 `NEWS_INTEL_AUTO_FETCH_ENABLED` 单开关，开启后个股分析、Agent 分析和大盘复盘会 fail-open 自动初始化并刷新 RSS/Atom/NewsNow 本地资讯池。
- Web AI 建议页新增主股票上下文，复用最近分析和股票索引候选，并改进表现统计零样本说明。
- DecisionSignal 将 `decision_profile` 升级为正式 nullable 字段，统一 same-profile 查询、去重、续期和失效语义，并保持 create metadata `null` 兼容与 SQLite 幂等回填诊断。
- 设置页移动端分类导航改为横向滚动列表并保证设置内容首屏可见，桌面端保留分类说明并收紧字段布局层级与间距。
- 新增 #1743 Phase 6a 内部 DSA Tool Surface 契约，统一工具 schema、stock scope fail-closed guard、结构化错误、审计摘要和脱敏诊断边界，并明确外部 AgentBackend 工具能力仍需 wire-level probe 证明。
- `src/services/analysis_service.py` 在 `report` 详情层新增 `details.raw_result` 回填，补齐与 API/历史详情的报告载荷一致性；不改变 provider、model、Base URL 或配置迁移语义。

### 修复

- 按股票代码删除历史记录时分批清理全部匹配项，并拒绝空白代码，避免超过 10000 条后残留记录或无筛选删除。
- 市场结构概念排行为空或超时时复用本轮负结果，避免批量个股分析重复请求同一概念排行数据源。
- Windows/macOS 桌面后端打包显式收集并校验 AkShare `file_fold/calendar.json`，避免发行包因缺少交易日历 package data 导致热点题材和选股日线增强降级。
- 邮件、Telegram 与报告共享的 DecisionSignal 摘要完整展示已脱敏的理由，避免固定 120 字符在句中无提示截断；Telegram 按最终 Markdown payload 长度安全分片。
- 推送报告、Jinja 报告与历史 Markdown 导出复用 Web/API 的评分-action 口径：高分但旧 `operation_advice` 仍为持有且无降级原因时，建议文案与三类统计展示为买入；有明确 guardrail reason 时继续保留持有/观望。
- WebUI 启动时显式 `--host` / `--port` 不再被 `.env` 中的 `WEBUI_HOST` / `WEBUI_PORT` 覆盖，未传 CLI 参数时统一使用解析后的运行时配置。
- Web 首页今日状态与排行使用带时区偏移的历史时间戳和完整分页数据，在查询失败、跨服务器时区边界或任务完成刷新时保持安全且准确。
- Web 首页 stock bar 刷新序列化：并发或乱序返回时仅最新请求可清除 `stockBarRefreshFailed`，避免旧Response覆盖任务完成后的刷新结果。
- Web 持仓页首屏快照改用 `include_realtime=false` 快速估值，跳过逐票实时行情预取后先展示持仓列表，避免外部实时行情源变慢时长时间空白等待。
- 修复任务状态接口重建报告动作字段时把合法情绪分 `0` 当成空值的issue，确保低分报告能按评分口径纠正为卖出建议。
- 修复 Agent 流式回复在未收到完成事件就断开时被显示为“（无内容）”的issue，改为提示流式Response中断并保留用户消息。
- 修复桌面端 `WEBUI_HOST=*` / `WEBUI_HOST=[::]` 会被原样传给端口探测和后端启动导致无法监听的issue，启动前分别规范化为 `0.0.0.0` / `::`。

### 文档

- 在 README 快速开始中补充行情数据源配置说明（`TUSHARE_TOKEN` / Longbridge），明确未配置时仍可使用 AkShare、Baostock、YFinance 等免费兜底源，并同步中英文完整指南。

## [3.25.0] - 2026-07-03

### Post highlights

- feat: New `claude_code_cli`、`opencode_cli` generation-only local CLI backend，And complete the generation of backend status diagnosis、Preview、smoke test API and Web status panel。
- feat: The Taiwan stock report has complete access to the information of the three major legal persons，Coverage report rendering、LLM prompt、TWD currency designation、Closing call auction identification and fetcher toughness reinforcement。
- feat: New DingTalk group robot notification、Korean report output and AI Suggested decision-making style reassessment preview。
- feat: Agent `/chat/stream` Standardization progress event，The new phase begins/Complete、pipeline timeout and budget skip semantics。
- fix: Fix desktop WebUI host/port binding、macOS Homebrew CLI PATH Diagnosis、Discord Long report fragmentation、AlphaSift timeout、yfinance Dividend analysis、A Stability issues such as stock backtest code normalization。

### new features

- DingTalk group robot notification support `DINGTALK_WEBHOOK_URL` and `DINGTALK_SECRET`，and automatically slice long text to fit 20KB Limit。
- Report output language added: Korean（`REPORT_LANGUAGE=ko`），Coverage individual stock reports、Market review、Prompt Output language、Decision guardrails、Notification template label with Web Report details page copy。
- New `claude_code_cli` with `opencode_cli` generation-only local CLI backend，Reserve LiteLLM default path、Agent tool call boundary、per-preset extractor、smallest env allowlist with structured errors。
- Added new generation backend status、Preview and smoke testing API，and Web Generate backend status panel，Distinguish between lightweight checking and JSON smoke test，and keep it local CLI “Generate only、Does not support stock inquiry tool calls”the boundary of。
- Agent `/chat/stream` progress event New `stage_start`、`stage_done`、`pipeline_timeout`、`pipeline_budget_skipped`，Make up stage progress、Timeout and budget skip semantics。
- Taiwan stock reports institution Block display TWSE T86 / TPEx The original net trading amount of the three major legal persons，And inject the net sales and sales of the three major legal persons into the form LLM analysis prompt As Taiwan stock chip filter。
- New AI Suggested decision-making style re-evaluation preview interface and page preview。

### Improve

- Three major legal persons in Taiwan stock market fetcher Increase concurrent cache penetration prevention、TWSE/TPEx Circuit breaker by market、TPEx Date protection and remainder stage budget reuse，Reduce current limit、Probability of degradation due to endpoint failure and cold crawl timeout。
- AlphaSift Default dependencies pin updated to `9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`，Access wrapper data source caller-side timeout、Dongcai direct speed limit/Jitter、Policy Catalog Metadata and Defense Policies。
- When the stock selection task status polling encounters a recoverable timeout, the background task will still be automatically retried.，`.env.example` Supplement related timeout tuning items。
- Convergence stock analysis scores and DecisionSignal action Caliber，unify 80/60/40/20 segmentation，And record when risk control is downgraded raw/adjusted score、final action with reason。
- Web When switching categories on the left side of the settings page, the check sum will only be started for the first time when the relevant category is displayed. AlphaSift Auxiliary cards，Reduce cross-category residues。

### Repair

- Repair Windows Fixed input when starting backend on desktop `--host 127.0.0.1` cause `.env` in `WEBUI_HOST=0.0.0.0` Not effective、LAN cannot be accessed WebUI question；Desktop is still used by default `127.0.0.1`，Only in explicit configuration `WEBUI_HOST` Then bind according to the configuration。
- Fix desktop startup `.env` in `WEBUI_PORT` with Electron Automatic port selection is inconsistent，Issue causing windows to continue waiting for old ports and connection timeouts。
- Repair macOS Desktop from Finder/Dock Backend at startup PATH Can't see Homebrew Codex CLI question，and make it clear Codex CLI Main analysis and Agent LiteLLM Tool call diversion diagnosis。
- Repair Discord Long report push button 2000 The upper limit of characters is sent segment by segment.，encounter 429 The current limit will be `retry_after`/`Retry-After` Limited retries，Avoid only receiving the first half of the report after failure midway。
- Repair Japanese stocks、Korean stocks and Taiwan stocks `market_phase` Closing call auction identification，Avoid being marked as normal near the closing stage `intraday`。
- Repair A Stock analysis encounters shortcomings `belong_boards` When occupying a seat, the section to which it belongs will not be rechecked.、The problem of unstable display of related section module。
- Repair the big disk review in LLM When the title drifts or the text lacks section segments，Web Issues with push reports occasionally missing section main lines。
- Repair Web Large market review structured data turnover、Index point、rise and fall and high/low value formatting，Avoid floating point long tail or missing values `0.00` Direct display。
- Repair Web The stock column on the home page is stock-bar The problem of hiding emotion analysis and suggestion identification when the summary field is missing or the action suggestions cannot be classified。
- Repair Web Set up page scheduled tasks“Execute once immediately”The background thread is not transmitted `stock_codes` Issues causing task crashes。
- Repair `opencode_cli` static instructions，avoid global JSON-only Constraint influence `generate_text()` Free text output with market review。
- Repair yfinance 1.2.x will `Ticker.dividends` Return as single column DataFrame The problem of time-divided analysis being discarded，restore TTM Calculation of dividends per share and frequency of dividends。
- Fix the currency indication of financial amounts of Taiwan stocks，will TWD The amount is marked as“New Taiwan Dollar”，avoid in A Misread as RMB in stock context。
- Fixed backtest daily line completion will `605066.SH`、`SS605066`、`SS.605066` Wait A The stock equivalent code mistakenly requested the data source. `SS605066`，Problems leading to insufficient backtest data。

### Documentation

- New Agent `/chat/stream` progress event contract document，Explain the semantics of the new event field、Web Compatibility boundary、Verification and rollback methods。
- Sync local CLI backend Privacy/Deployment boundaries，clear local CLI Not an offline model，Docker/CI/The remote end needs to install and log in by itself.，DSA Do not read Claude/OpenCode credential File。
- update README Trilingual portal and market support boundaries，Explain Taiwan stocks `.TW` / `.TWO`、Three major legal person reporting areas、TWD Marking and Closing Bid Identification Ability Boundaries。

### test

- Three major legal persons in Taiwan stock market fetcher New live-smoke script vs. `@pytest.mark.network` Drift detection test，for non-blocking network-smoke Check scheduled tasks TWSE T86 / TPEx Core fields and parsing results。

## [3.24.1] - 2026-06-28

### Repair

- Correction Longbridge SDK The version constraint is to select the installable version by platform，Avoid desktop and Docker Posted in `pip install -r requirements.txt` temporal cause does not exist `0.2.75` version failed。

## [3.24.0] - 2026-06-28

### Post highlights

- feat: Expand Taiwan stocks、Japanese stocks、Korean stock market support，Covering Taiwan stocks suffix-only analysis、Information layer of Taiwan's three major legal persons、JP/KR Market review and cross-service market enumeration。
- feat: New GenerationBackend abstract、`codex_cli` local CLI backend、reserved Hermes local HTTP channels and prompt cache capability registry。
- feat: Web/API/Desktop Support multi-time scheduled push and runtime scheduler hot reconstruction，Web The settings page completes the first startup check and scheduled task panels。
- feat: Report link completion signal attribution、Single Stock Signal Timeline、Concept section rankings and notifications/Report related section display。
- fix: Repair Docker/Start probe、Static resources MIME、Backtest empty result、portfolio valuation、Notification Markdown、AlphaSift Stability issues such as data source and test environment isolation。

### new features

- Newly added Taiwan stocks suffix-only individual stock analysis MVP：`.TW`/`.TWO` The code is runnable YFinance Daily and near real-time quotes，and complete market identification、trading calendar and Prompt Capability boundary。
- Taiwan stocks `tw` incorporate DecisionSignal、Portfolio、Intelligence service layer、API enumeration and Web Filter，Prevent Taiwan stock analysis signals from being silently discarded by market normalization。
- Added data layer for Taiwan's three major legal persons fetcher `TwInstitutionalFetcher`，support TWSE/TPEx Source、date conversion、Single day cache and fail-open Degenerate。
- New additions to market review `jp`/`kr` market，Support Nikkei225/TOPIX、KOSPI/KOSDAQ Index review，and extend `MARKET_REVIEW_REGION`、Trading day filter and Web Set enumeration。
- New GenerationBackend Phase 1 abstract and explicit opt-in of `codex_cli` local CLI generation backend，Provide structured errors、fallback、stream downgrade and usage unavailable contract。
- New reserved Hermes local HTTP generation channel，provide JSON generation、no-proxy local call and saved secret endpoint binding。
- New Provider Cache Capability Registry，press provider、API surface、gateway with verification status Modeling prompt cache Ability。
- support `SCHEDULE_TIMES` Multi-time scheduled push，long run Web/API/Desktop After the process saves the scheduling configuration, it can be hot started, stopped or rebuilt. runtime scheduler。
- Added signal attribution analysis and Web AI Advice Page Single Stock Signals Timeline，And for automatic generation and historical backfill DecisionSignal write default `decision_profile` metadata。
- Market review、Web The report page and notification related sections complete the ranking of concept sections and the display of concept signals.。

### Improve

- TickFlow Extended to optional A stock day K、Real-time quotes、stock list/Name data source，and increase count、Integrity check and batch prefetch cache protection。
- harden JP/KR/TW suffix identify、Japan and South Korea stock seed index、YFinance quote/fundamental context，and JP/KR Portfolio with Market Light border。
- Web The settings page adds a first-time startup configuration check card and a scheduled task panel.，hide inside `SCHEDULE_TIMES` key，And improve the experience of closing and automatically disappearing repeated task prompts。
- Web Historical report details are no longer embedded AI Suggestion card，Structured decision signals are concentrated into AI Suggestion page，and retain source reports ID/URL Parameter precise positioning。
- `GENERATION_BACKEND=codex_cli` Common analysis and market review are no longer due to lack of LiteLLM API Key Misjudged to be unavailable，and use instead `--output-last-message` File read final response。
- local CLI backend Yes stdout/stderr Diagnostic preview and final response are subject to a total execution period cap，and complete the new generation backend Digital configuration maximum value verification。
- AlphaSift Default dependencies pin updated to `0a7b9cd59e81718f851890535241bc105d4ddc64`，and go by default DSA EastMoney Keep everything in mind provider、exposed source health Diagnosis。
- Docker Compose It is recommended to increase the default memory to 1G；daily analysis workflow Compatibility `STOCK_LIST` Matched to the same name Environment variables scene。
- Agent Path synchronization signal attribution prompt，Notification report summary is no longer expanded AI Decision signal details，Complete signals remain in Individual Stock Details and Single Stock Reports。

### Repair

- API Asynchronous batch analysis shared concept section ranking cache，Avoid repeatedly pulling multiple stocks from the same batch to rank the entire market concept。
- Repair notification Markdown The problem of table conversion mismatching the subsequent content to the wrong table header after an empty cell。
- Repair Market Light Regional normalization rejection `jp`/`kr`、Japan and South Korea historical list market stage summary misinformation `analysis_phase` and the default notification report is missing `dashboard.phase_decision` question。
- Fixed Docker installable Longbridge SDK The version is 0.2.75，and fix Docker Mirroring efinance Caused by the owner of the cache directory A Issues with stock data source downgrade。
- Today's valuation of position snapshot is changed to limited concurrent prefetch real-time price，Reduce the position when the position is large Web Combination page refresh timeout。
- Web After the homepage re-analysis is completed, it will automatically switch to the latest report on the same stock.，and fix Windows environment Web/Desktop static JS Resources may be `text/plain` Return to the problem that caused the black screen。
- Repair `--serve --schedule` with Web/API runtime scheduler Status out of touch、Immediately execute busy status error prompt、Rebuilding scheduled tasks to repeatedly monitor and start parameter semantics are lost。
- Repair `main.py --serve-only` Due to laziness on low-configuration hosts import Application exceeds uvicorn The problem of repeatedly restarting after starting the self-test window。
- Repair Web The backtest did not transmit the analysis date range、The stock code is not normalized, resulting in a successful response but an empty result.，and empty candidate、Insufficient quotes and illegal suffixes provide diagnostic information。
- Repair unsupported `GENERATION_BACKEND` Treated as an empty response/Template fallback、`codex_cli` stdout Duplicate counting towards output caps and main analysis JSON schema fallback The problem of semantic fallback。
- Docker Deploying Web Settings page save customization Webhook will be escaped when using the template `$content_json` placeholder，and restore at runtime，avoid Compose Redeploy expansion is empty。

### Documentation

- Complete the concept section ranking field contract、Notify reporting industry/Concept type column display and data source stability and troubleshooting diagram。
- supplement JP/KR/TW suffix-only MVP、`MARKET_REVIEW_REGION` save/Verification/backoff matrix、Market Light border and PR Submit process constraints。
- supplement local CLI backend privacy boundary、Non-offline model description、Docker/CI Login status restrictions and `codex_cli` experimental/limited Status。
- Supplementary backtest request link description，and synchronize updates `docs/full-guide.md` with `docs/full-guide_EN.md` Example。

### test

- New/Update Taiwan stocks、JP/KR Market review、GenerationBackend、`codex_cli`、Hermes、local CLI、runtime scheduler、Backtesting and regression testing related to concept section rankings。
- strengthen `tests/test_analysis_api_contract.py`、`tests/test_analysis_history.py` with `tests/test_backtest_service.py` temporary `.env` quarantine，avoid local truth `.env` Contamination system configuration testing。

## [3.23.0] - 2026-06-20

### Post highlights

- feat: DecisionSignal Extraction of report、Web show、feedback/posteriori、Alert notifications and combined risks，AI It is recommended that the signal enter a traceable closed loop。
- feat: Add new compliance RSS/Atom with NewsNow Information source intelligence pool，analysis、Agent And the market review can fail-open Reuse local information evidence。
- feat: Add Japan/South Korea suffix-only individual stock analysis MVP，support `.T`、`.KS`、`.KQ` The target passed YFinance Get market and technical context。
- feat: New Token Usage monitoring dashboard、legacy LLM usage telemetry and message stability audit，Enhance LLM Calling observability。
- fix: Fix run flow live Status、AlphaSift cache/Field compatible、Release notes diagnostics and Japanese and Korean stock input/Stability issues such as historical display。

### new features

- After the individual stock analysis history is successfully saved, it will be retrieved from the final report. best-effort Extract `DecisionSignal` decision signal，Reuse existing signals to remove duplication、Plan quality calculations and masking contracts。
- New Web AI Suggestion page、Position page latest active Signal summary、Historical reporting signal display and more complete signal details card，Show rating、Confidence、price plan、catalysis、Risks and Failure Conditions。
- New DecisionSignal User feedback、Signal Level Daily Posterior Evaluation、Statistics API with Web show，Use outcome/feedback sidecar table and retain the main signal table contract。
- will DecisionSignal Reuse to alarm、Notice and Portfolio Risk：Alarm trigger association latest active signal or create a minimum alert signal，Notification appended low-sensitivity signal summary，Position risk aggregation active sell/reduce/alert signal and hold fail-open。
- Add new compliance RSS/Atom Information source configuration、pull、Remove duplicates、Warehouse、Query、retention Check with basic security API，as individual stocks/Market Intelligence Pool Baseline。
- Information source added `newsnow` Type、`NEWSNOW_BASE_URL` configuration and `/api/v1/intelligence/sources/defaults` Default source initialization interface，Built-in popular financial association、Snowball Hot Stocks、Wall Street News Flash、Financial hot spots such as Golden Ten Data and the Gelonghui Incident。
- individual stock analysis、Agent Analysis and market review meeting fail-open Read local information/intelligence pool，and use the source link as news context and evidence input。
- Add Japan/South Korea suffix-only individual stock analysis MVP：hand lose `.T` / `.KS` / `.KQ` The code is runnable YFinance Daily and near real-time quotes，Supplementary market identification、trading calendar、Prompt Semantics、Web/API Type and Capability Boundary Documentation。
- New Token Usage monitoring dashboard and `/api/v1/usage/dashboard` interface，show LLM Total calls、Prompt/Completion Split、Model usage、Call type distribution and recent call details。

### Improve

- for `DecisionSignal` Complete the default life cycle、narrow homology relaxed Remove duplicates、On the contrary active Signal automatic invalidated、terminal The status is not available PATCH Resurrection and hyposensitivity market phase hints Extract。
- supplement Web decision-signals typed API wrapper Testing in isolation from contracts，and report history AI It is recommended that the query be closed to the accurate report and lazy extraction。
- DSA Data source link added Tencent day K direct connection fetcher、daily source health short term circuit breaker，and upgrade AlphaSift Default pin/runtime bridge。
- Enabled by default `DAILY_SOURCE=auto`、Sina snapshot priority、candidate level quote context with LLM ranking timeout/max tokens border。
- New legacy LLM usage provider/cache telemetry、message HMAC Diagnostic fields and common stock analysis legacy message stability audit，Do not change public Usage API、prompt or provider parameters。
- The strategy selection on the mobile side of the stock question page has been changed to the default button entrance.，After expansion, you can still select multiple strategies and automatically collapse them after sending.，Reduce occlusion of conversation content。

### Repair

- Fix run flow live SSE Desensitization、later stage LLM/Duplicate notification card、Data source aggregation card succeeds prematurely、Web Home page narrow sidebar squeezes stock information，And individual stock analysis automatically generates market context when running and diagnosing cross-talk problems.。
- Repair AlphaSift hot topics EastMoney Empty state when there is a transient and no cache、Desktop update hotspot cache retained，and `leader_stocks` / `stocks` Dual field compatibility issue。
- Repair Web AI Suggested page filters/Status update pagination、Price plan unilateral entry price display、Position latest Signal refresh、Details JSON Safe rendering and card interaction semantic issues。
- Only allow historical reports to exist explicitly `action` Lazy backfilling of the decision signal is triggered only when the action can be parsed.，avoid `decision_type=hold` Waiting for statistical caliber to incorrectly backfill in unclear scenarios。
- Repair #1390 P6 DecisionSignal Omissions in combined risk snapshot semantics and default aggregation notification presentation。
- Disabled by default `/api/v1/intelligence/sources/defaults` New source，Avoid public examples NewsNow Instances are enabled by default，unified at the same time 500 Response details are only logged、The response returns a generic error message。
- Web Stock autocomplete、Input validation、history/Task display and screening are completed in Japan and South Korea Yahoo suffix code、Commonly used Japanese and Korean stock indexes and stock pool naked code analysis，avoid `000660`、`005930`、`7203.T`、`005930.KS`、`035720.KQ` Wait for the scene to collapse、Enter by mistake A Share semantic or historical split display。
- Japan and South Korea stock analysis is used when local historical context is missing YFinance Daily pocket bottom structure K Lines and Technical Indicators in Context，Avoid reporting misrepresentation of Japanese stocks/Core market and technical data of Korean stocks are not available。
- Release Notes Build Query PR Preserve downgrade on author failure and output includes PR number and exception type warning，Easy to troubleshoot token、Permissions、network or GitHub API Abnormal。

### Documentation

- README、Complete guide and market support documents supplement Japanese stocks/Korean Stock Example（`7203.T`、`005930.KS`），and make it clear `.T/.KS/.KQ` Currently YFinance-only MVP。
- New DecisionSignal Decision Signal Special Document，Complete fields/API/Web/Alarm notification/portfolio risk/Posterior evaluation、Desensitization、Migration and rollback instructions，And shut up Web i18n Show borders。
- supplement AlphaSift Migration and fallback boundaries：clear `ALPHASIFT_INSTALL_SPEC` Explicit override semantics、`requirements.txt + DEFAULT_ALPHASIFT_INSTALL_SPEC` Compatibility boundaries with runtime。
- Supplemental Source Baseline Documentation，Description `NEWS_INTEL_*` Configuration、NewsNow Self-build suggestions、model/provider/base URL Do not change boundaries，and fallback paths for disabling or removing feed variables。

### test

- New/update DecisionSignal service、Extract、feedback/posteriori、Summary、Documentation、Notification、Alarm、Position risk、Web show and label regression coverage。
- New/update RSS/Atom / NewsNow Intelligence source service、API、Security check、Analyze access and configuration compatibility testing。
- New/Updated Japanese and Korean market identification、stock index、YFinance Quotes、Web Autocomplete and input validation testing。
- New/update LLM usage、run flow、AlphaSift、Release note generation and mobile interaction related regressions。


## [3.22.0] - 2026-06-13

### Post highlights

- feat: New DecisionSignal Independent storage and API、Run flow snapshot API and Web Run flow view，Complete suggested action structured fields and history/Backtest display link。
- feat: AlphaSift Hot topic links are upgraded to a new version of the contract，Support hot list、Subject details、fermentation route、Concept stock details、Caching and backing up data sources。
- feat: Individual stock analysis defaults to a summary of the day's market environment，and at high risk/Aggressive buying recommendations softened in ebbing environment。
- fix: Fixed the context of stock history inquiry target、Optional stock equivalent code matching、Low quality news filtering、Run flow desensitization with AlphaSift Stability issues such as hotspot details display。

### new features

- Add independent `DecisionSignal` storage、Repository、Service with `/api/v1/decision-signals` API，Support source/market/stocks/action/term/Stage deduplication、Query、Renew、status update、Lazy expired、Position filtering and sensitive information desensitization。
- Added analysis tasks and historical report running flow snapshots API，provide lanes、nodes、edges、events、summary waiting for unified contract，and from the task queue、Run diagnostics and AnalysisContextPack overview Build a masked data flow/information flow。
- Web active task、Historical reports and market review reports supplement the running flow view entrance，Support viewing running summary、topology node、Event flow and basic troubleshooting details。
- New AlphaSift Hot topic links：Backend provided `/api/v1/alphasift/hotspots` with `/api/v1/alphasift/hotspots/{topic}` API，Web The stock selection page has added a hot topic area and supports viewing of fermentation routes and concept stocks.。

### Improve

- Analysis of individual stocks added by current day/Summary of market environment for market reuse，Ordinary Pipeline with Agent analysis Prompt Can read low-sensitivity disk background；Added default enabled `DAILY_MARKET_CONTEXT_ENABLED` Configuration，Users can still explicitly close。
- Individual Stock Analysis and History/Eight optional states are added to the backtest display `action` / `action_label` Suggested action fields，Reserve `operation_advice` free text and `decision_type=buy|hold|sell` Statistical caliber。
- supplement Web decision-signals typed API wrapper Testing in isolation from contracts，Not connected yet UI。
- Improve runtime log context，supplement logger name、trigger source、Market statistics and real-time market prefetch link status，Easy to troubleshoot and schedule、API、Bot and data source downgrade path。
- A new entry for deleting position accounts has been added to the position management page.，Reuse existing account soft deletion interface，Accounts created by mistake will be removed from the default list、Snapshot、risk、The entry entrance and event list are hidden and the historical water is not physically cleared.。
- AlphaSift Dependency lock updated to `d038c52c468543726fc1fd830b53c27d3f09d6da`，And for the new version last-good snapshot、Daily history、Industry/concept provider cache、hotspot List、Theme fermentation route、Concept stock details、Last successful hotspot cache with post-analysis Meta information completion DSA runtime and Web adapt。
- AlphaSift By default, when reading hot topics, the last successful cache will be used first.，Manual refresh will pull and overwrite the cache in real time.，Try to roll back the old cache when real-time pull fails。
- AlphaSift The hot topic area is changed to collapse by default，Expand and select a specific topic to read the details；The fermentation route is changed to a timeline display with time markers，For concept stocks, you can click to enter the homepage and start analysis directly.。
- AlphaSift Hot topic data link reuses the same snapshot of Oriental Fortune sector changes，And from the real increase or decrease、The number of changes and trend analysis of high-frequency stocks、Continuous points、Stages and leading samples。
- AlphaSift Hot topic refresh is used when the contract layer returns a small number or missing key fields. DSA Oriental wealth sector changes directly linked to the list，Ignore less than 3 local hotspot cache，And complete the bottom field of the section。
- AlphaSift Hot topic cards are changed to a more compact multi-column layout，The list of concept stocks is changed to independent“analysis”Button triggers individual stock analysis；Details: Priority merger of Oriental Fortune constituent stocks、Flush analysis and sector changes lead the way and aggregate the fermentation timeline by day。
- AlphaSift Added details of hot topics DSA side 30 minutes disk cache，When you click on the same topic repeatedly, the fermentation timeline and concept stock details are reused.；Theme events are only displayed AlphaSift Contract timeline、Flush Summary、Real sources such as news search or Dongcai sector changes have been configured.。
- AlphaSift Hot topic news catalysis is changed to summary display：Configuration LLM Prioritize compression into a one-sentence catalytic summary of the subject，Fallback to local short summary when not configured or when call fails。
- AlphaSift Added options to the list of hot topics `include_details` Detailed prefetch，Web By default, it will be brought back in batches along with the hotspot list. Top Theme fermentation route and concept stocks and reusing the front-end memory cache；News catalyzed in LLM Change to local event summary when unavailable。
- Transformation `main.py --webui-only` initiating behavior：If FastAPI The listening port is already occupied，Start that fail-fast Throw an explicit error and exit。

### Repair

- After entering the question stock from the historical report, the follow-up question will continue to carry the current target.，When switching back or reloading an existing session, the basic current target can be restored from historical messages.，And the backend blocks incorrect stock tool calls when not explicitly switched、Exchange fragments and indicator abbreviations misrouted。
- Add and delete optional stocks to match Hong Kong stocks and uppercase and lowercase U.S. stock variants according to equivalent stock codes，avoid `00700`、`HK00700`、`00700.HK` or `aapl`、`AAPL` Misjudged as different targets。
- Tighten recommended actions legacy fallback：Negate/Avoid expression、Chinese financial context、`buy or sell`、Much guard Ambiguous text and English compound words are no longer mistakenly rendered as action badge；structured `action` time backtest/Historical trends and other entries are displayed according to the interface language action label。
- Stock news and multi-dimensional intelligence search have added domain name-independent admission filtering after relevance sorting.，Eliminate downloads/Installation package/App rating page and adults/Prostitution service spam page，And there are already valid bids in the same batch/Removed when industry candidate `score=0` background fill item。
- Fix historical reporting run stream snapshots returning with mixed time zone event timestamps 500 question。
- Fix run flow live SSE The problem of events not reusing the recursive desensitization rules of the snapshot layer，Avoid local paths、prompt/raw response、The agent's first class sensitive diagnostic field is in refetch brief exposure before。
- AlphaSift Hot topics are loaded by default without cache and the old adaptation layer is missing. `alphasift.hotspot` module returns empty state，No longer displayed as soon as you open the stock selection page AlphaSift Not ready；Manual refresh will still prompt that dependencies need to be updated。
- for THS Fermentation route supplementary list：When `stock_board_concept_summary_ths` When returning missing columns, only skip the source enrichment，Does not affect the details of hot topics API Return。
- Desktop publishing packaging uses frozen executable file runtime probe verification instead `alphasift.dsa_adapter`，avoid macOS PyInstaller When embedding a module into an executable file, the file system/zip Scan misidentified as missing。
- AlphaSift The detailed display of hot topics has been changed to give priority to using the back-end integrated `route`，avoid old `timeline` coverage news/LLM Summary；When manually refreshing the hotspot list, the same subject details cache will be bypassed simultaneously.。

### Documentation

- README with traditional Chinese README Quick Start Entry Supplementary Video Tutorial Link，And adjust the desktop client entrance copy to the client configuration tutorial。
- supplement `docs/alphasift-integration.md`：clear AlphaSift Lock commit Source、Hotspot contract boundaries、LLM/LiteLLM Compatible semantics and fallback path under shutdown switch。
- supplement #1381 runtime scope、Compatibility boundary、Official semantic basis and general release rollback instructions。

### test

- Cover #1381 backend runtime Compatibility verification：`tests/test_main_schedule_mode.py`、`tests/test_pipeline_daily_market_context.py`、`tests/test_daily_market_context.py`、`tests/test_daily_market_context_guardrail.py`、`tests/test_agent_executor.py`、`tests/test_config_env_compat.py`、`tests/test_config_registry.py` with `apps/dsa-web/tests/system_config_i18n.test.ts`。
- New/update AlphaSift Backend regression：`python -m pytest tests/test_alphasift_api.py -q`、`python -m pytest tests/test_docker_entrypoint.py -q`、`python -m pytest tests/test_main_schedule_mode.py -q -k "start_api_server_fails_before_thread_when_port_is_busy"`。

## [3.21.0] - 2026-06-07

### Post highlights

- feat: New Web UI Chinese and English interface language switching and Feishu App Bot notification mode，Improve the experience of multi-person deployment and enterprise notification scenarios。
- feat: Market review report、The historical entrance and individual stock column continue to be closed to structured data and unified Markdown/GFM rendering，Web/API Manually triggered entries are no longer blocked by trading days gate short circuit。
- feat: AlphaSift The stock selection link has been changed to resume background tasks.，and improve DSA LLM runtime bridge、Default adaptation layer presets and compatibility regression。
- fix: Repair the remaining Chinese characters in the English interface、diagnostic display、Runtime environment variable display、health check、Desktop update path、Workflow variable reading and multiple places Web Narrow layout problem。

### new features

- WebUI Added independent interface language status and Chinese and English switching entrance，Override main navigation、Home page、Login、Settings page and common control copywriting；UI Language and `report_language` decoupling，Do not rewrite reporting language links。
- Feishu notification adds new application robot（App Bot）mode，Support through `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_CHAT_ID` Configuration，No need to create additional custom bots。
- Web The market review report adds a dedicated display view，Historical entrances and real-time results on the homepage are used uniformly Markdown/GFM Render and hide individual stock-specific modules。
- New structure added to market review `market_review_payload`，Web、Historical details and push are unified and rendered based on structured data，and retain Markdown Compatible display。
- Added the default closed AlphaSift Stock selection tab，Pass `ALPHASIFT_ENABLED` clear control，and retain `/install` as an explicit repair path。

### Improve

- Web/API The manual trigger entry for market review will no longer be short-circuited due to trading day inspection or related market closures.；scheduled tasks、GitHub Actions Manually run and CLI The default entry remains the original trading day gate。
- AlphaSift Web Stock selection is changed to background task submission and status polling，Added display of resumable task status，Avoid external snapshots、Quote or LLM Browser long request timeout when slowing down。
- AlphaSift stock picking API converge with the service layer to `AlphaSiftService`，endpoint Only do routing parameter reception and error mapping。
- AlphaSift with DSA runtime LLM Compatible bridging changed to call-time injection，Reserve `provider/model/base_url/custom headers/fallback` semantic link，No persistent migration。
- Web The sidebar of the homepage no longer displays a separate collection of market review history，The latest market review `MARKET` Merged into individual stocks column，Sort by participation in latest analysis time，And reuse the selection of individual stock columns、Delete、Full reporting and historical trend viewing capabilities。
- Multi-Stock Alert Report Convergs Market Stages into Single Lines Below Overview `market status`，Data quality and restriction details are no longer duplicated under each stock summary。
- API Error response construction converges to shared helper，Keep existing errors envelope shape and lower endpoint Duplicate code。
- WebUI Bind the public network address or CORS Add a new runtime when fully open and administrator authentication is not enabled warning；Only increases observability，Do not block startup、Do not rewrite configuration。
- Database initialization added `schema_migrations` baseline Tag tables and idempotent records，for follow-up schema Evolution tracking；Do not migrate、Not cleaning up、Do not rewrite existing business table data。
- #1386 P6 Reuse market stage and AnalysisContextPack Public summary linkage alarm、Manual analysis of positions、history、Backtesting and notification display，No new database migration。

### Repair

- Web English interface completion backtest、Localization of copywriting related to portfolio risks and alarm rules，Avoid remaining Chinese filters in English mode、Buttons and enum labels。
- The dimensions of institutional analysis and performance expectations in comprehensive intelligence search are reused 180 day provider request window，Avoid missing financial reports in the default short news window、Research reports and other periodic financial materials。
- Web The individual stock columns and history cards no longer allow the market stage label to obscure the stock name in narrow layouts.。
- Free text questioning of stocks will no longer be TTM、PE、YOY Other financial abbreviations are mistakenly recognized as new stock codes.。
- [Repair] GitHub Actions Daily analysis workflow reads SearXNG Supported when creating a self-created instance address Variables Priority、Secrets rollback，Fix configuration only Variables time URL Invalid problem。
- Web/Changed to the selected state of left navigation on desktop border realize，Prevent the blue vertical bar indicator from overflowing the sidebar border；Sidebar expanded width 116px -> 136px，New rail compact mode。
- Windows The automatic update installation directory on the desktop is no longer pre-quoted.，Avoid paths with spaces from being triggered during automatic installation“Missing shortcut / not found Daily Stock Analysis.exe”System pop-ups。
- Agent Analysis path generation AnalysisContextPack overview Reuse the daily analysis context that has been dropped into the library before，Avoid showing that the daily line has been captured successfully `daily_bars_missing`。
- Revise the market review structure `breadth` usability judgment：It will not be issued when the market does not support it or the fetch fails. `breadth`，Front-end display“No data yet”，avoid misleading 0 value。
- Market review language behavior follows the overall situation `report_language`，And localize market labels and strategic blueprints in the Chinese scenario of US stocks，Avoid mixing in English strategy paragraphs。
- Docker Web The settings page is active when reading configuration `.env` When the file is missing, it will fall back and display the environment variable of the same name injected by startup.，And complete the relevant mounting boundary documents。
- The report page running diagnostics will distinguish between successful data source crawling and entering LLM Analyze input，The relevant news area is marked as a supplement to the report page/Subsequent search information，Avoid misreading of input data block status。
- `/health` Root path health check now always returns JSON，avoid static Web fallback Swallow health probe；`/api/health` with `/api/v1/health` remain compatible。
- `ALPHASIFT_ENABLED` Does not trigger when closed `alphasift` Runtime injection；After enabling it, the configured ones will be reused first. DSA/provider Configure and inject `LITELLM_*` with `LLM_*` runtime variables。
- complete openai-compatible scene base URL、`extra_headers` with `LITELLM_FALLBACK_MODELS` Compatibility path and fallback chain verification。
- Desktop/The image packaging link remains consistent with the runtime AlphaSift Adaptation layer preset，avoid `pip install` As an online repair dependency。

### Documentation

- clear Issue #777 UI Language switching adopts Cangnei `UiLanguageContext` + `uiText` realize，persistence key for `dsa.uiLanguage`，And supplement the corresponding visual acceptance guidelines。
- Clarify the market review display link、structured payload、verbal behavior、trading day gate Diff and rollback boundaries。
- supplement LLM / LiteLLM The compatibility key is Settings Backoff boundaries in display and validation contexts，Description does not need to be rewritten、Do not migrate、Do not clean up user's existing provider/model/base URL Persistence configuration。
- complete #1602 Run diagnostic caliber repair coverage，Note that only unified input and display caliber，The rollback method is regular release rollback。
- clear AnalysisContextPack P6 Documentation、Migration and rollback boundaries，and synchronize existing `SAVE_CONTEXT_SNAPSHOT` Arrive `.env.example`、Configure the registry、Web Setup help and complete guide。
- complete #1386 P7 Before the market/intraday/Entrance to after-hours analysis、Migrate、Rollback and user-visible instructions。
- for AlphaSift runtime bridge Add official compatibility basis，clear provider/model/base_url/extra_headers/fallback with fallback boundary。

### test

- Web direction execution `npm run lint`、`npm run build`、Related Vitest and smoke command；not set `DSA_WEB_SMOKE_PASSWORD` time smoke Use cases by design skip。
- Web Test runtime declaration Node `>=20.19.0 <27` with npm `>=10`，supplement localStorage Test the pocket for stability Vitest。
- supplement AlphaSift runtime bridge Static validation with packaging scripts，Cover `LLM_CHANNELS`、`LITELLM_FALLBACK_MODELS`、`alphasift.dsa_adapter`、`--collect-all alphasift`。

### chore

- Remove any issue / PR Screenshot assets mistakenly entered into the database during the acceptance process，And make it clear that one-time screenshot evidence should be retained in PR Description、Comment、attachment or artifact in，Not merged as warehouse file。

## [3.20.0] - 2026-06-03

### Post highlights

- feat: New AlphaSift Stock selection entrance、Automatic installation and stable adaptation layer，support Web Strategy execution、LLM Controlled enablement of reflow display and default closing。
- feat: Improve individual stock history、Select queue、market stage and AnalysisContextPack visibility，Enhance Web report and API structured contextual capabilities。
- feat: MiniMax Default model upgraded to `MiniMax-M3`，and complete relevant prices、Presets and test coverage。
- fix: Fix health checks、Windows Desktop updates and first-run coding、ETF daily line secid、LLM base_url Checksum Agent Stability issues such as daily line context misjudgment。

### new features

- Added the default closed AlphaSift Stock selection tab，Pass `ALPHASIFT_ENABLED` After opening, read the strategy through the stable adaptation layer and execute stock selection.。
- Web The left column of the home page is changed to the stock column，Remove duplicate display by stock，Top market review，Click on a stock to load the latest report，Support for code-by-code variants（.SZ/.SH/.SS）Normalization deduplication and merging。Keep all selected、Batch deletion and deletion confirmation entrance；Added batch deletion by stock code API `DELETE /api/v1/history/by-code/{stock_code}`。
- A new optional operation entry is added to the right column of the report details，Support checking whether the current stock is in the self-selected queue、Add or remove with one click；The market review report does not show this operation。
- A new optional operation button is added above the input area of the stock inquiry page.，After the user sends a message containing the stock code, it is automatically displayed to join the optional/Delete entry from your choice。
- Web A new drawer entry for historical trends of the same stock has been added to the report page.，Historical List Summary Supplemental Trends、Summary、Model and analysis time quote fields，Supports viewing historical analysis by current stock and loading more。
- AnalysisContextPack P4 hypoallergenic overview Access history details、Synchronous analysis of responses、completed task status and Web report page，Show data block status、Source、Summary of missing reasons and downgrades。
- #1386 P5 Added to individual stock analysis report `dashboard.phase_decision` Intraday Decision Guardrails，And limit high-confidence intraday buying and selling conclusions based on market stage and data quality before saving history.。
- #1386 P4a New `analysis_phase=auto|premarket|intraday|postmarket` API parameters，and in async task accepted、memory status、list、SSE and analysis pipeline Transparent transmission request stage。
- #1386 P4b Web Added final market stage label to report page，The task panel shows the request phase，and reuse AnalysisContextPack Low sensitivity data quality summary。
- MiniMax Channel model list upgrade：New `MiniMax-M3` and as default，Press official OpenAI-compatible Documentation support 1M input context（The project is conservatively registered as `<=512K` Price range：context_window 512K、`max_tokens` 128K，Correspond $0.6/M input、$2.4/M output，>512K Input price bracket is not modeled），Reserve `MiniMax-M2.7` with `MiniMax-M2.7-highspeed`，and retain `MiniMax-M2.5` legacy Price entries are configured with cost estimates compatible with existing users。Web settings page MiniMax Preset models and prices M3 Refresh。
- New AnalysisContextPack P1 Internal contract and desensitized serialization testing。
- Market stage low-sensitivity summary access history details、Synchronous analysis of responses and completed task status report metadata。

### Improve

- First run configuration verification to supplement missing information AI Key、empty STOCK_LIST、Telegram/Mail pair fields and Webhook URL prefix diagnostics。
- AlphaSift The stock selection entrance is at Web Move to the sidebar“Ask about stocks”below，close Agent/Research Assist Workflow。
- Docker Image build phase preset default AlphaSift Adaptation layer，Like desktop distribution packages, avoid additional installation during runtime。
- AlphaSift Stock selection becomes dependent on `alphasift.dsa_adapter` stable interface，Web The strategy list consists of AlphaSift Dynamically provided，No more hard coding on the front end。
- AlphaSift Stock selection page supplement Run ID、Number of snapshots、Quantity after filtering、Factor and risk details，Show true details when expanding candidates，And for the time being, only currently supported A stock market。
- Web New settings page AlphaSift Stock pick switch card，You can directly open or close the stock selection tab。
- turn on AlphaSift Switch first when picking stocks `ALPHASIFT_ENABLED` and check the adaptation layer availability，Automatically call the controlled installation interface when missing，No more requiring users to click to install。
- AlphaSift When it is turned on but the adaptation layer is missing，The strategy list and stock selection interface will serialize and automatically install the lock source，And force reinstall to overwrite the old version `alphasift` package。
- AlphaSift Stock selection page merges duplicate snapshot sources fallback Tips，and retain AlphaSift own Tushare Prioritize snapshot source logic。
- AlphaSift The stock selection page is at LLM Shown when rescheduling and downgrading warning/source error/parse error，and avoid mistakenly displaying local factor scores as LLM judge。
- Web The settings page no longer `ALPHASIFT_ENABLED` Repeatedly displayed as a common data source configuration item，This value is only used as“Start stock picking”Persistent state behind the button。
- AlphaSift Hide when closed Web left side“stock picking”Navigation entrance，Avoid misleading uninitiated users。
- supplement AlphaSift Stock selection custom strategy display logic，Avoid erroneous display when preset items are not matched“Balanced multi-factor”。
- New GET /api/v1/history/stocks end click code Grouping returns a list of unique stocks；New GET /api/v1/stocks/watchlist、POST /api/v1/stocks/watchlist/add、POST /api/v1/stocks/watchlist/remove The endpoint supports optional queue addition, deletion and query。STOCK_LIST Read and write remain as is，No automatic normalization；add/remove Normalized comparison to determine equivalent code variants。
- New useWatchlist hook Unified management of self-selected queue front-end status，Reuse SystemConfigService of STOCK_LIST Configuration items achieve persistence。
- AnalysisContextPack P5 Add data quality score、`fetch_failed` Status、Prompt data limit block and Web Hypoallergenic quality display。
- #1386 P2-full in AnalysisContextPack Prompt Cross-constraints on additional market stages and downgraded data in data restrictions，and correct the Chinese analysis Prompt Staged market tags。
- Notification report default sending path restores existing channels to be compatible with conversion and sharding logic，New renderer Capabilities are only retained as a basis for future expansion。
- When the associated section lacks type data, the section name is displayed in a single line.，Avoid generating entire columns `N/A` section table。
- Optimize Web Report details page information level，Collapsed auxiliary information after moving input data blocks and run diagnostics down to the main content。
- Intraday analysis complements the real-time market acquisition time、provider time、stale、fallback with partial/estimated mark，supply AnalysisContextPack Mapping input data limits。

### Repair

- Agent Analysis path generation AnalysisContextPack overview Reuse the daily analysis context that has been dropped into the library before，Avoid showing that the daily line has been captured successfully `daily_bars_missing`。
- Register /api/v1/health Route and join certification exemptions，Repair the path and return 404 and turn on ADMIN_AUTH_ENABLED After health probe received 401 question。
- Windows The local first run environment check is compatible with non- UTF-8 console output，and will `requirements.txt` Comment changed to ASCII To reduce the probability of dependency installation failure under the default code page。
- AlphaSift DSA Adaptation layer is enabled by default LLM rearrange，Backend explicit request `use_llm=True`，Stock selection page display LLM score、judge、Coverage and concerns。
- AlphaSift Embed DSA Time multiplexing DSA parsed LLM model、Channel and key configuration，avoid Web configured LLM But stock picking LLM rearrangement still due to lack of provider key Downgrade。
- AlphaSift Stock selection reuse DSA LLM Filter undeclared hosting when routing provider alternative model，And add the declared channel model to the fallback chain，avoid residue Gemini fallback Override available DSA channel。
- AlphaSift Default installation source changed to locked commit of trusted GitHub address；Desktop mode automatic installation does not require an administrator session，Non-desktop deployment requires administrator authentication session，and continue to limit installation sources。
- Repair Web turn on AlphaSift When installing first and then writing the configuration, the default closed state cannot be opened.。
- AlphaSift The status and installation interface will no longer return `install_spec` plain text，Return only `install_spec_is_default` Other non-sensitive status fields。
- AlphaSift State detection distinguishes optional dependency missingness from unexpected exceptions，Abnormal scene records warning and returns non-sensitive diagnostic information。
- adjust AlphaSift filter call compatible：`screen` to `max_results` Lord and support history `max_output` keywords，Also allows policy transparent transmission to align front-end manual policy parameters。
- AlphaSift Web Stock pick request uses independent long timeout，avoid opening LLM Commonly used after rearrangement 30 seconds API Timeout early interrupt。
- Desktop packaging stage preset AlphaSift and collect the adaptation layer，Avoid asking the administrator to automatically install the package when it is running。
- AlphaSift Automatic installation only in `status` Diagnosed as `missing_module` triggered when（Only module missing scenario）；The adaptation layer can be imported but runtime exceptions are no longer automatic `pip install`，Instead return `424` and retain diagnostics，Avoid masking real runtime failures as reinstallations。
- Close up Web The Chinese interface remains with English copywriting and settings pages help notch，The backtest page is changed to Chinese display，and let Web The settings page only displays registered configuration items with descriptions。
- Windows Desktop automatically updates and explicitly reuses the current installation directory during silent installation，Avoid failure to uninstall old version files in custom installation directory scenarios。
- Windows Installer retries old uninstaller `_?=` Add quotation marks to the installation directory parameters，Fixed issue where old version installation returns when path with spaces 2 causing automatic updates to fail。
- Windows Desktop automatically updates to NSIS of `/D=` Directory parameters are automatically quoted when containing spaces，Avoid installation location registry truncation。
- Reinforcement LLM channel base_url Verification，Avoid parsing differences caused by SSRF bypass。
- Correction efinance ETF daily line Eastmoney secid routing，avoid Shanghai stock market ETF Pressed on the Shenzhen Stock Exchange quote id Query results in daily line being empty。

### Documentation

- clear AlphaSift with LiteLLM Compatibility boundary：bridge only DSA Declared provider/model/base URL Inject for call period，Wrong `.env` do provider/model Route migration；Fallback mode is close AlphaSift and restore the original `LITELLM_*`/`LLM_*` Configuration。
- clear AlphaSift Reuse only DSA Existing LLM/LiteLLM Configuration semantics，No new addition `LITELLM_MODEL`、`OPENAI_MODEL`、`OPENAI_BASE_URL`、`LLM_TIMEOUT_SEC` Equivalent model semantic transfer；Failure prompts and fallback paths uniformly use the existing system configuration links.，Only affects AlphaSift Stock picking ability itself。
- clear AlphaSift Automatic installation source locking、`missing_module` Boundaries on abnormal runtime behavior，and LLM/provider/base URL Fallback path with custom channel，Facilitates problem tracing and rollback to original LLM Configuration。
- Clarify the historical trend of the same stock. Add a new model field to display metadata for historical snapshots.，Does not affect runtime LLM Provider/Model/Base URL Routing and configuration migration and cleanup；The rollback method is to roll back this change according to the regular release。
- clear #1311 compatibility boundaries：The rendering layer only consumes the analysis results `model_used` Display fields，Unmodified `wechat/slack/feishu/telegram` sender Send link，Not triggered provider/model/base_url Compatible with migration。
- clear AlphaSift Lock commit of `alphasift.dsa_adapter` Contract basis，and currently DSA API/Web Compatibility boundaries for calling structures。
- clear Settings page pair LLM Configure only display grouping and field merging，Not overwritten or triggered LLM Migrate/fallback path；Compatible with existing `LLM` Configuration saving and rollback semantics。
- New AnalysisContextPack P0 Contextual inventory。
- Complete the alarm center P8 Documentation and configuration closing instructions，clear legacy JSON、Advanced rules、Web/API、Docker、GitHub Actions with Desktop border。

### test

- Synchronous updates `llmProviderTemplates`、LiteLLM fallback pricing with MiniMax Default related single test，Assert new default model。
- supplement ETF Daily data source routing、Enter variant、fallback with MA Field regression coverage。

### chore

- Added notification reporting channel capability portrait、PreparedMessage and structure perception Markdown Sharding infrastructure，for #1311 Omni-channel rendering adaptation base。
- Preset enterprise WeChat、Feishu、Telegram、DingTalk、Slack Platform renderer metadata，The default push report entrance and visible layout will not be changed for the time being.。

## [3.19.0] - 2026-05-29

### new features

- landing #1391 Phase 1 Run Diagnostics Minimal Link：Task/SSE Append trace_id，And record daily and real-time market conditions ProviderRun Snapshot。
- Alarm center added P7 Market traffic light structured rules，support `market_light_status` with `market_light_score_drop` and reuse existing worker、Trigger history、Notifications and Cooldown Links。
- landing #1391 Phase 2 Run diagnostic summary：Generate user-readable RunDiagnosticSummary，Provide historical report diagnostics API Copy text with desensitization。
- landing #1391 Phase 3 Run diagnostic visibility：Report details and task panels are collapsed by default to display running status、trace with reproducible troubleshooting information；Backend passes `api/v1/history/{record_id}/diagnostics` with `context_snapshot.diagnostics` Provide historical link backfill。
- New AnalysisContextPack P1 Internal contract and desensitized serialization testing。
- New AnalysisContextPack P2 builder，From ordinary analysis pipeline Already artifacts Assembling the internal context package。
- Added visible conversation context compression that is turned off by default，support Web switch、Agent Advanced preset、Rolling summary and recent round original text protection，Reduce long sessions token consume。
- Stock auto-complete index supports by default from GitHub main Refresh remotely and cache locally，Web/CLI Automatically downgrade to built-in index when analysis entry fails，Reduce the probability of old abbreviation contamination analysis after decapitation and name change。
- General analysis and Agent runtime Prompt Access AnalysisContextPack Hypoallergenic summary，keep history/API/Web Output compatible。

### Improve

- `scripts/fetch_tushare_stock_list.py` Yes A medium band `XD`/`XR`/`DR`/`N`/`C` The name of the prefix is backfilled and corrected，Used by default for the auto-complete refresh process。
- Web The routing page is changed to load on demand，Reduce the size of the first packet and increase the recovery prompt for route loading failure。
- Web full report Markdown Drawers changed to load on demand。
- Added market phases to infer baselines and clarify premarket、intraday、lunch break、Nearing closing、After-hours and non-trading day semantics。
- Added running market stage context construction and degradation testing。
- The settings page configuration help is completed in stages. Web Actual display of settings page/Bilingual copywriting in Chinese and English with configurable fields，Cover Agent、backtest、report、Notification route、system runtime、AI legacy、Advanced configuration of data sources and notifications。
- P2-min：LLM Prompt Inject market stage context。

### Repair

- Stock autocomplete index generation is missing `pypinyin` when changed to direct failure，Avoid writing downgraded indexes with missing pinyin fields。
- Normalize Tencent real-time market trading volume into stock caliber，Avoid magnifying the change in quantity and energy and misleading the analysis report。
- Docker Default deployment removed `.env` Single file mount，avoid WebUI Save configuration time `os.replace` Update mount point trigger `Device or resource busy`。
- Convergence #1391 Phase 0 A Stock code ownership boundary：complete `SH`/`SZ` Attribution consistency of prefix scenarios，clear `data_provider/baostock_fetcher.py`、`data_provider/pytdx_fetcher.py`、`data_provider/tushare_fetcher.py` The repair scope of this round。
- Repair `STOCK_LIST` Use bare A stock code Baostock and other data sources fallback internal format conversion，Keep user configuration and continue to use it 6 digit stock number。
- Windows Desktop automatic updates change to silently executing the installer after the user confirms restarting the installation.，and clean up the process references after stopping the built-in backend，Reduce installer prompts“Daily stock analysis cannot be turned off”probability of。
- macOS Migrate runtime configuration to user data directory on desktop，and in the old `.app` Migrate files within the package while they are still accessible `.env`、Database and logs，Avoid subsequent replacement and reconfiguration after upgrade。
- restore Agent/Extraction of related sectors and sector linkage fields in historical compatible snapshots，Fix the missing report on the new home page“Sector linkage”regression problem。
- Correction Web Setting up help legacy Alarm JSON Description of field names and silent period delivery semantics。
- Repair Web Chinese setting page in data source、Notification、System and Agent Configuration header for the zone、Description and key drop-down options are missing。
- Fixed the problem that stock session switching and homepage tasks may remain after reconnection Agent/Analyze issues with task in progress status。
- Ask about stocks single-agent New provider-aware trace split track，Reserved across rounds DeepSeek V4 thinking + tool-call of `reasoning_content` Agreement materials with tools。
- for Akshare Sina/Tencent A The stock history bottom-up interface increases the call-level timeout，and complete Tushare `605xxx` Shanghai code routing regression test，Avoid scheduled analysis from hanging due to unresponsive data source。
- will `exchange-calendars` The lower limit of dependency is raised to `4.13.0`，avoid pandas 3 Environment import transaction calendar time reason Timedelta unit `T` Failure causes analysis to fail。
- interactive commands（DingTalk session、Feishu conversation、Telegram）Triggered analysis results are only returned to the source session，No longer simultaneously broadcast to static notification channels。
- adapt Longbridge OAuth 2.0 Certification and token Cache recovery，Avoid new background without Legacy Access Token The duration bridge data source was misjudged as not configured.。
- Longbridge OAuth Path is currently SDK Not supported `OAuthBuilder` / `Config.from_oauth` clear log downgrade，avoid Linux/Docker Only old SDK The build fails when。
- Compatible YFinance Date line returns scenario with unnamed date index，Avoid missing after standardization `date` Column leads to U.S. stocks daily line fallback interrupt。

### Documentation

- New #1391 Phase 0 Run diagnostic contract document，clear trace_id、diagnostic summary、Critical link scope and desensitization/fail-open/retention border。
- Complete the alarm center P8 Documentation and configuration closing instructions，clear legacy JSON、Advanced rules、Web/API、Docker、GitHub Actions with Desktop border。
- Note that this desktop repair only covers Windows NSIS Update installation link and backend process life cycle cleanup；Save settings unchanged/Model runtime cleanup semantics。Remove previously mistakenly entered `docker/Dockerfile` `npm registry` change，Segregation of responsibilities for recovery deployment builds and update fixes。
- New AnalysisContextPack P0 Contextual inventory，Clarify field quality status、Existing state mapping and first release pack border。
- clear #1391 Phase 2 The structured detection alarm is a non-configuration migration signal：`agent_max_steps`/`agent_orchestrator_timeout_s` Illegal value will fallback to default and generate log alerts，New diagnostic link is only added `context_snapshot`/`RunDiagnosticSummary` Read and write fields，Do not rewrite `litellm_model`、`agent_litellm_model`、`openai_base_url`、LLM channel Routing or configuration migration semantics。
- supplement #1391 Phase 3 Compatibility Notes：Logging backend diagnostics persistence、Historical query and notification writeback link change boundary and rollback strategy，And complete the back-end access control level verification requirements。

### test

- Convergence #1391 Phase 3 backend/API with Web regression check：`./scripts/ci_gate.sh`、`test_pipeline_market_phase_context.py`、`test_analysis_api_contract.py`、`test_analysis_history.py`、`npm run lint`、`npm run build`。
- execute `python -c "import exchange_calendars as xcals; xcals.get_calendar('XSHG'); print('ok')"` Passed verification，To override import and trading calendar initialization compatibility。

## [3.18.0] - 2026-05-21

### Post highlights

- feat: The alarm center expands to P2-P6，Complete background evaluation、Real notification results、business cooling、Technical indicator rules，and discretionary stocks / Position / Account linkage rules。
- feat: Individual stock analysis supports strategy selection，Add hot topics、event driven、Growth quality and expected revaluation strategies，And for HK/US Report supplements fundamentals、financial summary、Shareholder Returns and Related Sectors。
- feat: New Finnhub / AlphaVantage US stock data source adapter，Expand the daily line of US stocks failover chain，Improve U.S. stock prices and gain resilience。
- fix: Fix desktop release packaging、Analysis status interface、AlphaVantage Increase or decrease、Real-time valuation of positions、Alarm history deduplication、Database cold start and fallback pricing Registration and other stability issues。

### What's Changed

- feat: Add alert-center P2-P6, Web strategy selection, HK/US fundamental context, static-report financial sections, and Finnhub / AlphaVantage US-market fallback.
- improve: Refine LiteLLM parameter recovery, yfinance currency/dividend handling, RSI calculation, market-review presentation, stock-news relevance ranking, and report table rendering.
- fix: Harden desktop packaging/update assets, completed analysis-status responses, AlphaVantage pct_chg routing, portfolio realtime snapshots, alert trigger dedupe, DatabaseManager cold start, and fallback pricing registration.
- docs/tests: Add beginner setup and settings-help docs, document compatibility/rollback boundaries, and extend regression coverage for API, alert, packaging, and release paths.

## [3.17.1] - 2026-05-16

### Post highlights

- fix: Desktop Windows / macOS Packaging script explicitly closed electron-builder Automatic publishing，avoid tag Built due to missing `GH_TOKEN` Failed after local packaging was completed；Release workflow Continue to be responsible for uploading and publishing products。

### What's Changed

- fix: Add `--publish never` to the Windows and macOS Electron packaging scripts so tag builds only create local artifacts and GitHub Actions handles release upload/publish.

## [3.17.0] - 2026-05-16

### Post highlights

- feat: New Alert API MVP，Support alert rules CRUD、Start and stop、One-time testing and triggering/Notification result query，First edition coverage `price_cross` / `price_change_percent` / `volume_spike` and keep legacy Configuration compatible。
- feat: Notification gateway new ntfy with Gotify First-class channel，And complete notification noise reduction、Static channel isolation、Diagnosis、Web test and GitHub Actions env Check against。
- feat: Windows Desktop installation version accesses the automatic update installation link，Support background download、Confirm restart installation、Runtime file backup/Recovery and release product metadata verification。
- improve: Ranking of new concepts in market review、Popular stocks、Underlying data sources such as daily limit pools，Support index rise and fall color semantic configuration，And write the review results into the history record。
- improve: Web Settings page support `.env` Configuration backup import/Export and notifications/Agent Regional local errors are covered；Report new `REPORT_SHOW_LLM_MODEL` Switch control model information display。
- improve: Docker The startup portal automatically repairs the mount directory permissions and downgrades to the console when the log directory is unwritable.，Reduce manual remediation steps for common deployments。
- fix: More gentle degradation when data sources lack credentials or connection fails，Longbridge / Pytdx Add to cooling，Avoid outputting high-confidence buy conclusions when there is a lack of capital flow。
- fix: Analysis and reporting link compatible OpenAI-compatible `content_blocks` response，Normalized strategy price field，And fix the problem of large disk review scrolling and historical record loss.。
- docs: Completion notice、Alarm center、desktop packaging、README / guide and PR title Governance Notes，Clarify multiple configuration compatibility boundaries and rollback paths。
- test: increase Alert API、Notification noise reduction/routing、Docker entrypoint、Data source prefetching、Regression coverage such as desktop update link and analysis history。

### What's Changed

- feat: Add an Alert API MVP with rule CRUD, enable/disable, one-shot testing, trigger history, notification results, and legacy config compatibility.
- feat: Promote ntfy and Gotify to first-class notification channels with Web tests, routing, Actions integration, diagnostics, and noise control.
- feat: Add the Windows desktop auto-update install flow with runtime state backup/restore and release artifact metadata verification.
- improve: Extend market review data sources, add configurable index color semantics, and persist market review results into analysis history.
- improve: Add Web `.env` backup import/export, local settings panel error boundaries, and a report model visibility toggle.
- improve: Harden Docker startup by repairing mounted directory permissions and falling back to console logging when mounted logs are not writable.
- fix: Cool down unavailable optional fetchers, reduce noisy Longbridge/Pytdx retries, and downgrade buy advice when capital flow data is missing.
- fix: Handle OpenAI-compatible `content_blocks`, normalize strategy price fields, and recover market review scrolling/history behavior.
- docs/tests: Update notification, alert, desktop packaging, README/guide, and governance docs; add focused regression coverage for the new release paths.

## [3.16.0] - 2026-05-10

### Post highlights

- feat: Web Home page new“Market review”Trigger entry、Task polling and direct reporting after completion；The first startup configuration status can prompt the gap and boot to the system settings。
- feat: Add notification routing policy，Support pressing report、alert、system_error Narrow notifications to specific channels；Web The settings page supports one-click testing of notification channels。
- feat: New configuration item help portal and multi-language help copywriting infrastructure are added to the system settings page，The first batch of self-selected stocks covered、LLM master model、LLM channel、Feishu Webhook with WebUI listening address。
- improve: Market review API、CLI、Bot share `build_market_review_runtime` assembly path，complete `litellm_model` / `llm_model_list` with legacy key Fallback instructions。
- improve: Individual stock report operation suggestions combined with support/pressure、Quantity、Calibration of chips and main capital flow，Buy less/Sell violent switch，and reinforce Agent Decision making。
- improve: Docker Mirroring supports non- root User runs，LiteLLM Dependency constraints are relaxed to subsequent safety 1.x Repair version。
- fix: Correction LLM Channel testing in progress `Model disabled`、provider blocked etc. misclassification，Avoid being falsely reported as network anomalies。
- fix: The daily line of Hong Kong stocks skips the built-in historical data source that does not support Hong Kong stocks.；Beijing Exchange `BJ` Prefix with `.BJ` Suffix code verification remains consistent。
- fix: Web Observability of market review button、Windows fallback Lock process detection and catalytic clue display are more robust。
- docs: Added documentation center and configuration help maintenance instructions，clean up README、Full guide vs. interim in configuration guide PR/Document synchronization instructions。

### What's Changed

- feat: Add a Web home market-review trigger with task polling and inline report display; setup status now points users to missing configuration.
- feat: Add notification routing by report, alert, and system_error; add one-click notification channel testing in Web settings.
- feat: Add settings field help infrastructure with multilingual help text for the first batch of core configuration fields.
- improve: Share `build_market_review_runtime` across API, CLI, and Bot market review paths; document `litellm_model` / `llm_model_list` and legacy key fallback behavior.
- improve: Calibrate stock advice with support/resistance, volume, chips, and main-force capital flow; strengthen Agent decision fallback behavior.
- improve: Run Docker images as a non-root user and relax LiteLLM constraints to allow safe future 1.x fixes.
- fix: Classify `Model disabled`, provider blocked, and related LLM channel test errors more accurately instead of reporting them as generic network failures.
- fix: Avoid unsupported built-in historical providers for Hong Kong daily data; align Beijing Stock Exchange `BJ` prefix and `.BJ` suffix validation.
- fix: Improve Web market-review observability, Windows fallback lock probing, and market catalyst snippet rendering.
- docs: Add the documentation index and settings-help maintenance guide; remove temporary PR/doc-sync notes from README and user-facing guides.

## [3.15.0] - 2026-05-05

### Post highlights

- LLM Channel configuration experience continues to upgrade：New Anspire OpenAI-compatible Gateway access，And complete the default settings of commonly used service providers、official source、Capability label、Configuration considerations and GitHub Actions Explicit mapping。
- Web LLM Configuration detection is more diagnostic：Segmentation error reason，And support users to explicitly trigger JSON、tools、vision、stream runtime smoke。
- LLM Runtime configuration cleanup is more robust：Clean hosting only provider Failure runtime selection of，and retain `cohere/*`、`google/*`、`xai/*` Wait for direct connection provider Compatible semantics。
- Notifications and Bot Enhanced state observability：Customize Webhook support JSON body Template，Bot `/status` Show a more complete LLM、Agent and notification channel status。
- Market review、Real-time alarm、Agent weak The bottom line and position valuations continue to strengthen，Lower default value override、Shortage pollution and configuration troubleshooting costs。

### new features

- support `ANSPIRE_API_KEYS` Default access Anspire OpenAI-compatible Large model gateway，And in LLM Channel Editor Supplement Anspire Open Default。
- Customize Webhook support `CUSTOM_WEBHOOK_BODY_TEMPLATE` JSON body Template，Easy to adapt AstrBot、NapCat and self-built push service。
- Large market review structured block adds large market traffic light conclusion，Output based on disk surface temperature green/yellow/red、Core reasons and action suggestions。
- EventMonitor support `price_change_percent` Increase and decrease threshold rules，Real-time alerts can be triggered in rising or falling direction。
- Web LLM The channel editor adds commonly used service provider configuration templates and presets，Cover MiniMax、Volcano Ark、OpenAI、Claude、Gemini、Kimi、Qwen、GLM、Bean bags and other imports。

### Improve

- Web LLM Configure detection to supplement segmentation error classification，And add an explicitly triggered JSON/tools/vision/stream runtime smoke；The default testing and saving process remains unchanged，The detection result is only used once for the current configuration. best-effort Diagnosis。
- Bot `/status` Show unity LLM master model、Agent model、channel model、YAML Configuration and more notification channel status。
- Web LLM Channel editor display provider Capability label、Official source links and configuration precautions；These tags are for configuration reference only，It does not mean that the runtime capabilities have been verified.。
- draw out Web LLM provider preset Single template data source，Keep existing configuration save semantics unchanged。
- complete LLM provider channel in GitHub Actions Explicit mapping in，and sync `.env` Examples and Configuration Documents。

### Repair

- Agent weak Completeness is compromised due to lack of scoring in the model、Trend、Operation suggestions or dashboard Priority is given to retaining local trend analysis results during critical blocks，and only fill in the truly missing dashboard fields，Prevent homepage ratings from being defaulted 50 Cover。
- Unified position snapshot output current price、Market value、Floating profit and loss、Yield and price meta-information，Avoid price shortages or stale Price pollutes position valuations。
- LLM Channel testing supplements structured diagnosis and setup page troubleshooting tips，Easy to locate provider、model、Base URL and authentication configuration issues。
- clear runtime Clean up compatibility boundaries：Hosting only provider（`gemini`、`vertex_ai`、`anthropic`、`openai`、`deepseek`）Trigger invalid value cleanup before saving，`cohere/*`、`google/*`、`xai/*` direct value button legacy Compatibility paths preserved，No silent migration or overwriting。
- will MiniMax Default adjusted to official OpenAI-compatible Base URL and current model example，and add MiniMax、Volcano Ark、LiteLLM Compatible sources and fallback instructions。
- Remove screenshot recognition pair Gemini 3 Vision Outdated degradation logic for models，The default inference uses the current Gemini Model configuration。

### Documentation

- perfect LLM provider Configuration document，Additional configuration options、Actions Variable comparison、Detect boundaries at runtime、Error reason Troubleshooting and rollback paths（#1180）。
- supplement LLM The official source of Channel Editor、Depend on compatibility window、Runtime model cleanup rules on save，And the description of the old configuration fallback path。
- for `cohere/*`、`google/*`、`xai/*` Direct connection semantic supplement official provider/model Description、`litellm>=1.80.10,<1.82.7` Compatible basis reference，And make it clear that the example model name is only a configuration reservation behavior description and not a usability endorsement.。
- clear `price_change_percent` Event alerts only extend configuration and runtime rules，unchanged model/provider/base URL/LiteLLM Compatible semantics；Fallback path is closed/Remove Event Monitor Configuration。
- sync README、DEPLOY、full-guide、Anspire、AIHubMix with SerpAPI Related instructions，Unify external links、Configuration caliber and review consistency instructions。

### test

- complete AI Configuration page with `task_queue` of LLM Runtime cleanup/Synchronous regression evidence：Retained when restoring channel model fallback、Runtime selection not silently cleared during model list editing，Cleaning fails when the channel has no available models. runtime Quote，and override legacy key with `cohere/*`、`google/*`、`xai/*` direct connection provider Preserve semantics。
- Cover Web LLM Configuring Segmentation Error Classification for Detection，and JSON、tools、vision、stream runtime smoke Explicit trigger path for。

## [3.14.2] - 2026-04-30

### Post highlights

- Market resumption extends to Hong Kong stocks，and let Bot `/market` with CLI/Scheduling portal uses consistent transaction day filtering semantics。
- Ask about stocks and Agent Link enhancement configuration is missing、decision making fallback and multi-strategy selection experience。
- LLM Improve stability with analysis report link：illegal JSON The response will continue to try the alternate model，LiteLLM DEBUG Log noise reduction by default。
- Added read-only first startup configuration status interface，for subsequent configuration wizards and smoke run lay the foundation。

### new features

- The resumption of the broader market supports the Hong Kong stock market：`MARKET_REVIEW_REGION` New `hk` Options；`both` expanded to Ashares+Hong Kong stocks+US stocks，and added a new Hong Kong stock index（HSI/HSTECH/HSCEI）Review link。
- Added read-only first startup configuration status interface `GET /api/v1/system/config/setup/status`，used to identify LLM、Agent、Optional stocks、Notifications and local storage configuration gap；This interface does not overload the runtime、write `.env` or create a database file。

### Improve

- The stock inquiry page supports multiple selections in combination Agent Strategy。

### Repair

- Bot `/market` Command reuse `get_open_markets_today()` / `compute_effective_region()` Do transaction day filtering：result as `override_region` pass through `run_market_review`；If the result is an empty string, skip the review and push“Relevant markets are closed today”，with CLI/Scheduling entry behavior is consistent。
- Ask about stocks Agent Available without configuration LLM When retaining the real error cause of the backend and maintaining `done.success=false` failure semantics，Prevent the front-end from mistaking missing configuration for a successful answer。
- Agent Preserve scores for local trend analysis when mode does not generate valid decision dashboards、Trends and action recommendations，and will force buy/Forced sale fallback normalize to compatible `buy`/`sell` Decision type，Prevent the home page results from being `50 / wait and see / unknown` Default value override。
- When the current price of the position snapshot is missing, it will no longer silently fall back to the position cost.；The snapshot of the day gives priority to historical closing prices.，Use live price only if missing fallback，Short positions no longer pollute the market value and unrealized profit and loss summary，And return the price source for position details、Date、stale with shortage status。
- analysis Prompt Injecting `trend_analysis` Press final `trend_status` / `ma_alignment` Cleaning mutex reasons：Short Structure Removes Bullish Reasons、Long structure removes risk from short structure，and in event/Technical conflicts and abnormal volume（>10 times）Force prompt when“Event first、Technology to be confirmed”Reduce power with quantity and energy。
- LLM Return non JSON The backup model switch is also triggered when responding.：Main model returned successfully but could not be parsed JSON time，No longer downgrades immediately to plain text fallback，Instead, try `LITELLM_FALLBACK_MODELS` Alternate model in；None of the models can return legal JSON time，downgrade to text fallback。
- LiteLLM internal DEBUG By default, the log is suppressed to WARNING，Avoid streaming builds token level log pollution `stock_analysis_debug_*.log`；If you need to troubleshoot LiteLLM interior details，Can be set temporarily `LITELLM_LOG_LEVEL=DEBUG`（Fixes #1156）。

### Documentation

- supplement LLM Configuration Guide and FAQ，Ask stocks clearly Agent Yes `LITELLM_CONFIG` / `LLM_CHANNELS` / legacy `GEMINI_*` `OPENAI_*` `ANTHROPIC_*` Compatibility priority、fallback path vs.“Do not migrate old configuration silently”conclusion。

### test

- New `tests/test_bot_market_command.py`，Cover `MARKET_REVIEW_REGION=both` + open markets `{"cn","us"}` / `{"cn","hk"}` of `override_region` pass-through assertion，And covers all market closures, skipping and closing trading day check paths；New `tests/test_yfinance_hk_indices.py` Covers Hong Kong stock index symbol mapping and parts/All failed downgrade paths。
- complete `task_queue` Lightweight import stub The stock code normalization function of，restore `tests/test_task_queue_config_sync.py` Collect and run。

## [3.14.1] - 2026-04-26
- [test] Correction of market review prompt test pair“Tomorrow's trading plan”title assertion，And synchronize the desktop version number，Resume publishing gate。

## [3.14.0] - 2026-04-26

### Post highlights

- 📊 **The market review was upgraded to an after-hours workbench structure.** — A Stock review fixed output disk surface temperature、Index details、plate Top table、news catalysis、Tomorrow’s trading plan and risk warning，Reduce the repetition and emptiness of pure text review。
- 🖥️ **New on desktop GitHub Release Update reminder** — Windows/macOS The desktop version automatically detects new versions after startup，You can also manually check and jump to the download page from the settings page。
- 🤖 **Pipeline Agent Significant noise reduction in data loading** — K Line tool changed to DB-first and warm up 240 days historical data，Avoid duplication of the same stock HTTP Request。
- 🐳 **Docker Post link sorting** — The release workflow converges into two paths: formal release and manual reissue.，official Docker Hub The image names are unified as `zhulinsen/daily_stock_analysis`。
- 🔧 **LLM Channels and DeepSeek V4 Configuration enhancement** — GitHub Actions Timing analysis to complete multi-channel variable transparent transmission，DeepSeek Official channel presets and examples are synchronized to V4。
- 🧩 **Desktop static resource consistency check** — Both packaging links and runtime can detect static resource mismatches earlier，lower Release Including white screen troubleshooting costs。

### new features

- 🏠 **Web A new re-analysis entry has been added to the history report area on the homepage** — Support based on original prompt Redo analysis of the same stock on the same date。
- 🖥️ **Windows/macOS New on desktop GitHub Release Update reminder** — Automatically detect new versions after startup，And supports jumping to the download page after manual checking from the settings page。

### Improve

- 📊 **A The stock market review report is changed to a structured after-hours workbench format** — Fixed output panel temperature、Index details、plate Top table、News Catalysts and Tomorrow's Trading Plan。
- 🐳 **Docker Publishing workflow convergence** — A clearer distinction between official release and manual reissue links，and unify the official Docker Hub Image name `zhulinsen/daily_stock_analysis`。
- 🤖 **Agent Daily tools prioritize reusing local cache** — At the same time, persist the newly obtained daily line and news information，Reduce duplicate data source calls。

### Repair

- 🤖 **Pipeline Agent K line tool DB-first Load** — `get_daily_history` / `analyze_trend` / `calculate_ma` / `get_volume_analysis` / `analyze_pattern` Change to read local first DB，Eliminate the same stock 9x5=45 repetitions HTTP Request（Fixes #1066）。
- 🤖 **Pipeline Agent Warm up on demand before execution 240 day K line history to DB** — Under normal circumstances K Online tool calls do not require repeated network requests。
- 🕒 **Freeze `target_date` and pass ContextVar Passthrough to Pipeline Agent K line tool thread** — Eliminate time drift across closing boundaries。
- 🪟 **Windows Desktop backend log transfer encoding repair** — Copy stdout/stderr priority when using UTF-8，and compatible with local code page fallback，Avoid garbled Chinese logs。
- ⚙️ **GitHub Actions Daily analysis workflow completion LLM Transparent transmission of channel variables** — support `LLM_CHANNELS`、Much Key and commonly used `LLM_<NAME>_*`，Avoid locally available multi-model configurations from becoming invalid in cloud scheduled tasks（Fixes #1063, #872）。
- 📈 **Historical report details interface correction `change_pct` value** — Use `is None` judge to avoid 0.0（Flat plate）discard as missing value，remove wrong `change_60d` Keep everything in mind，and fall back to the original real-time quote field if missing（Fixes #1084）。
- 🔧 **DeepSeek Official channel defaults and sample configurations are synchronized to V4** — Reserve legacy `deepseek-chat` Default value and add deprecation prompt，At the same time, the problem of old runtime selection after model discovery caused the save to fail was fixed.（Fixes #1108, #1109）。
- 🧩 **Added static resource consistency check for desktop packaging links** — `scripts/check_static_assets.py` will be in the source `static/` with PyInstaller In-product verification `index.html` Whether the referenced resource actually exists，The runtime also writes explicit logs on mismatches，avoid recurrence Release White screen after opening the package（Refs #1064 / #1065 / #1050）。
- 🧩 **backend `/assets/*` Change to explicit routing hosting** — When the resource is missing, return the file that matches the requested extension. `text/javascript` / `text/css` 404，reduce default JSON Misleading troubleshooting caused by incorrect responses（Refs #1064）。
- 🌙 **`kimi-k2.6` Automatically use fixed temperature** — main analysis、Market review and Agent Automatically used when calling this model `temperature=1.0`，Avoid model rejecting default temperature requests（Fixes #1102）。

### Documentation

- 🐳 **Supplement official Docker Mirror usage instructions** — Add image pull、`docker run` usage with `.env` / Data directory mapping instructions，no longer just cover Compose Deployment path。
- 📨 **Fix Feishu custom robot Webhook Example** — `feishu_sender.py` The example in is changed to interactive card JSON，And supplement Feishu Automation Webhook Trigger configuration tutorial。
- 📚 **Optimize root README structure** — Retain homepage-level features、technology stack、quick start、Push effect、Web、Agent、Sponsor and News Feed Portal，Configure in detail、Trading Discipline and Fundamental Semantics Come to a Complete Guide，and will Docker The badge points to the official mirror page。
- 🌐 **Synchronize English and Traditional Chinese README Streamlined entry structure** — Also complete the complete guide LLM Dosage API Instructions on position management。
- 🤝 **adjust AI Collaborate with PR in template README maintenance rules** — clear README Do not update unless necessary，Details enter the special document first。

### test

- 🧪 **Tests related to stable market review LiteLLM stub behavior** — Avoid local installation LiteLLM Impact on market review unit testing when test collection order changes。
- 🧪 **pytest Skip the front-end dependency directory by default** — local presence `apps/dsa-web/node_modules` is no longer recursively scanned by backend tests，avoid pre-publish gate Slowed down by irrelevant directories。

## [3.13.0] - 2026-04-21

### Post highlights

- 🌉 **long bridge OpenAPI Data source access** — US stocks/Priority use of Hong Kong stock quotes Longbridge，YFinance / AkShare Automatic bagging；Behavior unchanged when not configured。
- 📈 **Tushare Hong Kong stock full-link expansion** — Hong Kong stocks passed the daily line `hk_daily` Get；Chip distribution returns to Hong Kong stocks `None`；The conversion unit follows the caliber of Hong Kong stocks，Do not apply again A stock trader/thousand dollar rule。
- 🔍 **Anspire Search Semantic search access** — Configuration `ANSPIRE_*` Can be used after Anspire Search Get real-time market conditions and information，Fully transparent when not configured。
- 🚀 **Common analysis link support LLM Streaming generation** — Home page tasks SSE New `task_progress` event，Progress is more detailed；Does not support streaming provider Automatic fallback to non-streaming calls。
- 🤖 **Web The channel editor supports pulling the list of available models on demand** — `/v1/models` Unified model discovery portal，Multiple choice write back `LLM_{CHANNEL}_MODELS`，Preserve manual input downgrade when pull fails。
- 🛡️ **Agent Comprehensive enhancements to stability and budget guardrails** — `AGENT_MAX_STEPS` Semantic unity、Skill downgrade does not interrupt the pipeline、SSE Abnormal transparent transmission、Skill loading warning Log completion。
- 🛠️ **SQLite Write link atomization** — batch atomic upsert + WAL + `busy_timeout` + Limited write retries，Significantly reduces concurrent lock contention for batch analysis。

### new features

- 🌉 **Integrate Longbridge OpenAPI As a U.S. stock/Optional data sources for Hong Kong stocks**（fixes #981）— Configuration `LONGBRIDGE_*` Then give priority to using Long Bridge to obtain daily and real-time market conditions.，YFinance / AkShare Keep everything in mind；The behavior when not configured is the same as before。Joint debugging use `tests/longbridge_live_smoke.py`（manual script，Not participating pytest collect）。
- 📈 **Tushare Support daily query of Hong Kong stocks** — Configuration Tushare Called after credentials `hk_daily` Interface to obtain Hong Kong stock data；Exception thrown when permissions are insufficient，Consistent with the original process。
- 🔍 **Integrate Anspire Search Optional semantic search backend** — Configuration `ANSPIRE_*` available Anspire Search Get real-time market conditions and news information；The behavior when not configured is the same as before。Joint debugging use `tests/test_anspire_search.py`（manual script）。
- 🚀 **Common analysis link support LiteLLM Streaming generation and more detailed task progress** — stock analysis in LLM Prioritize attempts at stages `stream=True` and accumulate on the server side chunk，Home page tasks SSE New `task_progress` events and details `message/progress` update；only in the end JSON Persistent history report after successful parsing；Does not support streaming provider Automatic fallback to non-streaming calls。
- 🤖 **Web AI Model configuration supports obtaining the list of available models by channel** — Channel editor supports calling `/v1/models` Pull available models，and write back in multi-select mode `LLM_{CHANNEL}_MODELS`；Keep manual input as downgrade path when pull fails。

### Improve

- 🔎 **SerpAPI The scope of text supplementation converges** — Natural search results no longer simultaneously crawl the text of the web page one by one.；Only a very small number of high-ranking and insufficiently summarized results are delayed for catch-up.，Prioritize reuse SerpAPI Structured snippet returned，Reduce the risk of search link tail delay and slow site amplification。
- 🤖 **LLM Simplified access experience** — user-oriented AI Model access copywriting is unified as"master model / Agent master model / alternative model / model channel"，no more LiteLLM Concepts that must be learned as an ordinary user，Existing `LITELLM_*` / `LLM_CHANNELS` Configuration keys remain compatible。
- 🧠 **IntelAgent Added company announcement search and main capital flow tools** — Add Shanghai Stock Exchange/Shenzhen Stock Exchange/cninfo Announcement search dimensions and `get_capital_flow` Tools，Repair Agent Announcements and capital flow data are often missing in the model。
- 📦 **Back-end stock name resolution priority reuse `stocks.index.json`** — Lazy loading cache front-end static index，Pure backend/Missing static resource scenes silently degrade back `STOCK_NAME_MAP` Fallback link to original data source。
- 📊 **TushareFetcher Hong Kong stock unit adaptation** — `get_chip_distribution` Return directly to Hong Kong stocks `None`（Hong Kong stocks do not currently support chip distribution）；`_normalize_data` For Hong Kong stocks（`hk_daily`）no more A stock trader→shares、Thousand yuan→element scaling，with Tushare Hong Kong stock fields have consistent semantics。
- ⏱️ **Agent Increased number of superstep errors `AGENT_MAX_STEPS` Adjustment Tips** — Help users self-troubleshoot step limit issues。
- ⚙️ **GitHub Actions Analysis task timeout support `vars` Configuration** — `daily_analysis.yml` task timeout from repository variables read，Adjust run timeout caps without modifying code（fixes #1014）。

### Repair

- 📣 **Large disk review link access `REPORT_LANGUAGE`** — `REPORT_LANGUAGE=en` time，A shares/merged review Prompt、Chapter title、The template copywriting and notification package title are uniformly output in English.，Avoid the problem of mixing English text with Chinese titles。
- 📈 **EfinanceFetcher Index opening price mapping compatible**（fixes #1043）— `get_main_indices()` The opening price mapping was changed to be compatible with `Open today → Open → open`，Repair part efinance The problem that the opening price of the index is read as a missing value under version 1。
- 🤖 **AGENT_MAX_STEPS Semantic unity**（fixes #1026）— in orchestrator Much Agent mode is clearly"Each son Agent Step cap instead of hard override"；TechnicalAgent Equal height default value Agent will be capped，low default Agent Keep original value；Users actively increase the（>10）uniformly cover all sub- Agent。Fixed user settings 12 But TechnicalAgent Still as default 6 Run step by step and report "Agent exceeded max steps" question。
- 🛡️ **Specialist（Skill）Agent Failure changed to graceful degradation** — Skills Agent Failure no longer interrupts the entire analysis pipeline，with intel/risk Keep the same downgrade strategy。
- 🔧 **MiniMax-M2.7 Connection test fix** — Repair LLM Channel connection test at MiniMax-M2.7 Return next "Empty response" question；will `max_tokens` upper limit from 8 promoted to 256 to accommodate the thought process，and add `content_blocks` Format parsing logic。
- 📊 **Remove `sentiment_score` scope constraints**（fixes #942）— Remove `HistoryItem` with `ReportSummary` response Schema in `sentiment_score` of `ge=0/le=100` constraint，Out-of-range values stored in the history library no longer trigger Pydantic ValidationError。
- 🖥️ **WebUI Clear warning when front-end resources are missing** — `webui_frontend.py` in `static/index.html` exists but `static/assets/` Emitted when missing warning，avoid CSS/JS Lack of resources causes the page to become abnormally large, but there is no way to troubleshoot it（fixes #944）。
- 🔗 **Analysis pipeline optional service degradation initialization** — `StockAnalysisPipeline` When either the search service or the social public opinion service is initialized abnormally，record warning and continue running in a disabled state，Avoid external dependency jitter blocking the main analysis link。
- 🖥️ **The desktop version displays unified reading `package.json`** — unified reading `apps/dsa-desktop/package.json`，Remove preload hardcoded `0.1.0`，The settings page shows the real desktop version；Fixed version number display error（fixes #1048）。
- 🐋 **Fix for failure to obtain Hong Kong stock names**（fixes #940）— Fixed the problem that when the main data source field is missing, it cannot correctly fall back to the backup field to obtain the name of Hong Kong stocks.。
- 🔄 **SSE When the task flow is disconnected `CancelledError` Correct re-raise**（fixes #967）— Repair SSE When the flow is interrupted, exceptions are swallowed silently, resulting in no logs to check the failure.。
- 🔄 **Agent SSE Background task exceptions are correctly reported during the cleanup phase.**（fixes #969）— Background executor exceptions at the end of the flow are now correctly logged and reported，Avoid errors that cannot be perceived。
- 🔇 **Skill loading exception supplement `logger.warning` Log**（fixes #970）— in `ask.py`、`skills/aggregator.py`、`skills/router.py` of silence except block supplement log，Make sure there are logs available when the skill list is empty。
- 🛠️ **SQLite Write link atomization**（fixes #878）— `stock_daily(code,date)` Use batch atoms upsert；File type SQLite Connection enabled by default WAL + `busy_timeout` + Limited write retries；"Number of new additions"Change to calculate based on the real insertion window this time。
- 💰 **Much Agent / Single Agent Budget guardrail semantics are unified** — Actively skip and downgrade when the remaining budget is below the minimum threshold.；Returned when the stage has been completed and a degradation report can be built. `success=True` and carry non-empty content，Otherwise return `success=False`。
- ⚙️ **GitHub Actions `daily_analysis.yml` complete `REPORT_LANGUAGE` Inject**（fixes #1013）— Fix user in Secrets/Variables Medium configuration `REPORT_LANGUAGE` The problem of not taking effect after。
- 📊 **Task status API Complete real-time price fields**（fixes #983）— `GET /api/v1/analysis/status/{task_id}` Complete when backfilling completed tasks from the database `current_price` / `change_pct`，Fixed the issue where the real-time price is not displayed next to the stock name in the homepage report。
- 📅 **Non-trading day data returns to the most recent trading day**（fixes #1009）— Fix non-trading days（weekend/holidays）Problem with chip distribution and sector ranking returning data of the penultimate trading day，Now returns the most recent trading day data normally。
- 🔍 **A Stock information search restores Chinese priority** — `search_stock_news()` in the first provider Continue to try subsequent engines when mainly returning English information，And arrange the Chinese information in the same batch of results to the front；Non-US stock queries are no longer used by default. Brave of `en/US` Regional language preference。
- 📨 **Feishuqun robot notification supports signature verification** — Feishu notifications now support `FEISHU_WEBHOOK_SECRET` / `FEISHU_WEBHOOK_KEYWORD`；Web Clear distinction between settings and documentation Webhook push mode and `FEISHU_APP_ID` / `FEISHU_APP_SECRET` application mode，Reduce risk of mismatch。
- ⚡ **LLM New adaptation layer `RateLimitError` and `ContextWindowExceeded` Detection** — Identify and handle rate limit and context window exceeded errors，Improve the robustness of analysis links under high load or long text scenarios（fixes #1002）。

### test

- 🧪 **TushareFetcher Hong Kong stock related unit tests** — New `get_chip_distribution` Chip distribution acquisition and `_normalize_data` Hong Kong stocks/A shares/ETF Unit testing for unit processing，Covering special paths for Hong Kong stocks。

### Documentation

- 📘 **DEPLOY.md supplement UI Troubleshooting steps for abnormally enlarged elements** — Add new rebuild Docker Mirror or manual execution `npm run build` Troubleshooting guide for；`deploy-webui-cloud.md` Synchronous updates。
- 📨 **Feishu Webhook Configuration description completion** — emphasize `FEISHU_WEBHOOK_URL` This is a required field for group notification、Signature verification must be enabled or disabled at both ends、`FEISHU_APP_SECRET` only for application/Stream Bot mode；`.env.example` Supplementary inline comments；Synchronized English Guide。
- 🤝 **FAQ supplement Ollama Connection failure troubleshooting items（Q12c）** — Coverage service is not started、URL Configuration error、Missing model prefix、Model not downloaded、Remote firewall, etc. 5 checkpoint（fixes #854）。
- 🌉 **README Supplementary instructions for using the Longbridge data source** — in/English/Traditional README clear long bridge"First choice / Keep everything in mind / Not called if not configured"border；`docs/` Internal relative path link fix；`LONGBRIDGE_PRINT_QUOTE_PACKAGES` Configuration and code `.env.example` Alignment。
- 🐋 **Docker Installation scenario version instructions** — Supplementary minimal documentation，clear Docker In the installation scenario, it should be Git tag / mirror tag Judgment version（fixes #1091）。

## [3.12.0] - 2026-04-01

### Post highlights

- 📊 **New backtest page"Next day verification"view** — View by stock and date range AI Forecast vs Actual price rise or fall the next day，Reuse historical analysis and 1 Daily backtest results，Quickly verify analysis accuracy。
- 🔧 **LLM Simplified access experience** — The user-side copywriting uniformly ends with:"master model / alternative model / model channel"，no more LiteLLM Concepts that must be learned as an ordinary user，Existing configuration keys remain compatible。
- 🐳 **Docker / WebUI Runtime steady-state reinforcement** — Fix the problem that the configuration does not take effect after saving the system settings、Early startup log is missing、Issues such as reuse of pre-built static resources，Reduce operation and maintenance friction of containerized deployment。
- 🔒 **Security and concurrency stability are simultaneously enhanced** — Discord Inbound Webhook complete Ed25519 Verification，Fixed the problem that shared state is not locked during concurrent execution、Issues such as concurrent multiplexing of notifications in single push mode。
- 🖥️ **Polishing the details of desktop and scheduled tasks** — Windows The installer supports self-selected installation directory，Built-in timing scheduler senses running SCHEDULE_TIME change，Breakpoint resume transfer is judged according to the market time zone。

### new features

- 📊 **New backtest page"Next day verification / 1 day window"view** — Viewable by stock symbol and analysis date range AI Forecast、The next day’s actual price rise and fall and the accuracy of the screening range，Reuse historical analysis and 1 Daily backtest results achieved。
- 🏷️ **Web Added version information card to settings page** — `apps/dsa-web` Front-end package version and build time are now injected at build time，Added read-only to the system settings page"Version information"block，show `WebUI version / Build identity / Build time`；When `package.json` Still a placeholder version `0.0.0` time，Will automatically fall back to the build ID，Convenient Docker After reconstruction, quickly confirm whether the current static resources have taken effect.。
- 🪟 **Windows Desktop installer supports custom installation directory** — The installer now supports customizing the installation directory in the installation wizard，After installing to a non-default drive letter, the existing packaging directory logic will still be used to read and write next to the installation directory. `.env`、`data/stock_analysis.db` and `logs/desktop.log`，Also keep `win-unpacked` Installation-free distribution method。The installer only supports installation by the current user、Administrator privilege escalation disabled（`allowElevation: false`），and pass NSIS `.onVerifyInstDir` Prevent selection of system protection directories。

### Improve

- 🔎 **SerpAPI The scope of text supplementation converges** — Natural search results no longer simultaneously crawl the text of the web page one by one.；Now only for a very small number of high-ranking and clearly under-summary results，Delay catch-up within shorter timeout budget，and prioritize reuse SerpAPI Structured snippet returned，Reduce the risk of search link tail delay and slow site amplification。
- 🤖 **LLM Simplified access experience** — user-oriented AI Model access copywriting has been unified as"master model / Agent master model / alternative model / model channel / Advanced model routing configuration"；Web settings page、Configuration metadata、Verification prompts and Chinese and English documents are no longer LiteLLM As an ordinary user, you must learn concepts by default，Existing `LITELLM_*` / `LLM_CHANNELS` Configuration keys remain compatible。

### Repair

- 🚀 **Exposing the true root cause when early startup fails** — `python main.py` Pass now stderr Expose the true root cause，bootstrap Stages are no longer hard-coded `logs/` Directory write file log，file log deferred to `config.log_dir` Created when available，Avoid healthy startup leaving log files in unexpected paths。
- 🐳 **Docker WebUI Prioritize reuse of pre-built static resources at runtime** — `prepare_webui_frontend_assets()` Now the existing ones in the image will be checked first. `static/index.html` Can it be reused directly?；When the container is running it does not contain `apps/dsa-web` Source code directory and not installed `npm` time，There will be no false alarms"Frontend project not found，Unable to build automatically"，thereby restoring Docker after deployment WebUI open ability。
- 🐳 **Docker WebUI The configuration will take effect after the system settings are saved.** — Docker scene WebUI save `STOCK_LIST`、`SCHEDULE_ENABLED`、`SCHEDULE_TIME`、`SCHEDULE_RUN_IMMEDIATELY`、`RUN_IMMEDIATELY` after，`Config` Persistence will be read first `.env` new value in，Avoid being overwritten by old environment variables injected when the container was created。
- 📈 **Market review LLM max_tokens promote** — The market review generation link will LLM `max_tokens` from `2048` promoted to `8192`，Reduce the output cost of long review disks `MAX_TOKENS` Probability that premature truncation results in unfinished content。
- ⏰ **Built-in timing scheduler awareness SCHEDULE_TIME Runtime changes** — The scheduler is now aware on the fly WebUI After saving `SCHEDULE_TIME` change，and re-bind it during the next round of inspections daily job。
- 🪟 **Windows Release Channel editor reserved MiniMax model prefix** — Fill in the channel mode `minimax/<Model name>` time，Backend normalization vs. Web The model list will retain this value when the settings page is run.，No longer mistakenly rewritten as `openai/minimax/<Model name>`。
- 🤖 **Discord Inbound Webhook complete Ed25519 Verification** — `DiscordPlatform` will now be based on `X-Signature-Ed25519`、`X-Signature-Timestamp` Verify the original request body Discord Interaction signature；Missing signature header、The request is directly rejected when the public key format is illegal or the signature does not match.，at the same time timestamp do ±5 Minute aging window verification to defend against replay attacks。
- ⚙️ **STOCK_GROUP_N / EMAIL_GROUP_N Clarification of configuration relationships** — clear with `STOCK_LIST` relationship，And in the configuration verification, exceed the `STOCK_LIST` mail group given warning。
- 🗓️ **Breakpoint resume transfer is judged based on market time zone and trading calendar.**（fixes #880）— Stock data existence check no longer directly uses the server calendar day，Instead press A shares / Hong Kong stocks / U.S. stock market time zone analysis"Latest reusable transaction date"。
- 📨 **Single push mode no longer reuses shared notification instances concurrently** — `StockAnalysisPipeline.run()` Individual stock analysis concurrency will now be retained，But put `SINGLE_STOCK_NOTIFY=true` The real-time notifications below are moved to the result collection side and sent serially.。
- 🔇 **The real-time market downgrade prompt is closed to a single alarm.** — When analyzing the main process to obtain stock names, a real-time market query will no longer be triggered in advance.，Only when all data sources are unavailable will the prompt be downgraded to historical closing prices to continue analysis.。
- 🔍 **A Stock Chinese information search resumes Chinese priority** — `search_stock_news()` will now be the first provider Continue to try subsequent engines when mainly returning English information，And arrange the Chinese information in the same batch of results to the front。
- 🔒 **Shared state completion and unified locking during concurrent execution** — Fixed the problem of lack of unified locking of shared state during concurrent execution，Avoid data competition in multi-threaded scenarios。

### test

- 🧪 **Supplementary setting page version information regression test** — New Web Set page version information rendering assertion，and overwrite the placeholder version `0.0.0` Automatically fallback to logic that builds the identity。
- 🧪 **UI Governance and critical path regression and reinforcement** — supplement `SidebarNav`、`ChatPage`、`BacktestPage` Other component testing，and add UI governance guard，Continuously prevent interactive elements from being reintroduced natively `title` properties or old `input-terminal` style reflow。Synchronous updates smoke / markdown drawer Related verification，Cover key main links after theme upgrade。

## [3.11.0] - 2026-03-27

### Post highlights

- 🎨 **Web Workbench completes one round UI Unified and dual theme upgrades** — Home page、Ask about stocks、backtest、The position and settings pages are further integrated into a unified design token、Input surface and state expressions；Added a complete light theme，and supports light colors / One-click switching and persistent saving of dark colors。
- 🤖 **Bot / Agent Ability to repopulate the main branch** — restore `/history`、`/strategies`、`/research` Waiting for orders，`/ask` Continue to support multi-stock comparison and combination perspectives；Deep Research、event monitoring and schedule Polling link reconnection ability。
- 🔒 **Synchronous enhancement of safety and operational stability** — Repair `X-Forwarded-For` Current limit bypass risk，restore LiteLLM official PyPI Installation path，Tushare Initialization no longer relies on local SDK，lower Docker、Vulnerabilities during desktop packaging and environment rebuilding。
- 🖥️ **Continue to polish the details of daily use** — Fix the automatic completion and submission of Hong Kong stocks on the homepage、Login page home screen theme flashes、Stock names with long history overlap，and Telegram Markdown Issues such as interruption of sending the entire notification when parsing fails。

### new features

- 🎨 **New light theme and dual theme switching are online** — Web A new complete light theme has been added to the workbench，And supports one-click switching of light colors in the sidebar / dark mode；Theme selection will be persisted，Keep current preferences after refreshing the page。This upgrade is not a partial color adjustment，But for the card level、border contrast、input surface、A complete set of status prompts and page backgrounds light theme Redraw。
- 🤖 **Fill in the missing parts of the main branch Agent / Bot Ability** — `#648` / `#649` Has been replenished `main`：Bot restore `/history`、`/strategies`、`/research`，`/ask` Preserve multi-stock comparison and combination perspectives；Deep Research with Event Monitor The configuration is reset in Web Settings page is visible and editable，schedule Mode also reconnects to event alarm polling。

### Improve

- 🖥️ **Unify core pages into the same workbench visual language** — `Home / Chat / Backtest / Portfolio / Settings` Closer to shared design token、`input-surface` input system、Empty state/Error expressions and drawer mask semantics，Reduce visual fragmentation and local private style drift between pages。
- 💬 **Enhanced interactive accessibility and feedback for stock asking questions** — The stock question page has enhanced session export、Notification sent、message copy、History deletion and questioning context prompts；AI Reply operations are no longer overly dependent on hover，Key buttons can also be directly reached on touch screen devices and small screen scenarios.。
- 📊 **The surface and status expressions of backtesting and position pages continue to be standardized.** — Backtest page filter control、Boolean status、Result tables and summary cards are unified into shared inputs/status primitives；Import feedback on the position page、Exchange rate refresh prompt、Empty states and warning information are further classified into shared components，Reduce page-level duplication。
- 🧭 **Navigation and page shell collaborative optimization** — Sidebar theme switching、Asking stocks to complete corner bid、The mobile drawer mask and main content scrolling contracts are further unified，Home page、The page switching experience of stock inquiry and backtesting on the desktop and mobile terminals is more stable。

### test

- 🧪 **UI Governance and critical path regression and reinforcement** — supplement `SidebarNav`、`ChatPage`、`BacktestPage` Other component testing，and add UI governance guard，Continuously prevent interactive elements from being reintroduced natively `title` properties or old `input-terminal` style reflow。Synchronous updates smoke / markdown drawer Related verification，Cover key main links after theme upgrade。

### Repair

- 🌗 **Web The default theme on the first screen is dark** — `apps/dsa-web/index.html` will be in now React Read locally saved theme preferences before mounting；If there is no saved value，then give it immediately `<html>` Default `dark` and sync `color-scheme`，Avoid using a light theme on the first screen of the homepage and login page。
- 🔐 **Login page independent theme layer closing** — Login page input box、label、Toggle button and button copy now use separate `--login-*` Vision token，No longer inherit global shallow/Dark theme text color；Even if the browser caches the light theme，The login page still maintains stable dark visuals and cyan password input performance，Avoid password dots and copywriting being turned into black。
- 🖥️ **Home page Hong Kong stock code input repair** — Web The homepage analysis input box can now correctly accept Hong Kong stock codes and automatically complete selected Hong Kong stock items.，complete `00700.HK` / `HK00700` Recognition of other formats，Avoid false positives when submitting“Please enter a valid stock code or stock name”。

- 🔒 **Certification current limit X-Forwarded-For Value repair（CWE-345）**（#841 / #842）— `get_client_ip()` Take from `X-Forwarded-For` Change the leftmost value to the rightmost value，Prevent attackers from bypassing brute-force cracking protection by forging headers to rotate current-limiting buckets；Only affects `TRUST_X_FORWARDED_FOR=true` And the deployment scenario of single-layer trusted reverse proxy，The multi-level agent environment needs to be configured according to the deployment document evaluation。
- 📦 **restore LiteLLM official PyPI Install and lock the safety cap** — `requirements.txt` reuse `pip install litellm` official PyPI Installation path，and retain historical minimum requirements `>=1.80.10` increase at the same time `<1.82.7` safety upper limit，Avoid accidentally installing files that have been removed `1.82.7` / `1.82.8` risk version；Windows The desktop packaging script also synchronously falls back to the standard `pip install -r requirements.txt` link，Reduce maintenance costs caused by special download branches。
- 📨 **Telegram Markdown Return to plain text if parsing fails**（fixes #850）— `src/notification_sender/telegram_sender.py` will be in now Telegram Return `HTTP 400` and contains `can't parse entities` / Markdown When parsing errors，Automatically remove `parse_mode` Retry plain text sending later，avoid `*ST` Waiting for the text content directly causes the entire notification to fail.。
- 🔢 **A Real-time market quotations for stocks with the same code and exchange reminders**（fixes #852）— `DataFetcherManager` with `TushareFetcher` Will keep it now `SZ000001` / `000001.SZ` This type of explicit Shanghai and Shenzhen prompts，Old version Tushare The real-time market downgrade branch will no longer `000001` Misjudged as `sh000001` Shanghai Composite Index。
- 🎯 **Much Agent Suboptimal buying points no longer blindly copy ideal buying points**（fixes #851）— When multi-agent results lack independence `secondary_buy` time，Dashboards are now shown first `N/A` instead of fallback The value is hard copied into the `ideal_buy` exactly the same，Reduce misleading dual buy point displays。
- 🧩 **Tushare Initialization no longer relies heavily on local SDK package** — `TushareFetcher` Now use the built-in directly HTTP client visit Tushare Pro，No longer first in the startup phase `import tushare` to initialize；fixed Docker、After the desktop is packaged or the environment is rebuilt, the `tushare` Guaranteed and reported in advance `No module named 'tushare'` question，And supplement corresponding regression testing。
- ⚙️ **`daily_analysis` Workflow completion `DEEPSEEK_API_KEY` mapping** — GitHub Actions Daily analysis workflows now pass through correctly `DEEPSEEK_API_KEY`，Avoid cloud tasks that are configured with keys but cannot get the corresponding environment variables during runtime。
- 🖥️ **The history list is too long, stock names are truncated and displayed on hover**（fixes #815）— Stock names that are too long in the history list, Now automatically truncated by character type（English15/Chinese8/mix10character），Display truncated results by default，Show full name on hover；solve 1920x1080 The stock name overlaps with the status label text on the right under different resolutions。New `stockName.ts` Tool functions and supplemented corresponding tests。

### Documentation

- 🧾 **README The donation entrance is updated to Xiaohongshu QR code** — README And the sponsorship entrance in the Chinese and English descriptions has been updated to Xiaohongshu QR code material，Keep the display caliber consistent。

## [3.10.1] - 2026-03-24

### new features

- 🔔 **Web End analysis push notification switch**（#808）— Added next to the analysis button on the homepage「push notification」checkbox，Checked by default；This analysis will not be sent when unchecked Telegram/Corporate WeChat and other push notifications。API `POST /api/v1/analysis/analyze` New `notify` Field（`bool`，Default `true`），When not passed, the behavior will be the same as before modification.，Bot and scheduled tasks are not affected。

### Improve

- 🖥️ **Ask about stocks / Backtest page layout and shell collaborative optimization** — unify Chat / Backtest page container、Share UI Status and follow Q&A interaction paths，Remove some hardcoded height restrictions，Make the filling and scrolling behavior within the navigation frame more consistent。
- 🎨 **Global vision and shared components continue to converge** — Light theme Introduce dynamics HSL shadow system，Unify sidebar activation state、Alarm component contrast and chat bubble style，And close some scattered inline styles to semantic CSS variable，Improve consistency and maintainability。

### Repair

- 🖼️ **System settings smart import file selection recovery** — fixed“System settings > Basic settings > Smart import”in module “Select picture / Select file” Two buttons are unresponsive when clicked。
- 🖥️ **Mobile scrolling and interaction level repairs** — Solve the problem that the theme switching menu is blocked by the main content on the mobile terminal z-index conflict，And restore normal vertical scrolling in the long report scenario on the homepage，Does not affect the existing scrolling behavior of other pages。
- 🧾 **Markdown Plain text copy cleaning enhancement** — Improved plain text export algorithm，Clearing table separators, etc. more consistently when copying analysis reports Markdown traces，Improve the purity of shared and archived content。
- 🧠 **Trading philosophy injection Cover legacy + Agent Full link**（#810）— `GeminiAnalyzer`、Single Agent mode and skill-aware Prompt Now share the same set of policy injection states；Only implicit fallback to built-in default `bull_trend` Only keep old trend tips，Explicit policy selection or custom default skill No longer secretly superimposed `MA5>MA10>MA20` bull baseline。
- 🛠️ **backend CI Depends on installation link stabilization**（#835）— Split backend gate stage、Add retry for dependency installation，and put CI Used `litellm` Adjust the installation source to be more stable GitHub source，Reduce dependency parsing jitter caused by backend gate Occasional failure。
- 🪟 **Windows Desktop release build recovery LiteLLM Installation compatibility** — `scripts/build-backend.ps1` It will now be filtered first `requirements.txt` in LiteLLM GitHub source package，Then download the corresponding tag of zipball It is optional to remove the upstream locally. `enterprise/` Install after directory，bypass Windows runner on Poetry build wheel Failure caused by mistaking the directory for file packaging；Make up at the same time `pip install` Exit code check，Avoid dependency installation failure and only follow-up `python-multipart` It is only during the verification phase that it is exposed as a secondary error.。

### test

- 🧪 **Ask about stocks / backtest / Intelligent import regression coverage completion** — Synchronous updates E2E Smoking expectations，supplement `DashboardStateBlock`、Chat page、Intelligent import file selection and related interactive regression assertions，ensure the near future UI The adjusted critical path can still pass stably。

## [3.10.0] - 2026-03-24

### Post highlights

- 🔎 **Autocompletion and indexing tools expanded to three markets** — Completion index generation links now cover both A shares、Hong Kong stocks、US stocks，New package Tushare Stock list crawler with more complete static index data，Let the home page search entrance start from“Can be used”towards“More complete、more stable”。
- 🖥️ **Dashboard Continue closing with report viewing experience** — Home page Dashboard panel、state boundary、The font level and complete report table density have completed a round of unification；The report details have also been completed Markdown/Plain text copy with more reliable button interaction，Reduce friction when viewing and sharing historical reports。
- 🤖 **Agent skill Clearer boundaries with market semantics** — skill bundle、Default policy、Backtest summary semantics and compatible interfaces are further converged；Analyze simultaneously Prompt No longer hardcoded by default A stock context，U.S. and Hong Kong stock analysis can also generate more relevant content according to their respective market rules.。
- ⏰ **Timing and desktop configuration capabilities are closer to real usage scenarios** — Desktop support `.env` Import and export；`python main.py --schedule --stocks ...` Stock snapshot errors at startup will no longer be carried into subsequent plan executions.，Scheduled tasks will follow the latest saved `STOCK_LIST`。
### new features

- 💾 **Desktop `.env` backup/restore entrance**（#754）— New system settings page in desktop mode has been added `Export .env` / `import .env` button，Can directly back up the currently saved configuration，Or merge the key values in the backup file and restore them to the current desktop `.env`；Import inherits existing `config_version` Collision protection and runtime reloading of links，Do not change the existing desktop portable mode path。
- 📊 **Tushare Stock list acquisition tool** — New `scripts/fetch_tushare_stock_list.py`，Support from Tushare Pro Get Ashares、Hong Kong stocks、US stock list information and save it as CSV，Equipped with paged reading、Intelligent current limiting、Error handling and progress prompts；Add corresponding usage documents `docs/TUSHARE_STOCK_LIST_GUIDE.md`。
- 🔎 **Index generation script multi-market support** — `generate_index_from_csv.py` Refactored to support Tushare and AkShare Dual data sources，Cover simultaneously Ashares、Hong Kong stocks、Three U.S. stock markets；Added alias mapping by market（Ashares、Common aliases for Hong Kong stocks，Commonly used stock abbreviations in the U.S. stock market）；add `--source` Parameter switching data source、`--test` Parameter validation mode；Strictly filter U.S. stocks DUMMY record。
- 🔎 **Index generation script enhancement** — `generate_stock_index.py` New `--test`/`-t` test mode and `--verbose`/`-v` Verbose output mode，Add market distribution statistics，Optimize JSON Output format。
- 📋 **Home full report supports dual-mode replication** — Added new header for historical report details“Copy Markdown Source code”and“Copy plain text”Tool button；The former retains the original Markdown structure，The latter removes common Markdown Format symbols，Easy to share、Archiving and cross-report comparison。Copy button copy will follow `REPORT_LANGUAGE` Keep Chinese and English consistent，Avoid fixed Chinese copywriting on English report pages。
- 🧩 **The individual stock analysis page completes the display of related sectors**（#669）— A The stock analysis write path will now `belong_boards` write once `fundamental_context` / `fundamental_snapshot`，Structured report details are added simultaneously `belong_boards` with `sector_rankings` Field，Web The home screen of the individual stock analysis page can directly display the sector it belongs to and whether it hits the daily sector rise and fall list.；Keep when no data fail-open hide，Does not affect the existing main analysis process。

### Improve

- 🖥️ **Dashboard Panel unification（PR7-2）** — New `DashboardPanelHeader` and `DashboardStateBlock` as history、report、information、Common components for panels such as tasks and transparency；Unified the title hierarchy of each panel、Load/Empty state/error state CSS variable token。
- 🖥️ **HomePage state boundary closing（PR7-2）** — introduce `useHomeDashboardState` hook，Concentrate `stockPoolStore` State selection logic，Remove `HomePage` Duplicate local state derivation and callback definitions in。
- 🧭 **Agent skill Unified to a single configuration semantics** — Multi-Agent runtime、API、Web chat and configuration metadata unified around `skill` concept convergence；`/api/v1/agent/skills` Become the main discovery portal，`AGENT_SKILL_*` Become the main configuration interface，Built-in skill Metadata also starts stating that it is enabled by default、Sort priority、market regime tag and other information，Reduce the implicit coupling of default strategies scattered throughout the code。
- 🔎 **Autocomplete index data update** — Regenerate `stocks.index.json`，Cover Ashares、Hong Kong stocks、Three U.S. stock markets，Improve auto-completion coverage。
- 🧾 **Dashboard Font and full report table density fine-tuning** — Convergence Home Page Sidebar、Empty state、Font level of history operation area，and will be complete Markdown report form `th/td` The padding is adjusted to be more compact 4-6px interval，Let information density be the same as existing Dashboard More consistent visual rhythm。

### Repair

- ⏰ **Timer mode no longer locks on startup CLI stock snapshot** — `python main.py --schedule --stocks ...` Subsequent plan executions will now not be made to inherit the old stock list from startup；Each time the scheduled task is triggered, it will re-read the latest saved `STOCK_LIST`，ensure WebUI or `.env` The updated self-selected stock allocation can participate in subsequent pushes。
- 🌍 **LLM Prompt Inject context by stock market dynamics** — The analysis link no longer hard-codes market rules into A shares；system Prompt Will be identified based on stock code A shares、Hong Kong stocks or US stocks，And inject the corresponding role description and transaction rule prompts，Reduce the problem of caliber misalignment or conclusion distortion in cross-market analysis。
- 🔎 **U.S. stock auto-completion and reuse ticker Remove duplicates** — `generate_index_from_csv.py` Importing Tushare `us_basic` CSV will first press `ts_code` Folding and reusing U.S. stocks ticker，Prioritize records that are more likely to be still in use，avoid `stocks.index.json` Duplication occurs `canonicalCode` Give way Web Auto-complete to display historical names or submit ambiguous codes。
- 🧾 **Web Report details copy interaction stability fixes**（#749）— `ReportDetails` in“Original analysis results / Analyze Snapshot”The copy button completes the clickable hierarchy，avoid being underneath JSON Content coverage；The copy prompts of the two panels have also been changed to be independent.，The two buttons after copying one will no longer appear at the same time.“Copied”misleading feedback。
- 📊 **Agent skill Backtesting and semantic convergence of compatible interfaces** — `get_skill_backtest_summary` Now requires explicit passing in `skill_id`，Return clear verification prompt when missing；The warehouse has not yet persisted the real skill Level aggregation will return an explicit unsupported/info response，and retain `normalized` with `*_pct` Compatible fields，avoid copying overall Indicators are misleading Agent or user。
- 🔧 **Skill Default selection and compatibility layer behavior reinforcement** — `allowed-tools` will continue to serve only as `SKILL.md` bundle Metadata retention，No longer leaks to runtime tool selection；`/api/v1/agent/strategies` restore old payload shape；Explicitly passed in `skills: []` stale context will be cleared when；When the user explicitly selects a strategy skill No longer secretly superimpose the default bull-trend，And in `AGENT_SKILLS` When it is empty, it will only fall back to the single main default skill。

### test

- 🧪 **Dashboard Component test coverage extension（PR7-2）** — New `ReportNews` and `TaskPanel` test；Yes `HistoryList`、`ReportDetails`、`HomePage`、`useDashboardLifecycle` and `stockPoolStore` Enhanced assertion coverage，Includes delete fallback、Scenarios such as mobile drawer and task life cycle。
- 🧪 **Multi-market index generation test completion** — New `tests/test_generate_index_from_csv.py`，Cover Tushare/AkShare Dual data source analysis、Multiple market judgments、US stocks DUMMY Filter and repeat ticker Core paths such as deduplication。
- 🧪 **Related section writing and API contract return** — New `tests/test_pipeline_related_boards.py`，And supplement the analysis history and analysis interface contract testing，ensure `belong_boards` / `sector_rankings` Only do incremental expansion and keep fail-open。
- 🧪 **Timed Mode Stock List Semantic Regression Testing** — New `tests/test_main_schedule_mode.py`，Override timing mode ignores when starting `--stocks` Snapshot、A single run remains CLI Border scenes for stock coverage。

### Documentation

- 📘 **New Tushare Stock List Tool Documentation** — New `docs/TUSHARE_STOCK_LIST_GUIDE.md`，Explain how to use the stock list scraper tool、Data formats and FAQs。
- 🌍 **Complete bilingual instructions for timing mode and related sections** — `docs/full-guide.md` / `docs/full-guide_EN.md` Now make it clear scheduled mode Will be re-read before each execution `STOCK_LIST`，And simultaneously supplement the description of the ability to display related sectors of individual stocks.，Reduce configuration expectation deviation。
- 🧭 **adjust Agent Terminology compatible copywriting** — README、bilingual documentation、The settings page and stock inquiry interface continue with“Strategy”As the main title of the user entrance，Supplement at the same time `skill` As an internal unified naming，Reduce the cost of understanding during the migration period。

## [3.9.0] - 2026-03-20

### Post highlights

- 🤖 **Model linking and reporting language are more flexible** — Agent It is now possible to pass `AGENT_LITELLM_MODEL` Independent selection of model links，General analysis and Agent Reports can also be made via `REPORT_LANGUAGE=zh|en` output unified language，reduce“English content + Chinese shell”This kind of mixing problem，and allow teams to individually weigh primary analysis vs. Agent cost、speed and ability。
- 🔎 **Home page analysis experience completes a round of closed-loop optimization** — Home page new A Stock autocomplete，support code、Chinese name、Pinyin and alias search；At the same time Dashboard Status closed to unity store，history、report、News and Markdown Drawer interaction is more stable，“Ask AI” Follow-up questions will also give priority to carrying the current report context.。
- 💬 **Notification and retrieval capabilities continue to expand** — New Slack First class notification channel；SearXNG When self-built instances are not configured, public instances can be automatically discovered and downgraded according to controlled polling.；Tavily After the timely news link is repaired，Strict time-sensitive filtering no longer causes errors and loses effective results.。
- 💼 **The link between positions and market review is more stable** — A shares market review optional access TickFlow Enhanced index and rise and fall statistics；Position ledger writing changed to serialization to reduce concurrent oversold window；The exchange rate refresh entrance and disabled status prompts are also clearer，Reduce user misjudgment。

### new features

- 🔎 **Web Stock autocomplete MVP** — Added local index-driven auto-completion to the homepage analysis input box，Support stock code、Chinese name、Pinyin and alias matching；Candidates selected will be submitted canonical code，And pass through `stock_name`、`original_query`、`selection_source` to analysis request、task status and SSE event；Automatically fall back to old input mode when index loading fails，Do not block the original submission process。Sync complemented static index loader、Index generation script and front-end and back-end contract testing。Develop in stages，The first phase only supports A shares。
- 💬 **Slack First class notification channel** — New Slack Native notification support，Support both Bot Token and Incoming Webhook Two access methods；Use priority when configuring at the same time Bot API，Make sure text and images are sent to the same channel；Bot Token Mode supports image upload（raw body POST，Not used multipart）；New `SLACK_BOT_TOKEN`、`SLACK_CHANNEL_ID`、`SLACK_WEBHOOK_URL` Configuration items，GitHub Actions Workflow synchronization and completion corresponding Secrets pass on。
- 🌍 **Report output language configurable**（Issue #758）— New `REPORT_LANGUAGE=zh|en`，Default `zh`；The language setting will be injected simultaneously with normal analysis and Agent Prompt，and override Markdown/Jinja Template、Notification fallback、history/API `report_language` Metadata and Web Report page fixed copy，avoid“English content + Chinese shell”The mixed output of。
- 🚀 **Agent Decoupled from common analytical models**（Issue #692）— New `AGENT_LITELLM_MODEL`（Leave blank to inherit `LITELLM_MODEL`，Press without prefix `openai/<model>` Unify）；Agent Execution link with `/api/v1/agent/models` of `is_primary/is_fallback` Tags are changed to based on Agent actual model link；Complete system configuration and startup period verification `AGENT_LITELLM_MODEL` of `unknown_model/missing_runtime_source` Check；Web New settings page Agent Master model selection and synchronization with channel mode runtime configuration。
- 🔎 **SearXNG Public instance automatic discovery and controlled polling**（#752）— New `SEARXNG_PUBLIC_INSTANCES_ENABLED`，in unconfigured `SEARXNG_BASE_URLS` The default is from `searx.space` Pull a list of public instances，and select instances in controlled polling order；A timeout was encountered within the same request.、Connection error、HTTP Not 200 or invalid JSON will automatically switch to the next instance。Users who have configured self-built instances maintain their original priorities and semantics.；`daily_analysis` GitHub Actions Workflow also supports explicit transparent transmission of this switch and displays the current status in the startup log.。
- 📈 **TickFlow market review enhancement** (#632) — Add optional `TICKFLOW_API_KEY`；After configuration，A Prioritize attempts to review the major index trends of the stock market TickFlow；If current TickFlow The package supports target pool query，Market rise and fall statistics will also be tried first TickFlow。Immediately fall back to the existing `AkShare / Tushare / efinance` link；The order of decline in the sector’s rise and fall list remains unchanged。The access layer also adapts to the real SDK contract：The main index query is pulled in batches according to the upper limit of a single request.，and will TickFlow Returned proportional type `change_pct` / `amplitude` Uniformly converted to a percentage caliber within the project。

### Improve

- **Dashboard state slice and workspace closure** — moved Home / Dashboard state into `stockPoolStore`, consolidated history selection, report loading, task syncing, polling refresh, and markdown drawer handling under a single state slice.
- **Dashboard panel standardization** — kept the current dashboard layout contract stable while unifying history, report, news, and markdown presentation with shared tokens, standardized states, and bounded in-panel scrolling for the history list.
- **Dashboard-to-chat follow-up bridge** — routed “Ask AI” follow-ups through report-context hydration instead of direct cross-page state coupling, while keeping chat sends usable when enriched history context is still loading.
- 💼 **Concurrent writing to the position ledger is serialized**（#742）— Position source event writing/Delete will now be in SQLite Get the serialized write lock first，Reduce the window for concurrent sales to write oversold water into the ledger；Direct position writing interface returns when lock contention occurs `409 portfolio_busy`，CSV Import keeps submitting item by item and puts busy credited `failed_count`。
- 💱 **The exchange rate manual refresh entry of the position page has been completed.**（#748）— Web `/portfolio` The page will now be at“exchange rate status”Shown in card“Refresh exchange rate”button，Directly call existing `POST /api/v1/portfolio/fx/refresh` interface；After refreshing, only the snapshot and risk data will be reloaded.，and provide feedback with an inline summary“updated / still stale / Refresh failed”the result，Reduce the user's `fxStale` Misconceptions about long stays。

### Repair

- 🔎 **Web autocomplete Enter Submit semantic correction** — Stock auto-completion no longer highlights the first item by default when searching for hit candidates；When the candidate list is expanded but the user has not explicitly selected it using the arrow keys or mouse，press Enter will continue to submit the original input，Avoid manual input being silently overwritten by the first candidate。
- 🌍 **complete `REPORT_LANGUAGE` Start parsing and historical display localization boundaries** — `Config` Continue to follow at launch“Real environment variables take precedence、`.env` Keep everything in mind”the existing semantics of，And output an explicit warning when the two conflict，reduce `REPORT_LANGUAGE` Misjudgment caused by unclear sources；At the same time `/api/v1/history/{id}` English detailed responses will be localized simultaneously `sentiment_label`，history Markdown English will also be recognized correctly `bias_status` risk level emoji，avoid `optimistic` or `🚨Safe` This kind of mixed arrangement of Chinese and English/False positive display。
- 📰 **Tavily Time-sensitive news retrieval release time mapping repair**（#782）— Tavily Now explicitly used in stock news and strictly time-sensitive intelligence dimensions `topic="news"`，and compatible `published_date` / `publishedDate` Two publishing time fields；fixed Tavily Obviously the returned results were all recorded as `drop_unknown` discard problem，At the same time, the organization will be analyzed、performance expectations、Analytical dimensions such as industry analysis are restored to wide source search，No longer unified and compressed into news mode。
- 💱 **Semantic correction disabled for exchange rate refresh on position page**（#772）— When `PORTFOLIO_FX_UPDATE_ENABLED=false` time，`POST /api/v1/portfolio/fx/refresh` will now return an explicit `refresh_enabled=false` with `disabled_reason`，Web `/portfolio` The page will clearly prompt“Exchange rate online refresh has been disabled”，No more false positives“There are no exchange rate pairs to refresh in the current range.”。
- 🤖 **Agent timeout and config hardening** — `AGENT_ORCHESTRATOR_TIMEOUT_S` now also protects the legacy single-agent ReAct loop, parallel tool batches stop waiting once the remaining budget is exhausted, and invalid numeric `.env` values fall back to safe defaults with warnings instead of crashing startup.
- 🌐 **CORS wildcard + credentials compatibility** — `CORS_ALLOW_ALL=true` no longer combines `allow_origins=["*"]` with credentialed requests, avoiding browser-side cross-origin failures in demo/development setups.
- 🧭 **Unavailable Agent settings hidden from Web UI** — Deep Research / Event Monitor controls are now treated as compatibility-only metadata in the current branch and are removed from the Settings page to avoid exposing non-functional toggles.

### Documentation

- New Ollama Local model configuration instructions，Synchronous updates `README.md` with `docs/README_EN.md`（Fixes #690）
- perfect Ollama Configuration instructions：`docs/full-guide.md` / `docs/full-guide_EN.md` Environment variable table and Note supplement `OLLAMA_API_BASE`，To prevent English users from misunderstanding Ollama Cannot be used as an independent configuration entry；Merge duplicates `OLLAMA_API_BASE` Entry is a single entry
- Clarify document synchronization governance boundaries：supplement `README.md`、Topic documents、Default synchronization rules between bilingual documents and delivery instructions，Reduce subsequent document drift

## [3.8.0] - 2026-03-17

### Post highlights

- 🎨 **Web The interface completes a round of skeleton upgrades** — new App Shell、Side navigation、subject ability、Login and system setup processes have been strung together into a unified experience，The desktop loading background is also aligned。
- 📈 **Analysis context continues to be enhanced** — U.S. stocks add social public opinion intelligence，A Stocks complement financial reporting and dividend structuring context，Tushare Distribution of newly accessed chips and industry sector rise and fall data。
- 🔒 **Improved operational stability and configuration compatibility** — Logging out will immediately invalidate the old session，Scheduled startup is compatible with old configurations，Running `MAX_WORKERS` Adjustments and news timeliness window feedback are clearer。
- 💼 **The position error correction link is more complete** — Overbooking will be blocked in advance，Wrong transaction/Capital flow/Corporate actions can be directly deleted and rolled back，Easy to repair dirty data。

### new features

- 📱 **U.S. stock social public opinion intelligence** — New Reddit / X / Polymarket Social media sentiment data source，Provide real-time social heat for US stock analysis、Supplementary metrics such as sentiment score and mentions；Completely optional，Only in configuration `SOCIAL_SENTIMENT_API_KEY` Effective for U.S. stocks later。
- 📊 **A Enhanced stock financial reporting and dividend structure**（Issue #710）— `fundamental_context.earnings.data` New `financial_report` with `dividend` Field；Dividends are distributed according to the unified“Cash dividends only、Pre-tax caliber”Calculate，and add `ttm_cash_dividend_per_share` with `ttm_dividend_yield_pct`；analysis/history API of `details` Append `financial_report`、`dividend_metrics` optional fields，keep fail-open backward compatible with。
- 🔍 **Access Tushare The interface between chips and industry sectors** — Added chip distribution、Ability to obtain industry sector rise and fall data，And unified into configured data source priority；By default, intraday trading is divided into Shanghai time zones./After-hours trading day withdrawal，priority use Tushare Flush Interface，Downgrade to Dongcai if necessary。
- 🧱 **Web UI Basic skeleton upgrade** — Rebuilding shared design tokens and common components，New App Shell、Theme Provider、Side navigation，and adjust simultaneously Electron Load background，for Web / Desktop A unified experience foundation。
- 🔐 **Login and system setup process redone** — Refactor Login、Settings with Auth management process，Add explicit authentication setup-state Process，and let Web Endpoint and runtime authentication configuration API behavioral alignment。
- 🧪 **Front-end regression and smoke coverage enhancement** — Add and expand login、Home page、chat、Mobile terminal Shell、settings page、Component testing and testing of key paths such as backtest entry Playwright smoke coverage。

### change

- 🧭 **Page access new Shell layout contract** — Home、Chat、Settings、Backtest The new page container has been unified accessed、Drawer and scrolling conventions，lower UI Inconsistent page behavior during migration。
- 💾 **Setting page status synchronization is more stable** — Optimize draft retention、Direct save synchronization and conflict handling，Reduce the problem of inconsistent configuration status of front-end and back-end after module-level saving。
- 🎭 **Login page visual baseline regression** — Login page restored to existing `006` visual baseline for branches，While retaining the new authentication status logic and unified form interaction model。
- 🏛️ **AI Collaborative Governance Asset Hardening** — converge and strengthen `AGENTS.md`、`CLAUDE.md`、Copilot Consistency constraints on instructions and verification scripts，Reduce the risk of long-term drift of governance assets。

### Added

- **Web UI foundation refresh** — rebuilt shared design tokens and common primitives, introduced the app shell, theme provider, sidebar navigation, and Electron loading background alignment for the upgraded desktop/web experience
- **Settings and auth workflow overhaul** — rebuilt the Login, Settings, and Auth management flows, added explicit auth setup-state handling, and aligned the Web UI with the runtime auth configuration APIs
- **UI regression coverage and smoke checks** — expanded targeted frontend tests and added Playwright smoke coverage for login, home, chat, mobile shell, settings, and backtest entry flows

### Changed

- **Shell-driven page integration** — aligned Home, Chat, Settings, and Backtest with the new shell layout contract so routing, drawer behavior, and page-level scrolling are consistent during the UI migration
- **Settings state consistency** — refined draft preservation, direct-save synchronization, and conflict handling so module-level saves no longer leave the page out of sync with backend config state
- **Login visual baseline** — restored the login page visual treatment to the established `006` branch baseline while keeping the newer auth-state logic and unified form interaction model

### Repair

- ⏰ **Scheduled startup and immediate execution are compatible with old configurations**（Issue #726）— `SCHEDULE_RUN_IMMEDIATELY` Will fall back on reading when not set `RUN_IMMEDIATELY`，Repair old after upgrade `.env` Compatibility issues in scheduled mode；Also clarify `.env.example` / README The scope of application of the two configuration items in，and indicate Outlook / Exchange force OAuth2 Not supported yet。
- 🧵 **runtime `MAX_WORKERS` Configuration validation and interpretability enhancement**（#633）— Fix async analysis queue not pressing `MAX_WORKERS` Synchronization problem；Added task queue concurrency in-place Synchronization mechanism（Effective immediately when idle、Busy postponement），And clearly output it in the setting save feedback and running log. `profile/max/effective`，reduce“Parameter is not valid”misunderstanding。
- 🔐 **Log out to immediately invalidate existing sessions.** — `POST /api/v1/auth/logout` Will rotate now session secret，avoid old cookie Access to protected interfaces continues after exiting；The same browser tab and concurrent pages will be logged out simultaneously.。When authentication is turned on，The interface is no longer part of the anonymous whitelist，Requests that are not logged in will be returned `401`，Avoid anonymous requests triggering global session Invalid。
- 🧮 **Tushare plate/Chip call current limit and cross-day cache repair** — New `trade_cal`、Industry sector ranking、Unified access to chip distribution links `_check_rate_limit()`；The trading calendar cache is changed to be refreshed based on calendar days.，Prevent the service from continuing to use the old transaction date to determine the withdrawal date after the service runs across days.。
- 💼 **Oversold position interception and error flow recovery**（#718）— `POST /api/v1/portfolio/trades` Now verifies the sellable quantity before writing，oversold return `409 portfolio_oversell`；New transactions added to the positions page / Capital flow / Corporate Action Delete Ability，After deletion, the invalid position cache and future snapshots will be synchronized.，Facilitates direct recovery from errors in the pipeline。
- 📧 **Email Chinese sender name encoding**（#708）— Email notifications will now be sent to emails containing Chinese characters `EMAIL_SENDER_NAME` do it automatically RFC 2047 encoding，And add in the exception path SMTP Connection cleanup，Repair GitHub Actions / QQ SMTP down `'ascii' codec can't encode characters` Sending failure caused by。
- 🐛 **Hong Kong stocks Agent Real-time market deduplication and fast routing** — unify `HK01810` / `1810.HK` / `01810` Etc. Hong Kong stock code unification rules；The real-time quotation of Hong Kong stocks has been changed to direct single-time trading. `akshare_hk` path，avoid pressing A shares source priority Triggering the same failed interface repeatedly；Agent Explicit at runtime `retriable=false` Tool fails to increase short circuit cache，Reduce repeated failed calls in the same round of analysis。
- 📰 **News timeliness hard filtering and strategic windowing**（#697）— New `NEWS_STRATEGY_PROFILE`（`ultra_short/short/medium/long`）and with `NEWS_MAX_AGE_DAYS` Unified calculation effective window；Search results perform publication time hard filtering after they are returned（Unknown time culling、Super window culling、Only tolerate in the future 1 day），and in history fallback Add the same constraints to the link，Prevent old news from re-entering“Latest news/Risk alert”。

### Documentation

- ☁️ **Add a new cloud server Web Interface deployment and access tutorial**（Fixes #686）— Supplement the implementation instructions from cloud deployment to external access，Lower the threshold for remote self-hosting。
- 🌍 **Complete English document index and collaborative documents** — Added English document index、Contribution Guide、Bot command documentation，And supplemented by bilingual Chinese and English issue / PR Template，Facilitate Chinese and English collaboration and external contributors to understand the project entrance。
- 🏷️ **localization README supplement Trendshift badge** — in multiple languages README The new version of the ability entrance logo will be added simultaneously.，Reduce inconsistencies between Chinese and English explanations。

## [3.7.0] - 2026-03-15

### new features

- 💼 **Position management P0 Fully functional online**（#677，Correspond Issue #627）
  - **Core ledger and snapshot closed loop**：Add new account、transaction、cash flow、corporate behavior、Position cache、Core data models such as daily snapshots and API endpoint；support FIFO / AVG Dual Cost Method Replay；The order of events on the same day is fixed as `Cash → corporate behavior → transaction`；Position snapshot writing uses atomic transactions。
  - **Brokerage firm CSV import**：Support Huatai / CITIC / The first batch of investment promotion，Compatible with column name aliases；two-stage interface（Parse preview + Confirm submission）；`trade_uid` Priority、key-field hash Idempotent deduplication；Leading zero stock codes are kept intact。
  - **Portfolio Risk Report**：concentration risk（Top Positions + A Stock sector caliber）、Historical retracement monitoring（Support backfilling missing snapshots）、Stop loss approaching warning；Unified conversion of multiple currencies CNY Caliber；When extraction fails, fall back to the most recent successful exchange rate and mark it stale。
  - **Web Position page**（`/portfolio`）：Portfolio overview、Position details、Concentration pie chart、Risk summary、full combination / Single account switching；Manually entering transactions / Capital flow / corporate behavior；Embedded account creation portal；CSV parse + Submit Closed Loop and Brokerage Selector。
  - **Agent Position tool**：New `get_portfolio_snapshot` data tools，Default compact summary，Optional position details and risk data。
  - **Event query API**：New `GET /portfolio/trades`、`GET /portfolio/cash-ledger`、`GET /portfolio/corporate-actions`，Support date filtering and paging。
  - **Expandable Parser Registry**：Application-level shared registration，Supports registration of new brokers at runtime；New `GET /portfolio/imports/csv/brokers` Discovery interface。

- 🎨 **Front-end design system and atomic component library**（#662）
  - Introducing a progressive dual-theme architecture（HSL Variable design tokens），clean history Legacy CSS；Refactor Button / Card / Badge / Collapsible / Input / Select Wait 20+ core components；New `clsx` + `tailwind-merge` Class name merging tool；Boost history、LLM Configuration and other page readability。

- ⚡ **analysis API Asynchronous contracts and startup optimization**（#656）
  - normative `POST /api/v1/analysis/analyze` Return contract for asynchronous requests；Optimize service startup auxiliary logic；Fixed the alignment issue between front-end report type union definition and back-end response。

### Repair

- 🔔 **Discord Environment variables are backwards compatible**（#659）：Added at runtime `DISCORD_CHANNEL_ID` → `DISCORD_MAIN_CHANNEL_ID` of fallback read；Historical configurations can be restored by users without modification. Discord Bot Notification；All relevant documents and `.env.example` Alignment。
- 🔧 **GitHub Actions Node 24 Upgrade**（#665）：will all GitHub official actions Upgrade to Node 24 Compatible version，eliminate CI in the log Node.js 20 deprecation warning（influence 2026-06-02 Forced upgrade window）。
- 📅 **Position page default date localization**：The default date in the manual entry form is changed to local time（`getFullYear/Month/Date`），Repair UTC-N Time zone users have a date offset problem late in the day。
- 🔁 **CSV Import deduplication logic reinforcement**：dedup hash Incorporate row numbers as distinguishing factors，Ensure that legal separate transactions in the same field are not folded by mistake；at the same time `trade_uid` persist while it exists hash，Prevent duplicate writes from mixed sources。

### change

- `POST /api/v1/portfolio/trades` within the same account `trade_uid` Return in case of conflict `409`。
- New position risk response `sector_concentration` Field（incremental expansion），original `concentration` fields remain unchanged。
- analysis API `analyze` Interface asynchronous behavior contract documentation；Front-end report type federated updates。

### test

- Added new position core service test（FIFO / AVG partial sale、Sequence of events on the same day、Repeat `trade_uid` Return 409、Snapshot API contract）。
- New CSV Import idempotence、Legally separate transactions without errors and deduplication、Deduplication boundaries、risk threshold boundary、Exchange rate downgrade behavior test。
- New Agent `get_portfolio_snapshot` Tool call test。
- Add new analysis API Asynchronous contract regression testing。

## [3.6.0] - 2026-03-14

### Added
- 📊 **Web UI Design System** — implemented dual-theme architecture and terminal-inspired atomic UI components
- 📊 **UI Components Refactoring** — integrated `clsx` and `tailwind-merge` for robust class composition across Web UI

- 🗑️ **History batch deletion** — Web UI now supports multi-selection and batch deletion of analysis history; added `POST /api/v1/history/batch-delete` endpoint and `ConfirmDialog` component.
- 🔐 **Auth settings API** — new `POST /api/v1/auth/settings` endpoint to enable or disable Web authentication at runtime and set the initial admin password when needed
- openclaw Skill Integration Guide — New [docs/openclaw-skill-integration.md](openclaw-skill-integration.md)，Explain how to pass openclaw Skill call DSA API
- ⚙️ **LLM channel protocol/test UX** — `.env` and Web settings now share the same channel shape (`LLM_CHANNELS` + `LLM_<NAME>_PROTOCOL/BASE_URL/API_KEY/MODELS/ENABLED`); settings page adds per-channel connection testing, primary/fallback/vision model selection, and protocol-aware model prefixing
- 🤖 **Agent architecture Phase 0+1** — shared protocols (`AgentContext`, `AgentOpinion`, `StageResult`), extracted `run_agent_loop()` runner, `AGENT_ARCH` switch (`single`/`multi`), config registry entries
- 🔍 **Bot NL routing** — two-layer natural-language routing: cheap regex pre-filter (stock codes + finance keywords) → lightweight LLM intent parsing; controlled by `AGENT_NL_ROUTING=true`; supports multi-stock and strategy extraction
- 💬 **`/ask` multi-stock analysis** — comma or `vs` separated codes (max 5), parallel thread execution with 150s timeout (preserves partial results), Markdown comparison summary table at top
- 📋 **`/history` command** — per-user session isolation via `{platform}_{user_id}:{scope}` format (colon delimiter prevents prefix collision); lists both `/chat` and `/ask` sessions; view detail or clear
- 📊 **`/strategies` command** — lists available strategy YAML files grouped by category (Trend/form/reverse/frame) with ✅/⬜ activation status
- 🔧 **Backtest summary tools** — `get_strategy_backtest_summary` and `get_stock_backtest_summary` registered as read-only Agent tools
- ⚙️ **Agent auto-detection** — `is_agent_available()` auto-detects from `LITELLM_MODEL`; explicit `AGENT_MODE=true/false` takes full precedence
- 🏗️ **Multi-Agent orchestrator (Phase 2)** — `AgentOrchestrator` with 4 modes (`quick`/`standard`/`full`/`strategy`); drop-in replacement for `AgentExecutor` via `AGENT_ARCH=multi`; `BaseAgent` ABC with tool subset filtering, cached data injection, and structured `AgentOpinion` output
- 🧩 **Specialised agents (Phase 2-4)** — `TechnicalAgent` (8 tools, trend/MA/MACD/volume/pattern analysis), `IntelAgent` (news & sentiment, risk flag propagation), `DecisionAgent` (synthesis into Decision Dashboard JSON), `RiskAgent` (7 risk categories, two-level severity with soft/hard override)
- 📈 **Strategy system (Phase 3)** — `StrategyAgent` (per-strategy evaluation from YAML skills), `StrategyRouter` (rule-based regime detection → strategy selection), `StrategyAggregator` (weighted consensus with backtest performance factor)
- 🔬 **Deep Research agent (Phase 5)** — `ResearchAgent` with 3-phase approach (decompose → research sub-questions → synthesise report); token budget tracking; new `/research` bot command with aliases (`/Deep research`, `/deepsearch`)
- 🧠 **Memory & calibration (Phase 6)** — `AgentMemory` with prediction accuracy tracking, confidence calibration (activates after minimum sample threshold), strategy auto-weighting based on historical win rate
- 📊 **Portfolio Agent (Phase 7)** — `PortfolioAgent` for multi-stock portfolio analysis (position sizing, sector concentration, correlation risk, cross-market linkage, rebalance suggestions)
- 🔔 **Event-driven alerts (Phase 7)** — `EventMonitor` with `PriceAlert`, `VolumeAlert`, `SentimentAlert` rules; async checking, callback notifications, serializable persistence
- ⚙️ **New config entries** — `AGENT_ORCHESTRATOR_MODE`, `AGENT_RISK_OVERRIDE`, `AGENT_DEEP_RESEARCH_BUDGET`, `AGENT_MEMORY_ENABLED`, `AGENT_STRATEGY_AUTOWEIGHT`, `AGENT_STRATEGY_ROUTING` — all registered in `config.py` + `config_registry.py` (WebUI-configurable)

### Changed
- 🔐 **Auth password state semantics** — stored password existence is now tracked independently from auth enablement; when auth is disabled, `/api/v1/auth/status` returns `passwordSet=false` while preserving the saved password for future re-enable
- 🔐 **Auth settings re-enable hardening** — re-enabling auth with a stored password now requires `currentPassword`, and failed session creation rolls back the auth toggle to avoid lockout
- ♻️ **AgentExecutor refactored** — `_run_loop` delegates to shared `runner.run_agent_loop()`; removed duplicated serialization/parsing/thinking-label code
- ♻️ **Unified agent switch** — Bot, API, and Pipeline all use `config.is_agent_available()` instead of divergent `config.agent_mode` checks
- 📖 **README.md** — expanded Bot commands section (ask/chat/strategies/history), added NL routing note, updated agent mode description
- 📖 **.env.example** — added `AGENT_ARCH` and `AGENT_NL_ROUTING` configuration documentation
- 🔌 **Analysis API async contract** — `POST /api/v1/analysis/analyze` now documents distinct async `202` payloads for single-stock vs batch requests, and `report_type=full` is treated consistently with the existing full-report behavior

### Fixed
- 🐛 **Analysis API blank-code guardrails** — `POST /api/v1/analysis/analyze` now drops whitespace-only entries before batch enqueue and returns `400` when no valid stock code remains
- 🐛 **Bare `/api` SPA fallback** — unknown API paths now return JSON `404` consistently for both `/api/...` and the exact `/api` path
- 🎮 **Discord channel env compatibility** — runtime now accepts legacy `DISCORD_CHANNEL_ID` as a fallback for `DISCORD_MAIN_CHANNEL_ID`, and the docs/examples now use the same variable name as the actual workflow/config implementation
- 🐛 **Session secret rotation on Windows** — use atomic replace so auth toggles invalidate existing sessions even when `.session_secret` already exists
- 🐛 **Auth toggle atomicity** — persist `ADMIN_AUTH_ENABLED` before rotating session secret; on rotation failure, roll back to the previous auth state
- 🔧 **LLM runtime selection guardrails** — YAML The channel editor is no longer covered in mode `LITELLM_MODEL` / fallback / Vision；System configuration verification adds runtime source checking after all channels are disabled，and fix `vertexai/...` This type of protocol alias model is repeatedly prefixed.
- 🐛 **Multi-stock `/ask` follow-up regressions** — portfolio overlay now shares the same timeout budget as the per-stock phase and is skipped on timeout instead of blocking the bot reply; `/history` now stores the readable per-stock summary instead of raw dashboard JSON; condensed multi-stock output now renders numeric `sniper_points` values
- 🐛 **Decision dashboard enum compatibility** — multi-agent `DecisionAgent` now keeps `decision_type` within the legacy `buy|hold|sell` contract and normalizes stray `strong_*` outputs before risk override, pipeline conversion, and downstreamStatistics/Notification summary
- 🛟 **Multi-Agent partial-result fallback** — `IntelAgent` now caches parsed intel for downstream reuse, shared JSON parsing tolerates lightly malformed model output, and the orchestrator preserves/synthesizes a minimal dashboard on timeout or mid-pipeline parse failure instead of always collapsing to `50/wait and see/unknown`
- 🐛 **Shared LiteLLM routing restored** — bot NL intent parsing and `ResearchAgent` planning/synthesis now reuse the same LiteLLM adapter / Router / fallback / `api_base` injection path as the main Agent flow, so `LLM_CHANNELS` / `LITELLM_CONFIG` / OpenAI-compatible deployments behave consistently
- 🐛 **Bot chat session backward compatibility** — `/chat` now keeps using the legacy `{platform}_{user_id}` session id when old history already exists, and `/history` can still list / view / clear those pre-migration sessions alongside the new `{platform}_{user_id}:chat` format
- 🐛 **EventMonitor unsupported rule rejection** — config validation/runtime loading now reject or skip alert types the monitor cannot actually evaluate yet, so schedule mode no longer silently accepts permanent no-op rules
- 🐛 **P0 Fundamental aggregate stability fixes** (#614) — Repair `get_stock_info` Sector semantic regression（New `belong_boards` and retain `boards` Compatible with aliases）、Introducing fundamental context thin returns to control token、Add maximum entry eviction to fundamental cache，and complete ETF Overall status aggregation and NaN Section field filtering，guarantee fail-open with minimal intrusion。
- 🔧 **GitHub Actions Search engine environment variables supplement** — Workflow new `MINIMAX_API_KEYS`、`BRAVE_API_KEYS`、`SEARXNG_BASE_URLS` Environment variable mapping，make GitHub Actions User configurable MiniMax、Brave、SearXNG Search service（previously v3.5.0 Added provider Implemented but missing workflow configuration）
- 🤖 **Multi-Agent runtime consistency** — `AGENT_MAX_STEPS` now propagates to each orchestrated sub-agent; added cooperative `AGENT_ORCHESTRATOR_TIMEOUT_S` budget to stop overlong pipelines before they cascade further
- 🔌 **Multi-Agent feature wiring** — `AGENT_RISK_OVERRIDE` now actively downgrades final dashboards on hard risk findings; `AGENT_MEMORY_ENABLED` now injects recent analysis memory + confidence calibration into specialised agents; multi-stock `/ask` now runs `PortfolioAgent` to add portfolio-level allocation and concentration guidance
- 🔔 **EventMonitor runtime wiring** — schedule mode can now load alert rules from `AGENT_EVENT_ALERT_RULES_JSON`, poll them at `AGENT_EVENT_MONITOR_INTERVAL_MINUTES`, and send triggered alerts through the existing notification service
- 🛠️ **Follow-up stability fixes** — multi-stock `/ask` now falls back to usable text output when dashboard JSON parsing fails; EventMonitor skips semantically invalid rules instead of aborting schedule startup; background alert polling now runs independently of the main scheduled analysis loop
- 🧪 **Multi-Agent regression coverage** — added orchestrator execution tests for `run()`, `chat()`, critical-stage failure, graceful degradation, and timeout handling
- 🧹 **PortfolioAgent cleanup** — `post_process()` now reuses shared JSON parsing and removed stale unused imports
- 🚦 **Bot async dispatch** — `CommandDispatcher` now exposes `dispatch_async()`; NL intent parsing and default command execution are offloaded from the event loop, DingTalk stream awaits async handlers directly, and Feishu stream processing is moved off the SDK callback thread
- 🌐 **Async webhook handler** — new `handle_webhook_async()` function in `bot/handler.py` for use from async contexts (e.g. FastAPI); calls `dispatch_async()` directly without thread bridging
- 🧵 **Feishu stream ThreadPoolExecutor** — replaced unbounded per-message `Thread` spawning with a capped `ThreadPoolExecutor(max_workers=8)` to prevent thread explosion under message bursts
- 🔒 **EventMonitor safety** — `_check_volume()` now safely handles `get_daily_data` returning `None` (no tuple-unpacking crash); `on_trigger` callbacks support both sync and async callables via `asyncio.to_thread`/`await`
- 🧹 **ResearchAgent dedup** — `_filtered_registry()` now delegates to `BaseAgent._filtered_registry()` instead of duplicating the filtering logic
- 🧹 **Bot trailing whitespace cleanup** — removed W291/W293 whitespace issues across `bot/handler.py`, `bot/dispatcher.py`, `bot/commands/base.py`, `bot/platforms/feishu_stream.py`, `bot/platforms/dingtalk_stream.py`
- 🐛 **Dispatcher `_parse_intent_via_llm` safety** — replaced fragile `'raw' in dir()` with `'raw' in locals()` for undefined-variable guard in `JSONDecodeError` handler
- 🐛 **Chip structure LLM Complete the information if it is not filled in** (#589) — DeepSeek Wait until the model is not filled in correctly `chip_structure` time，Automatically complete with chip data obtained from the data source，Ensure consistent display of each model；General analysis and Agent All modes are valid
- 🐛 **Historical report sniper points show original text** (#452) — The historical details page is now displayed first `raw_result.dashboard.battle_plan.sniper_points` the original string in，avoid `analysis_history` Numeric column range、Compress explanatory text or complex points into a single number；Keep original numeric columns as fallback
- 🐛 **Session prefix collision** — user ID `123` could see sessions of user `1234` via `startswith`; fixed with colon delimiter in session_id format
- 🐛 **NL pre-filter false positives** — `re.IGNORECASE` caused `[A-Z]{2,5}` to match common English words like "hello"; removed global flag, use inline `(?i:...)` only for English finance keywords
- 🐛 **Dotted ticker in strategy args** — `_get_strategy_args()` didn't recognize `BRK.B` as a stock code, leaving it in strategy text; now accepts `TICKER.CLASS` format
- ⏱️ **efinance Long call hang fix** (#660) — for all efinance API Call introduction `_ef_call_with_timeout()` packaging（Default 30 seconds，Passable `EFINANCE_CALL_TIMEOUT` Configuration）；Use `executor.shutdown(wait=False)` Ensure that the main thread is no longer blocked after timeout，completely eliminate 81 minute hang problem
- 🛡️ **Type-safe content integrity checks** (#660) — `check_content_integrity()` Now convert non-string types `operation_advice` / `analysis_summary` Treat as missing field，avoid downstream `get_emoji()` Because `dict.strip()` collapse
- 📄 **Decoupling report saving and notification** (#660) — `_save_local_report()` No longer dependent on `send_notification` flag trigger，`--no-notify` Local reports are saved as usual in mode
- 🔄 **operation_advice dictionary normalization** (#660) — Pipeline and BacktestEngine will now LLM returned `dict` Format `operation_advice` Pass `decision_type`（Not case sensitive）Map to standard string，Prevent crashes caused by model output format changes
- 🛡️ **runner.py usage None protection** (#660) — `response.usage` for `None` no longer throws `AttributeError`，Fallback to 0 token count
- 📋 **orchestrator Silent failure changed to log warning** (#660) — `IntelAgent` / `RiskAgent` Stage failures are now logged `WARNING` instead of silently skipping，Easy to diagnose

### Notes
- ⚠️ **Multi-worker auth toggles** — runtime auth updates are process-local; multi-worker deployments must restart/roll workers to keep auth state consistent

## [3.5.0] - 2026-03-12

### Added
- 📊 **Web UI full report drawer** (Fixes #214) — history page adds "Full Report" button to display the complete Markdown analysis report in a side drawer; new `GET /api/v1/history/{record_id}/markdown` endpoint
- 📊 **LLM cost tracking** — all LLM calls (analysis, agent, market review) recorded in `llm_usage` table; new `GET /api/v1/usage/summary?period=today|month|all` endpoint returns aggregated token usage by call type and model
- 🔍 **SearXNG search provider** (Fixes #550) — quota-free self-hosted search fallback; priority: Bocha > Tavily > Brave > SerpAPI > MiniMax > SearXNG
- 🔍 **MiniMax web search provider** — `MiniMaxSearchProvider` with circuit breaker (3 failures → 300s cooldown) and dual time-filtering; configured via `MINIMAX_API_KEYS`
- 🤖 **Agent models discovery API** — `GET /api/v1/agent/models` returns available model deployments (primary/fallback/source/api_base) for Web UI model selector
- 🤖 **Agent chat export & send** (#495) — export conversation to .md file; send to configured notification channels; new `POST /api/v1/agent/chat/send`
- 🤖 **Agent background execution** (#495) — analysis continues when switching pages; badge notification on completion; auto-cancel in-progress stream on session switch
- 📝 **Report Engine P0** — Pydantic schema validation for LLM JSON; Jinja2 templates (markdown/wechat/brief) with legacy fallback; content integrity checks with retry; brief mode (`REPORT_TYPE=brief`); history signal comparison
- 📦 **Smart import** — multi-source import from image/CSV/Excel/clipboard; Vision LLM extracts code+name+confidence; name→code resolver (local map + pinyin + AkShare); confidence-tiered confirmation
- ⚙️ **GitHub Actions LiteLLM config** — workflow supports `LITELLM_CONFIG`/`LITELLM_CONFIG_YAML` for flexible AI provider configuration
- ⚙️ **Config engine refactor & system API** (#602) — unified config registry, validation and API exposure
- 📖 **LLM configuration guide** — new `docs/LLM_CONFIG_GUIDE.md` covering 3-tier config, quick start, Vision/Agent/troubleshooting

### Fixed
- 🐛 **analyze_trend always reports No historical data** (#600) — now fetches from DB/DataFetcher instead of broken `get_analysis_context`
- 🐛 **Chip structure fallback when LLM omits it** (#589) — auto-fills from data source chip data for consistent display across models
- 🐛 **History sniper points show raw text** (#452) — prioritizes original strings over compressed numeric values
- 🐛 **GitHub Actions ENABLE_CHIP_DISTRIBUTION configurable** (#617) — no longer hardcoded, supports vars/secrets override
- 🐛 **`.env` save preserves comments and blank lines** — Web settings no longer destroys `.env` formatting
- 🐛 **Agent model discovery fixes** — legacy mode includes LiteLLM-native providers; source detection aligned with runtime; fallback deployments no longer expanded per-key
- 🐛 **Stooq US stock previous close semantics** — no longer misuses open price as previous close
- 🐛 **Stock name prefetch regression** — prioritizes local `STOCK_NAME_MAP` before remote queries
- 🐛 **AkShare limit-up/down calculation** (#555) — fixed market analysis statistics
- 🐛 **AkShare Tencent source field index & ETF quote mapping** (#579)
- 🐛 **Pytdx stock name cache pagination** (#573) — prevents cache overflow
- 🐛 **PushPlus oversized report chunking** (#489) — auto-segments long content
- 🐛 **Agent chat cancel & switch** (#495) — cancel no longer misreports as failure; fast switch no longer overwrites stream state
- 🐛 **MiniMax search status in `/status` command** (#587)
- 🐛 **config_registry duplicate BOCHA_API_KEYS** — removed duplicate dict entry that silently overwrote config

### Changed
- 🔎 **Fetcher failure observability** — logs record start/success/failure with elapsed time, failover transitions; Efinance/Akshare include upstream endpoint and classified failure categories
- ♻️ **Data source resilience & cleanup** (#602) — fallback chain optimization
- ♻️ **Image extract API response extension** — new `items` field (code/name/confidence); `codes` preserved for backward compatibility
- ♻️ **Import parse error messages** — specific failure reasons for Excel/CSV; improved logging with file type and size

### Docs
- 📖 LLM config guide refactored for clarity (#583)
- 📖 `image-extract-prompt.md` with full prompt documentation
- 📖 AkShare fallback cache TTL documentation
## [3.4.10] - 2026-03-07

### Fixed
- 🐛 **EfinanceFetcher ETF OHLCV data** (#541, #527) — switch `_fetch_etf_data` from `ef.fund.get_quote_history` (NAV-only, no OHLCV, no `beg`/`end` params) to `ef.stock.get_quote_history`; ETFs now return proper open/high/low/close/volume/amount instead of zeros; remove obsolete NAV column mappings from `_normalize_data`
- 🐛 **tiktoken 0.12.0 `Unknown encoding cl100k_base`** (#537) — pin `tiktoken>=0.8.0,<0.12.0` in requirements.txt to avoid plugin-registration regression introduced in 0.12.0
- 🐛 **Web UI API error classification** (#540) — frontend no longer treats every HTTP 400 as the same "server/network" failure; now distinguishes Agent disabled / missing params / model-tool incompatibility / upstream LLM errors / local connection failures
- 🐛 **North Exchange code recognition failed** (#491, #533) — 8/4/92 beginning 6 Bit code is now correctly identified as Beijing Exchange；Tushare/Akshare/Yfinance Other data sources support .BJ or bj prefix；Baostock/Pytdx Explicitly switch the data source for the North Exchange code；Avoid misjudgment in Shanghai B shares 900xxx
- 🐛 **Sniper point analysis error** (#488, #532) — Ideal buy/Fields such as secondary purchase are in None「Yuan」Technical indicator numbers in brackets were mistakenly extracted when writing.；Now cut off the first bracket and then extract the content

### Added
- **Markdown-to-image for dashboard report** (#455, #535) — Individual stock daily summary support markdown Repost picture push（Telegram、WeChat、Custom、Email），Consistent with the market review behavior
- **markdown-to-file engine** (#455) — `MD2IMG_ENGINE=markdown-to-file` Optional，Yes emoji better support，Need `npm i -g markdown-to-file`
- **PREFETCH_REALTIME_QUOTES** (#455) — set to `false` Real-time quote prefetching can be disabled，avoid efinance/akshare_em Whole market pull
- **Stock name prefetch** (#455) — Prefetch stock names before analysis，Reduce reporting「stocksxxxxx」placeholder
- 📊 **Analysis report model tags** (#528, #534) — in analysis report meta、end of report、Shown in push content `model_used`（complete LLM Model name）；Agent Record and display the actual model used in each round when calling multiple rounds（support fallback switch）

### Changed
- **Enhanced markdown-to-image failure warning** (#455) — Prompt specific dependencies when image transfer fails（wkhtmltopdf or m2f）
- **WeChat-only image routing optimization** (#455) — Only when configuring corporate WeChat pictures，No more redundant transfer of complete reports，Avoid misleading failure logs
- **Stock name prefetch lightweight mode** (#455) — Name prefetch phase skipped realtime quote Query，Reduce additional network overhead

## [3.4.9] - 2026-03-06

### Added
- 🧠 **Structured config validation** — `ConfigIssue` dataclass and `validate_structured()` with severity-aware logging; `CONFIG_VALIDATE_MODE=strict` aborts startup on errors
- 🖼️ **Vision model config** — `VISION_MODEL` and `VISION_PROVIDER_PRIORITY` for image stock extraction; provider fallback (Gemini → Anthropic → OpenAI → DeepSeek) when primary fails
- 🚀 **CLI init wizard** — `python -m dsa init` 3-step interactive bootstrap (model → data source → notification), 9 provider presets, incremental merge by default
- 🔧 **Multi-channel LLM support** with visual channel editor (#494)

### Changed
- ♻️ **Vision extraction** — migrated from gemini-3 hardcode to `litellm.completion()` with configurable model and provider fallback; `OPENAI_VISION_MODEL` deprecated in favor of `VISION_MODEL`
- ♻️ **Market analyzer** — uses `Analyzer.generate_text()` for LLM calls; fixes bypass and Anthropic `AttributeError` when using non-Router path
- ♻️ **Config validation refinements** — test_env output format syncs with `validate_structured` (severity-aware ✓/✗/⚠/·); Vision key warning when `VISION_MODEL` set but no provider API key; market_analyzer test covers `generate_market_review` fallback when `generate_text` returns None
- ⚙️ **Auto-tag workflow defaults to NO tag** — only tags when commit message explicitly contains `#patch`, `#minor`, or `#major`
- ♻️ **Formatter and notification refactor** (#516)

### Fixed
- 🐛 **STOCK_LIST not refreshed on scheduled runs** — `.env` or WebUI changes to `STOCK_LIST` now hot-reload before each scheduled analysis (#529)
- 🐛 **WebUI fails to load with MIME type error** — SPA fallback route now resolves correct `Content-Type` for JS/CSS files (#520)
- 🐛 **AstrBot sender docstring misplaced** — `import time` placed before docstring in `_send_astrbot`, causing it to become dead code
- 🐛 **Telegram Markdown link escaping** — `_convert_to_telegram_markdown` escaped `[]()` characters, breaking all Markdown links in reports
- 🐛 **Duplicate `discord_bot_status` field** in Config dataclass — second declaration silently shadowed the first
- 🧹 **Unused imports** — removed `shutil`/`subprocess` from `main.py`
- 🔧 **Config validation and Vision key check** (#525)

### Docs
- 📝 Clarified GitHub Actions non-trading-day manual run controls (`TRADING_DAY_CHECK_ENABLED` + `force_run`) for Issue #461 / PR #466

## [3.4.8] - 2026-03-02

### Fixed
- 🐛 **Desktop exe crashes on startup with `FileNotFoundError`** — PyInstaller build was missing litellm's JSON data files (e.g. `model_prices_and_context_window_backup.json`). Added `--collect-data litellm` to both Windows and macOS build scripts so the files are correctly bundled in the executable.

### CI
- 🔧 Cache Electron binaries on macOS CI runners to prevent intermittent EOF download failures when fetching `electron-vX.Y.Z-darwin-*.zip` from GitHub CDN
- 🔧 Fix macOS DMG `hdiutil Resource busy` error during desktop packaging

### Docs
- 📝 Clarify non-trading-day manual run controls for GitHub Actions (`TRADING_DAY_CHECK_ENABLED` + `force_run`) (#474)

## [3.4.7] - 2026-02-28

### Added
- 🧠 **CN/US Market Strategy Blueprint System** (#395) — market review prompt injects region-specific strategy blueprints with position sizing and risk trigger recommendations

### Fixed
- 🐛 **`TRADING_DAY_CHECK_ENABLED` env var and `--force-run` for GitHub Actions** (#466)
- 🐛 **Agent pipeline preserved resolved stock names** (#464) — placeholder names no longer leak into reports
- 🐛 **Code cleanup** (#462, Fixes #422)
- 🐛 **WebUI auto-build on startup** (#460)
- 🐛 **ARCH_ARGS unbound variable** (#458)
- 🐛 **Time zone inconsistency & right panel flash** (#439)

### Docs
- 📝 Clarify potential ambiguities in code (#343)
- 📝 ENABLE_EASTMONEY_PATCH guidance for Issue #453 (#456)

## [3.4.0] - 2026-02-27

### Added
- 📡 **LiteLLM Direct Integration + Multi API Key Support** (#454, Fixes #421 #428)
  - Removed native SDKs (google-generativeai, google-genai, anthropic); unified through `litellm>=1.80.10`
  - New config: `LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS`, `GEMINI_API_KEYS`, `ANTHROPIC_API_KEYS`, `OPENAI_API_KEYS`
  - Multi-key auto-builds LiteLLM Router (simple-shuffle) with 429 cooldown
  - **Breaking**: `.env` `GEMINI_MODEL` (no prefix) only for fallback; explicit config must include provider prefix

### Changed
- ♻️ **Notification Refactoring** (#435) — extracted 10 sender classes into `src/notification_sender/`

### Fixed
- 🐛 LLM NoneType crash, history API 422, sniper points extraction
- 🐛 Auto-build frontend on WebUI startup — `WEBUI_AUTO_BUILD` env var (default `true`)
- 🐛 Docker explicit project name (#448)
- 🐛 Bocha search SSL retry (#445, #446) — transient errors retry up to 3 times
- 🐛 Gemini google-genai SDK migration (Fixes #440, #444)
- 🐛 Mobile home page scrolling (Fixes #419, #433)
- 🐛 History list scroll reset (#431)
- 🐛 Settings save button false positive (fixes #417, #430)

## [3.3.22] - 2026-02-26

### Added
- 💬 **Chat History Persistence** (Fixes #400, #414) — `/chat` page survives refresh, sidebar session list
- 🎨 Project VI Assets — logo icon set, PSD, vector, banner (#425)
- 🚀 Desktop CI Auto-Release (#426) — Windows + macOS parallel builds

### Fixed
- 🐛 Agent Reasoning 400 & LiteLLM Proxy (fixes #409, #427)
- 🐛 Discord chunked sending (#413) — `DISCORD_MAX_WORDS` config
- 🐛 yfinance shared DataFrame (#412)
- 🐛 sniper_points parsing (#408)
- 🐛 Agent framework category missing (#406)
- 🐛 Date inconsistency & query id (fixes #322, #363)

## [3.3.12] - 2026-02-24

### Added
- 📈 **Intraday Realtime Technical Indicators** (Issue #234, #397) — MA calculated from realtime price, config: `ENABLE_REALTIME_TECHNICAL_INDICATORS`
- 🤖 **Agent Strategy Chat** (#367) — full ReAct pipeline, 11 YAML strategies, SSE streaming, multi-turn chat
- 📢 PushPlus Group Push — `PUSHPLUS_TOPIC` (#402)
- 📅 Trading Day Check (Issue #373, #375) — `TRADING_DAY_CHECK_ENABLED`, `--force-run`

### Fixed
- 🐛 DeepSeek reasoning mode (Issue #379, #386)
- 🐛 Agent news intel persistence (Fixes #396, #405)
- 🐛 Bare except clauses replaced with `except Exception` (#398)
- 🐛 UUID fallback for HTTP non-secure context (fixes #377, #381)
- 🐛 Docker DNS resolution (Fixes #372, #374)
- 🐛 Agent session/strategy bugs — multiple follow-up fixes for #367
- 🐛 yfinance parallel download data filtering

### Changed
- Market review strategy consistency — unified cn/us template
- Agent test assertions updated (`6 -> 11`)


## [3.2.11] - 2026-02-23

### Repair（#patch）
- 🐛 **StockTrendAnalyzer never executed** (Issue #357)
  - root cause：`get_analysis_context` Return only 2 Day data and no `raw_data`，pipeline in `raw_data in context` always False
  - Repair：Step 3 call directly `get_data_range` Get 90 calendar days（approx. 60 trading day）Historical data for trend analysis
  - improve：Used when trend analysis fails `logger.warning(..., exc_info=True)` Complete records traceback

## [3.2.10] - 2026-02-22

### New
- ⚙️ support `RUN_IMMEDIATELY` Configuration items，set to `true` Execute an analysis immediately after the scheduled task is triggered，No need to wait for the first timing point

### Repair
- 🐛 Repair Web UI Page centering problem
- 🐛 Repair Settings Return 500 Error

## [3.2.9] - 2026-02-22

### Repair
- 🐛 **ETF The analysis only focuses on index trends**（Issue #274）
  - US stocks/Hong Kong stocks ETF（Such as VOO、QQQ）with A shares ETF No longer included in fund company level risks（litigation、Reputation etc.）
  - Search dimensions：ETF/Exclusive for index risk_check、earnings、industry Query，Avoid Hit Fund Manager News
  - AI Tips：Index-based analysis constraints，`risk_alerts` There shall be no operational risks of the fund manager company

## [3.2.8] - 2026-02-21

### Repair
- 🐛 **BOT with WEB UI Stock codes are case-sensitive**（Issue #355）
  - BOT `/analyze` with WEB UI The stock codes that trigger analysis are all capitalized（Such as `aapl` → `AAPL`）
  - New `canonical_stock_code()`，in BOT、API、Config、CLI、task_queue Standardization at the entrance
  - Historical records and task deduplication logic can correctly identify the same stock（Case no longer affects）

## [3.2.7] - 2026-02-20

### New
- 🔐 **Web Page password verification**（Issue #320, #349）
  - support `ADMIN_AUTH_ENABLED=true` enable Web Login protection
  - Set an initial password on the webpage when visiting for the first time；support「System settings > Change password」and CLI `python -m src.auth reset_password` reset

## [3.2.6] - 2026-02-20
### ⚠️ breaking changes（Breaking Changes）

- **History API change (Issue #322)**
  - Route changes：`GET /api/v1/history/{query_id}` → `GET /api/v1/history/{record_id}`
  - Parameter changes：`query_id` (string) → `record_id` (integer)
  - News interface changes：`GET /api/v1/history/{query_id}/news` → `GET /api/v1/history/{record_id}/news`
  - Reason：`query_id` May be duplicated during batch analysis，Unable to uniquely identify a single historical record。Use database primary key instead `id` ensure uniqueness
  - Scope of influence：Use legacy historical details API All clients need to be updated simultaneously

### Repair
- Repair U.S. stocks（Such as ADBE）Conflicting technical indicators：akshare U.S. stock rights restoration data is abnormal，The unified historical data source of U.S. stocks is YFinance（Issue #311）
- 🐛 **History query and display issues (Issue #322)**
  - Fixed date inconsistency issue in history list query：use tomorrow as endDate，Make sure to include data for all of today
  - Repair server UI Report selection issue：The reason is that multiple records share the same `query_id`，As a result, the first item is always displayed。Now use `analysis_history.id` as a unique identifier
  - historical details、News interface and front-end components have been fully adapted `record_id`
  - Added background polling（every 30s）Silently refresh the history list when page visibility changes，ensure CLI After the initiated analysis is completed, the front end can be synchronized in time，Use `silent` mode avoid trigger loading Status
- 🐛 **U.S. stock index real-time quotes and daily data** (Issue #273)
  - Repair SPX、DJI、IXIC、NDX、VIX、RUT The problem of not being able to obtain real-time quotes for U.S. stock indexes
  - New `us_index_mapping` module，Enter the user（Such as SPX）mapped to Yahoo Finance symbol（Such as ^GSPC）
  - U.S. stock index and U.S. stock daily data are routed directly to YfinanceFetcher，Avoid traversing unsupported data sources
  - Eliminate duplicate US stock identification logic，Use uniformly `is_us_stock_code()` function

### Optimize
- 🎨 **Home page input field and Market Sentiment Layout alignment optimization**
  - The left edge of the stock code input box and the history record glass-card box left aligned
  - The right edge of the analysis button is Market Sentiment Frame right aligned
  - Market Sentiment The card stretches downward to fill the grid，Eliminate with STRATEGY POINTS the gap between
  - The input field fills the width when the screen is narrow，Responsive alignment remains consistent

## [3.2.5] - 2026-02-19

### New
- 🌍 **Optional areas for market review**（Issue #299）
  - support `MARKET_REVIEW_REGION` environment variables：`cn`（Ashares）、`us`（US stocks）、`both`（both）
  - us Mode usage SPX/Nasdaq/Dow/VIX equal index；both Modes can be reviewed simultaneously A Stocks and US Stocks
  - Default `cn`，Stay backwards compatible

## [3.2.4] - 2026-02-18

### Repair
- 🐛 **The unified U.S. stock data source is YFinance**（Issue #311）
  - akshare U.S. stock rights restoration data is abnormal，The unified historical data source of U.S. stocks is YFinance
  - Repair ADBE Waiting for contradictions in technical indicators of U.S. stocks

## [3.2.3] - 2026-02-18

### Repair
- 🐛 **S&P500Missing real-time data**（Issue #273）
  - Repair SPX、DJI、IXIC、NDX、VIX、RUT The problem of not being able to obtain real-time quotes for U.S. stock indexes
  - New `us_index_mapping` module，Enter the user（Such as SPX）mapped to Yahoo Finance symbol（Such as `^GSPC`）
  - U.S. stock index and U.S. stock daily data are routed directly to YfinanceFetcher，Avoid traversing unsupported data sources

## [3.2.2] - 2026-02-16

### New
- 📊 **PE Indicator support**（Issue #296）
  - AI System Prompt increase PE Valuation concerns
- 📰 **News timeliness screening**（Issue #296）
  - `NEWS_MAX_AGE_DAYS`：News maximum timeliness（day），Default 3，Avoid using outdated information
- 📈 **The deviation rate of strong trend stocks eases**（Issue #296）
  - `BIAS_THRESHOLD`：Deviation rate threshold（%），Default 5.0，Configurable
  - Strong trend stocks（Long alignment and trend strength ≥70）Automatically relax the deviation rate to 1.5 times

## [3.2.1] - 2026-02-16

### New
- 🔧 **Dongcai interface patch configurable switch**
  - support `EFINANCE_PATCH_ENABLED` Environment variable switch Dongcai interface patch（Default `true`）
  - Can be downgraded and shut down when the patch is unavailable，Avoid affecting the main process

## [3.2.0] - 2026-02-15

### New
- 🔒 **CI Unified access control（P0）**
  - New `scripts/ci_gate.sh` As a single point of entry for back-end access control
  - Lord CI Change to `backend-gate`、`docker-build`、`web-gate` three-stage
  - CI Trigger changed to all PR，avoid Required Checks Merge stuck due to missing path filtering
  - `web-gate` Support front-end path changes to be triggered on demand
  - New `network-smoke` Workflow carries the return of non-blocking network scenarios
- 📦 **Release link convergence（P0）**
  - `docker-publish` Adjust to tag main trigger，And add access control verification before release
  - Manual release increased `release_tag` Enter with semver/changelog Strong validation
  - Added before publishing Docker smoke（Key module import）
- 📝 **PR Template upgrade（P0）**
  - add background、scope、Verify commands and results、Rollback scenario、Issue Required fields such as association
- 🤖 **AI Review coverage enhancements（P0）**
  - `pr-review` incorporate `.github/workflows/**` scope
  - New `AI_REVIEW_STRICT` switch，Optional AI Review failure upgraded to blocking

## [3.1.13] - 2026-02-15

### New
- 📊 **Analyze results summary only**（Issue #262）
  - support `REPORT_SUMMARY_ONLY` environment variables，set to `true` Only push summary，Does not include individual stock details
  - Default `false`，Suitable for quick browsing when there are multiple stocks

## [3.1.12] - 2026-02-15

### New
- 📧 **Individual stocks and market review combined push**（Issue #190）
  - support `MERGE_EMAIL_NOTIFICATION` environment variables，set to `true` Combine individual stock analysis and market review into one push
  - Default `false`，Reduce the number of emails、Reduce the risk of being identified as spam

## [3.1.11] - 2026-02-15

### New
- 🤖 **Anthropic Claude API support**（Issue #257）
  - support `ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL`、`ANTHROPIC_TEMPERATURE`、`ANTHROPIC_MAX_TOKENS`
  - AI Analysis Priority：Gemini > Anthropic > OpenAI
- 📷 **Identify stock symbols from pictures**（Issue #257）
  - Upload screenshots of stock selections，Pass Vision LLM Automatically extract stock symbols
  - API: `POST /api/v1/stocks/extract-from-image`；support JPEG/PNG/WebP/GIF，maximum 5MB
  - support `OPENAI_VISION_MODEL` Separately configure the image recognition model
- ⚙️ **Manual configuration of Tongdaxin data source**（Issue #257）
  - support `PYTDX_HOST`、`PYTDX_PORT` or `PYTDX_SERVERS` Configure self-built Tongdaxin server

## [3.1.10] - 2026-02-15

### New
- ⚙️ **Run configuration now**（Issue #332）
  - support `RUN_IMMEDIATELY` environment variables，`true` Execute once immediately after the scheduled task is started
- 🐛 Repair Docker Build issues

## [3.1.9] - 2026-02-14

### New
- 🔌 **Dongcai interface patch mechanism**
  - New `patch/eastmoney_patch.py` Repair efinance Upstream interface changes
  - Does not affect the normal operation of other data sources

## [3.1.8] - 2026-02-14

### New
- 🔐 **Webhook Certificate verification switch**（Issue #265）
  - support `WEBHOOK_VERIFY_SSL` environment variables，Can be closed HTTPS Certificate verification to support self-signed certificates
  - Keep verification by default，Close presence MITM risk，Only recommended for use on trusted intranets

## [3.1.7] - 2026-02-14

### Repair
- 🐛 Fix package import error（package import error）

## [3.1.6] - 2026-02-13

### Repair
- 🐛 Repair `news_intel` in `query_id` Inconsistency issue

## [3.1.5] - 2026-02-13

### New
- 📷 **Markdown Transfer picture notification**（Issue #289）
  - support `MARKDOWN_TO_IMAGE_CHANNELS` Configuration，Yes Telegram、Enterprise WeChat、Customize Webhook（Discord）、Email report in picture format
  - Email is an inline attachment，Enhancement is not supported HTML Client compatibility
  - Requires installation `wkhtmltopdf` and `imgkit`

## [3.1.4] - 2026-02-12

### New
- 📧 **Stock groups are sent to different mailboxes**（Issue #268）
  - support `STOCK_GROUP_N` + `EMAIL_GROUP_N` Configuration，Reports of different stock groups are sent to the corresponding mailboxes
  - The disk review is sent to all configured mailboxes

## [3.1.3] - 2026-02-12

### Repair
- 🐛 Repair Docker Reporting an error when modifying the configuration on the page during internal runtime `[Errno 16] Device or resource busy` question

## [3.1.2] - 2026-02-11

### Repair
- 🐛 Repair Docker Consistency issue，Resolve critical batch processing and notifications Bug

## [3.1.1] - 2026-02-11

### change
- ♻️ `API_HOST` → `WEBUI_HOST`：Docker Compose Unified configuration items

## [3.1.0] - 2026-02-11

### New
- 📊 **ETF Support enhancement and code standardization**
  - Unify data sources ETF Code processing logic
  - New `canonical_stock_code()` Unified code format，Make sure the data source is routed correctly

## [3.0.5] - 2026-02-08

### Repair
- 🐛 repair signal emoji Inconsistency with recommendations（Compound suggestions such as"sell/wait and see"Not mapped correctly）
- 🐛 Repair `*ST` Stock name on WeChat/Dashboard in markdown Escaping problem
- 🐛 Repair `idx.amount` for None Market review TypeError
- 🐛 Repair analysis API Return `report=None` and ReportStrategy Type inconsistency problem
- 🐛 Repair Tushare Return type error（dict → UnifiedRealtimeQuote）and API endpoint points to

### New
- 📊 Market review report injects structured data（Up and down statistics、Index table、Sector ranking）
- 🔍 Search results TTL cache（500 bar upper limit，FIFO Eliminate）
- 🔧 Tushare Token Automatically inject real-time market priority when it exists
- 📰 News summary truncation length 50→200 word

### Optimize
- ⚡ Supplementary quote field requests are limited to a maximum of 1 times，Reduce invalid requests

## [3.0.4] - 2026-02-07

### New
- 📈 **Backtesting engine** (PR #269)
  - Added a new backtesting system based on historical analysis records，Support yield、winning rate、Assessment of indicators such as maximum retracement
  - WebUI Integrated backtest results display

## [3.0.3] - 2026-02-07

### Repair
- 🐛 Fixed the problem of sniper point data parsing error (PR #271)

## [3.0.2] - 2026-02-06

### New
- ✉️ Configurable email sender name (PR #272)
- 🌐 Foreign stocks support English keyword search

## [3.0.1] - 2026-02-06

### Repair
- 🐛 Repair ETF Get real-time quotes、Market data rollback、Enterprise WeChat message chunking problem
- 🔧 CI Process simplification

## [3.0.0] - 2026-02-06

### Remove
- 🗑️ **Remove old version WebUI**
  - Delete based on `http.server.ThreadingHTTPServer` old version of WebUI（`web/` package）
  - Old version WebUI functionality has been completely FastAPI（`api/`）+ React Frontend replacement
  - `--webui` / `--webui-only` Command line parameters marked as deprecated，Automatically redirect to `--serve` / `--serve-only`
  - `WEBUI_ENABLED` / `WEBUI_HOST` / `WEBUI_PORT` Environment variables remain compatible，Automatically forward to FastAPI service
  - `webui.py` Reserved as a compatible entry，Called directly at startup FastAPI backend
  - Docker Compose removed from `webui` service definition，Use uniformly `server` service

### change
- ♻️ **Service layer reconstruction**
  - will `web/services.py` Migrate the asynchronous task service in `src/services/task_service.py`
  - Bot Analysis command（`bot/commands/analyze.py`）Use instead `src.services.task_service`
  - Docker environment variables `WEBUI_HOST`/`WEBUI_PORT` renamed `API_HOST`/`API_PORT`（Old names are still compatible）

## [2.3.0] - 2026-02-01

### New
- 🇺🇸 **Enhance support for US stocks** (Issue #153)
  - Implementation based on Akshare Obtain historical data of U.S. stocks (`ak.stock_us_daily()`)
  - Implementation based on Yfinance Get real-time quotes of U.S. stocks（priority strategy）
  - Add support for unsupported data sources（Tushare/Baostock/Pytdx/Efinance）US stock code filtering and quick downgrade

### Repair
- 🐛 Repair AMD Waiting for the U.S. stock code to be misidentified as A stock problem (Issue #153)

## [2.2.5] - 2026-02-01

### New
- 🤖 **AstrBot Push message** (PR #217)
  - New AstrBot notification channel，Support push to QQ and WeChat
  - support HMAC SHA256 Signature verification，Ensure communication security
  - Pass `ASTRBOT_URL` and `ASTRBOT_TOKEN` Configuration

## [2.2.4] - 2026-02-01

### New
- ⚙️ **Configurable data source priority** (PR #215)
  - Support via environment variables（Such as `YFINANCE_PRIORITY=0`）Dynamically adjust data source priority
  - Prefer specific data sources without modifying your code（Such as Yahoo Finance）

## [2.2.3] - 2026-01-31

### Repair
- 📦 update requirements.txt，increase `lxml_html_clean` Depends on compatibility issues

## [2.2.2] - 2026-01-31

### Repair
- 🐛 Fixed case sensitivity issue in proxy configuration (fixes #211)

## [2.2.1] - 2026-01-31

### Repair
- 🐛 **YFinance Compatibility fixes** (PR #210, fixes #209)
  - Repair new version yfinance Return MultiIndex Data parsing errors caused by column names

## [2.2.0] - 2026-01-31

### New
- 🔄 **Enhanced multi-source fallback strategy**
  - Implemented a more robust data retrieval fallback mechanism (feat: multi-source fallback strategy)
  - Optimized the automatic switching logic when data source fails

### Repair
- 🐛 Repair analyzer Cannot be changed after running .env Documentary stock_list Content Adjustments for Tracked Stocks

## [2.1.14] - 2026-01-31

### Documentation
- 📝 update README and optimization auto-tag rules

## [2.1.13] - 2026-01-31

### Repair
- 🐛 **Tushare Priorities and real-time quotes** (Fixed #185)
  - Repair Tushare Data source priority setting problem
  - Repair Tushare Real-time market quotation acquisition function

## [2.1.12] - 2026-01-30

### Repair
- 🌐 Fixed case sensitivity issue in proxy configuration in some cases
- 🌐 Fix the logic of disabling proxy in local environment

## [2.1.11] - 2026-01-30

### Optimize
- 🚀 **Feishu message flow optimization** (PR #192)
  - Optimize Feishu Stream Schema message type handling
  - Modify Stream Message mode is off by default，Prevent configuration errors and errors when running

## [2.1.10] - 2026-01-30

### merge
- 📦 merge PR #154 Contribute

## [2.1.9] - 2026-01-30

### New
- 💬 **WeChat text message support** (PR #137)
  - Added support for plain text message types pushed by WeChat
  - add `WECHAT_MSG_TYPE` Configuration items

## [2.1.8] - 2026-01-30

### Repair
- 🐛 Correction log in progress API Provider display error (PR #197)

## [2.1.7] - 2026-01-30

### Repair
- 🌐 Disable proxy settings for local environment，Avoid network connection issues

## [2.1.6] - 2026-01-29

### New
- 📡 **Pytdx data source (Priority 2)**
  - Added Tongdaxin data source，Free no registration required
  - Automatic switching between multiple servers
  - Support real-time market and historical data
- 🏷️ **Multi-source stock name analysis**
  - DataFetcherManager New `get_stock_name()` method
  - New `batch_get_stock_names()` Batch query
  - Automatically roll back between multiple data sources
  - Tushare and Baostock Add stock name/list method
- 🔍 **Enhanced search fallback**
  - New `search_stock_price_fallback()` Used when all data sources fail
  - Add new search dimension：market analysis、Industry analysis
  - Maximum number of searches from 3 increase to 5
  - Improve search results format（per dimension 4 results）

### Improve
- Update search query templates to improve relevancy
- Enhance `format_intel_report()` output structure

## [2.1.5] - 2026-01-29

### New
- 📡 New Pytdx Data sources and multi-source stock name resolution capabilities

## [2.1.4] - 2026-01-29

### Documentation
- 📝 Update sponsor information

## [2.1.3] - 2026-01-28

### Documentation
- 📝 Refactor README Layout
- 🌐 Added traditional Chinese translation (README_CHT.md)

### Repair
- 🐛 Repair WebUI Unable to enter US stock code issue
  - The input box logic is changed so that all letters are converted to uppercase
  - support `.` input（Such as `BRK.B`）

## [2.1.2] - 2026-01-27

### Repair
- 🐛 Fixed individual stock analysis push failure and report path issues (fixes #166)
- 🐛 Modify CR Error，Ensure that the WeChat message maximum byte configuration takes effect

## [2.1.1] - 2026-01-26

### New
- 🔧 add GitHub Actions auto-tag Workflow
- 📡 add yfinance Disclosure of data sources and missing data warnings

### Repair
- 🐳 Repair docker-compose Path and document commands
- 🐳 Dockerfile supplement copy src folder (fixes #145)

## [2.1.0] - 2026-01-25

### New
- 🇺🇸 **US stock analysis support**
  - Supports direct input of US stock codes（Such as `AAPL`, `TSLA`）
  - Use YFinance As a source of US stock data
- 📈 **MACD and RSI Technical indicators**
  - MACD：trend confirmation、golden cross signal（Golden cross on zero axis⭐、golden fork✅、Sicha❌）
  - RSI：Overbought and oversold judgment（oversold⭐、Strong✅、overbought⚠️）
  - Indicator signals are incorporated into the comprehensive scoring system
- 🎮 **Discord Push support** (PR #124, #125, #144)
  - support Discord Webhook and Bot API two ways
  - Pass `DISCORD_WEBHOOK_URL` or `DISCORD_BOT_TOKEN` + `DISCORD_MAIN_CHANNEL_ID` Configuration
- 🤖 **Robot command interaction**
  - DingTalk robot support `/analysis Stock code` Command trigger analysis
  - support Stream Long connection mode
- 🌡️ **AI Temperature parameters configurable** (PR #142)
  - Support customization AI Model temperature parameters
- 🐳 **Zeabur Deployment support**
  - add Zeabur Image deployment workflow
  - support commit hash and latest double label

### Refactor
- 🏗️ **Project structure optimization**
  - Core code moved to `src/` Directory，The root directory is cleaner
  - Document moved to `docs/` Directory
  - Docker Configuration moved to `docker/` Directory
  - fix all import path，Stay backwards compatible
- 🔄 **Data source architecture upgrade**
  - Added data source circuit breaker mechanism，Automatic switching if a single data source fails continuously
  - Real-time market cache optimization，Batch prefetch reduction API call
  - Network proxy intelligent offloading，Domestic interface automatic direct connection
- 🤖 Discord Robots refactored into platform adapter architecture

### Repair
- 🌐 **Improved network stability**
  - Automatically detect proxy configuration，Mandatory direct connection to domestic market interface
  - Repair EfinanceFetcher occasional `ProtocolError`
  - Add a capture and retry mechanism for underlying network errors
- 📧 **Email rendering optimization**
  - Fixed the problem of forms not rendering in emails (#134)
  - Optimize email layout，More compact and beautiful
- 📢 **Enterprise WeChat push repair**
  - Fixed the problem of incomplete push of large disk review
  - Enhance message segmentation logic，Support more title formats
  - Increase batch sending interval，Avoid current limit loss
- 👷 **CI/CD Repair**
  - Repair GitHub Actions Error in path reference

## [2.0.0] - 2026-01-24

### New
- 🇺🇸 **US stock analysis support**
  - Supports direct input of US stock codes（Such as `AAPL`, `TSLA`）
  - Use YFinance As a source of US stock data
- 🤖 **Robot command interaction** (PR #113)
  - DingTalk robot support `/analysis Stock code` Command trigger analysis
  - support Stream Long connection mode
  - Supports the selection of streamlined reports or full reports
- 🎮 **Discord Push support** (PR #124)
  - support Discord Webhook push
  - add Discord Environment variables to workflow

### Repair
- 🐳 Repair WebUI in Docker medium binding 0.0.0.0 (fixed #118)
- 🔔 Fixed Feishu long connection notification issue
- 🐛 Repair `analysis_delay` undefined error
- 🔧 On startup config.py Detection notification channel，Fixed the problem that even if a custom channel has been configured, it still prompts that it is not configured.

### Improve
- 🔧 Optimize Tushare Priority judgment logic，Improve packaging
- 🔧 Repair Tushare After the priority is raised, it is still ranked Efinance Next question
- ⚙️ Configuration TUSHARE_TOKEN Automatically improve when Tushare Data source priority
- ⚙️ realize 4 user feedback issue (#112, #128, #38, #119)

## [1.6.0] - 2026-01-19

### New
- 🖥️ WebUI management interface and API support（PR #72）
  - Brand new Web Architecture：layered design（Server/Router/Handler/Service）
  - core API：support `/analysis` (Trigger analysis), `/tasks` (Query progress), `/health` (health check)
  - Interactive interface：Supports directly entering code on the page and triggering analysis，Show progress in real time
  - operating mode：New `--webui-only` mode，Start only Web service
  - solved [#70](https://github.com/ZhuLinsen/daily_stock_analysis/issues/70) core needs（Provides an interface to trigger analysis）
- ⚙️ GitHub Actions Enhanced configuration flexibility（[#79](https://github.com/ZhuLinsen/daily_stock_analysis/issues/79)）
  - Support from Repository Variables Read non-sensitive configuration（Such as STOCK_LIST, GEMINI_MODEL）
  - stay right Secrets backwards compatibility

### Repair
- 🐛 Repair corporate WeChat/Feishu report truncation problem（[#73](https://github.com/ZhuLinsen/daily_stock_analysis/issues/73)）
  - Remove notification.py Unnecessary length hard truncation logic in
  - Rely on the underlying automatic sharding mechanism to handle long messages
- 🐛 Repair GitHub Workflow Environment variable missing（[#80](https://github.com/ZhuLinsen/daily_stock_analysis/issues/80)）
  - Repair `CUSTOM_WEBHOOK_BEARER_TOKEN` not passed correctly to Runner question

## [1.5.0] - 2026-01-17

### New
- 📲 Single stock push mode（[#55](https://github.com/ZhuLinsen/daily_stock_analysis/issues/55)）
  - Immediately push every stock analyzed，No need to wait for everything to be analyzed
  - Command line parameters：`--single-notify`
  - environment variables：`SINGLE_STOCK_NOTIFY=true`
- 🔐 Customize Webhook Bearer Token Certification（[#51](https://github.com/ZhuLinsen/daily_stock_analysis/issues/51)）
  - Support needs Token certified Webhook endpoint
  - environment variables：`CUSTOM_WEBHOOK_BEARER_TOKEN`

## [1.4.0] - 2026-01-17

### New
- 📱 Pushover Push support（PR #26）
  - support iOS/Android Cross-platform push
  - Pass `PUSHOVER_USER_KEY` and `PUSHOVER_API_TOKEN` Configuration
- 🔍 Bocha search API Integrate（PR #27）
  - Chinese search optimization，support AI Summary
  - Pass `BOCHA_API_KEYS` Configuration
- 📊 Efinance Data source support（PR #59）
  - New efinance as data source option
- 🇭🇰 Hong Kong stocks support（PR #17）
  - support 5 bit code or HK prefix（Such as `hk00700`、`hk1810`）

### Repair
- 🔧 Feishu Markdown Rendering optimization（PR #34）
  - Fix rendering issues with interactive cards and formatters
- ♻️ Stock list hot reload（PR #42 Repair）
  - Automatic reload before analysis `STOCK_LIST` Configuration
- 🐛 DingTalk Webhook 20KB restriction of processing
  - Long messages are automatically sent in chunks，avoid truncation
- 🔄 AkShare API Retry mechanism enhancement
  - Add failure cache，Avoid repeated request failure interfaces

### Improve
- 📝 README Streamlined optimization
  - Advanced configuration moved to `docs/full-guide.md`


## [1.3.0] - 2026-01-12

### New
- 🔗 Customize Webhook support
  - Support any POST JSON of Webhook endpoint
  - Automatically identify DingTalk、Discord、Slack、Bark and other common service formats
  - Supports configuring multiple Webhook（comma separated）
  - Pass `CUSTOM_WEBHOOK_URLS` Environment variable configuration

### Repair
- 📝 Enterprise WeChat long messages are sent in batches
  - Solve the problem that the content exceeds the limit when there are too many self-selected stocks 4096 Character limit causes push failure
  - Smart segmentation by stock analysis blocks，Add pagination mark to each batch（Such as 1/3, 2/3）
  - batch interval 1 seconds，Avoid triggering frequency limits

## [1.2.0] - 2026-01-11

### New
- 📢 Multi-channel push support
  - Enterprise WeChat Webhook
  - Feishu Webhook（New）
  - Mail SMTP（New）
  - Automatically identify channel types，Configuration is simpler

### Improve
- Use uniformly `NOTIFICATION_URL` Configuration，Compatible with older `WECHAT_WEBHOOK_URL`
- Email support Markdown turn HTML rendering

## [1.1.0] - 2026-01-11

### New
- 🤖 OpenAI Compatible API support
  - support DeepSeek、Tongyi Qianwen、Moonshot、Wisdom spectrum GLM Wait
  - Gemini and OpenAI Choose one of the formats
  - Automatic downgrade retry mechanism

## [1.0.0] - 2026-01-10

### New
- 🎯 AI Decision dashboard analysis
  - One sentence core conclusion
  - Accurate buy/stop loss/target point
  - Checklist（✅⚠️❌）
  - Suggestions on holding positions（short position vs Position holder）
- 📊 Market review function
  - Major index quotes
  - Up and down statistics
  - Sector rise and fall list
  - AI Generate review report
- 🔍 Multiple data sources support
  - AkShare（master data source，free）
  - Tushare Pro
  - Baostock
  - YFinance
- 📰 News search service
  - Tavily API
  - SerpAPI
- 💬 Enterprise WeChat robot push
- ⏰ Scheduled tasks
- 🐳 Docker Deployment support
- 🚀 GitHub Actions Zero cost deployment

### Technical characteristics
- Gemini AI model（gemini-3-flash-preview）
- 429 Current limiting automatic retry + Model switching
- Delay between requests to prevent bans
- Much API Key load balancing
- SQLite local data storage

---

[Unreleased]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.27.0...HEAD
[3.27.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.26.1...v3.27.0
[3.26.1]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.25.0...v3.26.1
[3.25.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.24.1...v3.25.0
[3.24.1]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.24.0...v3.24.1
[3.24.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.23.0...v3.24.0
[3.23.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.22.0...v3.23.0
[3.22.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.21.1...v3.22.0
[3.21.1]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.21.0...v3.21.1
[3.21.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.20.0...v3.21.0
[3.20.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.19.0...v3.20.0
[3.19.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.18.0...v3.19.0
[3.18.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.17.1...v3.18.0
[3.17.1]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.17.0...v3.17.1
[3.17.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.16.0...v3.17.0
[3.16.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.15.0...v3.16.0
[3.15.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.14.2...v3.15.0
[3.14.2]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.14.1...v3.14.2
[3.14.1]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.14.0...v3.14.1
[3.14.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.13.0...v3.14.0
[3.13.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.12.0...v3.13.0
[3.12.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.11.0...v3.12.0
[3.11.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.10.1...v3.11.0
[3.10.1]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.10.0...v3.10.1
[3.10.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.9.0...v3.10.0
[3.9.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.8.0...v3.9.0
[3.8.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.7.0...v3.8.0
[3.7.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.6.0...v3.7.0
[3.6.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.5.0...v3.6.0
[3.5.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.4.10...v3.5.0
[3.4.10]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.4.9...v3.4.10
[3.4.9]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.4.8...v3.4.9
[3.4.8]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.4.7...v3.4.8
[3.4.7]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.4.0...v3.4.7
[3.4.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.3.22...v3.4.0
[3.3.22]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.3.12...v3.3.22
[3.3.12]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.2.11...v3.3.12
[3.2.11]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v3.2.10...v3.2.11
[2.3.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.2.5...v2.3.0
[2.2.5]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.2.4...v2.2.5
[2.2.4]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.2.3...v2.2.4
[2.2.3]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.2.2...v2.2.3
[2.2.2]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.2.1...v2.2.2
[2.2.1]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.14...v2.2.0
[2.1.14]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.13...v2.1.14
[2.1.13]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.12...v2.1.13
[2.1.12]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.11...v2.1.12
[2.1.11]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.10...v2.1.11
[2.1.10]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.9...v2.1.10
[2.1.9]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.8...v2.1.9
[2.1.8]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.7...v2.1.8
[2.1.7]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.6...v2.1.7
[2.1.6]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.5...v2.1.6
[2.1.5]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.4...v2.1.5
[2.1.4]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.3...v2.1.4
[2.1.3]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.2...v2.1.3
[2.1.2]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v1.6.0...v2.0.0
[1.6.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/ZhuLinsen/daily_stock_analysis/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/ZhuLinsen/daily_stock_analysis/releases/tag/v1.0.0
