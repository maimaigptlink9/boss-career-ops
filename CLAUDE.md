# Boss-Career-Ops 开发工作流

BOSS 直聘 AI 求职全流程系统。融合 career-ops 的智能评估能力与 boss-agent-cli 的平台操作能力，覆盖从职位发现到拿到 offer 的完整闭环。

## 定位

本项目是专为 AI Agent 设计的求职命令中心，通过 `bco` CLI 提供完整的求职自动化能力。

**核心原则**：AI 评估推荐，人决定行动。系统自动执行高分职位，低分职位需人工确认。

**Agent 操作手册**：见 [skills/boss-career-ops.md](skills/boss-career-ops.md)

## 技术栈

| 层面            | 技术                       |
| ------------- | ------------------------ |
| 语言            | Python 3.12              |
| CLI 框架        | Click                    |
| 浏览器自动化        | patchright（反检测 Chromium） |
| PDF 生成        | Playwright + Chromium    |
| TUI Dashboard | Textual + Rich           |
| 数据存储          | SQLite                   |
| HTTP 客户端      | httpx                    |
| 包管理           | uv                       |

## 项目结构

```
boss-career-ops/
├── src/boss_career_ops/
│   ├── cli/                        # CLI 入口与命令注册
│   │   ├── __init__.py
│   │   └── main.py                 # Click 主入口，注册所有命令组
│   │
│   ├── commands/                   # 所有 CLI 命令实现
│   │   ├── setup.py                # 初始化配置（首次使用）
│   │   ├── search.py               # 职位搜索 + 8 维筛选 + 福利过滤
│   │   ├── recommend.py            # 个性化推荐
│   │   ├── evaluate.py             # 职位评估（5 维评分引擎）
│   │   ├── greet.py                # 单个/批量打招呼
│   │   ├── apply.py                # 投递简历
│   │   ├── resume.py               # 简历生成（Markdown + PDF）
│   │   ├── chat.py                 # 聊天管理 + 导出
│   │   ├── chatmsg.py              # 聊天消息历史 + AI 摘要
│   │   ├── mark.py                 # 联系人标签管理
│   │   ├── exchange.py             # 交换联系方式
│   │   ├── pipeline.py             # 求职流水线追踪
│   │   ├── follow_up.py            # 跟进提醒
│   │   ├── digest.py               # 每日摘要
│   │   ├── watch.py                # 增量监控（定时搜索新职位）
│   │   ├── shortlist.py            # 精选列表
│   │   ├── interview.py            # 面试准备（AI 增强 + 规则回退）
│   │   ├── negotiate.py            # 薪资谈判辅助（AI 增强 + 规则回退）
│   │   ├── export.py               # 多格式导出（CSV/JSON/HTML/Markdown）
│   │   ├── ai_config.py            # AI 配置管理（bco ai-config）
│   │   └── doctor.py               # 环境诊断
│   │
│   ├── data/                       # 包内数据文件（随 wheel 打包）
│   │   ├── profile.example.yml     # 个人档案模板
│   │   └── thresholds.example.yml  # 阈值配置模板
│   │
│   ├── evaluator/                  # 评估引擎核心
│   │   ├── __init__.py
│   │   ├── engine.py               # 5 维评分引擎主逻辑
│   │   ├── dimensions.py           # 5 个评估维度定义与权重
│   │   ├── scorer.py               # 评分计算器
│   │   └── report.py               # 评估报告生成器（中文 Markdown）
│   │
│   ├── resume/                     # 简历生成模块
│   │   ├── __init__.py
│   │   ├── generator.py            # Markdown 简历生成器
│   │   ├── pdf_engine.py           # PDF 生成（Playwright）
│   │   ├── templates/              # 简历模板（HTML/CSS）
│   │   └── keywords.py             # ATS 关键词注入
│   │
│   ├── boss/                       # BOSS 直聘 API 交互层（内嵌 boss-agent-cli 核心）
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── boss.yaml           # API 端点定义
│   │   │   ├── endpoints.py        # 端点暴露
│   │   │   └── client.py           # BossClient HTTP 客户端
│   │   ├── auth/
│   │   │   ├── manager.py          # 认证管理器
│   │   │   └── token_store.py      # Token 存储（原子文件锁）
│   │   ├── browser_client.py       # 浏览器会话管理
│   │   └── search_filters.py       # 搜索过滤逻辑
│   │
│   ├── pipeline/                   # 求职流水线引擎
│   │   ├── __init__.py
│   │   ├── manager.py              # 流水线状态管理（upsert_job/batch_add_jobs/update_job_data）
│   │   ├── stages.py               # 阶段定义（发现→评估→投递→沟通→面试→offer）
│   │   └── auto_action.py          # 自动执行策略（阈值驱动）
│   │
│   ├── ai/                         # AI 集成模块
│   │   ├── __init__.py
│   │   ├── provider.py             # AIProvider 抽象基类 + OpenAI 兼容实现
│   │   └── config.py               # AI 配置管理（~/.bco/config/ai.yml）
│   │
│   ├── dashboard/                  # Python TUI Dashboard
│   │   ├── __init__.py
│   │   ├── app.py                  # Textual 主应用（含事件串联）
│   │   ├── screens/                # 各屏幕
│   │   │   ├── pipeline_screen.py  # 流水线总览（搜索/筛选/行点击事件）
│   │   │   ├── analytics_screen.py # 数据分析（漏斗/转化率）
│   │   │   └── detail_screen.py    # 职位详情（Markdown 渲染）
│   │   └── widgets/                # TUI 组件
│   │
│   ├── bridge/                     # Browser Bridge（零配置浏览器连接）
│   │   ├── protocol.py             # 命令/结果类型定义（7 种命令）
│   │   ├── daemon.py               # aiohttp HTTP+WS daemon（转发给 Chrome 扩展）
│   │   └── client.py               # BridgeClient（7 种方法封装）
│   │
│   ├── cache/                      # 缓存层
│   │   ├── __init__.py
│   │   └── store.py                # SQLite 缓存存储
│   │
│   ├── config/                     # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py             # 全局配置（路径解析 + 用户目录支持）
│   │   └── thresholds.py           # 自动执行阈值配置
│   │
│   ├── hooks/                      # Hook 系统
│   │   ├── __init__.py
│   │   └── manager.py              # 钩子注册与执行（greet_before/after 等）
│   │
│   ├── display/                    # 输出格式化
│   │   ├── __init__.py
│   │   ├── output.py               # JSON 信封格式化
│   │   ├── logger.py               # 日志系统
│   │   └── error_codes.py          # 错误码枚举（17 种）
│   │
│   └── schema.py                   # 命令 schema 描述（供 AI Agent 理解）
│
├── extension/                      # Chrome 扩展（Browser Bridge）
│   ├── manifest.json               # Manifest V3
│   ├── background.js               # Service Worker
│   └── popup.html                  # 状态面板
│
├── skills/                         # AI Agent skill 定义
│   └── boss-career-ops.md          # 通用 skill 描述（Agent 操作手册）
│
├── templates/
│   └── resume/                     # 简历模板
│       └── default.html            # 默认 HTML 简历模板
│
├── tests/                          # 测试
│
├── CLAUDE.md                       # 本文件：开发工作流
├── pyproject.toml                  # Python 包配置
└── cv.md                           # 用户简历（Markdown 格式，开发模式回退）
```

