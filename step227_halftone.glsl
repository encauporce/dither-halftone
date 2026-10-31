//!HOOK POSTKERNEL
//!BIND HOOKED
//!DESC Hisense A7 E-ink Video Enhancer: Dynamic Rotating Halftone + Anti-Ghosting / Anti-Trailing

// ============================================================================
// 🛠️【海信 A7 墨水屏核心着色器参数调优区】
// ============================================================================
// 1. 【网点物理尺度】(按要求设为 1.0，即 4x4 像素原生 300 PPI 极细致印刷点阵)
#define DOT_SCALE           1.0       // 网点尺度：1.0 = 原生 4x4 单像素对齐

// 2. 【时域动态网点相位漫游 (消拖影/消纱窗核心)】
// 0 = 静态网点(会产生纱窗感和拖影)
// 2 = 奇偶帧对角互换 (0,0) <-> (2,2) [强烈推荐：消拖影、消残影、消纱窗最彻底！]
// 4 = 4 帧四边漫游 (0,0)->(2,2)->(2,0)->(0,2) [平滑流动感]
#define PHASE_CYCLE         2         // 时域相位循环模式 (2 或 4)

// 3. 【网点对比度与边缘柔和度】
#define DOT_CONTRAST        0.88      // 网点显现对比度 (0.0=纯平滑, 0.88=清晰印刷网点, 1.0=极硬网点)
#define DOT_SOFTNESS        0.16      // 网点边缘柔和度

// 4. 【暗部防残影控制】
#define DARK_LIFT_MIN       0.08      // 纯黑抬升底电平 (0.06 ~ 0.12)：将死黑提拉至浅灰安全区
#define DARK_LIFT_CURVE     0.78      // 暗部非线性展开伽马 (越小暗部反差越开朗)
#define TEMPORAL_DARK_BOOST 1.60      // 暗部时域震荡增强倍率

// 5. 【空域高频蓝噪抖动】
#define A_SPATIAL           0.65      // 空间蓝噪填隙振幅 (抚平网点边缘台阶)

// 6. 【边缘与字幕锐度自适应保护】(Sobel 梯度)
#define EDGE_MIN            0.035     // 梯度下限：低于此值全开动态网点
#define EDGE_MAX            0.180     // 梯度上限：高于此值视为边缘线条，淡出网点恢复 300 PPI 单像素直通
#define EDGE_BOOST          1.15      // 边缘对比度适度增强
// ============================================================================

// 采样指定位置的感知亮度 (ITU-R BT.709)
float get_luma_at(vec2 pos) {
    vec4 c = HOOKED_tex(pos);
    return dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
}

// 4x4 工业级经典印刷聚簇网点矩阵 (Clustered AM Screening)
// 支持时空相位动态平移 (Dynamic Phase Shift)，彻底消灭静态纱窗感与拖影
float get_dynamic_clustered_threshold(vec2 px, int frame_num) {
    vec2 scaled = px / DOT_SCALE;
    
    // 计算时域动态平移向量 (Phase Offset)
    ivec2 offset = ivec2(0, 0);
    #if PHASE_CYCLE == 2
        // 奇偶两帧对角绝对互换：(0,0) 与 (2,2)
        // 使得上一帧是黑墨点的位置，下一帧绝对变成白背景，彻底物理激发墨水微胶囊！
        int f = int(mod(float(frame_num), 2.0));
        if (f == 1) offset = ivec2(2, 2);
    #elif PHASE_CYCLE == 4
        int f = int(mod(float(frame_num), 4.0));
        if (f == 1) offset = ivec2(2, 2);
        else if (f == 2) offset = ivec2(2, 0);
        else if (f == 3) offset = ivec2(0, 2);
    #endif

    int x = (int(floor(scaled.x)) + offset.x) & 3;
    int y = (int(floor(scaled.y)) + offset.y) & 3;
    
    const float m[16] = float[16](
        12.0,  8.0,  9.0, 13.0,
         7.0,  0.0,  1.0,  5.0,
         6.0,  2.0,  3.0,  4.0,
        11.0, 10.0, 14.0, 15.0
    );
    return (m[y * 4 + x] + 0.5) / 16.0;
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

    // 4. 【空域蓝噪微抖动注入判定输入端】
    float step_val = 1.0 / 16.0;
    float noise_val = ign_dither(pixel_coord) - 0.5;
    float spatial_dither = noise_val * step_val * A_SPATIAL;

    float dithered_luma = clamp(luma_lifted + spatial_dither, 0.0, 1.0);

    // 5. 【时空动态旋转聚簇网点 (Dynamic Halftoning - 消拖影/消纱窗)】
    // 通过每帧改变网点空间相位，网点像生命体一样呼吸跳动，杜绝任何像素长时间固定为黑！
    float thresh = get_dynamic_clustered_threshold(pixel_coord, frame);
    float dot_val = clamp(0.5 + (dithered_luma - thresh) / DOT_SOFTNESS, 0.0, 1.0);

    // 平坦区按 DOT_CONTRAST 显现动态印刷网点，边缘区 (w_edge -> 1.0) 恢复 1:1 单像素高清
    float halftone_result = mix(dithered_luma, dot_val, DOT_CONTRAST * w_half);

    // 6. 边缘区域高频锐化与保真
    if (w_edge > 0.01) {
        float edge_enhanced = c + (c - (tl+t+tr+l+r+bl+b+br)/8.0) * (EDGE_BOOST - 1.0);
        halftone_result = mix(halftone_result, edge_enhanced, w_edge);
    }

    float final_luma = clamp(halftone_result, 0.0, 1.0);
    return vec4(vec3(final_luma), 1.0);
}
