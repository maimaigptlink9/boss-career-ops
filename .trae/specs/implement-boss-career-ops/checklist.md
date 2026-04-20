# Checklist

## Phase 1: 项目脚手架与基础设施

- [x] pyproject.toml 正确声明所有依赖和 `bco` 入口点
- [x] `bco --help` 输出所有可用命令
- [x] `config/profile.example.yml` 包含完整的个人档案模板字段
- [x] `config/thresholds.example.yml` 包含自动执行阈值配置模板
- [x] `cv.md` 模板文件存在
- [x] settings.py 能加载 profile.yml、thresholds.yml、cv.md，缺失时使用默认值
- [x] thresholds.py 正确解析 auto_greet_threshold、auto_apply_threshold、skip_threshold
- [x] output.py 的 JSON 信封格式包含 ok/schema_version/command/data/pagination/error/hints 字段
- [x] logger.py 对 Token/Cookie 等敏感信息脱敏
- [x] CacheStore 使用 SQLite WAL 模式，支持 context manager，支持 TTL 过期
- [x] HookManager 支持 greet_before/after、apply_before/after 注册和 veto 拦截
- [x] `bco doctor` 检查 Python 版本、依赖、浏览器驱动、配置文件、登录态

## Phase 2: BOSS 直聘 API 交互层

- [x] boss.yaml 声明式定义所有 API 端点
- [x] endpoints.py 正确解析 YAML 暴露端点对象
- [x] BossClient httpx 通道请求头模拟真实浏览器
- [x] BossClient 实现高斯随机延迟（默认 1.5-3.0 秒）
- [x] token_store.py 使用 Fernet + PBKDF2 机器绑定加密
- [x] token_store.py 使用原子文件锁（O_CREAT | O_EXCL）
- [x] manager.py 实现 4 级降级登录链（Cookie → CDP → QR httpx → patchright）
- [x] manager.py 实现 Token 质量检测（wt2/stoken 完整性）
- [x] BrowserClient 实现降级链（Bridge → CDP → patchright headless）
- [x] search_filters.py 实现 8 维筛选 + 福利关键词匹配
- [x] `bco login` 执行 4 级降级登录
- [x] `bco status` 检查登录态并输出 JSON 信封

## Phase 3: 核心职位操作命令

- [x] `bco search "Golang" --city 广州` 返回职位列表 JSON
- [x] `bco search --welfare "双休,五险一金"` 自动翻页逐条匹配福利
- [x] `bco recommend` 基于 profile.yml 和 cv.md 推荐匹配职位
- [x] `bco greet <sid> <jid>` 通过浏览器通道发送招呼
- [x] `bco greet` 触发 greet_before/after Hook
- [x] `bco batch-greet` 高斯随机延迟，最大批量 10 个
- [x] `bco apply <sid> <jid>` 通过浏览器通道投递简历
- [x] `bco apply` 触发 apply_before/after Hook

## Phase 4: 评估引擎

- [x] dimensions.py 定义 5 个评估维度及权重（匹配度30%/薪资25%/地点15%/发展15%/团队15%）
- [x] scorer.py 实现加权评分计算和 A-F 等级映射
- [x] engine.py 读取 cv.md + profile.yml 与 JD 比对，输出 5 维评分
- [x] report.py 生成中文 Markdown 评估报告
- [x] `bco evaluate <security_id>` 输出单个职位评估结果
- [x] `bco evaluate --from-search` 批量评估搜索结果

## Phase 5: 流水线引擎

- [x] stages.py 定义 6 阶段（发现→评估→投递→沟通→面试→offer）及转换规则
- [x] manager.py 追踪职位状态，阶段自动推进，SQLite 持久化
- [x] auto_action.py 阈值驱动自动执行（≥4.5投递/≥4.0打招呼/<2.0跳过/中间确认）
- [x] `bco pipeline` 显示所有职位及其当前阶段
- [x] `bco auto-action` 根据阈值自动执行
- [x] `bco follow-up` 列出需要跟进的职位
- [x] `bco digest` 输出每日摘要

## Phase 6: 简历生成模块

- [x] generator.py 根据 JD 定制内容从 cv.md 提取并重组简历
- [x] keywords.py 从 JD 提取关键词注入简历
- [x] pdf_engine.py 使用 Playwright 渲染 HTML 为 PDF
- [x] default.html 简历模板包含完整 HTML/CSS 样式
- [x] `bco resume <jid> --format md` 生成 Markdown 简历
- [x] `bco resume <jid> --format pdf` 生成 PDF 简历

## Phase 7: 沟通管理命令

- [x] `bco chat` 返回聊天会话列表
- [x] `bco chat --export csv` 导出聊天记录
- [x] `bco chatmsg <sid>` 返回聊天消息历史
- [x] `bco mark <sid> --tag 收藏` 添加联系人标签
- [x] `bco exchange <sid> --type phone` 发送交换联系方式请求

## Phase 8: 监控与导出命令

- [x] `bco watch add my-watch "Golang" --city 广州` 保存搜索条件
- [x] `bco watch run my-watch` 增量对比标记新职位
- [x] `bco shortlist` 显示精选职位列表
- [x] `bco export "Golang" -o jobs.csv` 导出 CSV，特殊字符转义防公式注入
- [x] 导出路径包含 `..` 或绝对路径时拒绝操作

## Phase 9: 高级功能命令

- [x] `bco interview <jid>` 输出面试准备材料
- [x] `bco negotiate <jid>` 输出薪资谈判策略

## Phase 10: TUI Dashboard

- [x] `bco dashboard` 启动 Textual TUI 应用
- [x] 流水线总览屏幕显示所有职位状态
- [x] 数据分析屏幕显示漏斗/转化率
- [x] 职位详情屏幕显示完整职位信息

## Phase 11: Browser Bridge 与 Chrome 扩展

- [x] protocol.py 定义命令/结果类型
- [x] daemon.py 实现 aiohttp HTTP+WS daemon
- [x] BridgeClient 能连接 daemon
- [x] Chrome 扩展 manifest.json 符合 Manifest V3
- [x] Chrome 扩展 background.js 实现 Service Worker
- [x] Chrome 扩展 popup.html 显示状态面板

## Phase 12: AI Agent 集成与收尾

- [x] schema.py 为所有命令生成结构化 schema 描述
- [x] skills/boss-career-ops.md 包含完整的 skill 定义
- [x] GEMINI.md 包含 Gemini CLI 上下文
- [x] cli/main.py 注册所有 26 个命令
- [x] 所有命令输出统一 JSON 信封格式
- [x] 所有代码注释使用中文
- [x] 所有面向用户的输出使用中文
- [x] 所有写操作通过 Hook 系统支持 veto 拦截
