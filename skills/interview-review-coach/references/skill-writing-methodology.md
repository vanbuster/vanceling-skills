# Claude Code Skill 编写方法论

> 基于 Anthropic 官方文档整理，适用于个人 Skill 开发。

## 1. Skill 是什么

Skill 是 Claude Code 的可复用指令包。用户输入 `/<skill-name>` 即可调用，相当于给 Claude Code 添加一个"专业技能"。

## 2. 文件结构

```
~/.claude/skills/<skill-name>/
├── SKILL.md              ← 主文件（必须）
├── references/           ← 参考资料（可选）
├── templates/            ← 模板文件（可选）
├── scripts/              ← 脚本文件（可选）
└── assets/               ← 其他资源（可选）
```

## 3. SKILL.md 格式

### 3.1 YAML Frontmatter（必填）

```yaml
---
name: skill-name                    # 小写 + 连字符
description: 一句话描述这个 skill 做什么    # 用于自动匹配
when_to_use: |                      # 触发条件描述
  - 用户说 "xxx" 时
  - 用户需要 xxx 时
---
```

### 3.2 Markdown Body（必填）

自由格式的指令文本。Claude 会把它当作当前任务的上下文来阅读。

**推荐结构**：

```markdown
# Skill 标题

## 角色定义
你是做什么的专家。

## 工作流程
### Step 1：xxx
具体操作步骤...

### Step 2：xxx
...

## 输入参数
- `$ARGUMENTS`：用户传入的参数

## 输出格式
期望的输出是什么。

## 约束
- 不要做什么
- 必须做什么
```

## 4. 动态上下文注入

用反引号 + 感叹号语法在运行时注入命令输出：

```
当前项目结构：
!`find . -type f -name "*.py" | head -20`
```

这在需要实时信息（如项目文件列表、git 状态）时很有用。

## 5. 子 Agent 执行

在 frontmatter 中设置：

```yaml
context: fork
```

Claude 会在子 Agent 中执行此 Skill，保护主会话的上下文窗口。

## 6. 编写最佳实践

### DO
- **具体化**：步骤要具体到"用什么工具、什么参数"
- **提供模板**：把输出格式写成模板，Claude 直接填充
- **约束边界**：明确"不要做什么"，避免 Skill 越界
- **单一职责**：一个 Skill 做一件事，不要堆叠多个功能
- **用 `$ARGUMENTS`**：让用户能传入参数

### DON'T
- 不要写冗长的背景介绍——Claude 已经知道很多
- 不要试图覆盖所有 edge case——写核心流程即可
- 不要硬编码路径——用变量或 `$ARGUMENTS`
- 不要重复 Claude Code 已有的能力

## 7. 质量自检清单

- [ ] `name` 是否小写 + 连字符？
- [ ] `description` 是否一句话能说清？
- [ ] `when_to_use` 是否覆盖了主要触发场景？
- [ ] 工作流程是否从 Step 1 到最终输出完整闭环？
- [ ] 是否有约束边界（不要做什么）？
- [ ] 是否有模板或示例输出？
- [ ] scripts/ 中的脚本是否可直接运行？

## 8. 来源

- Anthropic Help Center: "Creating custom skills for Claude Code"
- Claude Code Docs: "Extending Claude Code with custom skills"
- 实践经验：面试复盘教练 Skill 开发过程（2026-05-30）
