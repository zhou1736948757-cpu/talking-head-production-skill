# 口播写作、分析与视频制作 Skill

为中文口播视频写稿、改稿，并设计字幕、排版和剪辑方案。根据主题、受众、平台、时长与素材条件选择方法，适合写口播稿、改自然说法、规划画面和审校剪辑；制作分支还可用已有真人素材完成可逆粗剪、Hypit 视频渲染与可编辑工程导出。

## 安装

Skill 名仍是 `write-edit-talking-head`，仓库名为 `talking-head-production-skill`。下载整个目录，保留全部相对路径，不要只复制 SKILL.md。

```bash
git clone https://github.com/zhou1736948757-cpu/talking-head-production-skill.git write-edit-talking-head
cd write-edit-talking-head
python3 -m unittest discover -s tests -v
```

把该文件夹导入支持 Agent Skills 的工具，或放到该工具由你选择的 Skill 目录。仓库不会自动修改全局配置，也不会自动安装其它 Skill。已存在同名目录时先完整备份，再按需合并自定义内容。

| 使用深度 | 需要什么 |
|---|---|
| 写稿、改稿、参考分析、剪辑方案 | 能读取 Skill 的 Agent；无强制 ASR/生成服务 |
| 本地探测、转录导入、可逆粗剪 | Python 3.10+（仅标准库）、FFmpeg、FFprobe；已有实际计时转录 |
| Hypit 原生工程与渲染 | 上述工具、Node >=22.15、Hypit CLI 0.3.1、现有兼容 Chrome、可用且覆盖中文的独立字体文件 |

先检查已装工具。确实缺少 Hypit 时，可从官方 npm 包在当前目录隔离安装，不必全局安装：

```bash
npm install --prefix .tools --ignore-scripts @hypit/hypit@0.3.1
export PATH="$PWD/.tools/node_modules/.bin:$PATH"
hypit --version
```

本轮复用了已有 Hypit 安装；这条从零安装路径、其他操作系统和其他 Hypit 版本尚未端到端实测。若某依赖需要额外准备，按官方文档在项目内处理，不自动开启安装脚本、下载 ASR 模型或连接付费服务。FFmpeg/Chrome 按各自官方发行版准备，字体由当前项目指定并核对许可，不随本仓库分发。

## 使用

将整个仓库作为一个 Skill 导入支持 Agent Skills 的工具，保留 `SKILL.md`、`references/`、`assets/` 和 `agents/` 的相对位置。具体导入入口以所用工具为准。

制作前先从对话提取已知信息，再补问缺少的 **节奏、呼吸/气口/情绪停顿保留程度、必须保留的内容**；已明确的信息不重复问。“保守、标准、紧凑”只作可选例子，没有默认档。用户选择只分析、剪辑方案或实际成片后，按该深度执行。没有真实测量，不按字数估填语音时间。

可直接描述任务，例如：

> 用 write-edit-talking-head 帮我把这段稿改成适合小红书的 60 秒口播，保留必要限定。已有正面人像和两张产品图，请给出字幕排版与切点建议。

需要排版时，先按信息任务查图，再迁移适合当前素材的方法。无需一次加载全部图片；短边 480/720 像素的等比参考图用于查看层级与状态，不作为最终视频素材。WebP 版与已审 PNG 版的尺寸及解码像素完全相同。

## 内容与证据

- 41 条教程视频、282 条方法记录，按视频与时间段追溯
- 225/225 条视觉方法、62/62 条核心视觉子建议已逐项匹配核验；两组存在重叠，不能相加
- 53 个真实回放重绘主例、13 个原创机制图主例，另有 59 张辅助状态图，共 125 张参考图片（无损 WebP）
- 真实回放重绘：根据已核验成片局部的位置、层级与变化关系，使用新人物、物体和文字重绘
- 原创机制图：把文字方法转为说明图，明确标注其身份，不当作原教程的成片截图

从[视觉参考选择指南](references/visual-reference-guide.md)按信息任务查图。每项图例的来源角色、视频时间、适用条件和局限见[真实回放重绘说明](references/visual-reference-cases.md)与[原创机制图说明](references/visual-method-diagrams.md)；方法来源见逐视频证据索引。动态图使用多状态解释已核验变化，单张图不能证明完整节奏或听感。

## 来源与边界

