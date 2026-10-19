# Huashu：语义驱动的可选短动效

目录：选择与协作 → 版本和许可 → 使用 → 修改与验收。先保留用户已确认的节奏、气口、必留内容；不把一个新引擎变成所有句子的默认特效。

## 何时用哪条路径

| 当前内容 | 选择 | 与原片的关系 |
|---|---|---|
| 普通讲述、自然气口、基础字幕、已有 B-roll | 原有 Hypit 路径 | 真人音画与字幕持续，不需要 Huashu |
| 已有截图/产品资料，需要解释一个功能或关系 | Huashu `t2_keynote_ui` 短图卡 | 现有素材优先；镜头窗口由当前内容决定，避免遮脸 |
| 因果/步骤/结构需要逐步揭示 | Huashu `y3_whiteboard` | 保持对象关系，完整清单读时从最后一项呈现完起计算 |
| 少量重点词或章节落点 | Huashu `y5_kinetic_type` | 避免重复基础字幕，不整片逐句砸字 |
| 完整艺术动画、角色生帧、复杂图表、其它 Huashu 语法 | 单独创作任务/当前不自动接入 | 需新的材料与具体方案；不因此改变真人口播或自动调用服务 |

Hypit 持有原声、剪后 domain、Script/Selection/Moment、字幕和总片长。Huashu 只接收明确选择的短语义窗口，输出**无声片段**；回到 Hypit 时仍用相同 token 的 Selection/Moment 触发。气口与切点不由 Huashu 再剪一遍。只写改稿、分析不加载此后端。剪辑方案可以 prepare 供审阅，但 render 只接受已确认的 produce。

新风格方向有实质取舍时展示可比较方案；已确认方向直接沿用，不重复问。已有真实素材不被示范人物、AI 人物或几何角色替换。每个片段说明信息目的、主体和动作；允许大段真人稳定画面。

## 准确版本与执行边界

本轮选择用户本机 `huashu-art-motion` 的主安装副本；另一个 Codex 副本的 Skill 和渲染器哈希不同。只探测常见的具名安装位置或用户给出的 `--root`，不搜索无关私有目录、不读取声音配置或凭据。

```bash
python3 scripts/huashu_backend.py inspect --root /path/huashu-art-motion
```

inspect 不执行上游代码，返回身份、许可、支持接口与内容指纹。先读该根目录 SKILL.md、09/12 号指南、被选语法卡、相关 clip runtime 和许可，核对来源后才把审阅所得 `engine_fingerprint` 传给 render；内容变动则拒绝执行。它是版本确认，不代替代码审阅或操作系统权限。不要把含本地绝对路径的 inspect/运行输出提交公开仓库。

本地/公开上游 LICENSE 是 MIT，完整通知随附；字体另有许可。这个仓库提供独立适配，不复制引擎/样例/字体，也不自动安装 Huashu。缺少它时原有路径仍可用。渲染器需要 Node、已有 `puppeteer-core`（本轮复用 Hypit 0.3.1 安装中的版本）、FFmpeg/FFprobe 和显式 Chrome 路径；缺包只报告，安装需按当前项目隔离处理，不能自动改全局设置。

本适配没有运行上游 Python render.py/qa.py/deliver.py，没有打开其可选声音或图片服务。独立 Node 执行器只服务 clip runtime 与显式本地图片，限制本地文件范围并拦截所有外部浏览器请求，使用独立 Chrome 会话；不使用放宽浏览器安全的参数。评估未知安装后再运行；指纹变化先审阅，不静默接受新代码。

## 语义计划与运行

motion.json 的时间都用**当前剪后 token ID**，不能填写来源秒数。示例 ID 必须替换为真实 edit 的 token。具体语法、色板、片段尺寸和画面位置明确选择，不给默认视觉档：

```json
{
  "purpose":"解释这段产品功能，不重复口播基础字幕",
  "clips":[{
    "id":"product-proof",
    "grammar":"t2_keynote_ui",
    "theme":"paper",
    "first":"w00012","last":"w00019",
    "size":[360,640],
    "frame":[0.03,0.03,0.97,0.77],
    "safe":{"top":12,"bottom":12,"left":16,"right":16},
    "cues":[
      {"token":"w00012","kind":"card","text":"具体功能","sub":"已核验的说明","image":"product.png"},
      {"token":"w00016","kind":"card","text":"另一个重点","data":{"icon":"check"}}
    ]
  }]
}
```

