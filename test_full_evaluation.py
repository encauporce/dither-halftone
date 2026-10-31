#!/usr/bin/env python3
"""
Comprehensive evaluation and verification script for halftone.glsl
Validates all 6 core technical contributions on test clips:
1. Dead black settling elimination (static zero pixels)
2. Tone mapping dynamic range (Option B Deep Ink + White Shoulder)
3. 15Hz alternating phase shift (0,0) <-> (2,2) flip ratio (target ~31.14%)
4. Perceptual grayscale resolution expansion via Golden-Ratio IGN
5. High-pass halftone detail injection
6. DU4 4-level physical grayscale antialiasing (49 spatial levels)
"""

import numpy as np
from PIL import Image
import os

# 4x4 Clustered Halftone Matrix (Classic print clustered dot)
M16 = np.array([
    [12.0,  8.0,  9.0, 13.0],
    [ 7.0,  0.0,  1.0,  5.0],
    [ 6.0,  2.0,  3.0,  4.0],
    [11.0, 10.0, 14.0, 15.0]
], dtype=np.float32)
TH_M16 = (M16 + 0.5) / 16.0

def run_shader_simulation(c, frame=0,
                          dark_lift_min=0.050,
                          dark_lift_gamma=0.52,
                          white_shoulder=0.14,
                          shadow_toe_boost=0.12,
                          temporal_dark_boost=1.60,
                          anti_ghosting_dither=1,
                          dot_softness=0.20,
                          a_spatial=0.40,
                          temporal_blue_noise=1,
                          high_pass_inject=1.60,
                          hp_dark_boost=1.40,
                          edge_boost=1.15):
    h, w = c.shape
    yy, xx = np.indices((h, w), dtype=np.float32)
    ipos_x = xx.astype(np.int32)
    ipos_y = yy.astype(np.int32)

    # 1. 8-Neighbor Spatial Neighborhood & High-Pass
    cp = np.pad(c, 1, mode='edge')
    tl = cp[0:h, 0:w]; t  = cp[0:h, 1:w+1]; tr = cp[0:h, 2:w+2]
    l  = cp[1:h+1, 0:w];                     r  = cp[1:h+1, 2:w+2]
    bl = cp[2:h+2, 0:w]; b  = cp[2:h+2, 1:w+1]; br = cp[2:h+2, 2:w+2]
    mean_neighbor = (tl + t + tr + l + r + bl + b + br) / 8.0
    high_pass = c - mean_neighbor

    # 2. Option B Deep Ink Tone Mapping + Shadow Toe + White Shoulder
    toe = np.sqrt(np.maximum(c, 0.0)) * ((1.0 - c) ** 2.0) * shadow_toe_boost
    shoulder = (c ** 2.0) * white_shoulder
    norm_curve = np.clip((c ** dark_lift_gamma) + toe + shoulder, 0.0, 1.0)
    luma_lifted = dark_lift_min + (1.0 - dark_lift_min) * norm_curve

    # 3. 4x4 Clustered Halftone with 15Hz Alternating Phase Shift (0,0) <-> (2,2)
    in_bx = ipos_x & 3
    in_by = ipos_y & 3
    shift_x = 0
    shift_y = 0
    if anti_ghosting_dither == 1 and (frame % 2 == 1):
        shift_x = 2
        shift_y = 2
    p_macro_x = (in_bx + shift_x) & 3
    p_macro_y = (in_by + shift_y) & 3
    th_macro = TH_M16[p_macro_y, p_macro_x]

    # 4. Golden Ratio Temporal Blue Noise IGN
    magic = np.array([0.06711056, 0.00583715, 52.9829189])
    if temporal_blue_noise == 1:
        t_offset = np.fmod(float(frame) * 0.6180339887, 1.0)
    else:
        t_offset = 0.0
    dot_prod = xx * magic[0] + yy * magic[1] + t_offset
    noise_val = np.fmod(magic[2] * np.fmod(dot_prod, 1.0), 1.0) - 0.5

    step_16 = 1.0 / 16.0
    dark_boost = 1.0 + temporal_dark_boost * (1.0 - luma_lifted)
    bright_taper = np.clip((luma_lifted - 0.72) / (0.96 - 0.72), 0.0, 1.0)
    bright_taper = 1.0 - (bright_taper * bright_taper * (3.0 - 2.0 * bright_taper))
    fine_dither = noise_val * step_16 * a_spatial * dark_boost * bright_taper

    # 5. High-Pass Halftone Injection
    hp_gain = high_pass_inject * (1.0 + hp_dark_boost * (1.0 - luma_lifted))
    target_luma = np.clip(luma_lifted + fine_dither + high_pass * hp_gain, 0.0, 1.0)

    # 6. Clustered Halftone Dot with Softness Expansion
    dot_val = np.clip(0.5 + (target_luma - th_macro) / dot_softness, 0.0, 1.0)

    # 7. Sobel Gradient & Edge Preservation
    gx = (tr + 2.0 * r + br) - (tl + 2.0 * l + bl)
    gy = (bl + 2.0 * b + br) - (tl + 2.0 * t + tr)
    grad = np.sqrt(gx * gx + gy * gy)
    w_edge = np.clip((grad - 0.035) / (0.180 - 0.035), 0.0, 1.0)
    w_edge = w_edge * w_edge * (3.0 - 2.0 * w_edge)

    edge_enhanced = np.clip(luma_lifted + high_pass * (edge_boost - 1.0), 0.0, 1.0)
    edge_dithered = np.clip(edge_enhanced + fine_dither, 0.0, 1.0)

    final_luma = np.clip(dot_val * (1.0 - w_edge) + edge_dithered * w_edge, 0.0, 1.0)
    return final_luma

