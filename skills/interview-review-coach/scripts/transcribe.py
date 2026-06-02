#!/usr/bin/env python3
"""
Audio transcription script — Apple Silicon native (MLX)
Usage:
  python3 transcribe.py <audio_file>                          # Default: SenseVoice (Chinese best)
  python3 transcribe.py <audio_file> --engine whisper         # Whisper engine (multilingual)
  python3 transcribe.py <audio_file> --chunked                # Auto-chunk for long audio (>5min)
  python3 transcribe.py <audio_file> --chunk-size 300         # Custom chunk size in seconds (default: 300)
"""

import argparse
import json
import os
import subprocess
import tempfile
import time


def get_audio_duration(path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def chunk_audio(audio_path: str, chunk_seconds: int = 300) -> list[str]:
    """Split audio into chunks using ffmpeg. Returns list of chunk file paths."""
    chunks_dir = tempfile.mkdtemp(prefix="asr_chunks_")
    output_pattern = os.path.join(chunks_dir, "chunk_%03d.mp3")

    subprocess.run([
        "ffmpeg", "-y", "-i", audio_path,
        "-f", "segment", "-segment_time", str(chunk_seconds),
        "-c", "copy", output_pattern
    ], capture_output=True)

    chunks = sorted(
        os.path.join(chunks_dir, f)
        for f in os.listdir(chunks_dir)
        if f.endswith(".mp3")
    )
    return chunks


def transcribe_sensevoice(audio_path: str):
    """Transcribe using SenseVoiceSmall (Alibaba Tongyi Lab, MLX native)."""
    from mlx_audio.stt.generate import generate_transcription

    model_name = "mlx-community/SenseVoiceSmall"

    start = time.time()
    result = generate_transcription(model=model_name, audio=audio_path)
    elapsed = time.time() - start

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

    if not segments and text:
        segments = [{"start": 0, "end": 0, "text": text, "language": "zh"}]

    return {"text": text, "segments": segments}, elapsed


def transcribe_chunked(audio_path: str, chunk_seconds: int = 300):
    """Chunk long audio and transcribe each chunk with SenseVoice."""
    from mlx_audio.stt.generate import generate_transcription

    model_name = "mlx-community/SenseVoiceSmall"
    duration = get_audio_duration(audio_path)
    print(f"Duration: {duration:.0f}s ({duration/60:.1f}min)")
    print(f"Chunk size: {chunk_seconds}s")

    if duration <= chunk_seconds:
        print("Audio short enough, skipping chunking")
        return transcribe_sensevoice(audio_path)

    chunks = chunk_audio(audio_path, chunk_seconds)
    print(f"Split into {len(chunks)} chunks")

    all_segments = []
    full_text = []
    total_elapsed = 0

    for i, chunk in enumerate(chunks):
        offset = i * chunk_seconds
        offset_min = offset // 60
        offset_sec = offset % 60
        print(f"  [{i+1}/{len(chunks)}] {os.path.basename(chunk)} (offset: {offset_min:02d}:{offset_sec:02d})")

        start = time.time()
        result = generate_transcription(model=model_name, audio=chunk)
        elapsed = time.time() - start
        total_elapsed += elapsed

        text = result.text if hasattr(result, "text") and result.text else ""
        full_text.append(text)
        all_segments.append({
            "chunk": os.path.basename(chunk),
            "offset_seconds": offset,
            "timestamp": f"{offset_min:02d}:{offset_sec:02d}",
            "text": text,
            "chars": len(text),
        })

        # Clean up chunk file
        os.unlink(chunk)

    # Clean up temp dir
    try:
        os.rmdir(os.path.dirname(chunks[0]))
    except OSError:
        pass

    merged = {
        "text": "\n".join(full_text),
        "segments": all_segments,
        "chunked": True,
    }
    return merged, total_elapsed


def transcribe_whisper(audio_path: str, model: str = "medium", language: str = "zh"):
    """Transcribe using mlx-whisper (multilingual)."""
    import mlx_whisper

    hf_repo = f"mlx-community/whisper-{model}"

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
    is_chunked = result.get("chunked", False)
    text = result.get("text", "")
    segments = result.get("segments", [])

    print(f"Completed in {elapsed:.1f}s")
    if is_chunked:
        print(f"Chunks: {len(segments)}")
    else:
        print(f"Segments: {len(segments)}")
    print(f"Text length: {len(text)} chars")

    output_dir = os.path.dirname(os.path.abspath(audio_path))

    json_path = os.path.join(output_dir, "transcript_full.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    txt_path = os.path.join(output_dir, "transcript_timestamped.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        if is_chunked:
            for seg in segments:
                f.write(f"[{seg['timestamp']}] {seg['text']}\n\n")
        else:
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
    parser.add_argument(
        "--chunked",
        action="store_true",
        help="Auto-chunk long audio for SenseVoice (>5min causes Metal OOM)",
    )
    parser.add_argument("--chunk-size", type=int, default=300, help="Chunk size in seconds (default: 300)")
    args = parser.parse_args()

    print(f"Engine: {args.engine}")
    print(f"Audio: {args.audio_file}")

    if args.engine == "sensevoice" and args.chunked:
        result, elapsed = transcribe_chunked(args.audio_file, args.chunk_size)
    elif args.engine == "sensevoice":
        result, elapsed = transcribe_sensevoice(args.audio_file)
    else:
        model = args.model or "medium"
        result, elapsed = transcribe_whisper(args.audio_file, model, args.language)

    save_results(result, elapsed, args.audio_file)
