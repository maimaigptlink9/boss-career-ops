# Boss-Career-Ops

BOSS 直聘 AI 求职全流程 CLI 工具。覆盖从职位搜索到拿到 offer 的完整闭环。

**核心原则：AI 评估推荐，人决定行动。系统自动执行高分职位，低分职位需人工确认。**

**AI 编排：AI 任务（评估/润色/摘要/面试准备）由 Agent 直接完成，无需配置外部 LLM API。**

## 功能概览

- **职位搜索** — 关键词 + 城市 + 福利多维筛选
- **5 维评估** — 匹配度、薪资、地点、发展、团队自动评分
- **阈值驱动** — batch-greet 内置阈值逻辑，B 级自动打招呼，D 级自动跳过
- **简历定制** — 根据职位 JD 生成 ATS 友好的 MD/PDF 简历
- **批量打招呼** — 高斯随机延迟，最大 10 个，防封号
- **聊天管理** — 消息历史、摘要、标签、导出
- **求职流水线** — 发现→评估→投递→沟通→面试→offer 全程追踪，所有操作结果自动入库
- **面试准备** — 基于职位信息生成面试要点
- **TUI Dashboard** — 终端可视化求职看板

## 快速开始

### 安装

```bash
# 推荐：uv 全局安装
uv tool install boss-career-ops

# 或 pip
pip install boss-career-ops

# 或从源码安装
uv tool install git+https://github.com/maimaigptlink9/boss-career-ops.git
```

**要求：Python >= 3.12**

### 开发模式

```bash
git clone https://github.com/maimaigptlink9/boss-career-ops.git
cd boss-career-ops
uv sync
uv run bco <cmd>
uv run pytest
```

### 初始化

```bash
# 1. 环境诊断
bco doctor

# 2. 首次使用，初始化配置
bco setup

# 3. 登录 BOSS 直聘（自动检测 Chrome Profile，3 级降级）
bco login

# 4. 确认登录态
bco status
```

### 基本使用

```bash
# 搜索职位
bco search "Golang" --city 广州 --welfare "双休,五险一金"

# 对搜索结果批量评估
bco evaluate --from-search

# 批量打招呼（内置阈值逻辑）
bco batch-greet "Golang" --city 广州

# 生成定制简历
bco resume <job_id> --format pdf

# 查看求职流水线
bco pipeline
```

## 评估引擎

### 5 维评分体系

| 维度 | 权重 | 评估内容 |
|------|------|----------|
| 匹配度 | 30% | 技能、经验、学历与 JD 的匹配程度 |
| 薪资 | 25% | 薪资范围与预期的对比，行业竞争力 |
| 地点 | 15% | 通勤距离、城市偏好、远程可能性 |
| 发展 | 15% | 职业成长空间、技术栈前瞻性、团队规模 |
| 团队 | 15% | 公司阶段、团队文化、面试反馈信号 |

### 评分等级与自动动作

| 等级 | 分数 | 含义 | 自动动作 |
|------|------|------|----------|
| A | 4.5-5.0 | 强烈推荐 | 自动投递 |
| B | 3.5-4.4 | 值得投入 | 自动打招呼 |
| C | 2.5-3.4 | 一般 | 需人工确认 |
| D | 1.5-2.4 | 不太匹配 | 需人工确认 |
| F | 0.0-1.4 | 不推荐 | 跳过 |

## 命令参考

### 环境与认证

| 命令 | 说明 |
|------|------|
| `bco doctor` | 环境诊断 |
| `bco setup` | 初始化配置（首次使用） |
| `bco login` | 登录（3 级降级：Bridge Cookie→CDP→patchright），支持 `--profile` 指定 Chrome 配置文件 |
| `bco status` | 检查登录态 |
| `bco bridge status` | 查看 Bridge Daemon 状态 |
| `bco bridge test` | Bridge 连通性诊断（3 步检查） |
| `bco skill-update` | 检查远程版本并获取最新 skill.md 内容 |

### Agent AI 任务

