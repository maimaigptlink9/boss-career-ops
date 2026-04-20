# Boss-Career-Ops 全系统实现 Spec

## Why

当前项目仅有 CLAUDE.md 设计文档，无任何代码实现。需要按设计文档完整实现 BOSS 直聘 AI 求职全流程系统——融合 career-ops 的智能评估能力与 boss-agent-cli 的平台操作能力，覆盖从职位发现到拿到 offer 的完整闭环。

## What Changes

- 新建 Python 包项目（pyproject.toml + src 布局），CLI 入口为 `bco`
- 实现 BOSS 直聘 API 交互层（httpx 混合通道 + 4 级降级登录 + patchright 浏览器自动化）
- 实现 5 维评估引擎（匹配度/薪资/地点/发展/团队，加权评分 → A-F 等级）
- 实现简历生成模块（Markdown 生成 + ATS 关键词注入 + Playwright PDF 渲染）
- 实现求职流水线引擎（6 阶段状态机 + 阈值驱动自动执行）
- 实现 26 个 CLI 命令（doctor/login/status/search/evaluate/greet/apply/resume/pipeline 等）
- 实现 TUI Dashboard（Textual + Rich）
- 实现 Browser Bridge（aiohttp HTTP+WS daemon + Chrome 扩展）
- 实现配置管理、缓存层、Hook 系统、输出格式化等基础设施

## Impact

- Affected specs: 全新项目，无既有 spec
- Affected code: 从零构建 `src/boss_career_ops/` 下所有模块

## ADDED Requirements

### Requirement: 项目脚手架与包配置

系统 SHALL 提供 Python 3.12 包项目结构，使用 uv 包管理，src 布局，CLI 入口点为 `bco`。

#### Scenario: 安装与运行

- **WHEN** 用户执行 `uv sync` 安装依赖
- **THEN** 所有依赖（click, httpx, patchright, playwright, textual, rich, pyyaml 等）正确安装
- **WHEN** 用户执行 `bco --help`
- **THEN** 显示所有可用命令的帮助信息

### Requirement: 统一 JSON 信封输出

所有 CLI 命令 SHALL 输出统一 JSON 信封格式到 stdout：

```json
{
  "ok": true,
  "schema_version": "1.0",
  "command": "<命令名>",
  "data": <数据负载>,
  "pagination": {"page": 1, "has_more": true, "total": 15},
  "error": null,
  "hints": {"next_actions": ["<建议下一步>"]}
}
```

#### Scenario: 成功输出

- **WHEN** 命令执行成功
- **THEN** `ok` 为 `true`，`data` 包含结果数据，`error` 为 `null`，`hints.next_actions` 建议下一步操作

#### Scenario: 错误输出

- **WHEN** 命令执行失败
- **THEN** `ok` 为 `false`，`error` 包含中文描述和英文错误码，`data` 为 `null`

### Requirement: 配置管理

系统 SHALL 支持三层配置：`config/profile.yml`（个人档案）、`config/thresholds.yml`（自动执行阈值）、`cv.md`（用户简历）。

#### Scenario: 加载配置

- **WHEN** 系统启动时
- **THEN** 自动加载配置文件，缺失时使用默认值并提示用户配置

#### Scenario: 个人档案

- **WHEN** 用户编辑 `config/profile.yml`
- **THEN** 系统读取姓名、技能、期望薪资、城市偏好、职业目标等信息用于评估和推荐

### Requirement: 缓存层

系统 SHALL 使用 SQLite WAL 模式缓存数据，CacheStore 使用 context manager 管理生命周期。

#### Scenario: 缓存命中

- **WHEN** 重复请求相同数据
- **THEN** 从缓存返回结果，减少网络请求

#### Scenario: 缓存过期

- **WHEN** 缓存数据超过 TTL
- **THEN** 重新请求并更新缓存

### Requirement: BOSS 直聘 API 客户端

系统 SHALL 实现混合通道 BossClient：httpx 处理低风险操作（搜索、列表），浏览器处理高风险操作（登录、打招呼、投递）。

#### Scenario: 低风险操作

