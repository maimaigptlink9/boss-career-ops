# Boss-Career-Ops

BOSS 直聘 AI 求职全流程 CLI 工具。覆盖从职位搜索到拿到 offer 的完整闭环。

**核心原则：AI 评估推荐，人决定行动。系统自动执行高分职位，低分职位需人工确认。**

## 功能概览

- **职位搜索** — 关键词 + 城市 + 福利多维筛选
- **5 维评估** — 匹配度、薪资、地点、发展、团队自动评分
- **阈值驱动** — A 级自动投递，B 级自动打招呼，D 级自动跳过
- **简历定制** — 根据职位 JD 生成 ATS 友好的 MD/PDF 简历
- **批量打招呼** — 高斯随机延迟，最大 10 个，防封号
- **聊天管理** — 消息历史、摘要、标签、导出
- **求职流水线** — 发现→评估→投递→沟通→面试→offer 全程追踪，所有操作结果自动入库
- **增量监控** — 定时搜索新职位，不错过机会
- **面试准备** — 基于职位信息生成面试要点
- **薪资谈判** — 辅助谈判策略与话术

## 快速开始

### 安装

```bash
# 推荐：uv 全局安装
uv tool install boss-career-ops

# 或 pip
pip install boss-career-ops
```

### 初始化

```bash
# 1. 环境诊断
bco doctor

# 2. 首次使用，初始化配置
bco setup

# 3. 登录 BOSS 直聘（扫码或自动提取浏览器 Cookie）
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

# 阈值驱动自动执行（高分打招呼/投递，低分跳过）
bco auto-action

# 生成定制简历
bco resume <job_id> --format pdf

# 查看求职流水线
bco pipeline

# 每日摘要
bco digest
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
| `bco login` | 登录（4 级降级：Cookie→CDP→QR→patchright） |
| `bco status` | 检查登录态 |

### 职位搜索与评估

| 命令 | 说明 |
|------|------|
| `bco search <keyword> --city <city> --welfare <welfare>` | 搜索职位 + 福利筛选 |
| `bco recommend` | 个性化推荐 |
| `bco evaluate <security_id>` 或 `--from-search` | 5 维评估 |
| `bco auto-action` | 阈值驱动自动执行 |
| `bco shortlist` | 精选列表（B 级及以上） |

### 投递与沟通

| 命令 | 说明 |
|------|------|
| `bco greet <security_id> <job_id>` | 打招呼 |
| `bco batch-greet <keyword> --city <city>` | 批量打招呼（最大 10 个） |
| `bco apply <security_id> <job_id>` | 投递简历 |
| `bco resume <job_id> --format <md\|pdf>` | 生成定制简历 |

### 聊天管理

| 命令 | 说明 |
|------|------|
| `bco chat --export <csv\|json\|html\|md>` | 聊天管理 + 导出 |
| `bco chatmsg <security_id>` | 聊天消息历史 |
| `bco chat-summary <security_id>` | 聊天摘要 |
| `bco mark <security_id> --tag <tag>` | 联系人标签 |
| `bco exchange <security_id> --type <phone\|wechat>` | 交换联系方式 |

### 流水线与追踪

| 命令 | 说明 |
|------|------|
| `bco pipeline` | 求职流水线追踪（数据来自搜索/评估/投递等操作的自动入库） |
| `bco follow-up` | 跟进提醒（3 天未推进的职位） |
| `bco digest` | 每日摘要（新增/评估/投递/待跟进） |
| `bco shortlist` | 精选列表（B 级及以上） |

### 监控与导出

| 命令 | 说明 |
|------|------|
| `bco watch add <name> <keyword> --city <city>` | 添加监控 |
| `bco watch list` | 列出监控 |
| `bco watch remove <name>` | 移除监控 |
| `bco watch run <name>` | 执行监控 |
| `bco export <keyword> -o <output> --format <csv\|json\|html\|md>` | 多格式导出 |

### 面试与谈判

| 命令 | 说明 |
|------|------|
| `bco interview <job_id>` | 面试准备 |
| `bco negotiate <job_id>` | 薪资谈判辅助 |
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
```

## AI Agent 集成

本工具专为 AI Agent 设计，支持 OpenClaw、Claude Code、WorkBuddy 等。

### OpenClaw

将 [skills/boss-career-ops.md](skills/boss-career-ops.md) 放到 OpenClaw 的 skill 目录，Agent 即可自动理解并调用 `bco` 命令：

```bash
mkdir -p ~/.openclaw/skills/boss-career-ops && cp skills/boss-career-ops.md ~/.openclaw/skills/boss-career-ops/SKILL.md
```

重启 OpenClaw 后，在对话中提到求职相关话题，Agent 会自动按 skill 指引完成安装、登录和操作。

### Claude Code

在项目目录中打开 Claude Code，`CLAUDE.md` 会自动加载为上下文，Agent 即可理解 `bco` 命令。

### WorkBuddy

将 [skills/boss-career-ops.md](skills/boss-career-ops.md) 复制到 `~/.workbuddy/skills/boss-career-ops/SKILL.md`，重启 WorkBuddy 即可。

## 安全说明

- Token 使用 Fernet 加密存储（PBKDF2 密钥派生，绑定机器+用户）
- 请求间隔使用高斯随机延迟，模拟人类行为
- 批量操作内置上限（batch-greet 最大 10 个）
- 敏感信息不输出到日志
- CSV 导出防止公式注入，文件导出防止路径遍历

## 参考项目

本项目融合了以下两个开源项目的核心能力：

- [boss-agent-cli](https://github.com/can4hou6joeng4/boss-agent-cli) — AI Agent 专用的 BOSS 直聘求职 CLI 工具，提供平台操作能力（搜索、打招呼、投递、聊天等）
- [career-ops](https://github.com/santifer/career-ops/tree/main) — AI 驱动的求职评估系统，提供智能评估能力（多维评分、简历定制、面试准备等）

## License

MIT
