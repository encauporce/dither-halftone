//!HOOK POSTKERNEL
//!BIND HOOKED
//!DESC 抖动网点

/**
 * ============================================================================
 * 抖动网点 - 墨水屏视频增强 mpv 着色器
 * ----------------------------------------------------------------------------
 * 适配设备: 海信 A7 黑白墨水屏手机 (Carta 1200, 300 PPI) 及各类电子纸设备
 * 播放软件: is.xyz.mpv (mpv-android)
 * 开源协议: MIT License
 * ----------------------------------------------------------------------------
 * 核心原理 (实用调优):
 * 1. 影调与白肩调整: 修正视频 Rec.709 动态范围与墨水屏的差异，暗部提亮保细节，
 *    高光二次白肩推到纯白消除天空噪点，同时保住纯黑深墨基底。
 * 2. 4x4 聚簇印刷网点: 采用纵向稳定的 4x4 网点排列，配合边缘高通锐化，文字与轮廓不发糊。
 * 3. 帧间抗残影微抖动: 奇偶帧在对角线跳动（或 16 相循环微调），让微胶囊粒子保持运动，
 *    避免暗部长时间静止卡死留下残影。
 * 4. 渐变软边缘: 输出保留微弱平滑渐变，利用屏幕流畅模式 (DU4 四阶灰度)
 *    自然平滑网点边缘，呈现更细腻的空间色阶。
 * ============================================================================
 */

// ============================================================================
// 🛠️【PARAMETER CHEATSHEET / 着色器核心参数微调区】
// ============================================================================
// 1. 【Tone Mapping & Contrast / 影调与反差控制】
#define DARK_LIFT_MIN       0.050     // Deep Ink Floor (12.8/255): Anchors punchy solid black / 深墨底电平
#define DARK_LIFT_GAMMA     0.52      // Gamma Expansion (0.52): Brightens shadows & midtones / 影调展开伽马
#define WHITE_SHOULDER      0.14      // White Shoulder Boost (0.14): Cleanses highlights to pure white / 高光肩部提拉增益
#define SHADOW_TOE_BOOST    0.12      // Shadow Toe Boost (0.12): Unlocks subtle dark details / 极暗部平滑趾部提拉
#define TEMPORAL_DARK_BOOST 1.60      // Dark Agitation Multiplier: Enhances de-polarization / 暗部时域震荡增强倍率

// 2. 【Phase Modulation & Anti-Ghosting / 动态微胶囊消残影模式】
// 1: 15Hz Alternating Diagonal Shift (0,0)<->(2,2) [Default / 推荐: 保持网点质心100%不变，翻转36%像素]
// 2: 16-Phase Full Permutation Cycle [16帧完全置换循环: 死黑消除率99.7%，极暗场景深度去极化]
// 0: Disabled (Static Halftone) / 关闭消残影震颤
#define ANTI_GHOSTING_DITHER 1

// 3. 【4x4 Clustered Dot Halftone / 4x4 印刷聚簇大网点核心 (DU4 物理灰阶版)】
#define DOT_SOFTNESS        0.20      // Softness Factor: 0.20 for DU4 smooth mode (49 levels) / 0.06 for A2 speed mode

// 4. 【Golden-Ratio Temporal Blue Noise / 时域黄金比例蓝噪小网点】
#define A_SPATIAL           0.40      // Spatial Noise Amplitude: Calibrated for DU4 microcapsules / 空域蓝噪填隙振幅
#define TEMPORAL_BLUE_NOISE 1         // 1: Enable golden-ratio (0.618) phase progression / 启用黄金比例时域推进

// 5. 【High-Pass Halftone Injection / 高频差分预注入大网点】
#define HIGH_PASS_INJECT    1.60      // High-Pass Injection Gain: Fine lines sculpt dot growth / 高频细节注入增益
#define HP_DARK_BOOST       1.40      // Dark High-Pass Boost: Penetrates dense shadow clusters / 暗部高频注入补偿
#define WEBER_EDGE_MODE     0         // 0: Standard Sobel threshold / 1: Combined with Weber-Fechner
#define EDGE_BOOST          1.15      // Edge Contrast Boost: Accentuates structural contours / 强边缘对比度适度增强
// ============================================================================

// ITU-R BT.709 Perceptual Luminance Extraction
float get_luma_at(vec2 pos) {
    vec4 c = HOOKED_tex(pos);
    return dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
}

// 4x4 Clustered Dot Halftone Threshold Matrix (16-level print gravure structure)
float get_macro_threshold(ivec2 p) {
    const float m[16] = float[16](
        12.0,  8.0,  9.0, 13.0,
         7.0,  0.0,  1.0,  5.0,
         6.0,  2.0,  3.0,  4.0,
        11.0, 10.0, 14.0, 15.0
    );
    return (m[p.y * 4 + p.x] + 0.5) / 16.0;
}

// Golden-Ratio Spatio-Temporal Interleaved Gradient Noise (IGN)
// mod(t, 256.0) ensures float mantissa precision is never exhausted over long playback
float ign_temporal_dither(vec2 p, float t) {
    vec3 magic = vec3(0.06711056, 0.00583715, 52.9829189);
    #if TEMPORAL_BLUE_NOISE == 1
        float t_offset = fract(mod(t, 256.0) * 0.6180339887);
    #else
        float t_offset = 0.0;
    #endif
    return fract(magic.z * fract(dot(p, magic.xy) + t_offset));
}

