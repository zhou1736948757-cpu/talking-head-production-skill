#!/usr/bin/env python3
"""Select verified previous Hypit material outputs in a new SVRun."""
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from production import read


def result_for(project, build):
    matches = list((project / ".hypit/results").glob(f"*/{build}/result.json"))
    if len(matches) != 1:
        raise ValueError("此工程中未找到唯一 Build Result")
    return matches[0], read(matches[0])


def saved_timing(project, build, visited=None):
    visited = set() if visited is None else visited
    if build in visited: raise ValueError("循环结果引用")
    visited.add(build)
    path, result = result_for(project, build)
    record = result["outputs"].get("timing.timing")
    if record:
        v = record["value"]
        if v["kind"] == "build-output": return saved_timing(project, v["build"], visited)
        return read(path.parent / v["path"])["value"]
    # A style-only Build may keep alignment without demanding its timing again.
    alignment = result["outputs"].get("alignment.alignment", {}).get("value", {})
    if alignment.get("kind") == "build-output": return saved_timing(project, alignment["build"], visited)
    raise ValueError("旧结果缺少可核对的 timing；不能自动复用")


def reuse(project, build, source_run, destination, outputs):
    if not re.fullmatch(r"bld_[A-Za-z0-9_]+", build):
        raise ValueError("无效 Build ID；必须使用实际结果")
    matches = list((project / ".hypit/results").glob(f"*/{build}/result.json"))
    if len(matches) != 1:
        raise ValueError("此工程中未找到唯一 Build Result")
    result = json.loads(matches[0].read_text())
    if any(output not in result["outputs"] for output in outputs):
        raise ValueError("所选结果没有全部要求的输出")
    # A saved alignment is meaningful only for the same words, times and media.
    prior_timing = saved_timing(project, build)
    if prior_timing != read(project / "timing.json")["value"]:
        raise ValueError("词时/口播/媒体已改变；拒绝复用旧素材与对齐结果")
    text = source_run.read_text()
    root = ET.fromstring(text)
    selected = {e.attrib["output"] for e in root.findall("satisfy")}
    candidate_ids = {e.attrib["id"] for e in root if "id" in e.attrib}
    extra = []
    for i, output in enumerate(outputs):
        if output in selected:
            raise ValueError(f"保留既有选择：{output} 已有 Candidate；请明确编辑该选择")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", output):
            raise ValueError("无效输出名")
        candidate = f"reuse-{build[-10:]}-{i}"
        while candidate in candidate_ids:
            candidate += "-next"
        candidate_ids.add(candidate)
        extra += [f'  <build-record id="{candidate}" build="{build}" output="{output}"/>',
                  f'  <satisfy output="{output}" candidate="{candidate}"/>']
    destination.write_text(text.replace("</svrun>", "\n".join(extra) + "\n</svrun>"))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("project", type=Path); p.add_argument("build")
    p.add_argument("--run", default="render.svrun"); p.add_argument("--output", default="reuse.svrun")
    p.add_argument("--outputs", nargs="+", default=["prepared.media", "prepared.domain", "prepared.extent", "alignment.alignment"])
    a = p.parse_args(); reuse(a.project, a.build, a.project/a.run, a.project/a.output, a.outputs)