## 评估引擎：5 维评分体系

### 维度定义

| 维度      | 权重  | 评估内容               |
| ------- | --- | ------------------ |
| **匹配度** | 30% | 技能、经验、学历与 JD 的匹配程度 |
| **薪资**  | 25% | 薪资范围与预期的对比，行业竞争力   |
| **地点**  | 15% | 通勤距离、城市偏好、远程可能性    |
| **发展**  | 15% | 职业成长空间、技术栈前瞻性、团队规模 |
| **团队**  | 15% | 公司阶段、团队文化、面试反馈信号   |

### 评分等级

| 等级 | 分数        | 含义        |
| -- | --------- | --------- |
| A  | 4.5 - 5.0 | 强烈推荐，立即行动 |
| B  | 3.5 - 4.4 | 值得投入，优先处理 |
| C  | 2.5 - 3.4 | 一般，需人工判断  |
| D  | 1.5 - 2.4 | 不太匹配，谨慎考虑 |
| F  | 0.0 - 1.4 | 不推荐       |

### 自动执行阈值

在 `~/.bco/config/thresholds.yml` 中配置（可通过 `BCO_HOME` 环境变量自定义根目录）：

```yaml
auto_action:
  # 评估分数 >= 此值时，自动执行打招呼/投递
  auto_greet_threshold: 4.0    # B+ 及以上自动打招呼
  auto_apply_threshold: 4.5    # A 级自动投递

  # 评估分数 < 此值时，直接跳过
  skip_threshold: 2.0          # D 级及以下直接跳过

  # 中间分数段（2.0 - 4.0）需要人工确认
  confirm_required: true
```

