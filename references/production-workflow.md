# 口播制作流程

目录：分流与询问 → 证据与工程 → 本地执行 → 修改与交付。保留原有写稿、改稿、审校及 125 张图的用法。

## 分流与询问

从现有对话取出已明确答案，再补问缺项。例如：“你希望讲述更从容还是更紧凑？自然换气和情绪停顿想保留多少？哪些原话、事实和限定不能删？”可给保守、标准、紧凑作为例子，不替用户选默认档。时长、画幅、字幕密度、参考风格只在缺失且会改变结果时补问。

`analysis` 只探测和分析；`plan` 给剪辑建议与删留表；`produce` 才执行粗剪、工程与渲染。未答完节奏问题仍可读素材、做参考分析；不运行剪辑和渲染。不把例子中的合成夹具策略套给用户。

request.json 的最小内容：

```json
{
  "mode": "produce",
  "pace": "用户已确认的自由描述",
  "pause_policy": "用户已确认的气口与情绪停顿保留要求",
  "must_keep": ["w00012"],
  "protected_ranges": [{"start": 12.0, "end": 15.2}],
  "audio_track": 0,
  "cuts": [{"start": 8.0, "end": 9.0, "action": "delete", "approved": true, "reason": "已听审确认的重复空白；不含气口或词尾"}]
}
```

时间只是字段示例；以当前素材真实探测为准。`must_keep` 是接受稿的 token ID，明确没有可填 `[]`；用户描述的事实、否定词、限定与原话先定位成 ID/保护区间，在 BRIEF 保留原要求。`approved` 表示在用户已确认的策略内，经实际听审确认该候选可删；不表示要求用户逐刀确认。没有 cuts 则保留全片，不从节奏名称推导固定阈值。暂停候选保持为 keep，先听前后文和看嘴形、表情、动作，必要时只降气声而不缩时间（当前脚本不自动降气声）。

## 证据与工程

每个用户项目独立建目录，不在 Skill 或别人的分析归档内输出。

```text
project/
  references/ref-1/{ANALYSIS.md,TIMELINE.md,transcript.json,evidence/}
  BRIEF.md                   # 用户意图、已答/未答、必留内容、实际授权
  TREATMENT.md               # 当前创作方案；参考事实与新方案分开
  request.json
  edit.json                  # 完整 time_map / decisions / source hash
  roughcut.mp4
  hypit-project/
    production.svml          # Script、Projection、字幕、场景、实际输出
    look.svs                 # 配色与字号，独立于表演媒体
    render.svrun             # final.video
    preview.svrun            # main.composition
    timing.json              # 已接受测量，或明确的精确剪切映射
    anchors.json             # 新片语义事件与当前时间，非参考片时间
    assets/                  # 当前真人原片的粗剪、字体、替换槽
    packages/reviewed-alignment/
```

`analyze` 命令只写探测和边界提示，不代替 Agent 逐段分析。需按实际接触表/关键区间/声音补全 ANALYSIS/TIMELINE。现有标准化私人档案可按用户授权查单条，不能整包进入公开仓库，也不能用旧档案声称本次已看片。选用原库图例时必须实际查看像素。

## 无收费服务的执行路径

Python 3.10+ 标准库、FFmpeg/FFprobe。Hypit 制作使用已核验的 CLI 0.3.1（上游固定提交见来源说明）、Node >=22.15、一个本地 Chrome 和支持中文的独立字体文件。先用 `which`/版本检查现有工具。缺依赖时只用官方或知名源装进项目，解释实际缺项；不全局改配置、不查找秘密、不自动安装浏览器或 ASR 模型。字体文件需可用于该项目；共享工程前检查字体许可。`.ttc` 需先导出独立 face，不能假装支持 collection index。

以下命令从 Skill 根目录执行；路径替换为当前项目。首次调用生产参数前先检查 request 的缺项：

```bash
python3 scripts/production.py questions /path/project/request.json
python3 scripts/production.py analyze /path/source.mp4 --transcript /path/existing-scribe.json --output /path/project/references/ref-1
python3 scripts/production.py plan /path/source.mp4 /path/project/references/ref-1/transcript.json /path/project/request.json --output /path/project/edit.json
python3 scripts/production.py roughcut /path/project/edit.json --output /path/project/roughcut.mp4
python3 scripts/production.py export /path/project/edit.json /path/project/roughcut.mp4 --font /path/chinese-font.ttf --scenes /path/project/scenes.json --output /path/project/hypit-project
```

缺转录可以只 `analyze` 不带 `--transcript`，先完成画面证据和工具探测；其后无词时则不能假装完成语义生产。导入现有 Scribe `words`（word/text/start/end/speaker_id）或本包 `tokens`。真实转录须由用户提供或另行授权的本地转写获得；本包绝不调用上游 transcribe.py。

