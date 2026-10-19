# 来源、固定版本与许可

核验日期：2026-10-19。当前仓库新增 Python/JS 适配脚本按根目录 MIT；下列依赖及第三方素材按各自许可。没有无必要复制上游整库进 Skill。

## Hypit

- 仓库：https://github.com/hypit-ai/hypit
- 固定提交：`dc2b7a8f31b1ef1443a79ca448548d69e3ceb6a0`
- 本轮 CLI：`@hypit/hypit 0.3.1`。原生 `ANALYSIS.md` / `TIMELINE.md`、Script / Selection / Moment、NarrativeAlignment / Projection、SVML/SVS/SVRun 为集成依据。
- 核对的接口：[参考分析](https://github.com/hypit-ai/hypit/blob/dc2b7a8f31b1ef1443a79ca448548d69e3ceb6a0/skills/hypit/references/creation/reference-video.md)、[语义时间](https://github.com/hypit-ai/hypit/blob/dc2b7a8f31b1ef1443a79ca448548d69e3ceb6a0/skills/hypit/references/production/timing.md)、[Run Candidates](https://github.com/hypit-ai/hypit/blob/dc2b7a8f31b1ef1443a79ca448548d69e3ceb6a0/skills/hypit/references/production/runs.md)、[媒体](https://github.com/hypit-ai/hypit/blob/dc2b7a8f31b1ef1443a79ca448548d69e3ceb6a0/skills/hypit/references/production/media.md)、[公开 Author SDK](https://github.com/hypit-ai/hypit/tree/dc2b7a8f31b1ef1443a79ca448548d69e3ceb6a0/examples/minimal-author-package)、[NarrativeTemporal](https://github.com/hypit-ai/hypit/blob/dc2b7a8f31b1ef1443a79ca448548d69e3ceb6a0/packages/narrative-temporal/README.md)、[本地 HTML Provider](https://github.com/hypit-ai/hypit/blob/dc2b7a8f31b1ef1443a79ca448548d69e3ceb6a0/packages/provider-html-local/README.md)。
- 许可是带附加条款的 Apache 2.0 修改版，**不是纯 Apache 2.0/MIT**。上游 LICENSE 原文随附在 `licenses/Hypit-LICENSE.txt`。包括多租户托管、商业分发及标识保留等限制，商业部署/分发前按原许可审阅，不在此替用户作法律结论。本文不重写其条款。

## browser-use/video-use

- 仓库：https://github.com/browser-use/video-use
- 固定提交：`43cfc566833548093455c9d4a46bd69913b7e552`
- 核对：[Skill](https://github.com/browser-use/video-use/blob/43cfc566833548093455c9d4a46bd69913b7e552/SKILL.md)、[Scribe 上传接口与缓存](https://github.com/browser-use/video-use/blob/43cfc566833548093455c9d4a46bd69913b7e552/helpers/transcribe.py)、[字幕及私有 JSON 渲染](https://github.com/browser-use/video-use/blob/43cfc566833548093455c9d4a46bd69913b7e552/helpers/render.py)。
- MIT，版权 © 2026 Browser Use；原文随附在 `licenses/video-use-LICENSE.txt`。本包借鉴可逆删留、word-timestamp 导入及字幕末层处理思想，独立实现中文及指纹适配；未复制上游查密/上传脚本。
- 此项目属于 browser-use 组织，不等于已安装或实测浏览器自动化服务。网页证据/录屏可用当前 Hypit `capture screenshot/run` 的实际接口或现有可用浏览器工具，必须查看真实页面并标明执行范围，不能虚构网站状态。原生 capture 使用现有 Chrome 时需显式指定 browser/channel；录屏要求 Chrome 153+，这不意味着本轮已实测网页录屏。

## 现有参考库与输入

保留原仓库 41 片/282 方法、125 张原创重绘/机制图及完整来源索引。用户提供的 Hypit 官方参考 ZIP、标准化参考档案和六例 SAMPLES 用于核验集成；其中私人归档报告留在仓库外，本分支不公开它们。旧档案中缺原始视频/台词/词时的项不因集成而补成已知。图像不因保留而声称本轮重新逐图视觉验收。
