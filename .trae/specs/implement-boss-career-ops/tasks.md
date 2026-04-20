# Tasks

## Phase 1: 项目脚手架与基础设施

- [x] Task 1: 创建 pyproject.toml 与项目结构
  - [x] SubTask 1.1: 创建 pyproject.toml（依赖声明、入口点 `bco = boss_career_ops.cli.main:cli`）
  - [x] SubTask 1.2: 创建 `src/boss_career_ops/__init__.py`
  - [x] SubTask 1.3: 创建 `src/boss_career_ops/cli/__init__.py` 和 `src/boss_career_ops/cli/main.py`（Click 主入口，注册所有命令组）
  - [x] SubTask 1.4: 创建 `config/profile.example.yml` 和 `config/thresholds.example.yml` 模板文件
  - [x] SubTask 1.5: 创建 `cv.md` 空模板

- [x] Task 2: 实现配置管理模块 `src/boss_career_ops/config/`
  - [x] SubTask 2.1: 实现 `settings.py` — 加载 profile.yml、thresholds.yml、cv.md，缺失时使用默认值
  - [x] SubTask 2.2: 实现 `thresholds.py` — 自动执行阈值配置解析（auto_greet_threshold, auto_apply_threshold, skip_threshold）

- [x] Task 3: 实现输出格式化模块 `src/boss_career_ops/display/`
  - [x] SubTask 3.1: 实现 `output.py` — JSON 信封格式化函数 `format_envelope(ok, command, data, pagination, error, hints)`
  - [x] SubTask 3.2: 实现 `logger.py` — 日志系统，敏感信息脱敏

- [x] Task 4: 实现缓存层 `src/boss_career_ops/cache/`
  - [x] SubTask 4.1: 实现 `store.py` — SQLite WAL 模式缓存存储，context manager 管理生命周期，支持 TTL 过期

- [x] Task 5: 实现 Hook 系统 `src/boss_career_ops/hooks/`
  - [x] SubTask 5.1: 实现 `manager.py` — 钩子注册与执行（greet_before/after, apply_before/after），支持 veto 拦截

- [x] Task 6: 实现环境诊断命令 `bco doctor`
  - [x] SubTask 6.1: 实现 `src/boss_career_ops/commands/doctor.py` — 检查 Python 版本、依赖、浏览器驱动、配置文件、登录态

## Phase 2: BOSS 直聘 API 交互层

- [x] Task 7: 实现 API 端点定义 `src/boss_career_ops/boss/api/`
  - [x] SubTask 7.1: 创建 `boss.yaml` — 声明式 API 端点定义（搜索、职位详情、打招呼、投递、聊天等）
  - [x] SubTask 7.2: 实现 `endpoints.py` — 解析 YAML，暴露端点对象
  - [x] SubTask 7.3: 实现 `client.py` — BossClient HTTP 客户端（httpx 通道），请求头模拟真实浏览器，高斯随机延迟

- [x] Task 8: 实现认证管理 `src/boss_career_ops/boss/auth/`
  - [x] SubTask 8.1: 实现 `token_store.py` — Fernet + PBKDF2 机器绑定加密存储，原子文件锁
  - [x] SubTask 8.2: 实现 `manager.py` — 4 级降级登录链（Cookie 提取 → CDP → QR httpx → patchright），Token 质量检测

- [x] Task 9: 实现浏览器会话管理 `src/boss_career_ops/boss/browser_client.py`
  - [x] SubTask 9.1: 实现 BrowserClient — 降级链（Bridge → CDP → patchright headless），浏览器操作封装

- [x] Task 10: 实现搜索过滤逻辑 `src/boss_career_ops/boss/search_filters.py`
  - [x] SubTask 10.1: 实现 8 维筛选 + 福利关键词匹配，城市编码映射

- [x] Task 11: 实现登录与状态命令
  - [x] SubTask 11.1: 实现 `commands/login.py` — `bco login`（4 级降级登录）
  - [x] SubTask 11.2: 实现 `commands/status.py` — `bco status`（检查登录态）

## Phase 3: 核心职位操作命令

- [x] Task 12: 实现搜索命令 `bco search`
  - [x] SubTask 12.1: 实现 `commands/search.py` — 关键词搜索 + 8 维筛选 + 福利过滤 + 分页

- [x] Task 13: 实现推荐命令 `bco recommend`
  - [x] SubTask 13.1: 实现 `commands/recommend.py` — 基于 profile.yml 和 cv.md 的个性化推荐

