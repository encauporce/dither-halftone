//!HOOK POSTKERNEL
//!BIND HOOKED
//!DESC Hisense A7 E-ink Video Enhancer: Organic De-Correlated Halftone + Aggressive Shadow Toe Curve

// ============================================================================
// 🛠️【海信 A7 墨水屏核心着色器参数调优区】
// ============================================================================
// 1. 【暗部防死黑强力曲线控制 (彻底消灭死黑的核心)】
// 海信官方驱动阈值：输入亮度 < 30/255 (0.118) 会被硬件强制切断驱动脉冲跌入死黑！
#define DARK_LIFT_MIN       0.135     // 纯黑底电平 (0.12 ~ 0.16)：强行抬升至 34/255，彻底跨过海信 30 硬件死黑门槛！
#define DARK_LIFT_GAMMA     0.52      // 暗部非线性展开伽马 (0.48 ~ 0.58)：强力拉伸暗部宽容度，展开阴影层次
#define SHADOW_TOE_BOOST    0.16      // 极暗部专属趾部提拉增益：对 0~25 极黑细节进行非线性提拉，杜绝黑死一块
#define TEMPORAL_DARK_BOOST 1.60      // 暗部时域震荡增强倍率

// 2. 【空间网格解耦与伪随机抖动暂停 (彻底消除远看纱窗网格感)】
#define SPATIAL_DECORRELATE 1         // 1: 开启每个 4x4 宏块空间相位独立哈希解耦，彻底粉碎整齐划一的机械网格！
#define RANDOM_DITHER_PAUSE 1         // 1: 启用伪随机抖动暂停，使每个宏块呼吸节奏产生有机差异，自然流动
#define PAUSE_PERIOD        4         // 暂停周期基底：每 4 帧中伪随机暂缓 1 帧 (41ms)，既破除机械周期，又保微胶囊持续激发

// 3. 【4x4 聚簇消残影大网点核心】
#define DOT_SOFTNESS        0.14      // 网点边缘过渡柔和度 (兼顾微胶囊强力击发与渐变色阶)

