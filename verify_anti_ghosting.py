import numpy as np
from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

def sim_full_pipeline(img_path, frame_num=0, dark_lift_min=0.08, dot_period=4.5, dot_softness=0.12):
    img = Image.open(img_path).convert('L')
    arr = np.array(img, dtype=np.float32) / 255.0
    h, w = arr.shape
    
    # 1. Darkness lift curve
    toe = np.sqrt(arr) * np.power(1.0 - arr, 2.0) * 0.12
    norm_curve = np.clip(np.power(arr, 0.60) + toe, 0.0, 1.0)
    luma_lifted = dark_lift_min + (1.0 - dark_lift_min) * norm_curve
    
    # 2. Coordinates
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    p_rot_x = (x + y) * 0.70710678
    p_rot_y = (x - y) * 0.70710678
    
    # 3. 2-phase 15Hz temporal phase flip on 45 deg lattice
    if (frame_num % 2) == 1:
        p_rot_x += 0.5 * dot_period
        p_rot_y += 0.5 * dot_period
        
    cell_x = np.mod(p_rot_x, dot_period) - dot_period * 0.5
    cell_y = np.mod(p_rot_y, dot_period) - dot_period * 0.5
    dist_sq = cell_x * cell_x + cell_y * cell_y
    th_manga = np.clip(dist_sq / (0.5 * dot_period * dot_period), 0.0, 1.0)
    
    # 4. Temporal IGN blue noise
    magic = np.array([0.06711056, 0.00583715, 52.9829189])
    t_offset = np.fmod(float(frame_num) * 0.6180339887, 1.0)
    dot_prod = x * magic[0] + y * magic[1] + t_offset
    noise_val = np.fmod(magic[2] * np.fmod(dot_prod, 1.0), 1.0) - 0.5
    
    # Pre-dither on target_luma for smooth boundary transition
    dark_boost = 1.0 + 1.60 * (1.0 - luma_lifted)
    bright_taper = np.clip((luma_lifted - 0.72) / (0.96 - 0.72), 0.0, 1.0)
    bright_taper = 1.0 - (bright_taper * bright_taper * (3.0 - 2.0 * bright_taper))
    fine_dither = noise_val * (1.0 / 16.0) * 0.65 * dark_boost * bright_taper
    target_luma = np.clip(luma_lifted + fine_dither, 0.0, 1.0)
    
    # 5. Halftone dot value [0.0, 1.0]
    dot_val = np.clip(0.5 + (target_luma - th_manga) / dot_softness, 0.0, 1.0)
    
    # 6. HARD-LOCK: Re-map halftone dot so ink floor is strictly DARK_LIFT_MIN!
    # No pixel can ever be 0.0 dead black!
    dot_luma = dark_lift_min + (1.0 - dark_lift_min) * dot_val
    
    # 7. Post-dither pulse for dark microcapsule agitation (去极化微振荡)
    # Even in solid dark ink regions, microcapsules vibrate dynamically!
    dark_dither = noise_val * (dark_lift_min * 0.45) * (1.0 - luma_lifted)
    final_dot = np.clip(dot_luma + dark_dither, dark_lift_min, 1.0)
    
    return final_dot

if __name__ == "__main__":
    ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png"
    f0 = sim_full_pipeline(ds_path, frame_num=0)
    f1 = sim_full_pipeline(ds_path, frame_num=1)
    
    print("=== Death Stranding Frame Metrics ===")
    print(f"F0 Min: {f0.min():.4f} (8-bit: {int(f0.min()*255)}), Max: {f0.max():.4f}")
    print(f"F0 Zero count (<0.01): {(f0 < 0.01).sum()} (Total: {f0.size})")
    print(f"F0 Dead black count (<=0.05): {(f0 <= 0.05).sum()} (Ratio: {(f0<=0.05).mean()*100:.2f}%)")
    
    delta = np.abs(f1 - f0)
    print(f"Mean delta: {delta.mean():.4f}")
    print(f"Agitated pixel ratio (>0.02): {(delta > 0.02).mean()*100:.2f}%")
    print(f"High-energy flip ratio (>0.20): {(delta > 0.20).mean()*100:.2f}%")
    
    # Check dark areas specifically: where input arr < 0.10
    raw_ds = np.array(Image.open(ds_path).convert('L'), dtype=np.float32) / 255.0
    dark_mask = (raw_ds < 0.10)
    print(f"In pure dark areas (input < 0.10, {dark_mask.sum()} pixels):")
    print(f"  Dark area F0 min: {f0[dark_mask].min():.4f}")
    print(f"  Dark area mean agitation delta: {delta[dark_mask].mean():.4f}")
    print(f"  Dark area agitated pixel ratio (>0.01): {(delta[dark_mask] > 0.01).mean()*100:.2f}%")