- **WHEN** 执行搜索、列表等读取操作
- **THEN** 使用 httpx 通道，请求头模拟真实浏览器

#### Scenario: 高风险操作

- **WHEN** 执行登录、打招呼、投递等写操作
- **THEN** 使用浏览器通道（降级链：Bridge → CDP → patchright headless）

#### Scenario: API 端点声明

- **WHEN** 系统加载 `boss/api/boss.yaml`
- **THEN** 解析端点定义，自动构建请求 URL 和参数

### Requirement: 4 级降级登录

系统 SHALL 实现 4 级降级登录链：Cookie 提取 → CDP 登录 → QR httpx → patchright 兜底。

#### Scenario: Cookie 提取（级别 1）

- **WHEN** 本地浏览器存在有效 Cookie
- **THEN** 免扫码提取 Cookie，无需安装浏览器

#### Scenario: CDP 登录（级别 2）

- **WHEN** 用户启动带 `--remote-debugging-port` 的 Chrome
- **THEN** 复用 Chrome 实例完成登录

#### Scenario: QR httpx（级别 3）

- **WHEN** 前两级不可用
- **THEN** 纯 HTTP 二维码扫码登录，无需浏览器

#### Scenario: patchright 兜底（级别 4）

- **WHEN** 前三级均不可用
- **THEN** 启动反检测 Chromium 完成登录

### Requirement: Token 安全存储

系统 SHALL 使用 Fernet + PBKDF2 机器绑定加密存储 Token，原子文件锁（O_CREAT | O_EXCL）防止并发写入。

#### Scenario: Token 加密存储

- **WHEN** Token 写入磁盘
- **THEN** 使用机器特征绑定密钥加密，防止跨机器使用

#### Scenario: Token 质量检测

- **WHEN** 系统检查登录态
- **THEN** 验证 `wt2/stoken` 完整性，过期时提示重新登录

### Requirement: 职位搜索命令

`bco search` SHALL 支持关键词搜索 + 8 维筛选 + 福利过滤，结果输出 JSON 信封。

#### Scenario: 基本搜索

- **WHEN** 用户执行 `bco search "Golang" --city 广州`
- **THEN** 返回广州 Golang 职位列表，包含分页信息

#### Scenario: 福利筛选

- **WHEN** 用户执行 `bco search "Golang" --welfare "双休,五险一金"`
- **THEN** 自动翻页逐条匹配福利关键词，仅返回满足条件的职位

### Requirement: 5 维评估引擎

系统 SHALL 实现 5 维评分引擎：匹配度(30%) + 薪资(25%) + 地点(15%) + 发展(15%) + 团队(15%)，输出 A-F 等级。

#### Scenario: 单个职位评估

- **WHEN** 用户执行 `bco evaluate <security_id>`
- **THEN** 读取 `cv.md` 和 `profile.yml`，与 JD 比对，输出 5 维评分 + 加权总分 + 等级 + 建议

#### Scenario: 批量评估

- **WHEN** 用户执行 `bco evaluate --from-search`
- **THEN** 对上次搜索结果逐个评估，输出批量评估报告

#### Scenario: 等级映射

- **WHEN** 加权总分计算完成
- **THEN** 映射到等级：A(4.5-5.0), B(3.5-4.4), C(2.5-3.4), D(1.5-2.4), F(0.0-1.4)

### Requirement: 阈值驱动自动执行

系统 SHALL 根据评估分数自动决策：≥4.5 自动投递，≥4.0 自动打招呼，<2.0 跳过，中间需确认。

#### Scenario: 高分自动执行

- **WHEN** 评估分数 ≥ 4.5
- **THEN** 自动投递简历

#### Scenario: 中间分数需确认

- **WHEN** 评估分数在 2.0-4.0 之间
- **THEN** 提示用户确认是否继续

#### Scenario: 低分跳过

- **WHEN** 评估分数 < 2.0
- **THEN** 直接跳过，不执行任何操作

### Requirement: 打招呼与投递

`bco greet` / `bco apply` SHALL 通过浏览器通道执行，支持 Hook veto 拦截，批量操作有频率限制。

#### Scenario: 单个打招呼

