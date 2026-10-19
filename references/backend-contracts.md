# 后端与证据契约

## 上游实际能力

`browser-use/video-use` 固定版本的 `helpers/transcribe.py` 将 16kHz mono 音轨上传 ElevenLabs `/v1/speech-to-text`，`model_id=scribe_v1`，需要 API Key。它会查 `.env`/环境变量；本 Skill **不执行或复制该查密路径**。其缓存依视频文件名/轨道，不含内容指纹。本包只导入已有 JSON，以 SHA-256、音轨、语言、适配器版本及完整 payload 标识缓存。

上游没有专用 breath detector。token 间隙及音频事件可辅助定位，需要实际听审；低能量也不等于无意义气声。默认保留未确认候选。英文约 2–3 词的字幕分组不适合直接套中文，本包按汉字宽度、标点、停顿与实际持续时间分组；不拆一个计时 token 伪造字时。过长 token 明确要求人工断句或更细证据。

上游 `edl.json` 是其私有 JSON 约定（sources、ranges、overlays、subtitles 等），不是 CMX3600，也不是任意 NLE 都能导入的 EDL。本包 `edit.json` 为自有版本化删留/映射契约，不伪装行业标准。交付可编辑 Hypit 工程，不承诺 Premiere/剪映/Final Cut 直接导入。

## 模块边界

| 边界 | 输入 → 输出 | 当前实现 |
|---|---|---|
| Transcript | 本地媒体 + 已有 words/tokens → 带指纹转录 | `import_transcript`；无网络、无凭据 |
| Candidate detector | token 序列 → 待听审的 gap 候选 | `candidates`；只 keep，不判断呼吸 |
| Edit decision | 已答 BRIEF、保护区间、确认删除 → time_map/decisions | `make_edit`，原片不改 |
| Cut backend | 精确 CFR 源帧区间 → 粗剪音画 | `roughcut`；FFmpeg，帧数验证 |
| Alignment | 当前 Script、粗剪 domain、当前词时 → NarrativeAlignment | 项目包 `@koubo/reviewed-alignment`；SDK 公开接口，无外部 Need |
| Semantic composition | Selection/Moment → Projection → 绝对 Window/Instant | 原生 Hypit；Caption、卡片和现有素材槽共用关系 |
| Production backend | 工程、operation、显式 Runtime → 执行结果 | `ProductionBackend` Protocol / `HypitBackend` |

新增转录器应实现同等 fingerprint/track/language/provenance 约束，不把账户、费用或上传同意混入 token 数据。新增 Renderer 实现 `invoke(project, operation, runtime)`，保留 check/plan/build 分界和执行状态；不得让纯分析路径调用 build。需要音频降噪/气声衰减时另设可逆处理层，保留原 stem，当前脚本不假称已做。

## 重对齐的真实性

源转录随无变速且完整词保留的剪切，经精确 map 投影到剪后时间：`source-token-evidence-projected-through-exact-cut-map`。这是可验证的几何映射，不是新 ASR，也不证明听感。粗剪实际帧数必须一致；替换媒体、改发音文本、变速会使旧缓存/对齐失效。需用当前粗剪的真实转写或已测量手工标注重新对齐。没有测量则保留未知，不能按字数或估计语速冒充真实词时。

Hypit Script 的中文语义 Token 是单字，但 Scribe 可能只给整词时间。适配器为该整词内字保留**同一个已测量词区间包络**，不线性插值出假字时；显示为词组同步。场景的 Selection/Moment 只建在导入 token 边界，不允许用整词中的某一个字宣称精确触发。要逐字卡点，需更细测量。帧时钟的 round 只作离散量化；小于一帧的 token 报错。

`timing.json` 是 SVRun StoredValue wrapper，必须由 Run 的 value Candidate 显式满足 `timing.timing`。没有 Candidate 的默认 producer 直接报错，没有隐式 ASR。Script 变更会与接受语音文本比对；没有新证据就拒绝继续。`anchors.json` 记录当前 Script digest 与媒体指纹，修改后重新导出。成片仍按 review 重新看、听。

本项目适配包使用 Hypit 公共 SDK，不捆绑 Hypit 源码。0.3.1 是本轮验证范围；其他版本必须先查 vocabulary / check / plan。库的许可不会因为原仓库 MIT 而变成 MIT。
