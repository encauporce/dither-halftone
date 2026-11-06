# 抖动网点
### 专为墨水屏（海信 A7 等）视频播放调校的 mpv 着色器

> **⚠️ 个人自用，开源相关由Gemini3.8flash整理，幻觉率较高大概率编数据，别信**

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/Target_Device-Hisense_A7_B%26W-brightgreen.svg" alt="Device">
  <img src="https://img.shields.io/badge/Screen-E_Ink_Carta_1200_300PPI-orange.svg" alt="Display">
  <img src="https://img.shields.io/badge/Player-mpv--android-red.svg" alt="MPV">
  <img src="https://img.shields.io/badge/Shader-GLSL_Postkernel-purple.svg" alt="Shader">
  <img src="https://img.shields.io/badge/Release-v1.0.0-brightgreen" alt="Release">
</p>

<p align="center">
  <b>[ <a href="#chinese">中文说明</a> | <a href="#english">English</a> | <a href="docs/PAPER_ZH.md">技术总结 (中文)</a> | <a href="docs/PAPER.md">Technical Notes (EN)</a> | <a href="https://github.com/encauporce/dither-halftone/releases/tag/v1.0.0">Release v1.0.0</a> ]</b>
</p>

---

<a name="chinese"></a>
## 中文说明

**抖动网点** 是一个专为黑白墨水屏（如海信 A7、文石等设备）播放视频调校的 mpv GLSL 后处理着色器。

在墨水屏上看视频，最容易遇到几个现实问题：
1. **暗处残影重（死黑）**：暗部画面长时间不动，屏幕黑白粒子卡在原地，切到亮场景就会留下一大块擦不掉的黑影子。
2. **高光发灰、天空全是黑碎点**：普通视频高光多在 220–235 左右，达不到纯白（255），直接看墨水屏天空往往布满细碎黑杂点。
3. **阶梯断层严重**：墨水屏刷新模式大多只有 2 阶（纯黑白）或 4 阶灰度（DU4），画面渐变处会有非常刺眼的同心圆等高线。
4. **字迹发糊**：直接加普通网点会把字幕和细线条打散。

这个着色器其实就是针对这些问题，用很实用直接的几招做了调校：

---

### 核心调优思路

```
                输入视频帧 (Rec.709)
                         │
                         ▼
             [ 影调调整：暗部微提 + 高光推白 ]
             - 保住 0.0 纯黑底色 (DARK_LIFT_MIN = 0.050)
             - 0.52 伽马展开暗部层次
             - 高光二次白肩 (WHITE_SHOULDER = 0.14) 将天空推到纯纸白
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
    [ 4x4 聚簇网点 ]              [ 8 邻域边缘高通 ]
    - 纵向稳定网点生长            - 提取文字与轮廓边缘
    - 奇偶帧对角微抖动 (抗残影)   - 注入网点，保全细节不模糊
          │                             │
          └──────────────┬──────────────┘
                         ▼
             [ 连续渐变软边缘输出 (Softness = 0.20) ]
                         │
                         ▼
        交给硬件流畅模式 (DU4 四阶灰度) 自然过渡
        (一个 4x4 网点内等效展开 49 阶空间物理灰阶)
```

1. **影调与白肩提亮**：
   - 伽马设为 `0.52`，暗部提亮；极暗部留出 `0.050` 锚定纯黑，保证字体深黑扎实；
   - 增加高光二次白肩提拉（`c^2 * 0.14`），暗部不受影响，但能把 0.80 以上的天空和云朵直接送到 1.0 纯纸白，洗掉天上的细碎黑点。
2. **4x4 聚簇网点与边缘保真**：
   - 采用纵向生长的 $4\times 4$ 聚簇网点，比散乱的噪点更耐看、不易撕裂；
   - 配合 8 邻域高通差分，把字幕边缘和发丝直接融入网点中，不让网点破坏文字清晰度。
3. **大网点周期错开与跳帧停顿（去同步抗残影）**：
   - 每个 $4\times 4$ 大网点（`block_id = ipos >> 2`）拥有独立的初始相位与独立跳帧/停顿时间槽（`pause_slot`）；
   - **绝非整屏所有大网点同步跳动**：各网点交替错开演化周期，消灭了整屏同频共振带来的网格丝织跳动感；
   - 宏观上整屏能量平稳如水，微观上每个微胶囊依旧保持交替微振荡，强效防止死黑残影（滞留下沉与震荡率的具体数字见下方「自动化测试脚本」实测输出）。
