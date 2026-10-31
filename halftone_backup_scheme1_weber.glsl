//!HOOK POSTKERNEL
//!BIND HOOKED
//!DESC Hisense A7 E-ink Video Enhancer: Option B Deep Ink + Fixed Halftone + Weber Dark Detail Engine

// ============================================================================
// 🛠️【海信 A7 墨水屏核心着色器参数调优区】
// ============================================================================
// 1. 【暗部曲线控制 (Option B 纯黑高反差基底)】
#define DARK_LIFT_MIN       0.050     // 深墨底电平 (12.8/255)：恢复 Option B 纯黑基底，深邃硬朗
#define DARK_LIFT_GAMMA     0.60      // 暗部非线性展开伽马 (0.60)：压制浮灰白雾感，凝聚光影反差
#define SHADOW_TOE_BOOST    0.12      // 极暗部平滑趾部提拉：在 [0, 20] 极暗区间稳步释放层次
#define TEMPORAL_DARK_BOOST 1.60      // 暗部时域震荡增强倍率

// 2. 【垂直正交固定网点 + 动态时域消残影】
#define ANTI_GHOSTING_DITHER 1        // 1: 启用 15Hz 交替对角相位微震颤 (保持网点固定形态，消微胶囊残影)

// 3. 【4x4 聚簇消残影大网点核心 (固定生长结构)】
#define DOT_SOFTNESS        0.06      // Option B 原版 0.06：反差强劲，聚簇分明

// 4. 【时域黄金比例蓝噪小网点 (无缝连续插值微步)】
#define A_SPATIAL           0.65      // 小网点填隙微步振幅 (覆盖 1/16 阶梯，抹平阶梯感)
#define TEMPORAL_BLUE_NOISE 1         // 1: 启用黄金比例(0.618)时域相位推进，彻底杜绝谐波闪烁

// 5. 【方案 1：暗部相对对比度自适应保护 (韦伯-费希纳 Sobel，彻底提升暗部分辨率)】
#define WEBER_EDGE_MODE     1         // 1: 开启韦伯相对对比度自适应检测，拯救暗部细线与微弱纹理
#define EDGE_BOOST          1.15      // 边缘对比度适度增强
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

    // 1. 空间邻域亮度采样
    float c  = get_luma_at(HOOKED_pos);
    float tl = get_luma_at(HOOKED_pos + vec2(-pt.x, -pt.y));
    float t  = get_luma_at(HOOKED_pos + vec2( 0.0,  -pt.y));
    float tr = get_luma_at(HOOKED_pos + vec2( pt.x, -pt.y));
    float l  = get_luma_at(HOOKED_pos + vec2(-pt.x,  0.0));
    float r  = get_luma_at(HOOKED_pos + vec2( pt.x,  0.0));
    float bl = get_luma_at(HOOKED_pos + vec2(-pt.x,  pt.y));
    float b  = get_luma_at(HOOKED_pos + vec2( 0.0,   pt.y));
    float br = get_luma_at(HOOKED_pos + vec2( pt.x,  pt.y));

    // 2. 【方案 1：暗部相对对比度自适应 Sobel (彻底解决暗色分辨率退化)】
    float gx = (tr + 2.0 * r + br) - (tl + 2.0 * l + bl);
    float gy = (bl + 2.0 * b + br) - (tl + 2.0 * t + tr);
    float grad = sqrt(gx * gx + gy * gy);

    // 韦伯定律自适应阈值：暗部 (c接近0) 阈值自动缩紧至 [0.012, 0.050]，敏锐捕获暗部微弱纹理；
    // 亮部 (c接近0.8) 阈值自动平滑恢复至 [0.035, 0.154]，平坦区绝不误触发。
    #if WEBER_EDGE_MODE == 1
        float th_min = 0.012 + 0.028 * c;
        float th_max = 0.050 + 0.130 * c;
        float w_edge = smoothstep(th_min, th_max, grad);
    #else
        float w_edge = smoothstep(0.035, 0.180, grad);
    #endif

    // 3. 【Option B 原版暗部非线性展开 + 极暗部专属趾部提拉】
    float toe = sqrt(c) * pow(1.0 - c, 2.0) * SHADOW_TOE_BOOST;
    float norm_curve = clamp(pow(c, DARK_LIFT_GAMMA) + toe, 0.0, 1.0);
    float luma_lifted = DARK_LIFT_MIN + (1.0 - DARK_LIFT_MIN) * norm_curve;

    // 4. 【垂直正交固定网点 + 15Hz 全局交替消残影】
    ivec2 in_block = ipos & 3;
    ivec2 shift_vec = ivec2(0, 0);
    #if ANTI_GHOSTING_DITHER == 1
        if (int(mod(float(frame), 2.0)) == 1) {
            shift_vec = ivec2(2, 2);
        }
    #endif

    ivec2 p_macro = (in_block + shift_vec) & 3;
    float th_macro = get_macro_threshold(p_macro);

    // 5. 【时域正交黄金比例蓝噪微网点 (色阶无缝连续插值)】
    float step_16 = 1.0 / 16.0;
    float noise_val = ign_temporal_dither(pixel_coord, float(frame)) - 0.5;

    float dark_boost = 1.0 + TEMPORAL_DARK_BOOST * (1.0 - luma_lifted);
    float bright_taper = smoothstep(0.96, 0.72, luma_lifted);
    float fine_dither = noise_val * step_16 * A_SPATIAL * dark_boost * bright_taper;

    float target_luma = clamp(luma_lifted + fine_dither, 0.0, 1.0);

    // 6. 【原版 Option B 聚簇大网点 (固定生长，深黑 0.0 直出)】
    float dot_val = clamp(0.5 + (target_luma - th_macro) / DOT_SOFTNESS, 0.0, 1.0);

    // 7. 【原版 Option B 边缘锐化与单像素高刷保护】
    float mean_neighbor = (tl + t + tr + l + r + bl + b + br) / 8.0;
    float high_pass = c - mean_neighbor;

    float edge_enhanced = clamp(luma_lifted + high_pass * (EDGE_BOOST - 1.0), 0.0, 1.0);
    float edge_dithered = clamp(edge_enhanced + fine_dither, 0.0, 1.0);

    // 暗部微弱纹理受 w_edge 保护恢复 300 PPI 单像素直刷，平坦暗部依然保持聚簇深黑大网点
    float final_luma = clamp(mix(dot_val, edge_dithered, w_edge), 0.0, 1.0);
    return vec4(vec3(final_luma), 1.0);
}