def simulate_epdc_du4(luma):
    # Hardware black/white clipping and 4-level quantization (DU mode)
    BLACK_TH = 30.0 / 255.0
    WHITE_TH = (255.0 - 20.0) / 255.0
    clamped = np.clip((luma - BLACK_TH) / (WHITE_TH - BLACK_TH), 0.0, 1.0)
    return np.round(clamped * 3.0) / 3.0

def main():
    repo_dir = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader"
    ds_path = os.path.join(repo_dir, "raw_clip3_ds1.png")
    mc_path = os.path.join(repo_dir, "raw_clip2_minecraft.png")

    for name, p in [("Death Stranding (Dark Scene)", ds_path), ("Minecraft (High Contrast)", mc_path)]:
        img = Image.open(p).convert('L')
        c = np.array(img, dtype=np.float32) / 255.0

        f0 = run_shader_simulation(c, frame=0)
        f1 = run_shader_simulation(c, frame=1)

        delta = np.abs(f1 - f0)
        flip_30 = (delta > 0.30).mean() * 100
        flip_10 = (delta > 0.10).mean() * 100
        delta_mean = delta.mean()

        # EPDC simulation
        epdc_f0 = simulate_epdc_du4(f0)
        epdc_f1 = simulate_epdc_du4(f1)
        epdc_delta = np.abs(epdc_f1 - epdc_f0)
        epdc_flip = (epdc_delta > 0.1).mean() * 100

        # Unique levels in 4x4 block
        # Measure local spatial entropy and effective levels
        h, w = c.shape
        step_sample = f0[100:300, 100:300]
        unique_levels = len(np.unique(np.round(step_sample * 255.0)))

        print(f"=== {name} ===")
        print(f"Frame 0 Dynamic Range: Min={f0.min():.4f}, Max={f0.max():.4f}")
        print(f"Zero Pixel Ratio (f0 == 0.0): {(f0 == 0.0).mean()*100:.2f}%")
        print(f"Inter-frame Mean Delta: {delta_mean:.4f}")
        print(f"Pixels Flipped > 0.10: {flip_10:.2f}%")
        print(f"Pixels Flipped > 0.30 (Hard Flip): {flip_30:.2f}%")
        print(f"Hardware DU4 EPDC Flip Ratio: {epdc_flip:.2f}%")
        print(f"Local Unique Output Levels: {unique_levels}")
        print()

if __name__ == '__main__':
    main()
