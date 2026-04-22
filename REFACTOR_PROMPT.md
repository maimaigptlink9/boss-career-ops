# Boss-Career-Ops 核心工作流改造

## 目标

将项目聚焦到核心工作流：**查找岗位 → 基础打分 → AI 细致筛查 → 生成对应简历(PDF) → 面试准备**，删除无关功能，修复关键缺陷，提升核心链路的可用性。

## 一、删除命令及关联代码

删除以下 7 个命令，以及它们在 CLI 注册、Pipeline 阶段、CLAUDE.md 文档中的所有引用：

| 命令 | 文件 | 删除原因 |
|------|------|----------|
| `bco negotiate` | `commands/negotiate.py` | 删除 |
| `bco auto-action` | `commands/auto_action.py` + `pipeline/auto_action.py` | 删除（代码有致命 bug，引用不存在的函数） |
| `bco digest` | `commands/digest.py` | 删除 |
| `bco follow-up` | `commands/follow_up.py` | 删除 |
| `bco shortlist` | `commands/shortlist.py` | 删除 |
| `bco watch` | `commands/watch.py` | 删除，同时删除 `config/settings.py` 中的 `WATCHES_DIR` 常量 |
| `bco exchange` | `commands/exchange.py` | 删除 |

同时清理：
- `cli/main.py` 中这些命令的注册代码
- `schema.py` 中这些命令的 schema 描述
- `pipeline/stages.py` 中如果有过时的阶段引用需清理
- `CLAUDE.md` 中所有涉及这些命令的描述、数据流表格、Pipeline 持久化规则表格中的行
- `pipeline/auto_action.py` 整个文件删除（被 `commands/auto_action.py` 引用，命令删了它也没用了）

## 二、保留但需改进的功能

### 2.1 基础打分 `bco evaluate` — 修复评估精度

**文件**: `evaluator/engine.py`

#### 2.1.1 学历匹配逻辑修复

当前代码（第 84 行）：
```python
if profile.education and profile.education in self._extract_jd_text(job):
    score += 0.5
```

问题：字符串包含检查，`profile.education="硕士"` 无法匹配 JD 中的 `"本科及以上"`。

改为：建立学历等级映射，做等级比较：
```python
EDUCATION_LEVELS = {
    "初中": 1, "中专": 2, "高中": 2, "大专": 3, "专科": 3,
    "本科": 4, "硕士": 5, "博士": 6,
}
```
逻辑：如果用户学历等级 >= JD 要求的学历等级，加分。

#### 2.1.2 Profile 数据为空时的处理

当前行为：`skills` 为空返回 2.5，`expected_salary` 为 0 返回 3.0，`preferred_cities` 为空返回 3.0。

问题：用户不知道自己没填数据，以为所有岗位评分就是 2.5-3.0。

改为：在 `evaluate` 命令执行时，如果 profile 关键字段为空，在输出的 `hints` 中明确提示：
```
"⚠️ profile.skills 为空，匹配度评分不可靠，请运行 bco setup 配置"
"⚠️ expected_salary 未设置，薪资评分默认 3.0"
"⚠️ preferred_cities 未设置，地点评分默认 3.0"
```

#### 2.1.3 搜索结果自动附带基础评分

当前：`bco search` 只返回搜索结果，需要单独运行 `bco evaluate` 才能看到评分。

改为：在 `commands/search.py` 的 `run_search` 函数中，搜索完成后自动对结果调用 `EvaluationEngine.evaluate()`，将评分写入每条结果的 `data` 中。如果搜索结果量大（>50条），仅对前 50 条自动评分，其余提示用户手动评估。Pipeline 的 `batch_add_jobs` 写入时一并写入评分。

### 2.2 AI 细致筛查 — 修复关键缺陷

**文件**: `commands/ai_evaluate.py`, `commands/ai_evaluate_batch.py`, `evaluator/ai_scorer.py`

#### 2.2.1 消除重复代码

`ai_evaluate.py` 和 `ai_evaluate_batch.py` 中各自实现了 `_score_to_grade` 和 `_get_recommendation`，而 `evaluator/scorer.py` 已有完整实现。

