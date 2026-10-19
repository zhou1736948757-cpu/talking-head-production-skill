# 预览和交付验收

先看实际输出，再记录检查结果；无法执行的项写“未运行/未知”和原因。分析结论、代码通过、已构建、已观看是不同事实。

| 检查 | 实际证据 |
|---|---|
| 需求门禁 | 未回答节奏/气口/必留内容时不能删剪；明确答案不重复问；只分析无渲染 |
| 内容 | 否定、数字、单位、限定、必须保留原话在粗剪、脚本、字幕和卡片一致 |
| 呼吸 | 每个删除前后听连续片段，检查词尾、情绪与自然换气，候选未听审则保留 |
| 时间 | 源时间、剪后时间与语义映射可追溯；总帧数、A/V 长度、删除理由齐全 |
| 语义 | 看触发前一帧、触发时、动效途中、落定、离场；字幕/卡片随当前接受稿和粗剪移动 |
| 修改 | 改口播后旧 timing 被拒绝；新测量/映射更新相关锚点；改样式不产生新媒体请求 |
| 中文 | 实际字体含当前字符和标点，无豆腐块，断句保留短语/否定单位，读时足够且无英文 2 词模板 |
| 画面 | 真人素材保持身份，运动全程不遮脸遮字；安全区、素材比例、尾帧无意外黑帧或冻结 |
| 声音 | 完整输出听审，切点无爆音、断词、跳字、音画漂移；合成信号测试不等于真人呼吸验收 |
| 可编辑 | SVML、SVS、SVRun、项目包、当前 assets、指纹与来源一并提供；跨机依赖和字体许可明确 |

有原生 Hypit 运行环境时用 Studio 播放带声音的代表区间；snapshot/FFmpeg 抽帧检查实际编码文件。未运行浏览器预览时不能声称 Studio 验收通过。导出最终 MP4 后再核实编码文件，而不是仅检查中间 roughcut。

合成 smoke test：`python3 scripts/synthetic_demo.py /path/test-output --font /path/chinese-font.ttf`。它造 40 秒动态图和已知 tone windows、两段已知静音、一个保留的低幅信号；粗剪应为 36 秒/1080 帧（30fps）。生成声音不是中文语音，没有真实人物，无隐私输入、ASR 或付费生成。运行测试 `python3 -m unittest discover -s tests -v`，原生 bridge 的语义测试见 `tests/test_alignment.mjs`，命令为 `node tests/test_alignment.mjs /path/project/packages/reviewed-alignment/activation.mjs /path/installed/@hypit/hypit`（使用已装 CLI 同等 loader，仅影响当前进程）。最终报告必须区分合成技术验证和真人质量验证。
