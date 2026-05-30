#!/usr/bin/env python3
"""
音频转写脚本 —— Apple Silicon 原生
用法：
  python3 transcribe.py <audio_file>                          # 默认 Fun-ASR（中文首选）
  python3 transcribe.py <audio_file> --engine whisper          # Whisper 引擎
  python3 transcribe.py <audio_file> --model whisper-medium     # 指定 Whisper 模型
"""

import argparse
import json
import os
import time


def transcribe_fun_asr(audio_path: str):
    """使用 Fun-ASR-Nano-2512 转写（中文首选，MLX 原生）。"""
    from mlx_audio.stt import transcribe

    model = "mlx-community/Fun-ASR-Nano-2512-fp16"
    print(f"Engine: Fun-ASR (MLX)")
    print(f"Model: {model}")
    print(f"Audio: {audio_path}")

    start = time.time()
    result = transcribe(audio_path, model=model)
    elapsed = time.time() - start

    return result, elapsed


def transcribe_whisper(audio_path: str, model: str = "medium", language: str = "zh"):
    """使用 mlx-whisper 转写（多语言通用）。"""
    import mlx_whisper

    hf_repo = f"mlx-community/whisper-{model}"
    print(f"Engine: mlx-whisper")
    print(f"Model: {hf_repo}")
    print(f"Language: {language}")

    start = time.time()
    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=hf_repo,
        language=language,
        word_timestamps=True,
        verbose=False,
    )
    elapsed = time.time() - start

    return result, elapsed


def save_results(result, elapsed: float, audio_path: str):
    """保存转写结果为 JSON 和可读文本。"""
    # 统一输出格式
    text = result.get("text", "")
    segments = result.get("segments", [])

    print(f"Completed in {elapsed:.1f}s")
    print(f"Segments: {len(segments)}")
    print(f"Text length: {len(text)} chars")

    output_dir = os.path.dirname(os.path.abspath(audio_path))

    # 保存完整 JSON
    json_path = os.path.join(output_dir, "transcript_full.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 保存可读文本
    txt_path = os.path.join(output_dir, "transcript_timestamped.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for seg in segments:
            start_t = seg.get("start", 0)
            seg_text = seg.get("text", "").strip()
            if seg_text:
                mins = int(start_t) // 60
                secs = int(start_t) % 60
                f.write(f"[{mins:02d}:{secs:02d}] {seg_text}\n")

    print(f"Saved: {json_path}")
    print(f"Saved: {txt_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio transcription (Apple Silicon)")
    parser.add_argument("audio_file", help="Path to audio file")
    parser.add_argument(
        "--engine",
        default="funasr",
        choices=["funasr", "whisper"],
        help="STT engine: funasr (default, best for Chinese) or whisper (multilingual)",
    )
    parser.add_argument("--model", default=None, help="Model name (whisper: medium/large-v3-turbo)")
    parser.add_argument("--language", default="zh", help="Language code (whisper only)")
    args = parser.parse_args()

    if args.engine == "funasr":
        result, elapsed = transcribe_fun_asr(args.audio_file)
    else:
        model = args.model or "medium"
        result, elapsed = transcribe_whisper(args.audio_file, model, args.language)

    save_results(result, elapsed, args.audio_file)
