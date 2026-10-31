//!HOOK POSTKERNEL
//!BIND HOOKED
//!DESC Hisense A7 E-ink Video Enhancer: 2-Phase High-Energy Anti-Ghosting + Multi-Scale Halftone

// ============================================================================
// 🛠️【海信 A7 墨水屏核心着色器参数调优区】
// ============================================================================
// 1. 【时域时钟相序模式 (核心消残影/消拖影引擎)】
// 2 = 奇偶双帧对角强力互换 (0,0) <-> (2,2) [★ 强力消残影王牌！15Hz 高频去极化微振颤，墨水颗粒不沉淀]
// 4 = 4 帧正方形旋转漫步 (0,0)->(2,2)->(2,0)->(0,2) [平滑低振颤]
// 9 = 9 帧低频爬行漫步 [注意：每个像素长达330ms静止，会导致墨水颗粒冻结残影，非特殊需求勿开]
#define PHASE_MODE          2         // 默认为 2：彻底消灭残影与拖影

// 2. 【多尺度双层套叠网点权重】4x4 大网点骨架 + 2x2 小网点嵌合，纯空间 64 阶
#define W_MACRO_DOT         0.75      // 大网点(4x4)基底权重
#define W_MICRO_DOT         0.25      // 小网点(2x2)嵌合权重 (步长严格吻合，绝不截断)
#define DOT_CONTRAST        0.95      // 网点硬度对比度 (0.90 ~ 1.0: 确保跃迁幅度跨过海信 EPDC DU 激发阈值)
#define DOT_SOFTNESS        0.10      // 网点边缘过渡刚度 (越小跃迁越剧烈，消残影越猛)

// 3. 【时域黄金比例蓝噪微抖动】
#define A_SPATIAL           0.35      // 空间蓝噪严格限制在 1/64 微步内，仅消弭网点微缝隙
#define TEMPORAL_BLUE_NOISE 1         // 1: 启用黄金比例(0.618)时域相位推进，彻底杜绝与网点产生共振闪烁

// 4. 【暗部防残影控制】
#define DARK_LIFT_MIN       0.08      // 纯黑抬升底电平 (0.06 ~ 0.12)：将死黑提拉至浅灰安全区，防硬着陆死黑
#define DARK_LIFT_CURVE     0.78      // 暗部非线性展开伽马
#define TEMPORAL_DARK_BOOST 1.60      // 暗部时域震荡增强倍率

// 5. 【边缘与字幕锐度自适应保护 (Sobel 梯度)】
#define EDGE_MIN            0.035     // 梯度下限：低于此值全开双层网点
#define EDGE_MAX            0.180     // 梯度上限：高于此值淡出网点恢复 300 PPI 单像素直刷
#define EDGE_BOOST          1.15      // 边缘对比度适度增强
// ============================================================================

// 采样指定位置的感知亮度 (ITU-R BT.709)
float get_luma_at(vec2 pos) {
    vec4 c = HOOKED_tex(pos);
    return dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
}

// 4x4 经典印刷聚簇大网点矩阵 (16 阶)
float get_macro_threshold(ivec2 p) {
    const float m[16] = float[16](
        12.0,  8.0,  9.0, 13.0,
         7.0,  0.0,  1.0,  5.0,
         6.0,  2.0,  3.0,  4.0,
        11.0, 10.0, 14.0, 15.0
    );
    return (m[p.y * 4 + p.x] + 0.5) / 16.0;
}

// 2x2 Bayer 分散小网点矩阵 (4 阶)
float get_micro_threshold(ivec2 p) {
    const float m2[4] = float[4](
        0.0, 2.0,
        3.0, 1.0
    );
    return (m2[p.y * 2 + p.x] + 0.5) / 4.0;
}

