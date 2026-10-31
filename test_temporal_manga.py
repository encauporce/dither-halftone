import numpy as np
from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

def sim_manga_temporal(img_path, dot_period=4.5, dot_softness=0.12, dark_lift_min=0.08, phase=0):
    img = Image.open(img_path).convert('L')
    arr = np.array(img, dtype=np.float32) / 255.0
    h, w = arr.shape
    
    # 1. Curve
    toe = np.sqrt(arr) * np.power(1.0 - arr, 2.0) * 0.12
    norm_curve = np.clip(np.power(arr, 0.60) + toe, 0.0, 1.0)
    luma_lifted = dark_lift_min + (1.0 - dark_lift_min) * norm_curve
    
    # Coordinates
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    
    # 45 deg rotation
    p_rot_x = (x + y) * 0.70710678
    p_rot_y = (x - y) * 0.70710678
    
    # Phase shift: 2-phase swap on dual lattice: shift by 0.5 * period on both axes
    if phase == 1:
        p_rot_x += 0.5 * dot_period
        p_rot_y += 0.5 * dot_period
        
    cell_x = np.mod(p_rot_x, dot_period) - dot_period * 0.5
    cell_y = np.mod(p_rot_y, dot_period) - dot_period * 0.5
    
    dist_sq = cell_x * cell_x + cell_y * cell_y
    th_manga = np.clip(dist_sq / (0.5 * dot_period * dot_period), 0.0, 1.0)
    
    # Temporal blue noise / dither
    # ign dither
    magic = np.array([0.06711056, 0.00583715, 52.9829189])
    t_offset = np.fmod(phase * 0.6180339887, 1.0)
    dot_prod = x * magic[0] + y * magic[1] + t_offset
    noise_val = np.fmod(magic[2] * np.fmod(dot_prod, 1.0), 1.0) - 0.5
    
    dark_boost = 1.0 + 1.60 * (1.0 - luma_lifted)
    bright_taper = np.clip((luma_lifted - 0.72) / (0.96 - 0.72), 0.0, 1.0)
    bright_taper = bright_taper * bright_taper * (3.0 - 2.0 * bright_taper)
    bright_taper = 1.0 - bright_taper
    
    fine_dither = noise_val * (1.0 / 16.0) * 0.65 * dark_boost * bright_taper
    target_luma = np.clip(luma_lifted + fine_dither, 0.0, 1.0)
    
    dot_val = np.clip(0.5 + (target_luma - th_manga) / dot_softness, 0.0, 1.0)
    
    # CRITICAL: Remap dot_val so minimum is dark_lift_min, NEVER 0.0!
    dot_luma = dark_lift_min + (1.0 - dark_lift_min) * dot_val
    
    return dot_luma

if __name__ == "__main__":
    # Test on Death Stranding frame
    ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_frame_clip3.png"
    if not os.path.exists(ds_path):
        ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png"
    
    f0 = sim_manga_temporal(ds_path, phase=0)
    f1 = sim_manga_temporal(ds_path, phase=1)
    
    print(f"Frame 0: Min={f0.min():.4f}, Max={f0.max():.4f}, ZeroCount={(f0==0).sum()}")
    print(f"Frame 1: Min={f1.min():.4f}, Max={f1.max():.4f}, ZeroCount={(f1==0).sum()}")
    
    # Delta between consecutive frames (anti-ghosting excitation pulse)
    delta = np.abs(f1 - f0)
    print(f"Inter-frame excitation delta: Mean={delta.mean():.4f}, Max={delta.max():.4f}")
    print(f"Percentage of pixels oscillating (>0.05 change): {(delta > 0.05).mean()*100:.1f}%")
    
    # Save visual outputs
    h, w = f0.shape
    cy, cx = h//2, w//2
    box = (slice(cy-60, cy+60), slice(cx-60, cx+60))
    
    z0 = (f0[box] * 255).astype(np.uint8)
    z1 = (f1[box] * 255).astype(np.uint8)
    z_avg = (((f0[box] + f1[box]) * 0.5) * 255).astype(np.uint8)
    z_diff = ((delta[box] / delta.max()) * 255).astype(np.uint8)
    
    # 4x zoom
    im0 = Image.fromarray(z0).resize((120*4, 120*4), Image.NEAREST)
    im1 = Image.fromarray(z1).resize((120*4, 120*4), Image.NEAREST)
    im_avg = Image.fromarray(z_avg).resize((120*4, 120*4), Image.NEAREST)
    im_diff = Image.fromarray(z_diff).resize((120*4, 120*4), Image.NEAREST)
    
    im0.save(os.path.join(brain_dir, "test_manga_f0_zoom.png"))
    im1.save(os.path.join(brain_dir, "test_manga_f1_zoom.png"))
    im_avg.save(os.path.join(brain_dir, "test_manga_avg_zoom.png"))
    im_diff.save(os.path.join(brain_dir, "test_manga_excitation_map.png"))
    print("Saved test frames.")
