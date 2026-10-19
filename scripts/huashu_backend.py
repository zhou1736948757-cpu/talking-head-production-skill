#!/usr/bin/env python3
"""Optional local Huashu clip adapter. No copied engine, voice service or generation."""
import argparse
import json
import re
import subprocess
from pathlib import Path

from production import digest, fingerprint, questions, read, write

GRAMMARS = {
    "t2_keynote_ui": {"card", "step", "image", "highlight", "number"},
    "y3_whiteboard": {"draw", "point", "highlight"},
    "y5_kinetic_type": {"point", "highlight", "number"},
}
THEMES = {"paper", "poster", "ink", "navy", "bauhaus", "snow", "wood", "chalk"}
VERSION = "koubo-huashu@1"


def locate(explicit=None):
    candidates = [Path(explicit)] if explicit else [
        Path.home()/"skills/huashu-art-motion", Path.home()/".codex/skills/huashu-art-motion",
        Path.cwd()/".agents/skills/huashu-art-motion"]
    for candidate in candidates:
        if (candidate/"SKILL.md").is_file():
            return candidate.resolve()
    raise ValueError("未找到 huashu-art-motion；提供 --root 指向用户已安装的 Skill，不自动下载")


def inspect(root):
    root = Path(root).resolve()
    skill = (root/"SKILL.md").read_text()
    if not re.search(r"^name:\s*huashu-art-motion\s*$", skill, re.M):
        raise ValueError("Skill 身份不是 huashu-art-motion")
    license_text = (root/"LICENSE").read_text()
    if not license_text.startswith("MIT License") or "alchaincyf" not in license_text:
        raise ValueError("Huashu 许可不匹配；先重新审阅，不自动运行")
    engine = root/"scripts/engine"
    files = [engine/"clip.html", engine/"clip.js", root/"LICENSE", root/"SKILL.md"]
    files += sorted((engine/"lib").glob("*.js"))
    files += [engine/"clips"/(name+".js") for name in GRAMMARS]
    files += sorted((engine/"lib/fonts").glob("*"))
    hashes = {p.relative_to(root).as_posix(): fingerprint(p) for p in files if p.is_file()}
    required = [engine/"clip.html",engine/"clip.js",*[engine/"clips"/(name+".js") for name in GRAMMARS]]
    if not all(p.is_file() for p in required):
        raise ValueError("缺少已审阅的片段接口/语法文件")
    return {"format": VERSION, "identity": "huashu-art-motion", "license": "MIT (fonts separate)",
            "root": str(root), "engine_fingerprint": digest(hashes), "files_sha256": hashes,
            "supported_grammars": list(GRAMMARS), "voice_or_image_services": False}


