# Vanceling Skills

> 自建 Claude Code Skills —— AI 产品经理的效率工具箱。

## Skills

### interview-review-coach

> AI Agent PM 面试复盘教练

从面试录音/笔记/JD 出发，生成结构化复盘文档并写入飞书 Wiki，提供逐题更优解指导。

- 三阶段流程：信息采集 → 音频转写（mlx-whisper）与逐题分析 → 文档生成
- 支持 JD 图片提取、面试音频转写、逐题改进建议
- 最终输出：复盘文档 + (N+1) 面备战 Checklist

### ai-paper-reading

> AI 论文精读方法论 —— 30 分钟/篇

四阶段精读法：(0) 选文筛选 → (1) AI 辅助预读 → (2) 8 问结构化拆解 → (3) 费曼输出 → (4) 边界检测。适合面试准备和快速跟进新领域。

## 安装

```bash
# 安装单个 skill
cp -r skills/interview-review-coach ~/.claude/skills/

# 或安装全部
cp -r skills/* ~/.claude/skills/
```

安装后在 Claude Code 中输入 `/<skill-name>` 即可调用。

## 协议

MIT License