图片相对 motion.json，prepare 会检查为当前明确提供的本地文件；不下载 URL，不生成替代物。使用图片前实际查看像素和权利。没有图片就省略 image，用代码图卡。当前适配不接受角色帧库、任意顶层 data 或其它未审阅语法；它不是全量 Huashu API 透传。

`size` 是片段的像素尺寸；`frame` 是 Hypit 主画幅内的归一化 `[left,top,right,bottom]`，必须按实际真人位置和字幕区审查，示例框不是默认安全区。内部 `safe` 是 Huashu 画布的像素留白，不能替代主片的遮脸/遮字审查。素材按 contain 放入，原 A-roll 和音轨保留。`number` 的 at 代表**落定**，用 `timing:"settle"` 并保证至少0.9秒前置空间；其余 cue 是初次揭开。不要把落定误当动画起点。

白板另须明确 `pen:"hidden"` 或 `pen:"original"`。本轮独立逐帧审查发现原装饰笔退场时短暂遮住已写文字；`hidden` 只在独立浏览器会话内关闭装饰笔，保留逐笔揭示，不改外部安装。示例验证采用 hidden，original 须另看片确认遮挡，不能声称已通过此示例验收。

```bash
python3 scripts/huashu_backend.py prepare /path/project/edit.json /path/project/motion.json --output /path/project/motion-output
python3 scripts/huashu_backend.py render /path/project/motion-output /path/project/edit.json --root /path/huashu-art-motion --chrome /path/chrome --package-root /path/installed-hypit --reviewed-fingerprint REVIEWED_HASH
python3 scripts/huashu_backend.py attach /path/project/motion-output /path/project/edit.json --existing /path/project/scenes.json --select product-proof --output /path/project/scenes-with-motion.json
python3 scripts/production.py export /path/project/edit.json /path/project/roughcut.mp4 --font /path/chinese-font.ttf --scenes /path/project/scenes-with-motion.json --output /path/project/hypit-project
```

再走原有 Hypit check/plan/build/导出与复看流程。空 label 的媒体槽不额外创建重复标题；现有场景和声音不被 attach 删除。场景 ID 冲突需明确修改该项。多个备选在同一时间和画面位置时不能全部叠加，用 `--select` 选实际采用的项。

prepare 把接受词时量化到当前帧时钟：局部 at = 剪后 token 帧 − 窗口起帧；duration = 窗口总帧数/fps，范围1帧至8秒。长段拆成有实际信息事件的镜头，不加速口播以迁就引擎。剪点、台词或录音变动后 edit/token 摘要变化，旧动效工程拒绝 attach/render；先重新对齐并 prepare。改颜色/文字样式只重渲对应图形片段，原人物媒体不重请求。

缓存包含本地引擎指纹、spec、当前图片内容指纹、适配版本和渲染器内容指纹；相同输入复用文件。输出音频应为空且实际帧数必须一致。生成 spec、qa、收据和本地依赖信息留在用户项目，工程仍可编辑；不上传私人路径或素材。

## 无私人素材的复现示例

先按原流程运行 `synthetic_demo.py OUTPUT --font FONT`；它只创建动态测试图和人工计时音调，没有真实语音。随附 [huashu-motion-example.json](../assets/huashu-motion-example.json) 使用该夹具的 p2 token，三段是同一窗口的备选，不是三个同时叠加的镜头。复制到自选项目后，用上面的 prepare/render 命令，attach 时明确 `--select feature`；保留现有 review 场景，示例原 meaning 文字卡作为被替换项由夹具作者明确移除。其它用户素材须换成真实 token、片段选择和已审阅的画面位置，不沿用示例策略。

## 验收与实际测试边界

独立 QA 记录了重复时刻像素一致、采样帧变化、浏览器错误/缺字/外部请求、帧数和无声轨。还要看片段和主片的触发前、动画中、落定、离场，核对文字、脸与字幕、完整清单读时、数字/单位及原声。没有听真实口播就不能称呼吸/声画感知验收通过。

本轮实际运行的语法、主片合成、缓存与独立审查见 [VALIDATION.md](../tests/VALIDATION.md)。这些独立检查不等于通过上游 qa.py 的全部确定性/效率/动感/流畅/框景评分，更不等于上游 deliver.py 的完整成片门禁。上游原生 QA/交付脚本、其它5种可渲语法、第9种讲解员指南、透明 ProRes、真人身份/语音生成不在本适配实测范围。后续若需要其原生流程，先按所选版本审阅依赖、代码和输出，再单列验证，不凭本次结果作保证。