`roughcut` 按片段提取 FFV1/PCM 中间片段，再拼接并编码；picture/audio 共用区间，不用 keyframe `-c copy` 假装精确切词。原片不改动，删留表可改后重跑。拒绝截断词、删保护区间、重叠删除、无理由/未听审删除。VFR 输入先落到指定 CFR（默认 30fps 是工程时钟，不是剪辑档）；量化后再次检查词边界。

scenes.json 把语义区间绑定可替换素材与标题：

```json
[{"id":"proof","first":"w00012","last":"w00019","label":"当前观点","media":"/path/authorized-broll.mp4"}]
```

`media` 可省略，用代码文字卡；当前槽支持已有视频（不自动生成/下载）。图片先按实际持有时长制成静帧视频或在 SVML 用 Image Clip；音效等可在原生工程扩展，不声称脚本自动接入了未实现的槽。素材槽画面采用 contain，保护原有真人画面；做了主次布局后需按 review 验证遮脸和字区。没有足够时长的 B-roll 应显式裁切、hold 或 loop 并验收，不能默默填充。

工程依赖可在工程目录用官方 npm registry 的 `npm install --ignore-scripts` 隔离安装（需网络/权限时按环境规则处理），保留 lockfile。已有安装可离线复用：

```bash
python3 scripts/hypit_backend.py /path/project/hypit-project link-installed --distribution /absolute/installed/@hypit/hypit
```

这只在工程 node_modules 建链接，不复制依赖到 Skill、不改全局安装；移动工程后应重新安装依赖/链接。依赖声明在导出的 package.json，独立适配包随工程提供。

本地 runtime.json（自行填入现有 Chrome/工具绝对路径；不连接任何收费 Endpoint）：

```json
{
  "format":"hypit.runtime-local@1",
  "dataRoot":".hypit/execution",
  "credentials":{},
  "endpoints":{
    "media.local":{"use":"@hypit/media-local"},
    "html.local":{"use":"@hypit/provider-html-local","config":{"chromePath":"/absolute/chrome","workers":1,"browserCapacity":1}}
  },
  "bindings":{}
}
```

```bash
python3 scripts/hypit_backend.py /path/project/hypit-project check --runtime /path/project/hypit-project/runtime.json
python3 scripts/hypit_backend.py /path/project/hypit-project plan --runtime /path/project/hypit-project/runtime.json
python3 scripts/hypit_backend.py /path/project/hypit-project build --runtime /path/project/hypit-project/runtime.json
```

后端设置 `HYPIT_STATE_HOME` 到当前工程 `.hypit/host-state`，只允许本地 media/html Provider 且 credentials 为空。`check` 只验证语法与类型；`plan` 核实剩余工作无转写/生成；`build` 才提交执行。Runtime 如未运行，用当前 Hypit 的 `runtime up --runtime /absolute/runtime.json` 在同一工程启动，保持相同 HYPIT_STATE_HOME；必要时查看 `status/logs`。`--follow` 断开不等于取消，先查 Build 状态再重试。成功 Build 用 `hypit get BUILD_ID --output final.video --to /path/final.mp4` 导出，不能猜测 Build ID。

预览：`hypit studio --run preview.svrun`，使用同一工程/Runtime；`hypit snapshot` 可取语义触发前、触发中、落定及退出的真实帧。Studio/Comments 实际可访问时再交链接；原生工程文件一直保留可编辑。没有运行 Studio 则说明未运行，不把静态示意当预览。

## 修改与交付

- 改口播：先核对接受稿与实际录音，更新 token ID 对应和场景 first/last，重新生成 Script/anchors。只改 SVML 文字但仍用旧 timing 时，本地适配器会报不匹配。换录音用新素材及新转录重新粗剪；`export --final-transcript` 可给当前粗剪的新测量，必须带当前粗剪指纹且与接受稿一致。
- 改剪点：重算 edit 和粗剪、词时映射，再导出；不能沿用旧 domain/alignment。
- 改配色/字号：改 look.svs 或 `--style style.json`，保留粗剪与 timing；在 Run 明确用已有 timing Candidate，检查 plan 无媒体生成。需要跨 Build 保留 Normalize 的结果时，可运行 `python3 scripts/reuse_build.py /path/project/hypit-project ACTUAL_BUILD_ID`，它核对旧结果 timing 和当前工程完全一致后写 reuse.svrun，保留原有 Candidate，选用真实 prepared.media/domain/extent 和 alignment.alignment。用后端 `--run reuse.svrun` 再 plan/build；对齐或素材变化时拒绝复用。不要编造已完成的 Result。
- 换场景素材：替换对应 scenes 槽，重新检查实际纵横比、持续时间与声音。讲述者原素材持续保留，槽默认无声。

交付视频、整个可编辑项目、来源与许可证、删留表/映射/锚点、预览审查记录和实际未运行项。没有真实声音则 ASR、自然呼吸的感知听审均标未实测；可以交合成验证结果，不承诺真人成片已验收。
