#!/usr/bin/env python3
"""Verify actual synthetic deliverable: media clock, semantic outputs and audio signal."""
import argparse
import array
import json
import math
from pathlib import Path
import subprocess
from production import read, run, write


def audio_samples(path):
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"], check=True, capture_output=True)
    samples = array.array("f"); samples.frombytes(result.stdout)
    return samples


def rms(samples, start, end):
    selected = samples[round(start*48000):round(end*48000)]
    return math.sqrt(sum(x*x for x in selected)/len(selected))


def value(project, build, output):
    results = list((project/".hypit/results").glob(f"*/{build}/result.json"))
    if len(results) != 1: raise ValueError("Result missing")
    record = read(results[0])["outputs"][output]["value"]
    if record["kind"] == "build-output": return value(project, record["build"], record["output"])
    return read(results[0].parent/record["path"])["value"]


def verify(root, final, build):
    root = Path(root); final = Path(final)
    project = root/"hypit-project"
    stream = json.loads(run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", final]))
    video = next(s for s in stream["streams"] if s["codec_type"] == "video")
    audio = next(s for s in stream["streams"] if s["codec_type"] == "audio")
    assert int(video["nb_read_frames"]) == 1080
    assert (video["width"], video["height"]) == (360,640)
    assert abs(float(video["duration"])-36) < .034
    assert abs(float(audio["duration"])-36) < .05
    events = read(project/"anchors.json")["events"]
    resolved = []
    for event in events:
        actual = value(project, build, event["id"]+"-visible")["span"]
        assert actual["startFrame"] == round(event["start"]*30)
        assert actual["endFrameExclusive"] == round(event["end"]*30)
        resolved.append({"id":event["id"],**actual})
    samples = audio_samples(final)
    sound = {str(t):rms(samples,t,t+.1) for t in [1.1,7.1,8.4,9.1,17.1,27.1]}
    assert all(sound[str(t)] > .04 for t in [1.1,9.1,17.1,27.1])
    assert .003 < sound["7.1"] < .025, "retained breath-like cue missing"
    assert sound["8.4"] < .003, "deleted-gap mapping or tone onset wrong"
    write(root/"actual-verification.json", {"passed":True,"video_frames":1080,"duration":36,"dimensions":[360,640],
        "semantic_windows":resolved,"audio_rms":sound,"asr_executed":False,
        "full_human_listening":False,"basis":"synthetic-tone-signal-and-actual-native-render"})
    # Real encoded video, before/within/after semantic card entry and exit.
    frames = [29,30,209,216,509,514,519,653,654,809,818,954]
    selection = "+".join(f"eq(n\\,{n})" for n in frames)
    run(["ffmpeg","-v","error","-y","-i",final,"-vf",f"select='{selection}',scale=270:480,tile=4x3","-frames:v","1",root/"actual-contact-sheet.png"])
    print(json.dumps({"passed":True,"report":str(root/"actual-verification.json"),"contact_sheet":str(root/"actual-contact-sheet.png")},ensure_ascii=False))


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);p.add_argument("final",type=Path);p.add_argument("build")
    a=p.parse_args();verify(a.root,a.final,a.build)