| 命令 | 说明 |
|------|------|
| `bco agent "帮我找深圳的Agent岗位"` | AI Agent 对话式求职助手（LangGraph 多Agent编排） |
| `bco agent --interactive` | 交互模式，持续对话 |
| `bco agent-evaluate <job_id>` | 输出职位数据供 Agent 评估 |
| `bco agent-evaluate --stage 发现 --limit 10` | 输出待评估职位列表 |
| `bco agent-save evaluate --job-id <id> --score <n> --grade <G> --analysis "..."` | 保存评估结果 |
| `bco agent-save resume --job-id <id> --content "..."` | 保存简历润色结果 |
| `bco agent-save chat-summary --security-id <id> --data '...'` | 保存聊天摘要 |
| `bco agent-save interview-prep --job-id <id> --data '...'` | 保存面试准备 |

### RAG 知识库

| 命令 | 说明 |
|------|------|
| `bco rag-index` | 构建/更新 RAG 知识库索引（从 Pipeline DB 读取 JD） |
| `bco rag-index --reindex` | 全量重建索引 |
| `bco rag-search "AI Agent 开发" --collection jd --top-k 10` | RAG 语义搜索（jd/resume/interview） |

### MCP Server

| 命令 | 说明 |
|------|------|
| `bco mcp-server` | 启动 MCP Server（供 Claude Desktop 等客户端调用） |

### 职位搜索与评估

| 命令 | 说明 |
|------|------|
| `bco search <keyword> --city <city> --welfare <welfare>` | 搜索职位 + 福利筛选 |
| `bco recommend` | 个性化推荐 |
| `bco evaluate [target]` 或 `--from-search` | 5 维评估 |

### 投递与沟通

| 命令 | 说明 |
|------|------|
| `bco greet <security_id> <job_id>` | 打招呼 |
| `bco batch-greet <keyword> --city <city>` | 批量打招呼（最大 10 个） |
| `bco apply <security_id> <job_id>` | 投递简历 |
| `bco apply <security_id> <job_id> --resume <job_id>` | 投递前先上传简历再投递 |
| `bco resume <job_id> --format <md\|pdf>` | 生成定制简历 |
| `bco resume <job_id> --format pdf --upload` | 生成 PDF 并上传到 BOSS 直聘平台 |

### 聊天管理

| 命令 | 说明 |
|------|------|
| `bco chat --export <csv\|json\|html\|md>` | 聊天管理 + 导出 |
| `bco chatmsg <security_id>` | 聊天消息历史 |
| `bco chat-summary <security_id>` | 聊天摘要 |
| `bco mark <security_id> --tag <tag>` | 联系人标签 |

### 流水线与导出

| 命令 | 说明 |
|------|------|
| `bco pipeline` | 求职流水线追踪（数据来自搜索/评估/投递等操作的自动入库） |
| `bco export <keyword> -o <output> --format <csv\|json\|html\|md>` | 多格式导出 |

### 面试与 Dashboard

| 命令 | 说明 |
|------|------|
| `bco interview <job_id>` | 面试准备 |
| `bco dashboard` | 启动 TUI Dashboard |

## 配置

所有配置存储在 `~/.bco/` 目录（可通过 `BCO_HOME` 环境变量自定义）。

### 个人档案 — `~/.bco/config/profile.yml`

```yaml
name: ""
title: ""
experience_years: 0
skills: []
expected_salary:
  min: 0
  max: 0
preferred_cities: []
remote_ok: false
education: ""
career_goals: ""
avoid: ""
```

### 简历 — `~/.bco/cv.md`

Markdown 格式的完整简历，评估引擎和简历生成器都会读取此文件。越详细，评估越准确。

### 自动执行阈值 — `~/.bco/config/thresholds.yml`

```yaml
auto_action:
  auto_greet_threshold: 4.0    # B+ 及以上自动打招呼
  auto_apply_threshold: 4.5    # A 级自动投递
  skip_threshold: 2.0          # D 级及以下直接跳过
  confirm_required: true       # 中间分数段需人工确认

rate_limit:
  request_delay_min: 1.5       # 请求最小延迟（秒）
  request_delay_max: 3.0       # 请求最大延迟（秒）
  batch_greet_max: 10          # 批量打招呼上限
  batch_greet_delay_min: 2.0   # 批量打招呼最小延迟
  batch_greet_delay_max: 5.0   # 批量打招呼最大延迟
  burst_penalty_multiplier: 2.0  # 突发惩罚倍数
  retry_max_attempts: 3        # 最大重试次数
  retry_base_delay: 5.0        # 重试基础延迟
  retry_max_delay: 60.0        # 重试最大延迟
  search_page_delay_min: 3.0   # 搜索翻页最小延迟
  search_page_delay_max: 6.0   # 搜索翻页最大延迟
  search_max_pages: 5          # 搜索最大翻页数

cache:
  default_ttl: 3600            # 默认缓存 TTL（秒）
  search_ttl: 1800             # 搜索缓存 TTL（秒）
```

