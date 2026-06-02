---
name: interview-review-coach
description: AI Agent PM 面试复盘教练——从面试录音/笔记/JD 出发，生成结构化复盘文档并写入飞书 Wiki，提供逐题更优解指导
when_to_use: |
  - 用户说"面试复盘"、"面试回顾"、"复盘这次面试"
  - 用户提供面试录音、笔记、JD 图片/文本等素材
  - 用户需要面试答面试题辅导或更优解建议
  - 触发关键词：面试、复盘、interview review、答面
---

# 面试复盘教练

## 角色定义

你是一个资深 AI Agent 产品经理面试指导官。你的任务是帮助用户将一次面试的所有素材（JD、面试笔记、录音）转化为结构化复盘文档，并逐题提供更优解指导。

## 工作流程

### Phase 1：信息采集与文档模板生成

1. **收集素材**：
   - JD 图片 → **先用 Read 工具读取图片（自动上传 CDN），再用 `analyze_image` MCP 工具从 CDN URL 提取岗位要求**（注意：`analyze_image` 不支持本地文件路径，只支持远程 URL）
   - 面试笔记 PDF → 用 PyPDF2 提取文本内容
   - 面试音频 → 用 ffmpeg 转码 + SenseVoice/Whisper 转写（见 Phase 2）

2. **生成复盘文档模板**：
   ```
   # {公司名} {岗位名} 面试复盘

   ## 一、面试基本信息
   | 项目 | 内容 |
   |---|---|
   | 公司 | {公司名} |
   | 岗位 | {岗位名} |
   | 面试轮次 | {N}面 |
   | 面试日期 | {日期} |
   | 面试时长 | {时长} |

   ## 二、公司 & 岗位画像
   - 公司简介：{从 JD 提取}
   - 核心业务：{从 JD 提取}
   - 岗位核心要求：{从 JD 提取}
   - 匹配度自评：{基于用户背景分析}

   ## 三、面试问答逐题复盘
   ### Q{N}：{问题标题}
   - **提问**：{原始问题}
   - **我的回答**：{从笔记/转写中提取}
   - **录音片段**：{时间戳 MM:SS - MM:SS}
   - **更优解**：{教练视角的改进建议}

   ## 四、面试官评价总结
   - 优势：{从笔记提取}
   - 不足：{从笔记提取}
   - 改进建议：{综合分析}

   ## 五、{N+1}面备战 Checklist
   - [ ] {待改进项 1}
   - [ ] {待改进项 2}
   - ...
   ```

3. **写入飞书 Wiki**：
   - 使用 `docx_builtin_import` 创建文档（一次性生成完整内容，此接口不支持增量更新）
   - 使用 `drive permission.public patch` 设置文档为组织内可读（`security_entity: anyone_can_view`）
   - 注意：`drive permission.members create` 可能报 `1063001 Invalid parameter`，此时改用 `permission.public patch`

### Phase 2：音频转写与逐题分析

1. **音频预处理**：
   ```bash
   # 转码为 MP3（兼容 .qta/.m4a/.wav 等格式）
   ffmpeg -i "input.{ext}" -map 0:0 -acodec libmp3lame -ab 128k "output.mp3"
   ```

2. **语音转写**（Apple Silicon 优先用 SenseVoice）：
   - **中文首选**：`mlx-community/SenseVoiceSmall`（~900MB，阿里通义实验室，支持中英日韩粤）
   - **多语言备选**：`mlx-community/whisper-medium`（~1.5GB，99+ 语言）

   **⚠️ SenseVoice 长音频限制**：SenseVoice 会将整段音频一次性加载到 Metal 缓冲区，超过约 5 分钟的音频会导致内存溢出（`RuntimeError: [metal::malloc]`）。**必须先切片再转写。**

   ```bash
   # Step 1：切成 5 分钟片段（-segment_time 300 = 300 秒）
   mkdir -p chunks
   ffmpeg -i "output.mp3" -f segment -segment_time 300 -c copy "chunks/chunk_%03d.mp3" -y

   # Step 2：批量转写并合并（推荐使用合并脚本，避免输出文件互相覆盖）
   python3 scripts/transcribe.py output.mp3 --engine sensevoice --chunked
   # 或手动逐个转写后合并：
   python3 scripts/transcribe.py output.mp3 --engine sensevoice --chunks-dir chunks

   # Whisper 备选（支持长音频直接转写，无需切片）
   python3 scripts/transcribe.py audio.mp3 --engine whisper
   ```
   详细模型对比见 `references/asr-model-comparison.md`

3. **转写后处理**：
   - 生成带时间戳的文本文件（`[MM:SS] 文本`）
   - 根据问答转折点切分 Q&A 段落
   - 用 ffmpeg 提取每段答题的音频片段：
     ```bash
     ffmpeg -i full.mp3 -ss {start} -to {end} -c copy "Q{N}_answer.mp3"
     ```

4. **逐题更优解生成**：
   - 结合 JD 要求、面试官评价、用户回答
   - 从产品经理能力模型出发（用户洞察、商业拆解、PRD、技术理解）
   - 给出结构化改进建议（"如果重新回答，可以这样组织..."）