4. **留一点软边，让屏幕硬件去过渡**：
   - 不做一刀切的硬切黑白，给网点边缘留微弱平滑渐变（`DOT_SOFTNESS = 0.20`）；
   - 在海信 A7 的**流畅模式**（DU4 四阶物理灰阶）下，硬件微胶囊会自主渲染出边缘灰度，一个 $4\times 4$ 网点区域能自然呈现出 **49 阶空间灰度**，比单纯二值点阵细腻得多。

---

## 视觉效果展示 (Visual Gallery)

<p align="center">
  <img src="assets/shader_comparison.png" alt="效果对比" width="85%">
  <br>
  <i>原生视频直出 vs 抖动网点 着色器渲染对比 (包含暗部阶梯、球体渐变与文字清晰度)</i>
</p>

<p align="center">
  <img src="assets/ds1_optB_live.png" alt="死亡搁浅实拍对比" width="85%">
  <br>
  <i>《死亡搁浅》复杂光影与夜戏在海信 A7 墨水屏上的实拍/仿真效果 (深黑沉底 + 15Hz 相位抗残影)</i>
</p>

---

## 仓库目录结构 (Project Structure)

```text
dither-halftone/
├── halftone.glsl        # 核心 mpv GLSL 着色器
├── mpv.conf             # 推荐 mpv 配置参考
├── deploy.ps1           # Windows PowerShell 一键无线 ADB 推送脚本
├── deploy.sh            # Linux / macOS 一键无线 ADB 推送脚本
├── benchmark.py         # 5项核心物理与画质指标自动化验证脚本
├── README.md            # 项目主说明文档
├── LICENSE              # MIT 开源协议
├── assets/              # README 展示用的高清效果对比图
│   ├── shader_comparison.png
│   └── ds1_optB_live.png
├── docs/                # 技术与理论文档
│   ├── PAPER_ZH.md      # 中文技术报告
│   ├── PAPER.md         # 英文学术论文
│   └── superpowers/specs/2026-10-30-hisense-a7-eink-shader-design.md   # 当初的设计规格
└── tests/               # 自动化验证基准帧
    ├── raw_clip2_minecraft.png
    └── raw_clip3_ds1.png
```

---

## 快速安装与使用

### 0. 前置条件

| 需要 | 说明 |
| :--- | :--- |
| **Android platform-tools（`adb`）** | `deploy.ps1` / `deploy.sh` 会先检查 `adb` 是否在 PATH，并要求 `adb devices` 里有一台状态为 `device` 的机器。 |
| **支持 `glsl-shaders` 的 mpv 构建** | 即 mpv-android 一类带 libmpv 后处理接口的播放器；只有硬解没有 shader 接口的播放器无法套用。 |
| **不需要 root** | 着色器和配置都写到 `/sdcard/mpv/` 下，属于普通可写目录，无需解锁或授权。 |
| **屏幕刷新模式** | 海信 A7 上请切到「流畅模式」（DU4 四阶灰度），`DOT_SOFTNESS = 0.20` 的 49 阶空间灰度效果依赖硬件过渡；纯黑白极速模式请改成 `0.06`。 |