改为：删除这两个文件中的重复实现，直接 import `scorer.py` 的 `score_to_grade` 和 `get_recommendation`。

#### 2.2.2 无详情时不硬编码维度分数

当前 `ai_evaluate.py` 行为：无详情时调用 `ai_evaluator.score_job_match()` 返回一个总分，然后其他 4 个维度硬编码 2.5。

改为：无详情时，先调用 `adapter.get_job_detail()` 获取详情，再调用 `ai_evaluator.detailed_evaluate()`。如果获取详情失败，在输出中明确标注"详情获取失败，仅提供匹配度评分"，且其他维度标记为 `null` 而非 2.5，避免总分失真。

#### 2.2.3 批量评估加延迟控制

`ai_evaluate_batch.py` 无延迟控制，批量 AI 调用可能触发限流。

改为：添加 `--delay` 参数（默认 2.0 秒），每次 AI 调用之间 sleep。使用高斯随机延迟（均值=delay，标准差=delay*0.3），与项目中其他批量操作一致。

#### 2.2.4 AI 返回解析加重试

当前 `ai_scorer.py` 的 `_parse_json_response` 解析失败直接返回默认值。

改为：解析失败时重试一次（重新调用 AI，在 user_prompt 末尾追加"请严格返回 JSON 格式"）。两次都失败才回退到规则引擎。

#### 2.2.5 AI 评估 prompt 统一维度

当前 `ai_scorer.py` 的 `score_job_match()` 用的是自定义 4 维度（技能40%+经验20%+薪资20%+发展20%），与项目的 5 维评分体系不一致。

改为：`score_job_match()` 的 prompt 改为要求返回 5 维评分（匹配度/薪资/地点/发展/团队），与 `detailed_evaluate()` 和规则引擎保持一致。

### 2.3 简历生成 `bco resume` — **最大改进项，必须生成可直接使用的 PDF**

**文件**: `resume/generator.py`, `resume/pdf_engine.py`, `resume/keywords.py`, `resume/templates/default.html`

**重要区分**：
- 编码时（你）：可以调用 `resume-cv-builder` skill（路径 `.trae/skills/resume-cv-builder`）获取完整的模板结构、ATS 优化指南、写作规范，用于设计简历模板和 cv.md 模板
- 运行时（`generator.py` 调用的 AI provider）：看不到任何 skill，所以 `_ai_polish` 方法中发送给 AI 的 system_prompt 必须把写作规范完整内嵌

#### 2.3.1 替换手写 MD→HTML 转换为 markdown 库

当前 `pdf_engine.py` 的 `_simple_md_to_html()` 手写转换不支持行内粗体、链接、表格、嵌套列表等。

改为：
1. 添加 `markdown` 依赖（`uv add markdown`）
2. 用 `markdown.markdown(md, extensions=['tables', 'fenced_code'])` 替换手写转换
3. 删除 `_simple_md_to_html()` 方法

#### 2.3.2 重新设计简历模板

当前 `default.html` 模板过于简陋，缺少专业简历的排版。

改为重新设计 `default.html`。请调用 `resume-cv-builder` skill 获取其模板结构和 ATS 优化指南，在此基础上设计。核心要求：

**章节顺序**（标准简历结构）：
1. **页头**：姓名（h1 大字）+ 联系方式一行（城市 | 邮箱 | LinkedIn | GitHub）
2. **Professional Summary**（h2）：2-3 句职业概述
3. **Skills**（h2）：按分类展示（Languages / Frontend / Backend / Cloud & DevOps / Tools），用 `.skill-tag` 样式横向排列
4. **Experience**（h2）：公司名 + 职位 + 时间（右对齐），下方项目符号列表
5. **Education**（h2）：学位 + 专业 + 学校 + 年份
6. **Projects**（h2，可选）：项目名 + 技术栈标签，下方描述