def prepare(edit, motion, destination, asset_base=None):
    """Bind only accepted cut-token boundaries; reference timestamps are not inputs."""
    if questions(edit["request"]):
        raise ValueError("剪辑偏好未答完；不能擅定制作策略")
    if edit["request"]["mode"] not in ("plan", "produce"):
        raise ValueError("只分析不生成动效工程或渲染")
    if not motion.get("purpose") or not motion.get("clips"):
        raise ValueError("需要这次动效的信息目的和明确选择的 clips；没有默认特效")
    fps = edit["fps"]; tokens = {t["id"]: t for t in edit["tokens"]}
    destination = Path(destination).resolve()
    clips, ids = [], set()
    # Validate everything before writing any project output.
    for clip in motion["clips"]:
        cid = clip["id"]; grammar = clip["grammar"]
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,50}", cid) or cid in ids:
            raise ValueError("动效 ID 无效或重复")
        ids.add(cid)
        if grammar not in GRAMMARS or clip.get("theme") not in THEMES:
            raise ValueError("明确选择受支持的 grammar 和 theme；不默认套风格")
        if grammar == "y3_whiteboard" and clip.get("pen") not in ("hidden", "original"):
            raise ValueError("白板须明确选择 pen=hidden 或 original；原装饰笔可能短暂遮字，需逐帧检查")
        first, last = tokens[clip["first"]], tokens[clip["last"]]
        start, end = round(first["start"]*fps), round(last["end"]*fps)
        if not 1 <= end-start <= 8*fps:
            raise ValueError("片段须为 1 帧至 8 秒；长段拆镜，不改变口播速度")
        width, height = clip["size"]
        if any(not isinstance(v,int) or v < 64 or v > 1920 or v%2 for v in [width,height]):
            raise ValueError("size 须为64–1920之间的偶数像素")
        frame = clip["frame"]
        if len(frame)!=4 or not (0 <= frame[0] < frame[2] <= 1 and 0 <= frame[1] < frame[3] <= 1):
            raise ValueError("frame 须显式指定归一化 [left,top,right,bottom]；先避让真人与字幕")
        cues=[]
        for cue in clip["cues"]:
            if "at" in cue: raise ValueError("cue 不接受原秒数；用剪后 token 锚点")
            token=tokens[cue["token"]]; at_frame=round(token["start"]*fps)-start
            if not 0 <= at_frame < end-start or cue["kind"] not in GRAMMARS[grammar]:
                raise ValueError("cue 超出片段或语法不支持 kind")
            if cue["kind"]=="number" and (cue.get("timing")!="settle" or at_frame < round(.9*fps)):
                raise ValueError("number 的 at 是落定时刻；需 timing=settle 和至少0.9秒前置空间")
            data=cue.get("data",{})
            if not isinstance(data,dict): raise ValueError("cue.data 必须是对象")
            q={k:v for k,v in cue.items() if k not in ("token","timing")}
            if q.get("image"):
                if re.match(r"^(https?:|data:|file:)",q["image"],re.I):raise ValueError("只接收明确提供的本地图片，不联网取素材")
                image=Path(q["image"])
                if not image.is_absolute():image=Path(asset_base or destination)/image
                if not image.is_file():raise ValueError("动效图片不存在")
                q["image"]=str(image.resolve())
            q["at"]=at_frame/fps; cues.append(q)
        if not cues: raise ValueError("片段不能无事件")
        safe=clip.get("safe",{"top":0,"bottom":0,"left":0,"right":0})
        if set(safe)-{"top","bottom","left","right"} or any(not isinstance(v,(int,float)) or v<0 for v in safe.values()):
            raise ValueError("safe 只能指定非负的上下左右像素")
        if safe.get("top",0)+safe.get("bottom",0)>=height or safe.get("left",0)+safe.get("right",0)>=width:
            raise ValueError("safe 不能占满画布")
        spec={"grammar":grammar,"duration":(end-start)/fps,"fps":fps,"width":width,"height":height,
              "theme":clip["theme"],"safe":safe,"cues":cues}
        if grammar == "y3_whiteboard": spec["koubo_pen"] = clip["pen"]
        # Constrain the adapter to text, shapes and explicitly supplied local images.
        if any("frames" in c for c in cues) or clip.get("data"):
            raise ValueError("此适配不接受角色帧库或自定义顶层 data；沿用真人原素材")
        clips.append({"id":cid,"first":clip["first"],"last":clip["last"],"frame":frame,
                      "edit_start_frame":start,"edit_end_frame":end,"spec":spec,
                      "spec_key":digest(spec),"purpose":clip.get("purpose",motion["purpose"])})
    result={"format":VERSION,"mode":edit["request"]["mode"],"edit_key":edit["edit_key"],
            "token_digest":digest(edit["tokens"]),"fps":fps,"clips":clips}
    write(destination/"motion-project.json",result)
    for clip in clips: write(destination/(clip["id"]+".spec.json"),clip["spec"])
    return result


def validate_edit(project,edit):
    if questions(edit["request"]) or edit["request"]["mode"] not in ("plan","produce"):
        raise ValueError("当前请求只分析或偏好未答完；不接入旧动效工程")
    if project["edit_key"]!=edit["edit_key"] or project["token_digest"]!=digest(edit["tokens"]):
        raise ValueError("剪辑/口播锚点已变，重新 prepare；不能使用旧动效时序")