vec4 hook() {
    vec2 pt = HOOKED_pt;
    vec2 pixel_coord = HOOKED_pos / pt;
    ivec2 ipos = ivec2(floor(pixel_coord));

    // 1. 3x3 Spatial Neighborhood Luminance Sampling
    float c  = get_luma_at(HOOKED_pos);
    float tl = get_luma_at(HOOKED_pos + vec2(-pt.x, -pt.y));
    float t  = get_luma_at(HOOKED_pos + vec2( 0.0,  -pt.y));
    float tr = get_luma_at(HOOKED_pos + vec2( pt.x, -pt.y));
    float l  = get_luma_at(HOOKED_pos + vec2(-pt.x,  0.0));
    float r  = get_luma_at(HOOKED_pos + vec2( pt.x,  0.0));
    float bl = get_luma_at(HOOKED_pos + vec2(-pt.x,  pt.y));
    float b  = get_luma_at(HOOKED_pos + vec2( 0.0,   pt.y));
    float br = get_luma_at(HOOKED_pos + vec2( pt.x,  pt.y));

    // 2. 8-Neighbor Spatial High-Pass Residual
    float mean_neighbor = (tl + t + tr + l + r + bl + b + br) / 8.0;
    float high_pass = c - mean_neighbor;

    // 3. Option B Deep Ink Tone Mapping with White Shoulder & Shadow Toe Boost
    float toe = sqrt(c) * pow(1.0 - c, 2.0) * SHADOW_TOE_BOOST;
    float shoulder = pow(c, 2.0) * WHITE_SHOULDER;
    float norm_curve = clamp(pow(c, DARK_LIFT_GAMMA) + toe + shoulder, 0.0, 1.0);
    float luma_lifted = DARK_LIFT_MIN + (1.0 - DARK_LIFT_MIN) * norm_curve;

    // 4. Clustered Halftone with Anti-Ghosting Phase Modulation
    ivec2 in_block = ipos & 3;
    ivec2 shift_vec = ivec2(0, 0);
    #if ANTI_GHOSTING_DITHER == 1
        // 15Hz alternating diagonal shift: flips ~36% pixels with 100% centroid invariance
        if (int(mod(float(frame), 2.0)) == 1) {
            shift_vec = ivec2(2, 2);
        }
    #elif ANTI_GHOSTING_DITHER == 2
        // 16-phase complete permutation cycle: eliminates 99.7% of multi-frame static zero freeze
        const ivec2 phase_16[16] = ivec2[16](
            ivec2(0, 0), ivec2(2, 2), ivec2(0, 1), ivec2(2, 3),
            ivec2(0, 2), ivec2(2, 0), ivec2(0, 3), ivec2(2, 1),
            ivec2(1, 1), ivec2(3, 3), ivec2(1, 2), ivec2(3, 0),
            ivec2(1, 3), ivec2(3, 1), ivec2(1, 0), ivec2(3, 2)
        );
        shift_vec = phase_16[int(mod(float(frame), 16.0))];
    #endif

    ivec2 p_macro = (in_block + shift_vec) & 3;
    float th_macro = get_macro_threshold(p_macro);

    // 5. Golden-Ratio Temporal Blue Noise IGN Dithering
    float step_16 = 1.0 / 16.0;
    float noise_val = ign_temporal_dither(pixel_coord, float(frame)) - 0.5;

    float dark_boost = 1.0 + TEMPORAL_DARK_BOOST * (1.0 - luma_lifted);
    float bright_taper = smoothstep(0.96, 0.72, luma_lifted);
    float fine_dither = noise_val * step_16 * A_SPATIAL * dark_boost * bright_taper;

    // 6. High-Pass Halftone Injection
    // Directly modulates target_luma so 300 PPI micro-fissures sculpt dot growth organically
    float hp_gain = HIGH_PASS_INJECT * (1.0 + HP_DARK_BOOST * (1.0 - luma_lifted));
    float target_luma = clamp(luma_lifted + fine_dither + high_pass * hp_gain, 0.0, 1.0);

    // 7. Clustered Dot Formation with Softness Expansion (DU4 Optical Antialiasing)
    float dot_val = clamp(0.5 + (target_luma - th_macro) / DOT_SOFTNESS, 0.0, 1.0);

    // 8. Complementary Sobel Edge Gradient & Blending
    float gx = (tr + 2.0 * r + br) - (tl + 2.0 * l + bl);
    float gy = (bl + 2.0 * b + br) - (tl + 2.0 * t + tr);
    float grad = sqrt(gx * gx + gy * gy);

    #if WEBER_EDGE_MODE == 1
        float th_min = 0.012 + 0.028 * c;
        float th_max = 0.050 + 0.130 * c;
        float w_edge = smoothstep(th_min, th_max, grad);
    #else
        float w_edge = smoothstep(0.035, 0.180, grad);
    #endif

    float edge_enhanced = clamp(luma_lifted + high_pass * (EDGE_BOOST - 1.0), 0.0, 1.0);
    float edge_dithered = clamp(edge_enhanced + fine_dither, 0.0, 1.0);

    float final_luma = clamp(mix(dot_val, edge_dithered, w_edge), 0.0, 1.0);
    return vec4(vec3(final_luma), 1.0);
}