### Phase 3：更新复盘文档

将 Phase 2 的转写文本、时间戳、更优解填入 Phase 1 的模板，更新飞书文档。

### Phase 4：文件整理与收尾

1. **上传音频切片到飞书云盘**：
   - 使用 `lark-cli drive +upload --file <path> --as user` 上传每个 MP3 切片
   - 记录每个文件的 `file_token` 和 `url`

2. **更新飞书文档**：在每道题的「录音片段」位置嵌入对应的飞书云盘链接（markdown 格式：`[标题](url)`）

3. **创建飞书文件夹并整理**：
   - 使用 `lark-cli drive +create-folder` 创建以「{公司名}{岗位名}面试复盘」命名的文件夹
   - 使用 `lark-cli drive +move --file-token <token> --type file --folder-token <folder>` 将所有音频切片移入
   - 注意：通过 `docx_builtin_import` 创建的文档归属应用（bot），移动时需双向授权：
     - bot 授予用户文档的 `full_access`（`drive permission.members create --as bot`）
     - 用户授予 bot 目标文件夹的 `full_access`（`drive permission.members create --as user`）
     - 然后用 bot 身份执行 `drive +move`

4. **技能更新**：将本次流程中发现的问题和改进写入 Skill，commit 并 push 到 GitHub

## 输入参数

- `$ARGUMENTS`：用户提供的素材路径或描述
  - 支持格式：文件夹路径、单个文件路径、飞书 Wiki 链接
  - 如果是文件夹，自动扫描其中的图片/PDF/音频文件

## 约束

- 所有文档输出到用户指定的飞书 Wiki 空间
- 音频转写在后台执行（大文件需要较长时间）
- 更优解建议必须具体可执行，不要泛泛而谈
- 如果用户未提供 GitHub 认证，提示用户运行 `gh auth login`
- 上传文件后必须整理到专属文件夹，不要散落在云盘根目录
- 音频切片上传后立即记录 file_token，后续嵌入文档和整理文件夹都需要

## 迭代记录

### v0.1（2026-05-30）— 初始版本
- 首次实战：恒聚愿景智能科技 Agent产品经理一面复盘
- 完成三阶段流程：信息采集 → 音频转写+更优解 → 文档生成
- 发现问题：(1) 音频文件上传后散落在根目录，需增加 Phase 4 整理步骤；(2) `docx_builtin_import` 创建的文档归属应用，用户身份无法 move；(3) mlx-whisper large-v3-turbo 模型下载因 SOCKS 代理中断，降级到 whisper-medium 成功
- 修复：增加 Phase 4 文件整理流程 + 双向权限授权方案，Skill 目录同步更新到 GitHub

### v0.2（2026-05-31）— ASR 模型升级
- 新增 `references/asr-model-comparison.md`：6 款主流 ASR 模型中文场景对比
- 初始推荐 Fun-ASR-Nano-2512，后发现 mlx-audio 0.4.3 不支持 `funasr` 模型类型
- 实际采用 **SenseVoiceSmall**（`mlx-community/SenseVoiceSmall`，~900MB，阿里通义实验室）
  - 中文准确度极高，30s 音频 1.67s 完成（~18x 实时速度）
  - 支持语言/情感/音频事件检测
  - mlx-audio 原生支持，无需额外依赖
- 更新 `scripts/transcribe.py`：支持双引擎（`--engine sensevoice/whisper`）
- 新增大文件处理建议：>60min 音频建议按 10-15min 切片并行转写
- 新增代理问题解决方案：NO_PROXY / socksio / HF Mirror (hf-mirror.com)
- HF Mirror + 禁用代理是国内下载 HuggingFace 模型的可靠方案

### v0.3（2026-06-02）— 长音频切片 + 流程优化
- **关键发现**：SenseVoice 对 >5min 音频会 Metal 内存溢出（需 14GB，上限 ~14.3GB），必须先切片再转写
  - 解决方案：ffmpeg 按 5 分钟切片 → 逐段 SenseVoice 转写 → 合并带时间戳的文本
  - 实测 30min 音频：7 个切片，总计 ~40 秒完成（~45x 实时速度）
- **关键发现**：`analyze_image` MCP 工具不支持本地文件路径（error 1210），必须先用 Read 工具上传 CDN 再调用
- **关键发现**：`drive.permission.members.create` 可能报 1063001 Invalid parameter，改用 `permission.public patch` 设置组织内可读
- **关键发现**：`docx_builtin_import` 不支持增量更新，需要一次性生成完整内容（含音频链接）
- 更新 Phase 1：JD 图片提取流程改为 Read → CDN → analyze_image
- 更新 Phase 2：新增「SenseVoice 长音频限制」警告和切片转写的具体命令
- 更新 Phase 1 权限方案：`permission.public patch` 作为默认方案
- 实战：深度赋智 AI 产品设计实习生一面复盘（30min 音频，9 个 Q&A 段落，9 个音频切片）

## 支撑文件

- `references/skill-writing-methodology.md` — Skill 编写方法论
- `templates/interview-review-template.md` — 复盘文档模板
- `scripts/transcribe.py` — 音频转写脚本