// 4. 【时域黄金比例蓝噪小网点 (无缝连续插值微步)】
#define A_SPATIAL           0.65      // 小网点填隙微步振幅 (严格覆盖 1/16 宏阶梯，抹平一切阶梯感)
#define TEMPORAL_BLUE_NOISE 1         // 1: 启用黄金比例(0.618)时域相位推进，彻底杜绝谐波闪烁

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

    // 2. Sobel 空间梯度检测（检测高频边缘线条与文字）
    float gx = (tr + 2.0 * r + br) - (tl + 2.0 * l + bl);
    float gy = (bl + 2.0 * b + br) - (tl + 2.0 * t + tr);
    float grad = sqrt(gx * gx + gy * gy);

    // 边缘平滑权重（0.0 = 平滑平坦区，1.0 = 高频边缘）
    float w_edge = smoothstep(EDGE_MIN, EDGE_MAX, grad);
    float w_half = (1.0 - w_edge);

    // 3. 【强力防死黑曲线】动态暗部非线性展开 + 极暗部专属趾部提拉
    // 基础非线性伽马展开 + 极暗部专属非线性趾部提拉 (Toe Boost)
    float toe = sqrt(c) * pow(1.0 - c, 2.0) * SHADOW_TOE_BOOST;
    float norm_curve = clamp(pow(c, DARK_LIFT_GAMMA) + toe, 0.0, 1.0);
    float luma_lifted = DARK_LIFT_MIN + (1.0 - DARK_LIFT_MIN) * norm_curve;

    // 4. 【空间解耦与伪随机抖动暂停引擎 (彻底破除远观网格感)】
    const ivec2 phase_16[16] = ivec2[16](
        ivec2(0, 0), ivec2(2, 2),
        ivec2(0, 1), ivec2(2, 3),
        ivec2(0, 2), ivec2(2, 0),
        ivec2(0, 3), ivec2(2, 1),
        ivec2(1, 1), ivec2(3, 3),
        ivec2(1, 2), ivec2(3, 0),
        ivec2(1, 3), ivec2(3, 1),
        ivec2(1, 0), ivec2(3, 2)
    );

    // 空间宏块坐标 (每 4x4 像素为一个独立宏网点单元)
    ivec2 block_id = ipos >> 2;

    // 空间伪随机哈希计算 (Wang Hash / Integer Mixer)
    int n = block_id.x * 374761393 + block_id.y * 668265263;
    n = (n ^ (n >> 13)) * 1274126177;
    int h = (n ^ (n >> 16)) & 0x7fffffff;

    // A. 空间相位解耦：每个宏块赋予不同初始时相 [0 ~ 15]
    #if SPATIAL_DECORRELATE == 1
        int phase_offset = h & 15;
    #else
        int phase_offset = 0;
    #endif

    // B. 伪随机抖动暂停：每个宏块拥有独立的暂缓时隙 [0 ~ 3]
    #if RANDOM_DITHER_PAUSE == 1
        int pause_slot = (h >> 4) & 3;
        int f_raw = frame;
        int f_base = (f_raw / 4) * 3;
        int f_rem = f_raw & 3;
        int f_extra = (f_rem <= pause_slot) ? f_rem : (f_rem - 1);
        int f_organic = f_base + f_extra;
    #else
        int f_organic = frame;
    #endif

    int phase_idx = (f_organic + phase_offset) & 15;
    ivec2 shift_vec = phase_16[phase_idx];

    // 宏块内部局部坐标与大网点采样
    ivec2 in_block = ipos & 3;
    ivec2 p_macro = (in_block + shift_vec) & 3;
    float th_macro = get_macro_threshold(p_macro);

    // 5. 【时域正交黄金比例蓝噪微网点 (色阶无缝连续插值)】
    // 步长严格设为 1/16 = 0.0625，与 4x4 宏网点单阶宽度严格 1:1 吻合，彻底消除阶梯断崖与断层
    float step_16 = 1.0 / 16.0;
    float noise_val = ign_temporal_dither(pixel_coord, float(frame)) - 0.5;
    
    // 暗部适度强化以除残影，高亮平滑抑制防频闪
    float dark_boost = 1.0 + TEMPORAL_DARK_BOOST * (1.0 - luma_lifted);
    float bright_taper = smoothstep(0.96, 0.72, luma_lifted);
    float fine_dither = noise_val * step_16 * A_SPATIAL * dark_boost * bright_taper;

    float target_luma = clamp(luma_lifted + fine_dither, 0.0, 1.0);

    // 6. 生成经典高反差聚簇消残影大网点
    float dot_val = clamp(0.5 + (target_luma - th_macro) / DOT_SOFTNESS, 0.0, 1.0);

    // 7. 【统一色阶边缘锐化与单像素高刷保护 (彻底根除明暗倒挂与边缘死黑)】
    // 高频信号提取：提取相对于局域均值的锐化增量
    float mean_neighbor = (tl + t + tr + l + r + bl + b + br) / 8.0;
    float high_pass = c - mean_neighbor;

    // 关键修正：边缘锐化必须严格叠加在同一条暗部提拉基底 luma_lifted 之上，严禁使用未提拉的原始 c！
    float edge_enhanced = clamp(luma_lifted + high_pass * (EDGE_BOOST - 1.0), 0.0, 1.0);
    // 边缘区域叠加相同微步蓝噪微网点，保证微胶囊高频刷新不留死黑与残影
    float edge_dithered = clamp(edge_enhanced + fine_dither, 0.0, 1.0);

    // 平坦区为大网点半色调，边缘线条平滑恢复 300 PPI 单像素直刷，二者宏观光通量完全单调统一！
    float final_luma = clamp(mix(dot_val, edge_dithered, w_edge), 0.0, 1.0);
    return vec4(vec3(final_luma), 1.0);
}
