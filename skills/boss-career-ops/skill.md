---
name: "boss-career-ops"
skill_version: "0.7.0"
description: "BOSS直聘AI求职全流程CLI工具，覆盖搜索/评估/投递/沟通/面试闭环。Agent直接编排AI任务（评估/润色/摘要/面试准备），无需外部API。零配置可用（规则引擎开箱即用），AI无缝升级。Invoke when user asks about job search, BOSS直聘, 职位搜索, 投递, 打招呼, 面试, or any job-hunting operations."
---

# Boss-Career-Ops Skill

BOSS 直聘 AI 求职全流程系统。通过 `bco` CLI 命令完成从职位发现到拿到 offer 的完整闭环。
AI 任务（评估/润色/摘要/面试准备）由 Agent 直接完成，无需配置外部 LLM API。

核心原则：**AI 评估推荐，人决定行动。系统自动执行高分职位，低分职位需人工确认。**

零配置可用：规则引擎开箱即用（5 维评分 + 等级 + 推荐语 + 匹配原因），AI 是无缝升级而非前置条件。

## 全局选项

| 选项 | 说明 |
|------|------|
| `bco --version` | 查看版本号 |
| `bco --help` | 查看帮助 |

## 会话启动流程

**每次用户提到求职/BOSS直聘相关话题时，必须按顺序执行以下检查：**

### 第 1 步：检查 bco 是否已安装

```bash
bco --version
```

- 若成功，说明已通过 `uv tool install` 或 `pip install` 全局安装，后续所有命令直接用 `bco <cmd>`
- 若命令不存在，检查是否为开发模式（当前目录存在 `pyproject.toml` 且包含 `boss-career-ops`）：
  - 开发模式：使用 `uv run bco <cmd>` 执行所有后续命令
  - 非开发模式，提示用户安装：
    - 推荐：`uv tool install boss-career-ops`
    - 备选：`pip install boss-career-ops`
    - 若上述安装失败，可从源码安装：`uv tool install git+https://github.com/maimaigptlink9/boss-career-ops.git`
    - 安装完成后重新执行本步骤确认

### 第 2 步：检查并更新到最新版本

已安装或开发模式下均需检查版本是否为最新，旧版本可能缺少功能或存在已知 bug。

```bash
# 检查当前版本
bco --version
```

然后查询 PyPI 最新版本并比较：

```bash
# 方式一（推荐，需 uv）
uv tool upgrade boss-career-ops --dry-run 2>&1 | findstr "Upgraded"

# 方式二（需 pip）
pip index versions boss-career-ops 2>nul
```

- 若当前版本 < 最新版本，执行更新：
  - uv 安装的：`uv tool upgrade boss-career-ops`
  - pip 安装的：`pip install --upgrade boss-career-ops`
  - 源码安装的：`uv tool install --force --reinstall git+https://github.com/maimaigptlink9/boss-career-ops.git`
  - 开发模式：`git pull && uv sync`
- 更新完成后重新执行 `bco --version` 确认版本号已更新
- 若已是最新版本，直接进入下一步

### 第 2.5 步：检查并更新 skill.md

bco 更新后，skill.md 可能也需要同步更新（新命令、新错误码、工作流变更等）。执行：

```bash
bco skill-update --check
```

- 输出 `data.remote_version`，Agent 对比本地 skill.md 的 `skill_version`
- 若本地版本 < 远程版本，执行 `bco skill-update` 获取完整内容：
  ```bash
  bco skill-update
  ```
  输出的 `data.content` 即为最新 skill.md 全文，Agent 将其写入本地 skill.md 文件
- 更新后需重启 Agent 会话以加载新 skill

### 第 3 步：环境诊断

```bash
bco doctor
```

- 若输出 `ok: false` 且错误提示配置缺失，执行 `bco setup` 初始化，然后重新诊断
- 配置目录位于 `~/.bco/`（可通过 `BCO_HOME` 环境变量自定义根目录）

### 第 4 步：检查登录态

```bash
bco status
```

