#!/usr/bin/env python3
"""Explicit local Hypit backend. No install, auth, transcription or generation calls."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
from typing import Protocol

from production import digest, fingerprint, read, write


class ProductionBackend(Protocol):
    """Alternative engines consume the same exported project and evidence."""
    def invoke(self, project: Path, operation: str, runtime: Path): ...


class HypitBackend:
    def __init__(self, executable="hypit", run="render.svrun"):
        self.executable = executable
        self.run = run

    def invoke(self, project, operation, runtime):
        runtime = Path(runtime).resolve()
        profile = read(runtime)
        if profile.get("credentials") or any(e["use"] not in (
                "@hypit/media-local", "@hypit/provider-html-local") for e in profile.get("endpoints", {}).values()):
            raise ValueError("此后端只执行无凭据的本地媒体/HTML；外部服务另行实现并获得授权")
        evidence = read(project / "timing.json")["value"]
        if fingerprint(project / "assets/roughcut.mp4") != evidence["media_sha256"]:
            raise ValueError("粗剪素材指纹变化，重新对齐后才能执行")
        anchors = read(project / "anchors.json")
        script = re.search(r'<script\s+id="story">\s*<speech>(.*?)</speech>\s*</script>',
                           (project / "production.svml").read_text(), re.DOTALL)
        if script is None or digest(script[1]) != anchors["script_digest"]:
            raise ValueError("口播 Script 已变化：需新证据/重新导出锚点，不能绕过对齐复用旧结果")
        env = dict(os.environ)
        env["HYPIT_STATE_HOME"] = str(project / ".hypit/host-state")
        command = [self.executable]
        if operation == "check":
            command += ["check", self.run]
        elif operation == "plan":
            command += ["plan", self.run, "--runtime", str(runtime)]
        elif operation == "build":
            command += ["build", self.run, "--runtime", str(runtime), "--follow"]
        else:
            raise ValueError("不支持的后端操作")
        return subprocess.run(command + ["--json"], cwd=project, env=env, text=True, capture_output=True)


def link_installed_distribution(project, distribution):
    """Optional offline reuse. Links only inside the project, never edits an installation."""
    distribution = Path(distribution).resolve()
    if read(distribution / "package.json").get("version") != "0.3.1":
        raise ValueError("需要已验证的 @hypit/hypit 0.3.1；其他版本先做兼容验证")
    base = project / "node_modules/@hypit"
    base.mkdir(parents=True, exist_ok=True)
    targets = [(base / "hypit", distribution)]
    targets += [(base / p.name, p) for p in (distribution / "node_modules/@hypit").iterdir() if p.is_dir()]
    own = project / "node_modules/@koubo"
    own.mkdir(parents=True, exist_ok=True)
    targets.append((own / "reviewed-alignment", project / "packages/reviewed-alignment"))
    # Resolve SDK imports from the project-authored package as well.
    nested = project / "packages/reviewed-alignment/node_modules/@hypit"
    nested.parent.mkdir(parents=True, exist_ok=True)
    targets.append((nested, base))
    for dest, source in targets:
        if dest.is_symlink() and dest.resolve() == source.resolve():
            continue
        if dest.exists() or dest.is_symlink():
            raise ValueError(f"保留已有依赖；链接目标已存在：{dest}")
        dest.symlink_to(source.resolve(), target_is_directory=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("operation", choices=["link-installed", "check", "plan", "build"])
    ap.add_argument("--distribution", type=Path)
    ap.add_argument("--runtime", type=Path)
    ap.add_argument("--run", default="render.svrun")
    args = ap.parse_args()
    project = args.project.resolve()
    if args.operation == "link-installed":
        if not args.distribution: ap.error("需要 --distribution")
        link_installed_distribution(project, args.distribution)
    else:
        if not args.runtime: ap.error("需要显式本地 --runtime")
        r = HypitBackend(run=args.run).invoke(project, args.operation, args.runtime)
        print(r.stdout, end="")
        print(r.stderr, end="", file=__import__("sys").stderr)
        raise SystemExit(r.returncode)


if __name__ == "__main__":
    main()