- [x] Task 14: 实现打招呼命令 `bco greet` / `bco batch-greet`
  - [x] SubTask 14.1: 实现 `commands/greet.py` — 单个/批量打招呼，浏览器通道，Hook veto，高斯延迟

- [x] Task 15: 实现投递命令 `bco apply`
  - [x] SubTask 15.1: 实现 `commands/apply.py` — 投递简历，浏览器通道，Hook veto

## Phase 4: 评估引擎

- [x] Task 16: 实现评估维度定义 `src/boss_career_ops/evaluator/dimensions.py`
  - [x] SubTask 16.1: 定义 5 个评估维度（匹配度/薪资/地点/发展/团队）及权重

- [x] Task 17: 实现评分计算器 `src/boss_career_ops/evaluator/scorer.py`
  - [x] SubTask 17.1: 实现加权评分计算 + A-F 等级映射

- [x] Task 18: 实现评估引擎主逻辑 `src/boss_career_ops/evaluator/engine.py`
  - [x] SubTask 18.1: 实现评估流程编排（读取 cv.md + profile.yml → JD 解析 → 5 维评分 → 加权总分 → 等级 → 建议）

- [x] Task 19: 实现评估报告生成器 `src/boss_career_ops/evaluator/report.py`
  - [x] SubTask 19.1: 实现中文 Markdown 评估报告生成

- [x] Task 20: 实现评估命令 `bco evaluate`
  - [x] SubTask 20.1: 实现 `commands/evaluate.py` — 单个/批量评估，`--from-search` 参数

## Phase 5: 流水线引擎

- [x] Task 21: 实现流水线阶段定义 `src/boss_career_ops/pipeline/stages.py`
  - [x] SubTask 21.1: 定义 6 阶段（发现→评估→投递→沟通→面试→offer）及转换规则

- [x] Task 22: 实现流水线状态管理 `src/boss_career_ops/pipeline/manager.py`
  - [x] SubTask 22.1: 实现职位状态追踪、阶段自动推进、SQLite 持久化

- [x] Task 23: 实现自动执行策略 `src/boss_career_ops/pipeline/auto_action.py`
  - [x] SubTask 23.1: 实现阈值驱动自动执行（高分自动投递/打招呼，低分跳过，中间确认）

- [x] Task 24: 实现流水线相关命令
  - [x] SubTask 24.1: 实现 `commands/pipeline.py` — `bco pipeline`（查看流水线状态）
  - [x] SubTask 24.2: 实现 `commands/auto_action.py` — `bco auto-action`（阈值驱动自动执行）
  - [x] SubTask 24.3: 实现 `commands/follow_up.py` — `bco follow-up`（跟进提醒）
  - [x] SubTask 24.4: 实现 `commands/digest.py` — `bco digest`（每日摘要）

## Phase 6: 简历生成模块

- [x] Task 25: 实现 Markdown 简历生成器 `src/boss_career_ops/resume/generator.py`
  - [x] SubTask 25.1: 根据 JD 定制内容，从 cv.md 提取并重组简历

- [x] Task 26: 实现 ATS 关键词注入 `src/boss_career_ops/resume/keywords.py`
  - [x] SubTask 26.1: 从 JD 提取关键词，注入简历提高 ATS 通过率

- [x] Task 27: 实现 PDF 生成引擎 `src/boss_career_ops/resume/pdf_engine.py`
  - [x] SubTask 27.1: 使用 Playwright 渲染 HTML 模板为 PDF

- [x] Task 28: 创建简历模板 `src/boss_career_ops/resume/templates/default.html`
  - [x] SubTask 28.1: 创建默认 HTML/CSS 简历模板

- [x] Task 29: 实现简历命令 `bco resume`
  - [x] SubTask 29.1: 实现 `commands/resume.py` — 生成定制简历（MD/PDF）

## Phase 7: 沟通管理命令

- [x] Task 30: 实现聊天管理命令
  - [x] SubTask 30.1: 实现 `commands/chat.py` — `bco chat`（聊天列表 + 导出）
  - [x] SubTask 30.2: 实现 `commands/chatmsg.py` — `bco chatmsg`（聊天消息历史）
  - [x] SubTask 30.3: 实现 `commands/mark.py` — `bco mark`（联系人标签）
  - [x] SubTask 30.4: 实现 `commands/exchange.py` — `bco exchange`（交换联系方式）

## Phase 8: 监控与导出命令

- [x] Task 31: 实现增量监控命令 `bco watch`
  - [x] SubTask 31.1: 实现 `commands/watch.py` — 子命令 add/list/remove/run，增量对比新职位