- 若未登录，执行 `bco login` 提示用户登录
- 登录方式 4 级降级：Bridge Cookie → CDP → QR httpx → patchright，系统自动选择
- **登录需要用户交互**，Agent 必须等待用户完成操作：
  - Bridge Cookie 方式：系统自动启动 Daemon 并等待 Chrome 扩展连接，扩展在 Chrome 内部读取 Cookie 绕过 ABE 加密，无需手动操作
  - CDP 方式：系统自动检测 Chrome Profile 并启动调试模式，默认选择第一个配置文件；多配置文件时可通过 `bco login --profile <目录名>` 指定；若 Chrome 正在运行则需用户先关闭
  - QR httpx 方式：纯 HTTP 二维码登录，终端显示二维码链接，用户用 BOSS App 扫码，无需浏览器
  - patchright 方式会弹出浏览器窗口，需用户手动扫码或操作
  - Agent 不应跳过此步骤，必须确认登录成功后再继续

### 第 5 步：检查个人档案

提醒用户编辑个人档案（评估和推荐的核心依赖）：

- `~/.bco/config/profile.yml` — 填写技能、期望薪资、偏好城市等结构化信息
- `~/.bco/cv.md` — 填写完整简历内容（Markdown 格式）

**未配置档案的后果**：
- `evaluate`：4/5 维度退化为固定中低分（2.5~3.0），评估结果无区分度
- `recommend`：不传城市和关键词参数，返回与用户意向无关的默认推荐
- `resume`：回退到规则逻辑（关键词追加），无法使用 AI 润色

## 输出协议

所有命令输出 JSON，统一信封格式：

```json
{
  "ok": true,
  "schema_version": "1.0",
  "command": "<command_name>",
  "data": {},
  "pagination": {"page": 1, "pages_fetched": 1, "has_more": true, "total": 15},
  "error": null,
  "hints": {"next_actions": ["..."]}
}
```

- `ok` 字段判断成败
- 错误信息在 `error.message`（中文）和 `error.code`（英文）
- `hints.next_actions` 建议下一步操作，应遵循执行

### 编码与文件输出

- **CLI 输出强制 UTF-8**，管道和重定向不会导致中文乱码
- `bco search` 支持 `-o <file>` 直接写文件，推荐 Agent 使用此方式：
  ```bash
  bco search Python --city 深圳 --pages 2 -o output/search.json
  python -c "import json; d=json.load(open('output/search.json',encoding='utf-8')); print(len(d['data']))"
  ```
- 不使用管道（`bco search ... | python -c "..."`），避免 Windows PowerShell 编码问题

## 评估引擎：5 维评分体系

| 维度 | 权重 | 评估内容 |
|------|------|----------|
| 匹配度 | 30% | 技能、经验、学历与 JD 的匹配程度（全行业同义词表 ~100 组） |
| 薪资 | 25% | 薪资范围与预期的对比，连续评分（非阶梯跳变） |
| 地点 | 15% | 城市偏好、邻近城市支持、远程可能性 |
| 发展 | 15% | 职业成长空间（按岗位类型选关键词：技术/产品/运营/市场/设计/数据/管理） |
| 团队 | 15% | 公司阶段、团队文化（按岗位类型选关键词） |

### 评分改进

- **评分区分度提升**：发展/团队基准分从 3.0 降至 1.5，解决评分集中在 C 级的问题
- **全行业同义词表**：覆盖技术/产品/运营/市场/设计/数据/财务/人力/销售/内容/电商/法务/行政/通用共 ~100 组
- **匹配原因输出**：每个评估结果包含 `match_reasons`（优势）和 `mismatch_reasons`（不足）
- **信息不足标记**：搜索结果缺 description 时标记 `confidence: "preliminary"`，提示查看详情后评分可能变化
- **薪资连续评分**：用连续函数替代阶梯跳变
- **邻近城市支持**：广州→深圳 3.5 分（而非 2.0），北京→天津同理

### 评分等级

| 等级 | 分数 | 含义 | 自动动作 |
|------|------|------|----------|
| A | 4.5-5.0 | 强烈推荐，立即行动 | 自动投递 |
| B | 3.5-4.4 | 值得投入，优先处理 | 自动打招呼 |
| C | 2.5-3.4 | 一般，需人工判断 | 需确认 |
| D | 1.5-2.4 | 不太匹配，谨慎考虑 | 需确认 |
| F | 0.0-1.4 | 不推荐 | 跳过 |