- **WHEN** 用户执行 `bco greet <sid> <jid>`
- **THEN** 通过浏览器通道发送招呼，触发 `greet_before`/`greet_after` Hook

#### Scenario: 批量打招呼

- **WHEN** 用户执行 `bco batch-greet "Golang" --city 广州`
- **THEN** 逐个打招呼，高斯随机延迟，最大批量 10 个

#### Scenario: Hook veto

- **WHEN** `greet_before` Hook 返回 veto
- **THEN** 取消该次打招呼操作

### Requirement: 简历生成

`bco resume` SHALL 根据 JD 定制生成 Markdown 和 PDF 简历，支持 ATS 关键词注入。

#### Scenario: Markdown 简历

- **WHEN** 用户执行 `bco resume <jid> --format md`
- **THEN** 根据 JD 定制内容，生成 Markdown 简历

#### Scenario: PDF 简历

- **WHEN** 用户执行 `bco resume <jid> --format pdf`
- **THEN** 使用 Playwright 渲染 HTML 模板为 PDF，注入 ATS 关键词

### Requirement: 求职流水线

`bco pipeline` SHALL 追踪职位在 6 阶段流水线中的状态：发现→评估→投递→沟通→面试→offer。

#### Scenario: 查看流水线

- **WHEN** 用户执行 `bco pipeline`
- **THEN** 显示所有职位及其当前阶段、评估分数、下一步操作

#### Scenario: 阶段自动推进

- **WHEN** 职位完成某阶段操作（如打招呼成功）
- **THEN** 自动推进到下一阶段

### Requirement: 跟进与摘要

`bco follow-up` SHALL 提醒需要跟进的职位，`bco digest` SHALL 生成每日摘要。

#### Scenario: 跟进提醒

- **WHEN** 用户执行 `bco follow-up`
- **THEN** 列出超过 N 天未推进的职位

#### Scenario: 每日摘要

- **WHEN** 用户执行 `bco digest`
- **THEN** 输出今日新增职位、评估结果、投递状态、待跟进事项

### Requirement: 增量监控

`bco watch` SHALL 支持保存搜索条件、定时执行、增量标记新职位。

#### Scenario: 添加监控

- **WHEN** 用户执行 `bco watch add my-watch "Golang" --city 广州`
- **THEN** 保存搜索条件，后续可定时执行

#### Scenario: 执行监控

- **WHEN** 用户执行 `bco watch run my-watch`
- **THEN** 执行搜索，与历史结果对比，仅标记新出现的职位

### Requirement: 聊天管理

`bco chat` / `bco chatmsg` / `bco chat-summary` SHALL 管理与 HR 的聊天记录，支持导出和摘要。

#### Scenario: 聊天列表

- **WHEN** 用户执行 `bco chat`
- **THEN** 返回所有聊天会话列表

#### Scenario: 聊天导出

- **WHEN** 用户执行 `bco chat --export csv`
- **THEN** 导出聊天记录为 CSV 格式

#### Scenario: 聊天摘要

- **WHEN** 用户执行 `bco chat-summary <sid>`
- **THEN** 生成该会话的结构化摘要

### Requirement: 联系人标签与交换

`bco mark` SHALL 管理联系人标签，`bco exchange` SHALL 交换联系方式。

#### Scenario: 添加标签

- **WHEN** 用户执行 `bco mark <sid> --tag 收藏`
- **THEN** 为该联系人添加"收藏"标签

#### Scenario: 交换联系方式

- **WHEN** 用户执行 `bco exchange <sid> --type phone`
- **THEN** 发送交换手机号请求

### Requirement: 多格式导出

`bco export` SHALL 支持 CSV/JSON/HTML/Markdown 多格式导出，防止公式注入和路径遍历。

#### Scenario: CSV 导出

- **WHEN** 用户执行 `bco export "Golang" -o jobs.csv`
- **THEN** 导出搜索结果为 CSV，特殊字符转义防止公式注入

#### Scenario: 路径安全

- **WHEN** 导出路径包含 `..` 或绝对路径
- **THEN** 拒绝导出，提示路径不安全

### Requirement: 面试准备

`bco interview` SHALL 根据职位信息生成面试准备材料。

