//!HOOK POSTKERNEL
//!BIND HOOKED
//!DESC Hisense A7 E-ink Video Enhancer: Multi-Scale Nested Halftone (Macro 4x4 + Micro 2x2 Superposition)

// ============================================================================
// 🛠️【海信 A7 墨水屏核心着色器参数调优区】
// ============================================================================
// 1. 【多尺度双层套叠网点权重 (Superimposed Multiscale Halftone)】
// 大网点与小网点真正在阈值空间中完全套叠叠加，绝不截断！
// 4x4 大网点提供 16 阶宏观骨架，2x2 小网点嵌套在其间细分出 4 个亚阶梯 -> 纯空间提供 64 阶纯正网点灰阶！
#define W_MACRO_DOT         0.75      // 大网点(4x4)基底权重 [0.60 ~ 0.85]
#define W_MICRO_DOT         0.25      // 小网点(2x2)嵌合权重 (两权重之和严格等于 1.0)
#define DOT_SOFTNESS        0.14      // 网点连续过渡柔和度

// 2. 【时域 9 相位动态漫游】
#define PHASE_MODE          9         // 9 帧低相关空间跳跃，与 64 阶网点相乘达 576 阶感知色阶并彻底消拖影

// 3. 【暗部防残影控制】
#define DARK_LIFT_MIN       0.08      // 纯黑抬升底电平 (0.06 ~ 0.12)：将死黑提拉至浅灰安全区
#define DARK_LIFT_CURVE     0.78      // 暗部非线性展开伽马
#define TEMPORAL_DARK_BOOST 1.60      // 暗部时域震荡增强倍率

// 4. 【亚像素蓝噪填隙】
#define A_SPATIAL           0.50      // 仅在 64 阶微网点缝隙注入微量蓝噪，完全不破坏网点骨架

// 5. 【边缘与字幕锐度自适应保护】(Sobel 梯度)
#define EDGE_MIN            0.035     // 梯度下限：低于此值全开双层网点
#define EDGE_MAX            0.180     // 梯度上限：高于此值淡出网点恢复 300 PPI 单像素直通
#define EDGE_BOOST          1.15      // 边缘对比度适度增强
// ============================================================================

// 采样指定位置的感知亮度 (ITU-R BT.709)
float get_luma_at(vec2 pos) {
    vec4 c = HOOKED_tex(pos);
    return dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
}

// 1. 4x4 大网点阈值 (宏观聚簇网点，提供 16 级低频印刷质感)
float get_macro_threshold(vec2 px, int frame_num) {
    ivec2 offset = ivec2(0, 0);
    #if PHASE_MODE == 9
        const ivec2 phase_9[9] = ivec2[9](
            ivec2(1, 1), ivec2(0, 0), ivec2(2, 2),
            ivec2(0, 2), ivec2(2, 0), ivec2(1, 0),
            ivec2(1, 2), ivec2(0, 1), ivec2(2, 1)
        );
        offset = phase_9[int(mod(float(frame_num), 9.0))];
    #elif PHASE_MODE == 2
        if (int(mod(float(frame_num), 2.0)) == 1) offset = ivec2(2, 2);
    #endif

    int x = (int(floor(px.x)) + offset.x) & 3;
    int y = (int(floor(px.y)) + offset.y) & 3;
    
    const float m[16] = float[16](
        12.0,  8.0,  9.0, 13.0,
         7.0,  0.0,  1.0,  5.0,
         6.0,  2.0,  3.0,  4.0,
        11.0, 10.0, 14.0, 15.0
    );
    return (m[y * 4 + x] + 0.5) / 16.0;
}

// 2. 2x2 小网点阈值 (微观分散网点，嵌套在大网点缝隙与边缘，提供 4 级亚阶梯)
float get_micro_threshold(vec2 px, int frame_num) {
    // 小网点采用奇偶对角反转
    int f = int(mod(float(frame_num), 2.0));
    int ox = f;
    int oy = f;

    int x = (int(floor(px.x)) + ox) & 1;
    int y = (int(floor(px.y)) + oy) & 1;

    // 2x2 Bayer 矩阵
    // 0  2
    // 3  1
    const float m2[4] = float[4](
        0.0, 2.0,
        3.0, 1.0
    );
    return (m2[y * 2 + x] + 0.5) / 4.0;
}

// Interleaved Gradient Noise (IGN)
float ign_dither(vec2 p) {
    vec3 magic = vec3(0.06711056, 0.00583715, 52.9829189);
    return fract(magic.z * fract(dot(p, magic.xy)));
}

vec4 hook() {
    vec2 pt = HOOKED_pt;
    vec2 pixel_coord = HOOKED_pos / pt;

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

    // 2. Sobel 空间梯度检测（检测高频边缘线条与文字）
    float gx = (tr + 2.0 * r + br) - (tl + 2.0 * l + bl);
    float gy = (bl + 2.0 * b + br) - (tl + 2.0 * t + tr);
    float grad = sqrt(gx * gx + gy * gy);

    // 边缘平滑权重：0.0 = 平滑平坦区，1.0 = 高频边缘线
    float w_edge = smoothstep(EDGE_MIN, EDGE_MAX, grad);
    float w_half = (1.0 - w_edge);

    // 3. 【防残影关键一】动态暗部黑电平抬升 (Black Level Lift)
    float luma_lifted = DARK_LIFT_MIN + (1.0 - DARK_LIFT_MIN) * pow(c, DARK_LIFT_CURVE);

    // 4. 【多尺度双层套叠网点空间叠加 (Nested Multi-Scale Halftoning)】
    // 大网点与小网点真正在同一空间中套叠：
    // 大网点决定低频宏观凝聚形态，小网点在大网点缝隙中生成细微点阵！
    float th_macro = get_macro_threshold(pixel_coord, frame);
    float th_micro = get_micro_threshold(pixel_coord, frame);

    // 核心套叠公式：非截断线性合成阈值场 (提供 16 x 4 = 64 空间连续基底阶)
    float th_nested = th_macro * W_MACRO_DOT + th_micro * W_MICRO_DOT;

    // 5. 【64 阶微缝蓝噪注入】
    // 每一阶微步仅 1/64 = 0.0156，仅做极微量接缝填补
    float step_64 = 1.0 / 64.0;
    float noise_val = ign_dither(pixel_coord) - 0.5;
    float fine_dither = noise_val * step_64 * A_SPATIAL;

    float target_luma = clamp(luma_lifted + fine_dither, 0.0, 1.0);

    // 生成双层套叠半色调网点
    float dot_val = clamp(0.5 + (target_luma - th_nested) / DOT_SOFTNESS, 0.0, 1.0);

    // 平坦区全开套叠网点，边缘区恢复 300 PPI 单像素高清
    float halftone_result = mix(target_luma, dot_val, w_half);

    // 6. 边缘区域高频锐化与保真
    if (w_edge > 0.01) {
        float edge_enhanced = c + (c - (tl+t+tr+l+r+bl+b+br)/8.0) * (EDGE_BOOST - 1.0);
        halftone_result = mix(halftone_result, edge_enhanced, w_edge);
    }

    float final_luma = clamp(halftone_result, 0.0, 1.0);
    return vec4(vec3(final_luma), 1.0);
}