## 开发约定

- 所有代码注释使用中文
- 所有面向用户的输出使用中文
- 命令名和参数名使用英文（保持 CLI 惯例）
- 错误信息使用中文，错误代码使用英文
- 所有异步操作提供 `--delay` 参数控制速率
- 所有写操作（打招呼、投递）必须通过 Hook 系统支持 veto 拦截
- CacheStore 使用 context manager 管理生命周期
- 浏览器操作遵循降级链：Bridge → CDP → patchright headless
- **所有影响工作流的代码改动必须同步更新本文件**（CLAUDE.md），包括但不限于：新增/删除命令、数据流变更、设计模式变更、API 架构变更、配置项增减。未同步视为未完成

## 安全要求

- Token 存储在 `~/.bco/tokens.enc`，使用 Fernet 加密（PBKDF2 密钥派生，绑定机器+用户）
- Token 写入使用原子文件锁（O\_CREAT | O\_EXCL）
- 旧版 `~/.boss_career_ops/` 的 Token 首次运行时自动迁移到 `~/.bco/`
- CSV 导出防止公式注入
- 文件导出防止路径遍历
- 敏感信息（Token、Cookie）不输出到日志
- 速率限制防止账号被封

## BOSS 直聘 API 客户端架构

### 混合通道设计

BossClient 采用双通道架构，根据操作风险等级选择不同通道：

| 通道 | 适用操作 | 技术 |
|------|----------|------|
| httpx 通道 | 低风险（搜索、列表、聊天历史） | httpx HTTP/2 |
| 浏览器通道 | 高风险（登录、打招呼、投递） | patchright / CDP / Bridge |

### 声明式 API 端点

端点通过 `boss/api/boss.yaml` 声明式定义（12 个端点：搜索、详情、打招呼、投递、聊天等），代码通过 `Endpoints` 单例自动加载，便于维护和更新。

### 4 级降级登录链

| 级别 | 方式 | 反爬意义 | 需要浏览器 |
|------|------|----------|------------|
| 1 | Cookie 提取 | 从 10+ 浏览器免扫码提取真实用户 Cookie，最接近真人 | 否 |
| 2 | CDP 登录 | 复用真实 Chrome 实例（`--remote-debugging-port`），共享浏览器指纹 | 是 |
| 3 | QR httpx | 纯 HTTP 二维码，无需安装任何浏览器 | 否 |
| 4 | patchright | 反检测 Chromium 兜底 | 是 |

降级优先使用真实浏览器的 Cookie/会话（级别 1-2），仅在高级别不可用时降级。

### 浏览器连接 3 级降级链

浏览器操作遵循降级链：Bridge → CDP → patchright headless

### 反爬策略

- **高斯随机延迟**：请求间隔使用高斯分布（非固定 sleep），模拟人类行为
- **突发惩罚机制**：检测短时间密集请求并自动减速
- **批量操作限制**：`batch_greet_max: 10`，延迟区间 `[2.0, 5.0]`
- **反重定向保护**：通过 `add_init_script` 注入 JS，拦截 `Location.assign`/`Location.replace`/`history.pushState`，阻止非 `/web/geek/` 的跳转（在 `BrowserClient.get_page()`、CDP/patchright 登录中自动注入）
- **patchright 替代 Playwright**：移除 `navigator.webdriver` 等自动化指纹