**CSS 要求**：
- A4 页面，边距 top/bottom 20mm, left/right 15mm
- 中文友好字体栈：`"Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif`
- 打印友好：黑白可读，不依赖彩色
- ATS 友好：不用表格/分栏/文本框，标准 HTML 标签（h1/h2/ul/li/strong/p）
- `.skill-tag`：`background: #e8f0fe; color: #1a73e8; padding: 2px 8px; border-radius: 4px; font-size: 10pt;`
- Experience 条目时间右对齐（用 flex 或 float）
- 模板用 `{{CONTENT}}` 占位符，CSS 覆盖 markdown 库输出的所有 HTML 标签

#### 2.3.3 AI 润色 prompt — 运行时 AI 看不到 skill，必须内嵌完整写作规范

当前 AI 润色 prompt（`generator.py` 的 `_ai_polish` 方法）较简单。

改为：将以下写作规范**完整写入** `_ai_polish` 方法的 system_prompt 中（运行时 AI 看不到任何外部 skill，必须自包含）：

```
你是一位资深简历顾问，擅长根据目标岗位的职位描述（JD）优化求职者的简历。

写作规范：
1. 每条工作经历用 CAR 方法：强动作词 + 任务/项目 + 量化结果
   - 强动作词：Led / Architected / Optimized / Reduced / Implemented / Engineered / Automated / Streamlined / Managed / Directed
   - 禁止使用：Responsible for / Worked on / Helped with
   - 量化一切：数字、百分比、金额、用户数、时间节省
   - 示例：❌ "Responsible for managing a team" → ✅ "Led cross-functional team of 8 engineers, delivering 3 major features ahead of schedule"
   - 示例：❌ "Worked on improving performance" → ✅ "Optimized database queries reducing page load time by 65%, improving user retention by 23%"

2. Professional Summary 遵循公式：[Title] with [X years] of experience in [domain]. Proven track record of [key achievement]. Skilled in [top 3 skills].

3. Skills 按分类展示：Languages / Frontend / Backend / Cloud & DevOps / Tools

4. 绝不编造不存在的工作经历或技能

5. 保持原始简历的结构和章节不变

6. ATS 优化：使用标准章节标题（Experience / Education / Skills），包含 JD 关键词，不用创意章节名

7. 输出纯 Markdown 格式，不要添加代码块标记
```

#### 2.3.4 ATS 关键词注入改为可见文本

当前 `keywords.py` 把关键词以 HTML 注释注入，PDF 渲染不可见，ATS 系统也读不到。

改为：在简历 Skills 章节末尾添加"核心技能关键词"区域，以小字号（9pt）灰色文字展示，对人类阅读不突兀，对 ATS 系统可解析：
```html
<div class="ats-keywords" style="font-size: 9pt; color: #888; margin-top: 8px;">
  <strong>核心技能：</strong>Kubernetes, Docker, CI/CD, Microservices...
</div>
```

#### 2.3.5 AI 润色结果校验改进

当前仅检查长度 > 原文的 30%。

改为：校验 AI 返回的简历必须包含必要的章节结构（通过检查 Markdown 标题），如原始简历有"Experience"/"工作经历"或"Skills"/"技能"章节，AI 返回也必须有。校验失败则回退到规则逻辑，并在 hints 中提示"AI 润色结果结构不完整，已回退到规则逻辑"。

#### 2.3.6 cv.md 不存在时的处理

当前：生成空壳简历（工作经历/联系方式全空）。

改为：输出错误提示 `"简历文件 ~/.bco/cv.md 不存在，请先创建。可运行 bco setup 初始化模板"`，不生成文件。

#### 2.3.7 cv.md 模板重写

`bco setup` 生成的 `cv.md` 模板应替换为以下标准结构（请调用 `resume-cv-builder` skill 获取其模板示例，在此基础上适配中文场景）：

