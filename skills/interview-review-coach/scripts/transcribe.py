#!/usr/bin/env python3
"""
Audio transcription script — Apple Silicon native (MLX)
Usage:
  python3 transcribe.py <audio_file>                          # Default: SenseVoice (Chinese best)
  python3 transcribe.py <audio_file> --engine whisper         # Whisper engine (multilingual)
  python3 transcribe.py <audio_file> --model whisper-medium    # Specify Whisper model
"""

import argparse
import json
import os
import time


def transcribe_sensevoice(audio_path: str):
    """Transcribe using SenseVoiceSmall (Alibaba Tongyi Lab, MLX native)."""
    from mlx_audio.stt.generate import generate_transcription

    model_name = "mlx-community/SenseVoiceSmall"
    print(f"Engine: SenseVoice (MLX)")
    print(f"Model: {model_name}")
    print(f"Audio: {audio_path}")

    start = time.time()
    result = generate_transcription(model=model_name, audio=audio_path)
    elapsed = time.time() - start

    # Convert to standard format
    segments = []
    if hasattr(result, "segments") and result.segments:
        for seg in result.segments:
            segments.append({
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "text": seg.get("text", ""),
                "language": seg.get("language", "zh"),
                "emotion": seg.get("emotion", ""),
                "event": seg.get("event", ""),
            })

    text = ""
    if hasattr(result, "text") and result.text:
        text = result.text
    elif segments:
        text = " ".join(s["text"] for s in segments if s["text"])

    # SenseVoice returns single segment without timestamps
    if not segments and text:
        segments = [{"start": 0, "end": 0, "text": text, "language": "zh"}]

    return {"text": text, "segments": segments}, elapsed


def transcribe_whisper(audio_path: str, model: str = "medium", language: str = "zh"):
    """Transcribe using mlx-whisper (multilingual)."""
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
    """Save transcription results as JSON and readable text."""
    text = result.get("text", "")
    segments = result.get("segments", [])

    print(f"Completed in {elapsed:.1f}s")
    print(f"Segments: {len(segments)}")
    print(f"Text length: {len(text)} chars")

    output_dir = os.path.dirname(os.path.abspath(audio_path))

    # Save full JSON
    json_path = os.path.join(output_dir, "transcript_full.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Save timestamped text
    txt_path = os.path.join(output_dir, "transcript_timestamped.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for seg in segments:
            start_t = seg.get("start", 0)
            seg_text = seg.get("text", "").strip()
            if seg_text:
                if start_t > 0:
                    mins = int(start_t) // 60
                    secs = int(start_t) % 60
                    f.write(f"[{mins:02d}:{secs:02d}] {seg_text}\n")
                else:
                    f.write(f"{seg_text}\n")

    print(f"Saved: {json_path}")
    print(f"Saved: {txt_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio transcription (Apple Silicon)")
    parser.add_argument("audio_file", help="Path to audio file")
    parser.add_argument(
        "--engine",
        default="sensevoice",
        choices=["sensevoice", "whisper"],
        help="STT engine: sensevoice (default, best for Chinese) or whisper (multilingual)",
    )
    parser.add_argument("--model", default=None, help="Model name (whisper: medium/large-v3-turbo)")
    parser.add_argument("--language", default="zh", help="Language code (whisper only)")
    args = parser.parse_args()

    if args.engine == "sensevoice":
        result, elapsed = transcribe_sensevoice(args.audio_file)
    else:
        model = args.model or "medium"
        result, elapsed = transcribe_whisper(args.audio_file, model, args.language)

    save_results(result, elapsed, args.audio_file)