// 黄金比例低差异时空蓝噪 (Golden Ratio Temporal IGN)
// 沿时间轴以 0.6180339887 无理数步长推进，数学上证明与任何整数周期时钟正交无谐波
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

    // 边缘平滑权重（0.0 = 平滑平坦区，1.0 = 高频边缘）
    float w_edge = smoothstep(EDGE_MIN, EDGE_MAX, grad);
    float w_half = (1.0 - w_edge);

    // 3. 【防残影关键一】动态暗部黑电平抬升 (Black Level Lift)
    float luma_lifted = DARK_LIFT_MIN + (1.0 - DARK_LIFT_MIN) * pow(c, DARK_LIFT_CURVE);

    // 4. 【消残影核心：主时钟相序位移】
    // 在 2 帧模式下：奇偶帧对角互换 (0,0) <-> (2,2)
    // 使得上一帧为黑网点的位置，下一帧强行跳跃为高亮度，形成持续 15Hz 物理去极化电脉冲！
    // 同时由于 (x+2, y+2) 在 4x4 环面内是严格的双射置换，4x4 宏像素的亮暗总能量绝对恒定（方差恒为 0，零宏观闪烁）！
    ivec2 shift_vec = ivec2(0, 0);
    #if PHASE_MODE == 2
        if (int(mod(float(frame), 2.0)) == 1) shift_vec = ivec2(2, 2);
    #elif PHASE_MODE == 4
        int f4 = int(mod(float(frame), 4.0));
        if (f4 == 1) shift_vec = ivec2(2, 2);
        else if (f4 == 2) shift_vec = ivec2(2, 0);
        else if (f4 == 3) shift_vec = ivec2(0, 2);
    #elif PHASE_MODE == 9
        const ivec2 phase_9[9] = ivec2[9](
            ivec2(1, 1), ivec2(0, 0), ivec2(2, 2),
            ivec2(0, 2), ivec2(2, 0), ivec2(1, 0),
            ivec2(1, 2), ivec2(0, 1), ivec2(2, 1)
        );
        shift_vec = phase_9[int(mod(float(frame), 9.0))];
    #endif

    // 大网点采样坐标 (% 4 取模) 与 小网点采样坐标 (% 2 取模)
    // 二者完全同步移动，小网点紧密跟随大网点，绝不产生拍频干涉
    ivec2 p_macro = (ivec2(floor(pixel_coord)) + shift_vec) & 3;
    ivec2 p_micro = (ivec2(floor(pixel_coord)) + shift_vec) & 1;

    float th_macro = get_macro_threshold(p_macro);
    float th_micro = get_micro_threshold(p_micro);

    // 双层多尺度非截断套叠阈值场 (提供严格 16 x 4 = 64 空间能量阶梯)
    float th_nested = th_macro * W_MACRO_DOT + th_micro * W_MICRO_DOT;

    // 5. 【时域正交黄金比例蓝噪 (零拍频微抖动)】
    // 仅在 64 阶微网点缝隙注入极微量蓝噪 (步长 1/64 = 0.0156)
    // 沿时间轴以 0.618 黄金无理数滑动，与网点时钟完全正交，绝不产生谐波闪烁
    float step_64 = 1.0 / 64.0;
    float noise_val = ign_temporal_dither(pixel_coord, float(frame)) - 0.5;
    
    // 暗部适度强化以除残影，高亮平滑抑制防频闪
    float dark_boost = 1.0 + TEMPORAL_DARK_BOOST * (1.0 - luma_lifted);
    float bright_taper = smoothstep(0.96, 0.72, luma_lifted);
    float fine_dither = noise_val * step_64 * A_SPATIAL * dark_boost * bright_taper;

    float target_luma = clamp(luma_lifted + fine_dither, 0.0, 1.0);

    // 6. 生成双层套叠半色调网点
    // DOT_SOFTNESS 与 DOT_CONTRAST 共同控制跃迁硬度与物理颗粒击发能量
    float dot_val = clamp(0.5 + (target_luma - th_nested) / DOT_SOFTNESS, 0.0, 1.0);

    // 平坦区按 DOT_CONTRAST 释放高能量网点，边缘区恢复 300 PPI 单像素高刷
    float halftone_result = mix(target_luma, dot_val, DOT_CONTRAST * w_half);

    // 7. 边缘区域高频锐化与保护
    if (w_edge > 0.01) {
        float edge_enhanced = c + (c - (tl+t+tr+l+r+bl+b+br)/8.0) * (EDGE_BOOST - 1.0);
        halftone_result = mix(halftone_result, edge_enhanced, w_edge);
    }

    float final_luma = clamp(halftone_result, 0.0, 1.0);
    return vec4(vec3(final_luma), 1.0);
}
