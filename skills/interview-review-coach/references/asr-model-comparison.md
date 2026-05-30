# ASR（语音转文字）模型选型指南

> 适用于：macOS Apple Silicon 本地推理，中文场景优先
> 更新日期：2026-05-31

## 1. 当前使用方案

| 项目 | 值 |
|---|---|
| 模型 | `mlx-community/whisper-medium` |
| 框架 | mlx-whisper |
| 大小 | ~1.5GB |
| 中文效果 | 中等（口语转写有较多错字，如「PRD」→「pid」） |
| 38min 音频耗时 | 约 2-3 分钟（含下载） |

**已知问题**：
- 口语化对话中专业术语识别差（「PRD」「Agent」「Hook」等中英混合场景）
- 标点符号不准确
- 说话人区分不支持
- large-v3-turbo 下载在 SOCKS 代理环境下容易中断

## 2. 模型对比

| 模型 | 中文准确度 | 方言 | 说话人分离 | Apple Silicon | 大小 | 速度 | 推荐场景 |
|---|---|---|---|---|---|---|---|
| **Fun-ASR-Nano-2512 (MLX)** | ⭐⭐⭐⭐⭐ | 7种方言 | ❌ | ✅ MLX 原生 | ~400MB | 极快 | **中文首选** |
| SenseVoice | ⭐⭐⭐⭐⭐ | 粤语 | ❌ | ⚠️ 需 onnxruntime | ~900MB | 52x realtime | 高精度中文 |
| Voxtral Transcribe 2 | ⭐⭐⭐⭐⭐ | 多语言 | ❌ | ❌ 需 GPU/CPU | 较大 | 实时流式 | 多语言通用 |
| Whisper Large-v3 (MLX) | ⭐⭐⭐⭐ | ❌ | ❌ | ✅ MLX 原生 | ~3GB | 快 | 多语言通用 |
| Whisper Medium (MLX) | ⭐⭐⭐ | ❌ | ❌ | ✅ MLX 原生 | ~1.5GB | 快 | 轻量备选 |
| WhisperX | ⭐⭐⭐⭐ | ❌ | ❌ | ⚠️ 需 faster-whisper | ~1.5GB | 较快 | 需词级时间戳 |
| FunASR Paraformer | ⭐⭐⭐⭐⭐ | 多种 | ✅ | ⚠️ 需 PyTorch | ~1GB | 170x realtime | 工业级中文 |

## 3. 推荐方案

### 🏆 首选：SenseVoiceSmall（MLX 版）

- **HuggingFace**: `mlx-community/SenseVoiceSmall`
- **来源**: 阿里巴巴通义实验室（同 Fun-ASR 系列）
- **优势**:
  - mlx-audio 原生支持，无需额外依赖
  - 中文准确度极高（30s 音频实测，口语识别远超 whisper-medium）
  - 支持语言检测（zh/en/ja/ko/yue）、情感识别、音频事件检测
  - Apple Silicon 原生推理，30s 音频 1.67s 完成（~18x 实时速度）
  - 模型 ~900MB
- **安装**:
  ```bash
  pip install mlx-audio
  ```
- **使用**:
  ```python
  from mlx_audio.stt.generate import generate_transcription
  result = generate_transcription(model="mlx-community/SenseVoiceSmall", audio="audio.mp3")
  ```

> **注意**：Fun-ASR-Nano-2512（`mlx-community/Fun-ASR-Nano-2512-fp16`）虽然在 HF 上有 MLX 版，
> 但其 `model_type: funasr` 截至 mlx-audio 0.4.3 尚未被支持，加载时会报 `ValueError: Model type funasr not supported`。
> 同属通义实验室的 SenseVoice 是当前 mlx-audio 中中文场景的最佳选择。

### 🥈 备选：whisper-large-v3-turbo（MLX 版）

- **HuggingFace**: `mlx-community/whisper-large-v3-turbo`
- **优势**: 多语言通用，99+ 语言支持
- **劣势**: 中文不如 Fun-ASR，模型 ~800MB
- **适用**: 英文为主或中英混合的通用场景

### 🥉 重度场景：FunASR Paraformer（完整版）

- **GitHub**: `modelscope/FunASR`
- **优势**: 工业级精度，支持说话人分离、情感检测、流式识别
- **劣势**: 需要 PyTorch + ModelScope，环境较重
- **适用**: 需要说话人分离的会议记录、多人对话场景

## 4. 优化后的工作流

### 4.1 标准转写流程

```bash
# Step 1: 转码（如果需要）
ffmpeg -i "input.qta" -map 0:0 -acodec libmp3lame -ab 128k "output.mp3"

# Step 2: 转写（首选 SenseVoice）
python3 -c "
from mlx_audio.stt.generate import generate_transcription
result = generate_transcription(model='mlx-community/SenseVoiceSmall', audio='output.mp3')
print(result.text)
"

# Step 3: 切段（按时间戳）
ffmpeg -i output.mp3 -ss START -to END -c copy clip.mp3
```

### 4.2 大文件处理建议

对于 >60 分钟的音频：
1. **预处理切片**: 先用 ffmpeg 按 10-15 分钟切段，并行转写
2. **结果合并**: 转写后按时间戳拼接
3. **上下文保留**: 保存完整转写 JSON（含时间戳），摘要只用于显示

### 4.3 避免 Context 压缩丢失

- 完整转写文本保存为本地文件（`transcript_full.json`）
- Agent 只读取当前需要的段落，不一次性加载全文
- 关键信息（问答边界、时间戳）用结构化格式存储

## 5. 模型缓存位置

| 框架 | 缓存路径 |
|---|---|
| mlx-whisper / mlx-audio | `~/.cache/huggingface/hub/` |
| FunASR (ModelScope) | `~/.cache/modelscope/hub/` |

## 6. 代理问题解决方案

下载模型时如果 SOCKS 代理卡住：

```bash
# 方案 A: 临时禁用代理
NO_PROXY="huggingface.co" http_proxy="" https_proxy="" python3 transcribe.py

# 方案 B: 安装 socksio（让 httpx 支持 SOCKS）
pip install "httpx[socks]" socksio

# 方案 C: 提前手动下载
huggingface-cli download mlx-community/Fun-ASR-Nano-2512-fp16
```

## 7. 来源与参考

- [FunASR GitHub](https://github.com/modelscope/FunASR) — 阿里巴巴通义实验室
- [mlx-community/Fun-ASR-Nano-2512-fp16](https://huggingface.co/mlx-community/Fun-ASR-Nano-2512-fp16) — MLX 优化版
- [mlx-audio GitHub](https://github.com/Blaizzy/mlx-audio) — Apple Silicon 音频库
- [SenseVoice 对比](https://whispernotes.app/blog/sensevoice-fastest-cjk-transcription) — 中文 ASR 基准
- [Voxtral vs Whisper 2026](https://weesperneonflow.ai/en/blog/2026-03-31-voxtral-whisper-open-source-speech-models-comparison-2026/) — 2026 年 ASR 对比
- [WhisperX](https://github.com/m-bain/whisperX) — 词级时间戳增强