教程出处与具体时间段保留在 [逐视频证据索引](references/corpus-evidence.md)。分析流程参考 [video-analyst](https://github.com/zhou1736948757-cpu/video-analyst/tree/c593460e31bb222310aa56e9b9652eb5471c4dac)。原教程及其中第三方素材的权利归相应权利人所有。

本仓库仅发布原创视觉资产、方法摘要和来源索引，不包含原视频、原始截图或逐字转写稿。教学参数和案例风格需结合条件使用，不保证播放量、留存或转化效果；示例中的外部事实与素材许可需另行核实。

视觉研究采用全长抽帧、接触表与关键区间加密查看，并非逐原帧观看。自动转写用于理解讲解内容，未人工听审全片，不据此保证音色、重音、混音或声效质量。

以下两条未取得视频，未纳入方法推导：
- [BV1fqHx6bESy](https://www.bilibili.com/video/BV1fqHx6bESy/)
- [BV1VNhB6GERp](https://www.bilibili.com/video/BV1VNhB6GERp/)

本仓库沿用建库时选择的 [MIT License](LICENSE)。第三方教程、素材及其权利不因本仓库的许可证而改变。


## 制作能力

完整流程见 [production-workflow.md](references/production-workflow.md)。先沿用已知信息，再问缺少的节奏、呼吸/停顿保留程度和必留内容；保守/标准/紧凑只是可选示例，没有默认档。支持只分析、剪辑方案、实际制作三种深度。

- `scripts/production.py`：现有转录导入、素材 SHA-256、待听审停顿候选、可逆删留表、精确剪后映射、FFmpeg 粗剪、中文断句、Hypit 原生工程导出。
- `assets/hypit-reviewed-alignment/`：独立项目包，用实际词时/精确剪切映射连接 Script、Selection/Moment、NarrativeAlignment 与 Projection；无隐式 ASR。
- `scripts/hypit_backend.py`：可替换的本地执行后端，只接受无凭据的 media/html Runtime，不装依赖、不连接收费服务。
- `scripts/synthetic_demo.py` 和 `tests/`：40 秒非私人合成夹具及行为验证。其声音是按已知时间生成的音调，不能据此声称真人 ASR/呼吸感知已实测。

Python 3.10+、FFmpeg/FFprobe；原生 Hypit 验证范围是 CLI 0.3.1、Node >=22.15 和现有本地 Chrome。项目内隔离依赖，中文字体由当前项目指定，详见制作流程。完整 Skill 不包含依赖缓存、Git 元数据或私人研究档案；不会自动修改全局配置。来源与许可见 [third-party-sources.md](references/third-party-sources.md)，Hypit 是附加条款许可，video-use 是 MIT。

实际运行结果、合成视频验证与未测试边界见 [tests/VALIDATION.md](tests/VALIDATION.md)。


## 快速验证与成片路径

```bash
python3 scripts/production.py questions /path/project/request.json
python3 scripts/synthetic_demo.py /path/demo-output --font /path/chinese-font.ttf
```

第一条仅列出缺少的偏好；不要把测试夹具里的策略套给用户。第二条生成非私人 40 秒动态色条和已知音调，粗剪得到 36 秒，再导出 Hypit 工程；它不会调用 ASR 或生成服务，也不是中文真人语音。

完整的 analyze → plan → roughcut → export → check/plan/build 命令、request/scenes/style 格式和本地 Runtime 配置见 [制作流程](references/production-workflow.md)。生成工程的 `package.json` 声明项目依赖。可在该工程内隔离安装依赖，或用 `scripts/hypit_backend.py PROJECT link-installed --distribution DISTRIBUTION` 复用已有的 0.3.1 安装；依赖缓存和运行结果均不随 Skill 发布。

已验证：22 项 Python 单元测试、6 项原生对齐检查、36 秒 Hypit 实际编码输出、15 帧已有视频槽片段、剪后语义窗口与合成音频信号，以及样式修改后的媒体复用计划。**真实 ASR、自然呼吸检测/自动气声衰减、真人完整听审和 Studio UI 未实测**。词间空隙只是待听审候选，默认保留未确认项；`approved=true` 表示在已确认策略下完成了该项听审，不是凭空认定可删。

## 集成方式与许可

这是独立编写的 Skill、Python 适配器和 Hypit 项目 Author Package；Hypit 本身通过外部依赖安装，未把其整库源码、CLI 或模型捆绑进来。video-use 提供了已有转录格式和剪辑设计的参考，本包不执行其查找 Key/上传 Scribe 的脚本。Huashu／画术未集成，也不是依赖。

本仓库原创代码和既有原创资产使用 [MIT](LICENSE)。Hypit 采用**带附加限制的 Apache 2.0 修改版**，涉及多租户托管、商业分发与标识保留等条件；不能把它当成纯 Apache 2.0 或本仓库 MIT 的一部分。上游完整 [Hypit 许可](references/licenses/Hypit-LICENSE.txt)、[video-use MIT 许可](references/licenses/video-use-LICENSE.txt)、固定版本与接口来源均保留在 [第三方来源](references/third-party-sources.md)。按需要另行审阅依赖许可，发布本 Skill 不授予其它依赖、教程原视频、字体或用户素材的权利。

本次新仓库从已交付的完整 156 文件制作版本整理而来，本地来源提交为 `69cacd8cf175bf50e68b4b8c88fc90e0aeb23d58`；既有方法与图像来自 [koubo_worktable](https://github.com/zhou1736948757-cpu/koubo_worktable) 的公开基线 `e39c33b96403a8c674a4d31d4fa73d61cbfe9692`。新仓库使用独立 Git 历史，仅发布审查后的源码、方法摘要、125 张原创参考图与许可；不携带原仓库历史、私人归档、素材、音视频、字体、运行缓存或本机私人路径。原仓库不受本次发布影响。
