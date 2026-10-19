#!/usr/bin/env python3
"""Offline, reversible talking-head preparation; no credentials or network access."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

VERSION = "koubo-production@1"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def fingerprint(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(argv):
    return subprocess.run([str(x) for x in argv], check=True, capture_output=True, text=True).stdout


def probe(path):
    p = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]))
    v = next((s for s in p["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        raise ValueError("输入必须含视频；音频替换需先提供同画幅视频或扩展后端")
    return {"duration": float(p["format"]["duration"]), "width": v["width"], "height": v["height"],
            "has_audio": any(s["codec_type"] == "audio" for s in p["streams"])}


def normalize(text):
    return "".join(c for c in text.casefold() if c.isalnum())


def script_escape(text):
    return html.escape(re.sub(r"([\\@<|{}])", r"\\\1", text))


def questions(request):
    if request.get("mode") not in ("analysis", "plan", "produce"):
        return ["这次只分析、给剪辑方案，还是制作成片？"]
    if request["mode"] == "analysis":
        return []
    prompts = {"pace": "希望什么节奏？可自由描述，也可选保守、标准、紧凑；没有默认档。",
               "pause_policy": "自然呼吸、气口、情绪停顿想保留到什么程度？",
               "must_keep": "哪些事实、限定、原话或片段必须保留？没有也请明确说明。"}
    return [q for k, q in prompts.items() if k not in request or request[k] is None or request[k] == ""]


def import_transcript(payload, media, track=0, language="zh"):
    """Accept video-use/Scribe words or normalized tokens, never invent missing times."""
    words = payload.get("tokens", payload.get("words", []))
    tokens, events = [], []
    last = -1.0
    for i, w in enumerate(words):
        if w.get("type", "word") != "word":
            events.append(w)
            continue
        text = w.get("text", "").strip()
        if not normalize(text):
            continue
        a, b = w.get("start"), w.get("end")
        if not isinstance(a, (float, int)) or not isinstance(b, (float, int)) or not (math.isfinite(a) and math.isfinite(b)) or a < 0 or b <= a or a < last:
            raise ValueError(f"token {i}: 缺失、倒序或无效的真实时间；禁止估填")
        last = a
        tokens.append({"id": w.get("id", f"w{i:05d}"), "text": text, "start": a, "end": b,
                       "speaker": w.get("speaker_id", w.get("speaker"))})
    if not tokens or len({w["id"] for w in tokens}) != len(tokens):
        raise ValueError("转录为空或 token ID 重复")
    return {"format": VERSION, "source_sha256": fingerprint(media), "audio_track": track,
            "language": language, "provider": payload.get("provider", "imported-video-use/scribe"),
            "timing_basis": payload.get("timing_basis", "imported-word-evidence-not-listened"),
            "tokens": tokens, "audio_events": events,
            "cache_key": digest({"media": fingerprint(media), "track": track, "language": language,
                                  "adapter": VERSION, "payload": payload})}


def candidates(transcript, min_gap=0.25):
    result = []
    for left, right in zip(transcript["tokens"], transcript["tokens"][1:]):
        if right["start"] - left["end"] >= min_gap:
            result.append({"id": f"gap-{left['id']}-{right['id']}", "start": left["end"],
                           "end": right["start"], "kind": "token-gap-candidate",
                           "decision": "keep", "reason": "未听审；可能是自然呼吸、语义留白或噪声，不能自动判为气声"})
    return result


def validate_transcript(transcript, media, duration):
    if transcript["source_sha256"] != fingerprint(media):
        raise ValueError("素材指纹已变化：转录缓存失效")
    if any(t["end"] > duration + 0.002 for t in transcript["tokens"]):
        raise ValueError("转录超出素材时长")


def make_edit(media, transcript, request, fps=30):
    pending = questions(request)
    if pending:
        raise ValueError("待用户回答：" + "；".join(pending))
    if request["mode"] == "analysis":
        raise ValueError("纯分析不能进入剪辑或渲染")
    if not isinstance(request["must_keep"], list):
        raise ValueError("must_keep 必须是列表（明确无保留项时填 []）")
    info = probe(media)
    if request.get("audio_track", 0) != transcript.get("audio_track", 0):
        raise ValueError("剪辑音轨与转录音轨不一致")
    validate_transcript(transcript, media, info["duration"])
    frame_count = int(math.floor(info["duration"] * fps + 1e-6))
    protected = request.get("protected_ranges", [])
    cuts, decisions = [], []
    for cut in request.get("cuts", []):
        if cut.get("action") not in ("keep", "delete") or not cut.get("reason"):
            raise ValueError("每项删留必须有 action 和 reason")
        a, b = round(cut["start"] * fps), round(cut["end"] * fps)
        if not 0 <= a < b <= frame_count:
            raise ValueError("剪切区间超出素材或量化为空")
        decision = {**cut, "source_start_frame": a, "source_end_frame": b}
        decisions.append(decision)
        if cut["action"] != "delete":
            continue
        if cut.get("approved") is not True:
            raise ValueError("删除必须是已确认策略下人工/Agent 听审确认的项：approved=true")
        for p in protected:
            if a / fps < p["end"] and b / fps > p["start"]:
                raise ValueError("删除触及必须保留的片段")
        for word in transcript["tokens"]:
            overlaps = a / fps < word["end"] - 1e-8 and b / fps > word["start"] + 1e-8
            contains = a / fps <= word["start"] + 1e-8 and b / fps >= word["end"] - 1e-8
            if overlaps and (not contains or word["id"] in request["must_keep"]):
                raise ValueError(f"删除截断词或触及必须保留 token：{word['id']}")
        cuts.append((a, b))
    cuts.sort()
    if any(a < prev_b for (_, prev_b), (a, _) in zip(cuts, cuts[1:])):
        raise ValueError("删除区间重叠")
    kept, cursor, offset = [], 0, 0
    for a, b in cuts + [(frame_count, frame_count)]:
        if a > cursor:
            kept.append({"source_start_frame": cursor, "source_end_frame": a,
                         "output_start_frame": offset, "output_end_frame": offset + a - cursor,
                         "reason": "保留原有表演与未确认删除的自然气口"})
            offset += a - cursor
        cursor = b
    if not kept:
        raise ValueError("不能删除整片")
    mapped = []
    for word in transcript["tokens"]:
        for span in kept:
            a, b = span["source_start_frame"] / fps, span["source_end_frame"] / fps
            if a <= word["start"] + 1e-8 and word["end"] <= b + 1e-8:
                shift = span["output_start_frame"] / fps - a
                mapped.append({**word, "source_start": word["start"], "source_end": word["end"],
                               "start": round(word["start"] + shift, 8), "end": round(word["end"] + shift, 8)})
                break
    for required in request["must_keep"]:
        if required not in {t["id"] for t in mapped}:
            raise ValueError(f"must_keep 中未知或已删除的 token：{required}；原话/事实应另落到 protected_ranges")
    if not mapped:
        raise ValueError("剪后无可对齐的口播 token")
    return {"format": VERSION, "source": str(Path(media).resolve()), "source_sha256": fingerprint(media),
            "transcript_key": transcript["cache_key"], "request": request, "fps": fps,
            "source_frames": frame_count, "output_frames": offset, "media_info": info,
            "time_map": kept, "decisions": decisions, "tokens": mapped,
            "timing_basis": "source-token-evidence-projected-through-exact-cut-map",
            "edit_key": digest({"source": fingerprint(media), "transcript": transcript["cache_key"],
                                "cuts": cuts, "fps": fps})}


def roughcut(edit, output):
    if edit["request"]["mode"] != "produce":
        raise ValueError("剪辑方案模式不渲染；需要 mode=produce")
    if fingerprint(edit["source"]) != edit["source_sha256"]:
        raise ValueError("源素材已更改")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # One lossless intermediate per retained span; A/V share the same selected interval.
    parts = output.parent / "segments"
    parts.mkdir(exist_ok=True)
    paths = []
    fps = edit["fps"]
    for i, span in enumerate(edit["time_map"]):
        path = parts / f"part-{i:04d}.mkv"
        a, b = span["source_start_frame"] / fps, span["source_end_frame"] / fps
        n = span["source_end_frame"] - span["source_start_frame"]
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", edit["source"], "-map", "0:v:0",
               "-vf", f"fps={fps},trim=start_frame={span['source_start_frame']}:end_frame={span['source_end_frame']},setpts=PTS-STARTPTS",
               "-c:v", "ffv1"]
        if edit["media_info"]["has_audio"]:
            cmd += ["-map", f"0:a:{edit['request'].get('audio_track', 0)}", "-af",
                    f"atrim=start={a}:end={b},asetpts=PTS-STARTPTS,aresample=48000,apad,atrim=duration={n/fps}", "-c:a", "pcm_s16le"]
        cmd += [path]
        run(cmd)
        paths.append(path)
    concat = parts / "concat.txt"
    # Generated names are safe; do not interpolate user paths into concat syntax.
    concat.write_text("".join(f"file 'part-{i:04d}.mkv'\n" for i in range(len(paths))))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "1", "-i", concat,
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", fps,
         "-c:a", "aac", "-ar", "48000", "-t", edit["output_frames"] / fps, output])
    check = json.loads(run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                           "-show_entries", "stream=nb_read_frames", "-of", "json", output]))
    if int(check["streams"][0]["nb_read_frames"]) != edit["output_frames"]:
        raise ValueError("粗剪输出帧数不符；禁止导出旧对齐")
    write(str(output) + ".provenance.json", {"edit_key": edit["edit_key"], "media_sha256": fingerprint(output),
                                            "frames": edit["output_frames"]})
    return output


def chinese_cues(tokens, max_chars=14, max_seconds=6.0):
    """Break at punctuation, pauses and width, never slice a timed token to invent timing."""
    cues, group = [], []
    for token in tokens:
        if group and (sum(len(t["text"]) for t in group) + len(token["text"]) > max_chars or
                      token["end"] - group[0]["start"] > max_seconds or
                      token["start"] - group[-1]["end"] > 0.4):
            cues.append(group)
            group = []
        group.append(token)
        if re.search(r"[。！？；!?;]$", token["text"]):
            cues.append(group)
            group = []
    if group:
        cues.append(group)
    if any(sum(len(t["text"]) for t in cue) > max_chars for cue in cues):
        raise ValueError("单个计时 token 太长，需人工断句/更细粒度证据，不能估填字时")
    return cues


def script_text(edit, scenes, max_chars=14):
    tokens = edit["tokens"]
    ids = [t["id"] for t in tokens]
    starts, ends = {}, {}
    for scene in scenes:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", scene["id"]):
            raise ValueError("场景 ID 必须是小写 ASCII 名称")
        a, b = ids.index(scene["first"]), ids.index(scene["last"])
        if a > b:
            raise ValueError("场景语义区间倒序")
        starts.setdefault(scene["first"], []).append(scene)
        ends.setdefault(scene["last"], []).append(scene)
    boundaries = {g[-1]["id"] for g in chinese_cues(tokens, max_chars)}
    body = []
    for i, token in enumerate(tokens):
        for scene in starts.get(token["id"], []):
            body.append("@{" + scene["id"] + "}@{" + scene["id"] + "-enter!}")
        # Preserve Chinese adjacency; separate adjacent Latin tokens for Script parsing.
        if i and re.search(r"[a-zA-Z0-9]$", tokens[i-1]["text"]) and re.match(r"[a-zA-Z0-9]", token["text"]):
            body.append(" ")
        body.append(script_escape(token["text"]))
        for scene in reversed(ends.get(token["id"], [])):
            body.append("@{/" + scene["id"] + "}")
        if token["id"] in boundaries and i < len(tokens) - 1:
            body.append(" || ")
    return "".join(body)


def export_hypit(edit, rough, destination, font, scenes=None, style=None, final_transcript=None):
    """A local-only native Hypit project. Style is downstream of retained media."""
    if edit["request"]["mode"] != "produce":
        raise ValueError("只分析/剪辑方案不会导出可执行渲染工程")
    rough, destination, font = Path(rough), Path(destination), Path(font)
    if not rough.is_file() or not font.is_file():
        raise ValueError("缺少粗剪或中文字体文件")
    receipt_path = Path(str(rough) + ".provenance.json")
    if not receipt_path.is_file() and final_transcript is None:
        raise ValueError("粗剪缺少与 edit 对应的产物记录；重新粗剪或提供当前媒体的新测量")
    if receipt_path.is_file():
        receipt = read(receipt_path)
        if receipt["edit_key"] != edit["edit_key"] or receipt["media_sha256"] != fingerprint(rough):
            raise ValueError("粗剪不是当前 edit 的输出；重新粗剪并重建锚点")
    if abs(probe(rough)["duration"] - edit["output_frames"] / edit["fps"]) > 0.1:
        raise ValueError("粗剪时长不匹配")
    scenes, style = scenes or [], style or {}
    if len({s["id"] for s in scenes}) != len(scenes):
        raise ValueError("场景 ID 重复")
    # Replacing speech requires fresh evidence for the actual roughcut bytes.
    if final_transcript is not None:
        validate_transcript(final_transcript, rough, probe(rough)["duration"])
        if normalize("".join(w["text"] for w in edit["tokens"])) != normalize("".join(w["text"] for w in final_transcript["tokens"])):
            raise ValueError("剪后录音与接受稿不一致；先修改稿件、重建锚点再导出")
        edit = {**edit, "tokens": final_transcript["tokens"], "timing_basis": final_transcript["timing_basis"]}
    assets = destination / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(rough, assets / "roughcut.mp4")
    # System fonts can carry immutable flags; copy bytes without those host flags.
    shutil.copyfile(font, assets / ("caption" + font.suffix))
    package_dir = Path(__file__).parent.parent / "assets" / "hypit-reviewed-alignment"
    shutil.copytree(package_dir, destination / "packages" / "reviewed-alignment", dirs_exist_ok=True)
    write(destination / "package.json", {"name": "koubo-production", "version": "0.0.0", "private": True,
          "type": "module", "hypit": {"project": True}, "dependencies": {
              "@koubo/reviewed-alignment": "file:./packages/reviewed-alignment", "@hypit/hypit": "0.3.1"}})
    words = [{"text": t["text"], "start": t["start"], "end": t["end"]} for t in edit["tokens"]]
    write(destination / "timing.json", {"kind": "inline", "value": {
        "words": words, "fps": edit["fps"], "frames": edit["output_frames"],
        "media_sha256": fingerprint(assets / "roughcut.mp4"), "basis": edit["timing_basis"]}})
    text = script_text(edit, scenes, style.get("max_chars", 14))
    write(destination / "edit.json", edit)
    write(destination / "scenes.json", scenes)
    write(destination / "style.json", style)
    q = lambda value: html.escape(str(value), quote=True)
    declarations, tracks, events = [], [], []
    for scene in scenes:
        sid = scene["id"]
        frame_ref = "card-frame"
        if "frame" in scene:
            frame = scene["frame"]
            if len(frame) != 4 or not all(isinstance(v, (int,float)) and math.isfinite(v) for v in frame) or not (0 <= frame[0] < frame[2] <= 1 and 0 <= frame[1] < frame[3] <= 1):
                raise ValueError("场景 frame 须为归一化 [left,top,right,bottom]")
            frame_ref = sid + "-frame"
            declarations.append(f'  <space:Frame id="{frame_ref}" within={{canvas.bounds}} left="{frame[0]*100}%" top="{frame[1]*100}%" right="{frame[2]*100}%" bottom="{frame[3]*100}%"/>')
        declarations += [f'  <semantic:Window id="{sid}" projection={{story-time}} during={{story.selection.{sid}}}/>',
                         f'  <semantic:Instant id="{sid}-enter" projection={{story-time}} at={{story.moment.{sid}-enter}}/>',
                         f'  <time:Window id="{sid}-visible" timeline={{speech.timeline}} from={{{sid}-enter}} until={{{sid}.end}}/>']
        # The scene slot holds a replaceable local video; no generated presenter.
        if scene.get("media"):
            source = Path(scene["media"]).resolve()
            if not source.is_file():
                raise ValueError(f"场景素材不存在：{source}")
            name = f"scene-{sid}{source.suffix}"
            shutil.copy2(source, assets / name)
            declarations += [f'  <asset:Video id="{sid}-asset" src="./assets/{q(name)}"/>',
                             f'  <mediaop:Normalize id="{sid}-media" source={{{sid}-asset}} clock={{clock}} video="primary-moving" audio="none" span-authority="video"/>',
                             f'  <visual:Track id="{sid}-picture" timeline={{speech.timeline}}><visual:Clip id="slot" media={{{sid}-media.media}} during={{{sid}-visible}} frame={{{frame_ref}}} z="20" fit="contain"/></visual:Track>']
            tracks.append(f'    <film:Track source={{{sid}-picture.visual}}/>')
        if scene.get("label"):
            declarations += [f'  <typo:Flow id="{sid}-label" timeline={{speech.timeline}} within={{{frame_ref}}} style={{card-style}} during={{{sid}-visible}} z="30" align="center" block-align="center" motion={{card-motion}}>{q(scene["label"])}</typo:Flow>']
            tracks.append(f'    <film:Track source={{{sid}-label.visual}}/>')
        first = next(t for t in edit["tokens"] if t["id"] == scene["first"])
        last = next(t for t in edit["tokens"] if t["id"] == scene["last"])
        events.append({"id": sid, "first": scene["first"], "last": scene["last"],
                       "start": first["start"], "end": last["end"], "binding": "Selection+Moment"})
    author = '''<?svml using="@hypit/markup@1"?>
<svml>
  <import from="@hypit/script@1"/>
  <import as="time" from="@hypit/timeline-author@1"/>
  <import as="space" from="@hypit/spatial@1"/>
  <import as="asset" from="@hypit/media@1"/>
  <import as="mediaop" from="@hypit/media-operations@1"/>
  <import as="semantic" from="@hypit/narrative-temporal@1"/>
  <import as="reviewed" from="@koubo/reviewed-alignment@1"/>
  <import as="nc" from="@hypit/narrative-caption@1"/>
  <import as="caption" from="@hypit/caption-fine@1"/>
  <import as="typo" from="@hypit/text-fine@1"/>
  <import as="visual" from="@hypit/visual-track@1"/>
  <import as="audio" from="@hypit/audio-track@1"/>
  <import as="film" from="@hypit/film@1"/>
  <import as="html" from="@hypit/html-video@1"/>
  <import as="look" source="./look.svs"/>
  <script id="story"><speech>BODY</speech></script>
  <time:Clock id="clock" frame-rate="FPS"/>
  <space:Canvas id="canvas" width="WIDTH" height="HEIGHT"/>
  <space:Frame id="full" within={canvas.bounds} left="0%" top="0%" right="100%" bottom="100%"/>
  <space:Frame id="card-frame" within={canvas.bounds} left="8%" top="12%" right="92%" bottom="35%"/>
  <asset:Video id="recording" src="./assets/roughcut.mp4"/>
  <asset:Font id="font" src="./assets/FONT" weight="400" style="normal"/>
  <mediaop:Normalize id="prepared" source={recording} clock={clock} video="primary-moving" audio="AUDIO" span-authority="video"/>
  <reviewed:Timing id="timing"/>
  <reviewed:Alignment id="alignment" narrative={story} segment={story.segment.speech} domain={prepared.domain} timing={timing.timing}/>
  <time:Timeline id="speech" clock={clock} end="performance.end"><time:Window id="performance" from="start" for={prepared.extent}/></time:Timeline>
  <semantic:Projection id="story-time" narrative={story} timeline={speech.timeline}><semantic:Map alignment={alignment.alignment} domain={prepared.domain} window={speech.performance}/></semantic:Projection>
  <nc:Timing id="caption-time" document={story.caption} binding={story.caption-binding} projection={story-time}/>
  <caption:Style id="caption-style" recipe={look.caption.main} font={font}/>
  <caption:Caption id="captions" document={story.caption} timing={caption-time} timeline={speech.timeline} within={canvas.bounds}><caption:Use style={caption-style}/></caption:Caption>
  <typo:Style id="card-style" recipe={look.text.card} font={font}><typo:Stroke color="#09111F" width="2" placement="outside"/><typo:Fill color="COLOR"/></typo:Style>
  <typo:Motion id="card-motion"><typo:ItemKeyframe at="0" opacity="0"/><typo:ItemKeyframe at="8" opacity="1" easing="ease-out"/></typo:Motion>
  <visual:Track id="picture" timeline={speech.timeline}><visual:Clip id="presenter" media={prepared.media} during={speech.performance} frame={full} z="0" fit="contain"/></visual:Track>
SOUND
DECLARATIONS
  <film:Film id="main" canvas={canvas.canvas} timeline={speech.timeline} appearance={look.film.main}>
    <film:Track source={picture.visual}/>
SOUNDTRACK
TRACKS
    <film:Track source={captions.visual}/>
  </film:Film>
  <html:Video id="final" composition={main.composition} timeline={speech.timeline}/>
</svml>
'''
    values = {"BODY": text, "FPS": str(edit["fps"]), "WIDTH": str(edit["media_info"]["width"]),
              "HEIGHT": str(edit["media_info"]["height"]), "FONT": "caption" + font.suffix,
              "AUDIO": "default" if edit["media_info"]["has_audio"] else "none",
              "COLOR": q(style.get("accent", "#80E8D0")), "DECLARATIONS": "\n".join(declarations),
              "TRACKS": "\n".join(tracks),
              "SOUND": '<audio:Track id="sound" timeline={speech.timeline}><audio:Clip id="voice" source={prepared.media} during={speech.performance}/></audio:Track>' if edit["media_info"]["has_audio"] else "",
              "SOUNDTRACK": '<film:Track source={sound.audio}/>' if edit["media_info"]["has_audio"] else ""}
    # Replace all placeholders in one pass; never re-interpret user text as a placeholder.
    author = re.sub(r"\b(" + "|".join(sorted(values, key=len, reverse=True)) + r")\b", lambda m: values[m[0]], author)
    (destination / "production.svml").write_text(author, encoding="utf-8")
    (destination / "look.svs").write_text('''<?svml using="@hypit/recipe@1"?>
<sheet version="1">
film.main { background: #152434; }
caption.main { stack-order: 70; x: 0.5; y: 0.82; width: 0.88; height: 0.18; anchor-x: center; anchor-y: center; align: center; block-align: center; max-lines: 2; max-words-per-line: 10; word-gap: 0; line-height: 1.2; background: #00000088; padding: 4 8; radius: 6; size: SIZE; fill: #FFFFFF; stroke-color: #09111F; stroke-width: 1; }
text.card { size: CARD; weight: 400; }
</sheet>
'''.replace("SIZE", str(style.get("caption_size", 24))).replace("CARD", str(style.get("card_size", 30))))
    for name, target in [("render", "final.video"), ("preview", "main.composition")]:
        (destination / (name + ".svrun")).write_text(f'''<?svml using="@hypit/markup/run@1"?>
<svrun version="1">
  <author source="./production.svml"/>
  <target output="{target}"/>
  <value id="reviewed-timing" type="@koubo/reviewed-alignment@1#Timing" from="./timing.json"/>
  <satisfy output="timing.timing" candidate="reviewed-timing"/>
</svrun>
''')
    write(destination / "anchors.json", {"script_digest": digest(text), "media_sha256": fingerprint(rough), "events": events,
                                         "basis": edit["timing_basis"]})
    return destination


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("questions"); q.add_argument("request")
    a = sub.add_parser("analyze"); a.add_argument("media"); a.add_argument("--transcript"); a.add_argument("--output", required=True)
    a.add_argument("--track", type=int, default=0); a.add_argument("--language", default="zh")
    e = sub.add_parser("plan"); e.add_argument("media"); e.add_argument("transcript"); e.add_argument("request"); e.add_argument("--output", required=True); e.add_argument("--fps", type=int, default=30)
    r = sub.add_parser("roughcut"); r.add_argument("edit"); r.add_argument("--output", required=True)
    x = sub.add_parser("export"); x.add_argument("edit"); x.add_argument("roughcut"); x.add_argument("--output", required=True); x.add_argument("--font", required=True)
    x.add_argument("--scenes"); x.add_argument("--style"); x.add_argument("--final-transcript")
    args = p.parse_args()
    try:
        if args.command == "questions":
            print(json.dumps({"pending": questions(read(args.request))}, ensure_ascii=False))
        elif args.command == "analyze":
            dest = Path(args.output); dest.mkdir(parents=True, exist_ok=True)
            info = {"source": str(Path(args.media).resolve()), "sha256": fingerprint(args.media), **probe(args.media), "asr_executed": False}
            write(dest / "media.json", info)
            if args.transcript:
                t = import_transcript(read(args.transcript), args.media, args.track, args.language)
                validate_transcript(t, args.media, info["duration"])
                write(dest / "transcript.json", t); write(dest / "pause-candidates.json", candidates(t))
            (dest / "ANALYSIS.md").write_text("# 参考分析\n\n素材已探测；语义、全片结构与画面观察需按实际证据补充。ASR 未执行。\n", encoding="utf-8")
            (dest / "TIMELINE.md").write_text("# 参考时间线\n\n原时间只作来源证据。词间空隙是候选，不证明气声或应删除。未听审。\n", encoding="utf-8")
        elif args.command == "plan":
            if args.fps <= 0: raise ValueError("fps 必须大于零")
            write(args.output, make_edit(args.media, read(args.transcript), read(args.request), args.fps))
        elif args.command == "roughcut":
            print(roughcut(read(args.edit), args.output))
        elif args.command == "export":
            print(export_hypit(read(args.edit), args.roughcut, args.output, args.font,
                               read(args.scenes) if args.scenes else None, read(args.style) if args.style else None,
                               read(args.final_transcript) if args.final_transcript else None))
    except (ValueError, KeyError, subprocess.CalledProcessError) as error:
        p.exit(2, str(error) + "\n")


if __name__ == "__main__":
    main()