```markdown
# 张三
北京 | zhangsan@email.com | linkedin.com/in/zhangsan | github.com/zhangsan

## Professional Summary
[职位] with [X] years of experience in [领域]. Proven track of [关键成就]. Skilled in [前3项技能].

## Skills
**Languages:** Python, Go, TypeScript
**Backend:** FastAPI, Django, PostgreSQL, Redis
**Cloud & DevOps:** AWS, Docker, Kubernetes, CI/CD
**Tools:** Git, Linux, Nginx

## Experience

**高级后端工程师** | XX科技 | 2022.01 – Present
- Led team of 5 engineers building microservices platform serving 2M+ daily requests
- Optimized API response time by 60% through database query tuning and caching strategy
- Implemented CI/CD pipeline reducing deployment time from 2 weeks to 2 days

**后端工程师** | YY公司 | 2019.06 – 2021.12
- Developed real-time notification system handling 500K+ concurrent connections
- Reduced infrastructure cost by 35% through auto-scaling optimization
- Mentored 3 junior developers through structured onboarding program

## Education
**本科 计算机科学** | XX大学 | 2019

## Projects
**开源项目** | github.com/project
- Contributed authentication module to popular framework (500+ GitHub stars)
```

### 2.4 面试准备 `bco interview` — 改进 AI prompt 和规则回退

**文件**: `commands/interview.py`

#### 2.4.1 AI prompt 加入用户简历内容

当前 prompt 只发了 `settings.profile.skills`，没发工作经历。

改为：在 user_prompt 中加入 `settings.cv_content`（截取前 2000 字），让 AI 能基于简历内容生成"可能被问到的简历相关问题"。

#### 2.4.2 规则回退改为报错提示

当前规则回退的技术问题库仅 10 个技术栈各 2 个问题，覆盖面太窄。

改为：AI 不可用时，不再回退到规则库，而是输出错误：
```json
{
  "ok": false,
  "error": "AI 服务不可用，面试准备功能需要 AI 支持。请运行 bco ai-config 配置",
  "code": "AI_NOT_AVAILABLE"
}
```

#### 2.4.3 输出增加"简历相关问题"字段

AI prompt 中要求额外返回 `resume_questions` 字段（3-5 个基于简历内容可能被问到的问题），输出中包含此字段。

## 三、代码清理

| 清理项 | 说明 |
|--------|------|
| `commands/ai_evaluate.py` 中 `update_score` 用 `security_id` 而非 `job_id` | 统一改为用 `job_id`，与 PipelineManager 的主键一致 |
| `commands/ai_evaluate_batch.py` 同上 | 同上 |
| `commands/evaluate.py` 中循环内重复打开 PipelineManager | 改为循环外打开一次 |
| `commands/ai_evaluate_batch.py` 同上 | 同上 |
| `config/settings.py` 中的 `WATCHES_DIR` | 随 `bco watch` 一起删除 |

## 四、CLAUDE.md 同步更新

所有改动完成后，必须同步更新 `CLAUDE.md`：
1. 项目结构中删除已移除的命令文件
2. 删除 Pipeline 持久化规则表格中已移除命令的行
3. 删除数据流图中已移除模块的引用
4. 更新搜索命令的描述（自动附带评分）
5. 更新简历生成的描述（PDF 可直接使用）
6. 更新面试准备的描述（AI 必须，无规则回退）
7. 登录系统描述从"4 级降级链"修正为"3 级降级链（Bridge Cookie → CDP → patchright）"，删除已不存在的 QR httpx 登录级别

## 五、测试要求

每个改动必须编写最小测试用例并通过 `uv run pytest`：
1. 学历等级映射和匹配逻辑测试
2. Profile 为空时的 hints 提示测试
3. AI 评估重复代码删除后的 import 正确性测试
4. PDF 生成使用 markdown 库后的输出测试
5. ATS 关键词可见文本注入测试
6. cv.md 不存在时的错误提示测试
7. 面试准备 AI 不可用时的错误输出测试

## 六、不改动的部分

- Chrome 扩展（`extension/` 目录）保留不动
- Browser Bridge（`bridge/` 目录）保留不动
- 登录系统（3 级降级链：Bridge Cookie → CDP → patchright）保留不动
- BossClient HTTP 客户端保留不动
- TokenStore 安全机制保留不动
- CacheStore 保留不动
- Dashboard TUI 保留不动
- `bco mark` 保留不动
- `bco recommend` 保留不动
- `bco chat` / `bco chatmsg` 保留不动
- `bco greet` / `bco apply` 保留不动
- `bco login` / `bco doctor` / `bco setup` / `bco status` / `bco export` / `bco pipeline` / `bco ai-config` 保留不动