## AI Agent 集成

本工具专为 AI Agent 设计，AI 任务由 Agent 直接完成，无需配置外部 LLM API。

### 工作原理

```
Agent 读取数据（bco agent-evaluate / bco chatmsg）
  → Agent 思考分析（评估/润色/摘要/面试准备）
  → Agent 写入结果（bco agent-save）
  → 后续命令读取 Agent 结果（bco evaluate / bco resume / bco interview）
```

### Agent 工具命令

- `bco agent-evaluate` — 输出职位数据供 Agent 评估分析
- `bco agent-save` — 保存 Agent 的 AI 分析结果到数据库

### Skill 集成

将 [skills/boss-career-ops/skill.md](skills/boss-career-ops/skill.md) 放到对应 Agent 的 skill 目录即可自动理解并调用 `bco` 命令：

**OpenClaw：**

```bash
mkdir -p ~/.openclaw/skills/boss-career-ops && cp skills/boss-career-ops/skill.md ~/.openclaw/skills/boss-career-ops/skill.md
```

**Claude Code：**

在项目目录中打开 Claude Code，`CLAUDE.md` 会自动加载为上下文。

**WorkBuddy：**

```bash
cp skills/boss-career-ops/skill.md ~/.workbuddy/skills/boss-career-ops/skill.md
```

## 安全说明

- Token 使用 Fernet 加密存储（PBKDF2 密钥派生，绑定机器+用户）
- 请求间隔使用高斯随机延迟，模拟人类行为
- 批量操作内置上限（batch-greet 最大 10 个）
- 敏感信息不输出到日志
- CSV 导出防止公式注入，文件导出防止路径遍历

## 系统升级路线图

> 目标：将现有 CLI 自动化工具升级为真正的 AI Agent 系统，同时满足「求职实用」和「面试证明 Agent 开发能力」两个目标。

### 已完成改造

| 改造 | 状态 | 核心变化 | 详细文档 |
|------|------|----------|----------|
| LangGraph 多Agent编排 | ✅ 已完成 | Agent I/O 数据通道 → StateGraph + Conditional Edge 路由，6 个专业 Agent 节点 | [upgrade-langgraph.md](doc/upgrade-langgraph.md) |
| RAG 知识库 | ✅ 已完成 | 关键词匹配 → ChromaDB 语义向量检索 + MMR 重排 | [upgrade-rag.md](doc/upgrade-rag.md) |
| MCP Server | ✅ 已完成 | CLI 命令行 → MCP 协议（JSON-RPC over stdio），9 Tool + 3 Resource | [upgrade-mcp.md](doc/upgrade-mcp.md) |

### 新增依赖

`pyproject.toml` 的 dependencies 已新增：`langchain>=0.3`、`langgraph>=0.2`、`langchain-openai>=0.2`、`chromadb>=0.5`、`mcp>=1.0`

### LLM 配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `BCO_LLM_PROVIDER` | LLM 提供者（openai/deepseek/local） | deepseek |
| `BCO_LLM_API_KEY` | API Key | — |
| `BCO_LLM_BASE_URL` | API Base URL（兼容 OpenAI 接口） | — |
| `BCO_LLM_MODEL` | 模型名 | deepseek-chat |

### Claude Desktop 集成

```json
{
  "mcpServers": {
    "boss-career-ops": {
      "command": "bco",
      "args": ["mcp-server"]
    }
  }
}
```

---

## 参考项目

本项目融合了以下两个开源项目的核心能力：

- [boss-agent-cli](https://github.com/can4hou6joeng4/boss-agent-cli) — AI Agent 专用的 BOSS 直聘求职 CLI 工具，提供平台操作能力（搜索、打招呼、投递、聊天等）
- [career-ops](https://github.com/santifer/career-ops/tree/main) — AI 驱动的求职评估系统，提供智能评估能力（多维评分、简历定制、面试准备等）

## License

MIT