## 核心工作流

```
搜索职位 → 5维评估 → 自动/手动决策 → 简历定制（Agent润色） → 上传简历 → 打招呼/投递（浏览器通道） → 沟通跟进 → 面试准备 → offer
```

## Web 仪表盘工作流

`bco web` 启动 AI 求职决策仪表盘，零配置可用（规则引擎开箱即用）。

### 使用场景

- **决策看板**：Pipeline 看板 + 5 维评分可视化 + 优劣势分析 + 待办提醒
- **AI 助手**：回复建议、简历定制（预览+下载）、面试准备、技能差距分析
- **设置页**：AI Key 配置引导（30 秒完成，Provider 信息从 `data/llm_providers.yml` 读取）

### AI 配置 Web 化

未配置 AI 时，规则引擎功能（评分、Pipeline 看板）始终可用。AI 助手页面显示引导提示 + "去设置"按钮。

配置方式：
1. Web 设置页：`bco web` → 设置 → AI 配置 → 选择 Provider → 粘贴 API Key → 保存
2. 环境变量：`BCO_LLM_API_KEY` + `BCO_LLM_PROVIDER`

优先级：环境变量 > `~/.bco/ai_config.yml` > 规则引擎

## Agent AI 编排

AI 任务由 Agent 直接完成，无需配置外部 API。Agent 读取数据 → 思考分析 → 调用工具写入结果。

### 评估流程

```
Agent:
  1. bco agent-evaluate <job_id>              # 读取职位数据
  2. [思考：分析 JD、匹配技能、评估薪资、考虑地点...]
  3. bco agent-save evaluate --job-id <id> --score 4.2 --grade B --analysis "..."
```

### 简历润色流程

```
Agent:
  1. 读取 ~/.bco/cv.md                        # 原始简历
  2. bco agent-evaluate <job_id>              # 读取 JD
  3. [思考：提取 JD 关键词、优化经历描述、注入 ATS 关键词...]
  4. bco agent-save resume --job-id <id> --content "# 简历\n..."
  5. bco resume <job_id> --format pdf         # 使用润色内容生成 PDF
```

### 聊天摘要流程

```
Agent:
  1. bco chatmsg <security_id>                # 读取聊天记录
  2. [思考：总结要点、判断语气、建议下一步...]
  3. bco agent-save chat-summary --security-id <id> --data '{"summary":"...","sentiment":"positive"}'
```

### 面试准备流程

```
Agent:
  1. bco agent-evaluate <job_id>              # 读取职位+公司信息
  2. [思考：技术问题、STAR 故事、反问、简历可能被问到的问题...]
  3. bco agent-save interview-prep --job-id <id> --data '{"tech_questions":[...],"star_stories":[...]}'
```

## 命令完整参考

### 环境与认证

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco doctor` | 环境诊断 | `bco doctor` |
| `bco setup` | 初始化配置（首次使用） | `bco setup` |
| `bco login` | 登录（4级降级：Bridge Cookie→CDP→QR httpx→patchright） | `bco login` 或 `bco login --profile <目录名>` |
| `bco logout` | 清除本地登录态 | `bco logout` |
| `bco status` | 检查登录态 | `bco status` |
| `bco bridge` | Bridge Daemon 管理 | 见下方子命令 |
| `bco skill-update` | 检查远程版本并获取最新 skill.md 内容 | `bco skill-update --check` 或 `bco skill-update` |

### Agent AI 任务

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco agent-evaluate` | 输出职位数据供 Agent 评估 | `bco agent-evaluate <job_id>` 或 `bco agent-evaluate --stage 发现 --limit 10` |
| `bco agent-save` | 保存 Agent AI 结果到数据库 | 见下方子命令 |

#### bridge 子命令

| 子命令 | 说明 | 用法 |
|--------|------|------|
| `bridge status` | 查看 Bridge Daemon 状态 | `bco bridge status` |
| `bridge test` | Bridge 连通性诊断（3 步检查） | `bco bridge test` |