def render(project_dir,edit,root,chrome,package_root,reviewed_fingerprint):
    project_dir=Path(project_dir).resolve(); project=read(project_dir/"motion-project.json")
    validate_edit(project,edit)
    if project["mode"]!="produce" or edit["request"]["mode"]!="produce": raise ValueError("剪辑方案不渲染；需要已明确的 produce")
    identity=inspect(root)
    if identity["engine_fingerprint"]!=reviewed_fingerprint:
        raise ValueError("本地 Huashu 内容与已审阅指纹不符；先审阅变化，不自动运行")
    write(project_dir/"local-engine-review.json",identity)
    renders=[]
    for clip in project["clips"]:
        spec_path=project_dir/(clip["id"]+".spec.json");spec=read(spec_path)
        if digest(spec)!=clip["spec_key"]: raise ValueError("spec 已变化；修改 motion plan 后重新 prepare")
        # External images are explicit local files only; fingerprints enter the cache key.
        assets=[]
        for cue in spec["cues"]:
            if cue.get("image"):
                image=Path(cue["image"])
                if not image.is_absolute():image=spec_path.parent/image
                if not image.is_file():raise ValueError("动效图片不存在；不生成替代素材")
                assets.append(fingerprint(image))
        key=digest({"engine":identity["engine_fingerprint"],"spec":spec,"assets":assets,"adapter":VERSION,
                    "renderer":fingerprint(Path(__file__).with_name("huashu_render.mjs"))})
        output=project_dir/(clip["id"]+".mp4");receipt=Path(str(output)+".json")
        cached=output.is_file() and receipt.is_file() and read(receipt).get("cache_key")==key and read(receipt).get("media_sha256")==fingerprint(output)
        if not cached:
            argv=["node",str(Path(__file__).with_name("huashu_render.mjs")),"--engine",str(Path(root)/"scripts/engine"),
                  "--spec",str(spec_path),"--out",str(output),"--chrome",str(chrome),"--package-root",str(package_root)]
            subprocess.run(argv,check=True)
            facts=read(str(output)+".qa.json")
            streams=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-show_streams","-of","json",str(output)],text=True))["streams"]
            video=next(s for s in streams if s["codec_type"]=="video")
            if int(video["nb_read_frames"])!=round(spec["duration"]*spec["fps"]) or any(s["codec_type"]=="audio" for s in streams):
                raise ValueError("动效实际帧数/无声约定不符；拒绝接入主片")
            write(receipt,{"cache_key":key,"media_sha256":fingerprint(output),"frames":facts["frames"],"engine_fingerprint":identity["engine_fingerprint"]})
        renders.append({"id":clip["id"],"media":str(output),"first":clip["first"],"last":clip["last"],
                        "frame":clip["frame"],"cache_hit":cached,"media_sha256":fingerprint(output)})
    write(project_dir/"rendered-scenes.json",renders);return renders


def attach(project_dir,edit,existing,destination,select=None):
    project_dir=Path(project_dir);project=read(project_dir/"motion-project.json");validate_edit(project,edit)
    rendered=read(project_dir/"rendered-scenes.json")
    if select:
        if set(select)-{s["id"] for s in rendered}:raise ValueError("选择了不存在的动效 ID")
        rendered=[s for s in rendered if s["id"] in select]
    planned={c["id"]:c for c in project["clips"]}
    for i,scene in enumerate(rendered):
        for previous in rendered[:i]:
            a,b=planned[scene["id"]],planned[previous["id"]]
            fa,fb=a["frame"],b["frame"]
            if a["edit_start_frame"]<b["edit_end_frame"] and b["edit_start_frame"]<a["edit_end_frame"] and fa[0]<fb[2] and fb[0]<fa[2] and fa[1]<fb[3] and fb[1]<fa[3]:
                raise ValueError("多个动效在同一时空位置重叠；用 --select 明确选用备选，不默认全部叠加")
    ids={s["id"] for s in existing}
    if any(s["id"] in ids for s in rendered):raise ValueError("保留现有场景：ID 冲突，先明确选择替换项")
    for scene in rendered:
        if fingerprint(scene["media"])!=scene["media_sha256"]:raise ValueError("动效文件已变化")
    result=existing+[{k:v for k,v in s.items() if k not in ("cache_hit","media_sha256")} for s in rendered]
    write(destination,result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    q=sub.add_parser("inspect");q.add_argument("--root")
    q=sub.add_parser("prepare");q.add_argument("edit");q.add_argument("motion");q.add_argument("--output",required=True)
    q=sub.add_parser("render");q.add_argument("project");q.add_argument("edit");q.add_argument("--root");q.add_argument("--chrome",required=True);q.add_argument("--package-root",required=True);q.add_argument("--reviewed-fingerprint",required=True)
    q=sub.add_parser("attach");q.add_argument("project");q.add_argument("edit");q.add_argument("--existing");q.add_argument("--output",required=True);q.add_argument("--select",nargs="+")
    a=p.parse_args()
    try:
        if a.command=="inspect":result=inspect(locate(a.root))
        elif a.command=="prepare":result=prepare(read(a.edit),read(a.motion),a.output,Path(a.motion).resolve().parent)
        elif a.command=="render":result=render(a.project,read(a.edit),locate(a.root),a.chrome,a.package_root,a.reviewed_fingerprint)
        else:result=attach(a.project,read(a.edit),read(a.existing) if a.existing else [],a.output,a.select)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,KeyError,FileNotFoundError,subprocess.CalledProcessError) as error:p.exit(2,str(error)+"\n")


if __name__=="__main__":main()