#### Scenario: 面试准备

- **WHEN** 用户执行 `bco interview <jid>`
- **THEN** 输出该职位相关的技术问题、行为面试 STAR 框架、公司背景信息

### Requirement: 薪资谈判辅助

`bco negotiate` SHALL 提供薪资谈判框架和策略建议。

#### Scenario: 谈判辅助

- **WHEN** 用户执行 `bco negotiate <jid>`
- **THEN** 输出市场薪资参考、谈判策略、话术建议

### Requirement: TUI Dashboard

`bco dashboard` SHALL 启动 Textual + Rich 构建的终端 UI，包含流水线总览、数据分析、职位详情三个屏幕。

#### Scenario: 启动 Dashboard

- **WHEN** 用户执行 `bco dashboard`
- **THEN** 启动 TUI 应用，显示流水线总览屏幕

#### Scenario: 屏幕切换

- **WHEN** 用户在 Dashboard 中切换屏幕
- **THEN** 可查看流水线总览、数据分析（漏斗/转化率）、职位详情

### Requirement: Browser Bridge

系统 SHALL 实现 Browser Bridge：aiohttp HTTP+WS daemon + Chrome 扩展，零配置连接用户浏览器。

#### Scenario: Bridge 连接

- **WHEN** Chrome 扩展检测到 BOSS 直聘页面
- **THEN** 自动连接 Bridge daemon，共享浏览器会话

#### Scenario: Bridge 降级

- **WHEN** Bridge 不可用
- **THEN** 降级到 CDP 或 patchright 模式

### Requirement: Hook 系统

系统 SHALL 实现 Hook 系统，所有写操作（打招呼、投递）支持 veto 拦截。

#### Scenario: 注册 Hook

- **WHEN** 用户注册 `greet_before` Hook
- **THEN** 每次打招呼前调用该 Hook，返回 veto 时取消操作

#### Scenario: Hook 执行

- **WHEN** 写操作执行
- **THEN** 按顺序调用 `before` Hook，执行操作，调用 `after` Hook

### Requirement: 环境诊断

`bco doctor` SHALL 检查所有依赖项和配置是否就绪。

#### Scenario: 环境诊断

- **WHEN** 用户执行 `bco doctor`
- **THEN** 检查 Python 版本、依赖安装、浏览器驱动、配置文件、登录态等，输出诊断报告

### Requirement: 速率限制与反爬

系统 SHALL 实现高斯随机延迟、突发惩罚、批量操作限制，防止账号被封。

#### Scenario: 请求延迟

- **WHEN** 发起 API 请求
- **THEN** 使用高斯随机延迟（默认 1.5-3.0 秒），模拟人类行为

#### Scenario: 突发惩罚

- **WHEN** 检测到短时间密集请求
- **THEN** 自动增加延迟，降低请求频率

### Requirement: 个性化推荐

`bco recommend` SHALL 根据 `profile.yml` 和 `cv.md` 推荐匹配职位。

#### Scenario: 推荐职位

- **WHEN** 用户执行 `bco recommend`
- **THEN** 基于个人档案和简历，推荐最匹配的职位列表

### Requirement: 精选列表

`bco shortlist` SHALL 管理用户精选的职位列表。

#### Scenario: 查看精选

- **WHEN** 用户执行 `bco shortlist`
- **THEN** 显示所有精选职位及其评估分数和状态

### Requirement: AI Agent 集成

系统 SHALL 提供 `schema.py` 命令描述文件和 `skills/boss-career-ops.md` skill 定义，供 AI Agent 理解和调用。

#### Scenario: Agent 调用

- **WHEN** AI Agent 通过 Bash 调用 `bco` 命令
- **THEN** 解析 stdout JSON，`ok` 字段判断成败，`hints.next_actions` 建议下一步

### Requirement: 安全规范

系统 SHALL 遵循安全要求：Token 原子文件锁、CSV 防公式注入、文件防路径遍历、敏感信息不输出日志。

#### Scenario: 敏感信息保护

- **WHEN** 系统输出日志或 JSON
- **THEN** Token、Cookie 等敏感信息脱敏或隐藏