- `bridge status` 输出：Daemon 是否运行、Chrome 扩展连接数、上次 Cookie 获取时间及有效性
- `bridge test` 按步骤诊断：[1/3] Daemon 连通性 → [2/3] Chrome 扩展连接 → [3/3] Cookie 获取
- 每步失败时停止并输出具体原因和恢复提示

#### agent-save 子命令

| 子命令 | 说明 | 用法 |
|--------|------|------|
| `evaluate` | 保存评估结果 | `bco agent-save evaluate --job-id <id> --score 4.2 --grade B --analysis "..."` |
| `resume` | 保存简历润色结果 | `bco agent-save resume --job-id <id> --content "# 简历\n..."` |
| `chat-summary` | 保存聊天摘要 | `bco agent-save chat-summary --security-id <id> --data '{"summary":"..."}'` |
| `interview-prep` | 保存面试准备 | `bco agent-save interview-prep --job-id <id> --data '{"tech_questions":[...]}'` |

### 职位搜索与评估

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco search` | 搜索职位 + 福利筛选 | `bco search <keyword> --city <city> --welfare <welfare> --page <n> --limit <n> --pages <n> -o <file>` |
| | 输出到文件（绕过管道编码问题） | `bco search <keyword> -o result.json` |
| `bco recommend` | 基于个人档案的个性化推荐 | `bco recommend` |
| `bco evaluate` | 5维评估（单个/批量，规则引擎） | `bco evaluate [target]` 或 `bco evaluate --from-search` |
| `bco detail` | 查看职位完整详情（双通道降级） | `bco detail <security_id>` |

### 投递与沟通

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco greet` | 打招呼 | `bco greet <security_id> <job_id>` |
| `bco batch-greet` | 批量打招呼（高斯延迟，最大10个） | `bco batch-greet <keyword> --city <city>` |
| `bco apply` | 投递简历（浏览器通道） | `bco apply <security_id> <job_id>` |
| `bco apply` | 投递前先上传简历再投递 | `bco apply <security_id> <job_id> --resume <job_id>` |
| `bco resume` | 生成定制简历（MD/PDF） | `bco resume <job_id> --format <md\|pdf>` |
| `bco resume` | 生成 PDF 并上传到 BOSS 直聘平台 | `bco resume <job_id> --format pdf --upload` |

### 聊天管理

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco chat` | 聊天列表（不带 --export 时列出所有聊天） | `bco chat` |
| `bco chat` | 聊天导出 | `bco chat --export <csv\|json\|html\|md>` |
| `bco chatmsg` | 聊天消息历史 | `bco chatmsg <security_id>` |
| `bco chat-summary` | 聊天摘要（Agent 生成或规则回退） | `bco chat-summary <security_id>` |
| `bco mark` | 联系人标签 | `bco mark <security_id> --tag <tag>` |

### 流水线与导出

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco pipeline` | 求职流水线追踪（无参数） | `bco pipeline` |
| `bco export` | 多格式导出 | `bco export <keyword> --city <city> -o <output> --format <csv\|json\|html\|md> --count <n>` |

### 面试与 Dashboard

| 命令 | 说明 | 用法 |
|------|------|------|
| `bco interview` | 面试准备（Agent 生成） | `bco interview <job_id>` |
| `bco dashboard` | 启动 TUI Dashboard（无参数） | `bco dashboard` |
| `bco web` | 启动 Web 仪表盘（AI 求职决策仪表盘，零配置可用） | `bco web` |

## 错误码速查表

遇到 `ok: false` 时，根据 `error.code` 执行对应恢复动作：