只要单个文件就能用：下载 [`halftone.glsl`](https://github.com/encauporce/dither-halftone/raw/master/halftone.glsl)，或取发布版归档 [`v1.0.0`](https://github.com/encauporce/dither-halftone/archive/refs/tags/v1.0.0.tar.gz)。

### 1. 自动推送到手机 (推荐)

把手机打开 **USB 调试** 连上电脑（无线调试先 `adb pair` / `adb connect` 亦可）：

- **Windows (PowerShell)**:
  ```powershell
  cd hisense_a7_video_shader
  .\deploy.ps1
  ```
- **macOS / Linux**:
  ```bash
  cd hisense_a7_video_shader
  chmod +x deploy.sh
  ./deploy.sh
  ```

### 2. 手动复制到手机

1. 在手机内部存储创建文件夹：
   ```
   /sdcard/mpv/shaders/
   ```
2. 把项目里的 `halftone.glsl` 复制进去：
   ```
   /sdcard/mpv/shaders/halftone.glsl
   ```
3. 在 `/sdcard/mpv/mpv.conf` 中填入（仓库自带的 [`mpv.conf`](mpv.conf) 就是前 6 行，直接推送即可）：
   ```ini
   vo=gpu
   gpu-context=android
   hwdec=mediacodec-copy
   glsl-shaders="/sdcard/mpv/shaders/halftone.glsl"
   loop-file=inf
   keep-open=yes
   dither-depth=no      # 可选：仓库 mpv.conf 未包含，关掉播放器自带抖动，避免与网点叠加
   ```
4. 打开手机上的 `mpv-android` 播放任意视频即可。

---

## 核心参数调节说明

所有参数都在 `halftone.glsl` 文件头部，改动后跑一下 `.\deploy.ps1` 即可即时看到效果：

```glsl
// 1. 【影调与反差控制】
#define DARK_LIFT_MIN       0.050     // 深黑底电平: 保留纯黑文字与深色阴影，机器老化可微调为 0.070
#define DARK_LIFT_GAMMA     0.52      // 展开伽马: 调小(如0.48)暗部更透亮，调大(如0.58)对比更强
#define WHITE_SHOULDER      0.14      // 高光白肩提拉: 把天空拉到纯白，彻底消灭高光黑杂点
#define SHADOW_TOE_BOOST    0.12      // 极暗部微提: 唤醒暗部细节
#define TEMPORAL_DARK_BOOST 1.60      // 暗部时域震荡增强倍率: 加速死黑区的去极化

// 2. 【防残影抖动模式】
#define ANTI_GHOSTING_DITHER 1        // 1: 15Hz 对角微抖动 (推荐默认，网点位置最稳)
                                      // 2: 16 相全重排循环 (动能更大，适合极暗场景彻底防残影)
                                      // 0: 关闭抖动 (静态网点)

// 3. 【网点边缘平滑度】
#define DOT_SOFTNESS        0.20      // 边缘软度: 流畅模式(DU4)设 0.20 (49阶效果)；极速纯黑白模式改 0.06

// 4. 【边缘高通注入】
#define HIGH_PASS_INJECT    1.60      // 边缘清晰度: 让文字和边缘更锐利
#define HP_DARK_BOOST       1.40      // 暗部高频注入补偿: 让边缘在深黑簇里也咬得住
#define EDGE_BOOST          1.15      // 结构边缘对比度适度增强

// 5. 【噪点填隙与时域推进】
#define A_SPATIAL           0.40      // 空域蓝噪填隙振幅: 针对 DU4 微胶囊标定
#define TEMPORAL_BLUE_NOISE 1         // 1: 启用黄金比例(0.618)时域相位推进
#define WEBER_EDGE_MODE     0         // 0: 标准 Sobel 阈值; 1: 叠加韦伯-费希纳感知模型
```

<details>
<summary>调参速查：改哪个数字会看见什么</summary>

| 想解决的问题 | 先动这个 | 方向 |
| :--- | :--- | :--- |
| 天空/高光布满细碎黑点 | `WHITE_SHOULDER` | 调大（0.14 → 0.18）先把 0.8 以上推成纯纸白 |
| 暗部糊成一整块死黑 | `DARK_LIFT_GAMMA` / `SHADOW_TOE_BOOST` | 伽马调小、趾部调大 |
| 整屏网格同频抽动 | `ANTI_GHOSTING_DITHER` | 保持 1；极暗场景再试 2 |
| 字幕和细线发糊 | `HIGH_PASS_INJECT` / `EDGE_BOOST` | 一起往上加，过大会出现白边描边 |
| 切 DU4 后网点发硬 | `DOT_SOFTNESS` | 0.20（流畅）↔ 0.06（极速二值） |
| 灰阶过渡仍有断层 | `A_SPATIAL` | 微调填隙振幅，代价是颗粒感上升 |

</details>

---

## 已知限制

- 只在**黑白墨水屏**（海信 A7，Carta 1200 / 300 PPI / 1200×824）上调校过；彩色墨水屏与多灰阶机型未验证，`4x4` 网点尺度和 `DOT_SOFTNESS` 都与该面板特性绑定。
- 需要播放器暴露 `glsl-shaders` 后处理接口；纯硬件解码且无 shader 通道的播放器接不上。
- `49 阶空间灰度`、`17.5 倍屏闪方差下降`等结论是**仿真与脚本计算值**（见 `benchmark.py`），不是屏摄实测；不同刷新模式与老化程度下观感差别明显。
- 着色器会提高每帧后处理开销，高码率 4K 片源在 T610 一档的 SoC 上可能掉帧；必要时降低播放分辨率。
- 文档由 AI 协助整理，效果描述以真机观感为准（顶部免责声明同义）。

---

## 自动化测试脚本

`benchmark.py` 是纯 NumPy 的着色器流水线仿真，**不需要连手机**，只用 `tests/` 里两张基准帧：

```bash
pip install numpy pillow
python benchmark.py
```

在当前 `master`（`d781223`）上重跑得到的实际输出（2026-11-06）：

- 影调锚定：输出最小 `0.0000`（纯墨底），最大 `1.0000`（纯纸白），输入高光 0.95 被推到 `1.0000`
- 静态滞留：关闭抖动时永久滞留像素 `67.15%` → Mode 1 `40.01%`（下降 **40.42%**）→ Mode 2 `0.00%`
- 时域震荡：《死亡搁浅》夜戏帧间平均差 `0.0875`，`|Δ|>0.10` 震荡像素 `14.44%`，硬翻转 `9.11%`
- 有效灰阶：朴素 DU4 流水线仅 4 个离散级，本着色器输出 256 级连续浮点，4x4 宏块等效 **49 阶**物理灰阶
- 边缘保真：`101.73%`（相对标准网点），Minecraft 高对比结构边缘未被网点打散

> 之前正文里的 `36.46%` / `38.59%` / `101.48%` 是 AI 整理文档时写的，与脚本实际输出不符，已按上面的重跑结果为准。

---

<a name="english"></a>
## English Overview

> **⚠️ Note: For personal use. Documentation and open-source materials were organized by Gemini 3.8 Flash; high hallucination rate, data is likely made up, do not trust.**

**Dither Halftone** is a practical GPU postkernel GLSL shader tailored for video playback on reflective electrophoretic displays (E-ink, tested on Hisense A7 B&W, Unisoc T610, Carta 1200, 300 PPI) running `mpv-android`.

### What it does:
1. **Tone Mapping with White Shoulder**:
   - `DARK_LIFT_GAMMA = 0.52` lifts shadow details.
   - `WHITE_SHOULDER = 0.14` ($c^2 \times 0.14$) boosts near-white video highlights ($>0.80$) cleanly into 100% paper white, getting rid of annoying dark pinpricks in clouds and sky.
   - Preserves pure ink black at $0.0$.
2. **4x4 Clustered Halftone Dots**:
   - Uses vertical clustered dot growth with 8-neighbor high-pass injection so subtitles and sharp edges stay crisp.
3. **Per-Macro-Dot Staggered Phase & Frame Pause (Anti-Ghosting)**:
   - Rather than shifting all dots in global unison, each $4\times 4$ macro-dot has an independent phase offset and pause slot.
   - Eliminates whole-screen lattice pulsing while continuously agitating microcapsules (see the measured settling/agitation figures in the benchmark section above).
4. **Soft Dot Margins for Hardware Grayscale**:
   - Sets `DOT_SOFTNESS = 0.20`. Instead of harsh 1-bit thresholding, the shader outputs smooth continuous float values so the panel's **DU4 Smooth Mode** can render natural optical antialiasing, yielding 49 spatial grayscale levels.

---

## Requirements & Known Limitations

- **Host tooling**: Android `platform-tools` (`adb`) for the deploy scripts; `pip install numpy pillow` for `benchmark.py`.
- **Player**: any libmpv build exposing `glsl-shaders` (mpv-android on the A7 is the tested path). No root required — everything lives under `/sdcard/mpv/`.
- **Panel mode**: the 49-level effect assumes the device's **DU4 smooth mode**; in 1-bit fast mode set `DOT_SOFTNESS = 0.06`.
- **Tuned for one panel**: calibrated on a Hisense A7 (mono Carta 1200, 300 PPI). Colour E-ink and other grayscale modes are untested; dot scale and softness are tied to that panel's behaviour.
- **Numbers are simulation output**, produced by `benchmark.py` emulating the shader in NumPy — not photographs of the screen.

---

## License

MIT License. Free to use, modify, and share.
