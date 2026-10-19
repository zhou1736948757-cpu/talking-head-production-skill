#!/usr/bin/env python3
"""Generate 40s non-private fixture with authored tone timing, NOT speech/ASR."""
import argparse
import math
from pathlib import Path
import struct
import wave
from production import run, write, import_transcript, make_edit, roughcut, export_hypit, fingerprint


def demo(root, font, render_rough=True):
    root = Path(root).resolve(); root.mkdir(parents=True, exist_ok=True)
    phrases = ["先把观点说清楚。", "保留自然的呼吸。", "再让画面跟着意思走。", "最后检查字幕和声音。"]
    tokens = []
    for j, phrase in enumerate(phrases):
        for i, char in enumerate(phrase):
            if char in "。！？":
                tokens[-1]["text"] += char
                continue
            a = j * 10 + 1 + i * 0.55
            tokens.append({"id": f"p{j}-{i}", "type": "word", "text": char, "start": a, "end": a + 0.4})
    audio = root / "authored-tones.wav"
    with wave.open(str(audio), "wb") as w:
        w.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        for second in range(40):
            samples = []
            for n in range(48000):
                t = second + n / 48000
                active = next((i for i, tok in enumerate(tokens) if tok["start"] <= t < tok["end"]), None)
                # Audible low noise in an uncut gap represents a breath-like test cue.
                value = .12 * math.sin(2*math.pi*(330 + (active % 4)*110)*t) if active is not None else (.015*math.sin(2*math.pi*170*t) if 7 <= t < 7.4 else 0)
                samples.append(int(value * 32767))
            w.writeframes(struct.pack("<"+"h"*len(samples), *samples))
    source = root / "source.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=30:duration=40", "-i", audio,
         "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", "40", source])
    payload = {"provider": "synthetic-fixture", "timing_basis": "authored-tone-windows-not-speech-not-ASR", "words": tokens}
    write(root / "source-words.json", payload)
    transcript = import_transcript(payload, source)
    write(root / "transcript.json", transcript)
    request = {"mode": "produce", "pace": "测试夹具明确策略：保持原速，仅删除两段已知数字静音", "pause_policy": "保留 7–7.4 秒的低声呼吸模拟信号及全部词间停顿", "must_keep": ["p0-0"],
               "protected_ranges": [{"start": 7, "end": 7.4}],
               "cuts": [{"start": 8, "end": 10, "action": "delete", "approved": True, "reason": "夹具作者确认：数字静音"},
                        {"start": 18, "end": 20, "action": "delete", "approved": True, "reason": "夹具作者确认：数字静音"}]}
    write(root / "request.json", request)
    edit = make_edit(source, transcript, request)
    write(root / "edit.json", edit)
    scenes = [{"id": "meaning", "first": "p2-0", "last": "p2-8", "label": "画面跟着意思走"},
              {"id": "review", "first": "p3-0", "last": "p3-8", "label": "检查字幕与声音"}]
    write(root / "scenes.json", scenes)
    if render_rough:
        rough = roughcut(edit, root / "roughcut.mp4")
        export_hypit(edit, rough, root / "hypit-project", font, scenes)
    write(root / "fixture-facts.json", {"source_seconds": 40, "output_seconds": 36,
          "source_sha256": fingerprint(source), "asr_executed": False,
          "audio": "authored tones and breath-like sine cue; no real speaker", "private_media": False})


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path); p.add_argument("--font", required=True)
    a = p.parse_args(); demo(a.output, a.font)