| 错误码 | 含义 | 恢复动作 |
|--------|------|----------|
| `AUTH_REQUIRED` | 未登录 | `bco login` |
| `AUTH_EXPIRED` | 登录过期 | `bco login` |
| `TOKEN_REFRESH_FAILED` | Token 刷新失败 | `bco login` |
| `LOGIN_FAILED` | 登录失败 | 检查网络，重试 `bco login` |
| `RATE_LIMITED` | 频率过高 | 等待后重试 |
| `ACCOUNT_RISK` | 风控拦截 | 建议用 CDP Chrome 重试：`chrome.exe --remote-debugging-port=9222` |
| `GREET_LIMIT` | 今日打招呼次数用完 | 告知用户，次日再试 |
| `ALREADY_GREETED` | 已打过招呼 | 跳过此职位 |
| `NETWORK_ERROR` | 网络错误 | 重试 |
| `INVALID_PARAM` | 参数错误 | 修正参数后重试 |
| `SEARCH_ERROR` | 搜索错误 | 检查参数，重试 |
| `EVALUATE_ERROR` | 评估错误 | 检查职位数据，重试 |
| `PARSE_ERROR` | 数据解析错误 | 检查输入格式 |
| `HOOK_VETO` | Hook 拦截 | 确认操作意图 |
| `SKIPPED_LOW_SCORE` | 低分跳过 | 正常行为，无需处理 |
| `CONFIRM_REQUIRED` | 需人工确认 | 提示用户确认 |
| `BATCH_GREET_ERROR` | 批量打招呼错误 | 检查登录态和参数 |
| `RESUME_UPLOAD_ERROR` | 简历上传失败 | 检查浏览器通道，手动上传 |
| `APPLY_BROWSER_ERROR` | 浏览器通道不可用 | 启动 Chrome CDP：`chrome.exe --remote-debugging-port=9222` |
| `AI_NOT_AVAILABLE` | AI 不可用 | 使用 `bco agent-evaluate` + `bco agent-save` 替代 |
| `AI_NOT_CONFIGURED` | AI 功能需要配置 API Key | 引导用户到 `bco web` 设置页配置，或设置环境变量 |
| `WEB_AUTH_REQUIRED` | Web 写操作需要认证 | 设置 `BCO_WEB_API_KEY` 环境变量 |
| `VALIDATION_ERROR` | 参数验证失败 | 检查输入参数 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `BCO_HOME` | 配置根目录 | `~/.bco/` |
| `BCO_LLM_PROVIDER` | LLM 提供者（deepseek/openai/local） | deepseek |
| `BCO_LLM_API_KEY` | LLM API Key | — |
| `BCO_LLM_BASE_URL` | API Base URL（兼容 OpenAI 接口） | — |
| `BCO_LLM_MODEL` | 模型名 | deepseek-chat |
| `BCO_WEB_API_KEY` | Web 仪表盘写操作认证 Key | —（未设置时仅本地访问，启动时打印警告） |
| `BCO_EMBEDDING_PROVIDER` | RAG Embedding 提供者（local/openai） | local |

修改 `BCO_HOME` 后，所有配置文件（profile.yml、thresholds.yml、tokens.enc 等）均从新目录读取。

AI 配置优先级：环境变量 > `~/.bco/ai_config.yml`（Web 设置页保存） > 规则引擎。

## 安全与合规规则

1. **严格遵守阈值配置**，不擅自降低自动执行标准
2. **所有写操作**（打招呼、投递）前确认用户意图
3. **速率限制**：系统内置高斯延迟 + 5% 概率随机长停顿，不要绕过
4. **浏览器通道节流**：降级到浏览器时同样受节流控制，不要绕过
5. **敏感信息**（Token、Cookie、API Key）不输出到日志或对话
6. **批量操作上限**：batch-greet 最大 10 个，不要拆分绕过
7. **串行执行**：禁止并发调用多个 bco 命令（如同时开多个终端运行 search + recommend），必须等上一个命令完成后再执行下一个。并发调用会导致进程间限流失效（每个进程独立计数，高斯延迟/突发惩罚/限流惩罚全部失效），实际 QPS 成倍增长，触发平台风控
8. 用户提到福利要求时使用 `--welfare` 参数
9. 评估后根据 `hints.next_actions` 建议下一步
10. 不要在未评估的情况下直接投递或打招呼
11. **Web 仪表盘**：默认仅本地访问（`127.0.0.1`），写操作需 `BCO_WEB_API_KEY` 认证
12. **Token 自动刷新**：stoken 过期时系统自动尝试 CDP 刷新，无需用户重新登录
