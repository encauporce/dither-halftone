//!HOOK POSTKERNEL
//!BIND HOOKED
//!DESC Hisense A7 E-ink Video Enhancer: Option B Deep Ink + Fixed Halftone + Scheme 2 High-Pass Injection

// ============================================================================
// 🛠️【海信 A7 墨水屏核心着色器参数调优区】
// ============================================================================
// 1. 【曲线与反差控制 (Option B 纯黑高反差基底 + 亮场高光白底映射)】
#define DARK_LIFT_MIN       0.050     // 深墨底电平 (12.8/255)：恢复 Option B 纯黑基底，深邃硬朗
#define DARK_LIFT_GAMMA     0.52      // 影调展开伽马 (0.52)：从 0.60 优化调低，整体释放中高光通透感
#define WHITE_SHOULDER      0.14      // 高光肩部提拉增益 (0.14)：让视频中的高光与白场释放纯净纸白 (让白色更白)
#define SHADOW_TOE_BOOST    0.12      // 极暗部平滑趾部提拉：在 [0, 20] 极暗区间稳步释放层次
#define TEMPORAL_DARK_BOOST 1.60      // 暗部时域震荡增强倍率

// 2. 【垂直正交固定网点 + 动态时域消残影】
#define ANTI_GHOSTING_DITHER 1        // 1: 启用 15Hz 交替对角相位微震颤 (保持网点固定形态，消微胶囊残影)

// 3. 【4x4 聚簇消残影大网点核心 (固定生长结构)】
#define DOT_SOFTNESS        0.06      // Option B 原版 0.06：反差强劲，聚簇分明

// 4. 【时域黄金比例蓝噪小网点 (无缝连续插值微步)】
#define A_SPATIAL           0.65      // 小网点填隙微步振幅 (覆盖 1/16 阶梯，抹平阶梯感)
#define TEMPORAL_BLUE_NOISE 1         // 1: 启用黄金比例(0.618)时域相位推进，彻底杜绝谐波闪烁

// 5. 【方案 2：高频差分预注入大网点 (High-Pass Halftone Injection)】
#define HIGH_PASS_INJECT    1.60      // 高频细节注入增益 (1.60)：使微弱暗部细线直接穿透 4x4 大网点
#define HP_DARK_BOOST       1.40      // 暗部高频注入补偿倍率 (1.40)：随亮度降低增强穿透力
#define WEBER_EDGE_MODE     0         // 方案 2 纯大网点注入测试：0 为基准 Sobel，细节全由网点消化；1 为与韦伯结合
#define EDGE_BOOST          1.15      // 强边缘对比度适度增强
// ============================================================================

// 采样指定位置的感知亮度 (ITU-R BT.709)
float get_luma_at(vec2 pos) {
    vec4 c = HOOKED_tex(pos);
    return dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
}

// 4x4 经典印刷聚簇大网点矩阵 (16 阶垂直正交固定结构)
float get_macro_threshold(ivec2 p) {
    const float m[16] = float[16](
        12.0,  8.0,  9.0, 13.0,
         7.0,  0.0,  1.0,  5.0,
         6.0,  2.0,  3.0,  4.0,
        11.0, 10.0, 14.0, 15.0
    );
    return (m[p.y * 4 + p.x] + 0.5) / 16.0;
}

// 黄金比例低差异时空蓝噪 (Golden Ratio Temporal IGN)
float ign_temporal_dither(vec2 p, float t) {
    vec3 magic = vec3(0.06711056, 0.00583715, 52.9829189);
    #if TEMPORAL_BLUE_NOISE == 1
        float t_offset = fract(t * 0.6180339887);
    #else
        float t_offset = 0.0;
    #endif
    return fract(magic.z * fract(dot(p, magic.xy) + t_offset));
}

vec4 hook() {
    vec2 pt = HOOKED_pt;
    vec2 pixel_coord = HOOKED_pos / pt;
    ivec2 ipos = ivec2(floor(pixel_coord));

    // 1. 空间邻域亮度采样 (3x3 窗口)
    float c  = get_luma_at(HOOKED_pos);
    float tl = get_luma_at(HOOKED_pos + vec2(-pt.x, -pt.y));
    float t  = get_luma_at(HOOKED_pos + vec2( 0.0,  -pt.y));
    float tr = get_luma_at(HOOKED_pos + vec2( pt.x, -pt.y));
    float l  = get_luma_at(HOOKED_pos + vec2(-pt.x,  0.0));
    float r  = get_luma_at(HOOKED_pos + vec2( pt.x,  0.0));
    float bl = get_luma_at(HOOKED_pos + vec2(-pt.x,  pt.y));
    float b  = get_luma_at(HOOKED_pos + vec2( 0.0,   pt.y));
    float br = get_luma_at(HOOKED_pos + vec2( pt.x,  pt.y));

    // 2. 高频差分计算 (8 邻域均值残差)
    float mean_neighbor = (tl + t + tr + l + r + bl + b + br) / 8.0;
    float high_pass = c - mean_neighbor;

    // 3. Option B 原版暗部非线性展开 + 极暗部专属趾部提拉 + 亮场肩部增白
    float toe = sqrt(c) * pow(1.0 - c, 2.0) * SHADOW_TOE_BOOST;
    float shoulder = pow(c, 2.0) * WHITE_SHOULDER;
    float norm_curve = clamp(pow(c, DARK_LIFT_GAMMA) + toe + shoulder, 0.0, 1.0);
    float luma_lifted = DARK_LIFT_MIN + (1.0 - DARK_LIFT_MIN) * norm_curve;

    // 4. 垂直正交固定网点 + 15Hz 全局交替消残影
    ivec2 in_block = ipos & 3;
    ivec2 shift_vec = ivec2(0, 0);
    #if ANTI_GHOSTING_DITHER == 1
        if (int(mod(float(frame), 2.0)) == 1) {
            shift_vec = ivec2(2, 2);
        }
    #endif

    ivec2 p_macro = (in_block + shift_vec) & 3;
    float th_macro = get_macro_threshold(p_macro);

    // 5. 时域正交黄金比例蓝噪微网点 (色阶无缝连续插值)
    float step_16 = 1.0 / 16.0;
    float noise_val = ign_temporal_dither(pixel_coord, float(frame)) - 0.5;

    float dark_boost = 1.0 + TEMPORAL_DARK_BOOST * (1.0 - luma_lifted);
    float bright_taper = smoothstep(0.96, 0.72, luma_lifted);
    float fine_dither = noise_val * step_16 * A_SPATIAL * dark_boost * bright_taper;

    // 6. 【方案 2 核心：高频细节预注入大网点】
    // 高频差分 high_pass 直接调变 target_luma，使 4x4 网点内部单像素根据微弱细节自适应增减面积
    float hp_gain = HIGH_PASS_INJECT * (1.0 + HP_DARK_BOOST * (1.0 - luma_lifted));
    float target_luma = clamp(luma_lifted + fine_dither + high_pass * hp_gain, 0.0, 1.0);

    // 7. 原版 Option B 聚簇大网点生成 (固定生长，深黑 0.0 直出)
    float dot_val = clamp(0.5 + (target_luma - th_macro) / DOT_SOFTNESS, 0.0, 1.0);

    // 8. 边缘 Sobel 判定与过渡
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