- [x] Task 32: 实现精选列表命令 `bco shortlist`
  - [x] SubTask 32.1: 实现 `commands/shortlist.py` — 精选职位管理

- [x] Task 33: 实现多格式导出命令 `bco export`
  - [x] SubTask 33.1: 实现 `commands/export.py` — CSV/JSON/HTML/Markdown 导出，防公式注入和路径遍历

## Phase 9: 高级功能命令

- [x] Task 34: 实现面试准备命令 `bco interview`
  - [x] SubTask 34.1: 实现 `commands/interview.py` — 技术问题、STAR 框架、公司背景

- [x] Task 35: 实现薪资谈判辅助命令 `bco negotiate`
  - [x] SubTask 35.1: 实现 `commands/negotiate.py` — 市场薪资参考、谈判策略、话术建议

## Phase 10: TUI Dashboard

- [x] Task 36: 实现 TUI Dashboard `src/boss_career_ops/dashboard/`
  - [x] SubTask 36.1: 实现 `app.py` — Textual 主应用入口
  - [x] SubTask 36.2: 实现 `screens/pipeline_screen.py` — 流水线总览屏幕
  - [x] SubTask 36.3: 实现 `screens/analytics_screen.py` — 数据分析屏幕（漏斗/转化率）
  - [x] SubTask 36.4: 实现 `screens/detail_screen.py` — 职位详情屏幕
  - [x] SubTask 36.5: 实现 `commands/dashboard.py` — `bco dashboard` 命令

## Phase 11: Browser Bridge 与 Chrome 扩展

- [x] Task 37: 实现 Bridge 协议 `src/boss_career_ops/bridge/protocol.py`
  - [x] SubTask 37.1: 定义命令/结果类型

- [x] Task 38: 实现 Bridge daemon `src/boss_career_ops/bridge/daemon.py`
  - [x] SubTask 38.1: 实现 aiohttp HTTP+WS daemon

- [x] Task 39: 实现 Bridge 客户端 `src/boss_career_ops/bridge/client.py`
  - [x] SubTask 39.1: 实现 BridgeClient，连接 daemon

- [x] Task 40: 创建 Chrome 扩展 `extension/`
  - [x] SubTask 40.1: 创建 manifest.json（Manifest V3）
  - [x] SubTask 40.2: 创建 background.js（Service Worker）
  - [x] SubTask 40.3: 创建 popup.html（状态面板）

## Phase 12: AI Agent 集成与收尾

- [x] Task 41: 实现命令 schema 描述 `src/boss_career_ops/schema.py`
  - [x] SubTask 41.1: 为所有命令生成结构化 schema 描述，供 AI Agent 理解

- [x] Task 42: 创建 AI Agent skill 定义 `skills/boss-career-ops.md`
  - [x] SubTask 42.1: 编写通用 skill 描述文件

- [x] Task 43: 创建 GEMINI.md
  - [x] SubTask 43.1: 编写 Gemini CLI 上下文文件

- [x] Task 44: 注册所有命令到 CLI 主入口
  - [x] SubTask 44.1: 在 `cli/main.py` 中注册所有 26 个命令

# Task Dependencies

- [Task 1] 无依赖，最先执行
- [Task 2, 3, 4, 5] 依赖 [Task 1]，可并行
- [Task 6] 依赖 [Task 1, 2]
- [Task 7, 8, 9, 10] 依赖 [Task 1, 3]，可并行
- [Task 11] 依赖 [Task 8, 9]
- [Task 12, 13] 依赖 [Task 7, 10, 11]
- [Task 14, 15] 依赖 [Task 9, 11, 5]
- [Task 16, 17, 18, 19] 依赖 [Task 2]，串行
- [Task 20] 依赖 [Task 18, 19]
- [Task 21, 22, 23] 依赖 [Task 4, 5]，串行
- [Task 24] 依赖 [Task 22, 23]
- [Task 25, 26, 27, 28] 依赖 [Task 2]，可并行
- [Task 29] 依赖 [Task 25, 27, 28]
- [Task 30] 依赖 [Task 7, 11]
- [Task 31, 32, 33] 依赖 [Task 4, 7]
- [Task 34, 35] 依赖 [Task 2, 7]
- [Task 36] 依赖 [Task 22, 4]
- [Task 37, 38, 39] 依赖 [Task 1, 3]，串行
- [Task 40] 依赖 [Task 38]
- [Task 41, 42, 43] 依赖 [Task 44]
- [Task 44] 依赖所有命令实现完成