### 错误码体系

| 错误码 | 含义 | 修复策略 |
|--------|------|----------|
| `AUTH_REQUIRED` | 未登录 | `bco login` |
| `AUTH_EXPIRED` | 登录过期 | `bco login` |
| `RATE_LIMITED` | 频率过高 | 等待后重试 |
| `TOKEN_REFRESH_FAILED` | Token 刷新失败 | `bco login` |
| `ACCOUNT_RISK` | 风控拦截 | CDP Chrome 重试 |
| `INVALID_PARAM` | 参数错误 | 修正参数 |
| `ALREADY_GREETED` | 已打过招呼 | 跳过 |
| `GREET_LIMIT` | 今日次数用完 | 告知用户 |
| `NETWORK_ERROR` | 网络错误 | 重试 |
| `AI_NOT_CONFIGURED` | AI 未配置 | `bco ai-config --api-key <key>` |

## 核心设计模式

| 模式 | 应用场景 |
|------|----------|
| **分层架构** | CLI → Commands → Domain（evaluator/resume/pipeline）→ Infrastructure（boss/cache/config） |
| **策略模式** | 评估维度可插拔，自动执行策略可配置，AI Provider 可插拔（OpenAI 兼容/本地模型） |
| **降级链** | 浏览器操作：Bridge → CDP → patchright headless；登录：Cookie → CDP → QR → patchright |
| **信封模式** | 所有输出统一 JSON 信封格式 `{ok, schema_version, command, data, pagination, error, hints}` |
| **Hook 系统** | 写操作支持 veto 拦截（`greet_before/after`、`apply_before/after`） |
| **Context Manager** | CacheStore 生命周期管理（`with CacheStore() as cache:`） |
| **阈值驱动** | 评估分数直接驱动自动/手动/跳过决策 |
| **Pipeline 持久化** | 所有命令结果自动入库（batch_add_jobs/upsert_job），阶段推进自动更新（update_stage），入库失败不中断命令 |
| **单例模式** | Endpoints、BossClient、TokenStore、AuthManager、BrowserClient、Settings、Thresholds 均为单例 |
| **声明式配置** | API 端点用 YAML 定义，阈值外部化到 `thresholds.yml` |
| **AI 优先回退** | chat-summary/interview/negotiate 优先使用 AI 生成，AI 不可用时回退到规则模板 |

### 数据流

```
用户 → CLI (Click) → Command → Domain Service → BossClient/Browser → BOSS直聘
                                              → CacheStore (SQLite WAL)
                                              → Evaluator Engine
                                              → Pipeline Manager (SQLite WAL)
                                              → AI Provider (OpenAI 兼容 / 规则回退)
```

### Pipeline 数据持久化规则

所有产生职位数据的命令**必须**将结果写入 PipelineManager，所有推进状态的命令**必须**更新 Pipeline 阶段：

| 命令 | Pipeline 操作 | 阶段 |
|------|--------------|------|
| `search` | `batch_add_jobs` 批量入库 | 发现 |
| `recommend` | `batch_add_jobs` 批量入库 | 发现 |
| `watch run` | `batch_add_jobs` 新职位入库 | 发现 |
| `evaluate` | `upsert_job` + `update_score` + `update_stage` + `update_job_data(评估报告)` | → 评估 |
| `greet` | `upsert_job` + `update_stage`（成功时） | → 沟通 |
| `apply` | `upsert_job` + `update_stage`（成功时） | → 投递 |
| `chat` | `update_stage`（阶段早于沟通时） | → 沟通 |
| `exchange` | `update_stage`（成功时） | → 沟通 |

关键约束：
- **入库失败不中断命令**：所有 Pipeline 写入包裹在 `try/except` 中，失败仅 `logger.warning`
- **去重语义**：`batch_add_jobs` 用 `INSERT OR IGNORE`（已存在则跳过），`upsert_job` 用 `ON CONFLICT DO UPDATE`（已存在则合并 data，不改变 stage/score/grade）
- **阶段不回退**：`upsert_job` 冲突时保留已有阶段和评分；`chat` 显式检查 `current_idx < comm_idx` 才推进
