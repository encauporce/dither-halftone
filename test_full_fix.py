import numpy as np
from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

def sim_shader_full(img_path, frame=0, dark_lift_min=0.08, dot_period=4.5, dot_softness=0.12):
    img = Image.open(img_path).convert('L')
    c = np.array(img, dtype=np.float32) / 255.0
    h, w = c.shape
    
    # 1. Darkness lift curve
    toe = np.sqrt(c) * np.power(1.0 - c, 2.0) * 0.12
    norm_curve = np.clip(np.power(c, 0.60) + toe, 0.0, 1.0)
    luma_lifted = dark_lift_min + (1.0 - dark_lift_min) * norm_curve
    
    # 2. Coordinates & 45 deg rotation
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    p_rot_x = (x + y) * 0.70710678
    p_rot_y = (x - y) * 0.70710678
    
    # 3. 2-phase temporal phase flip
    if (frame % 2) == 1:
        p_rot_x += 0.5 * dot_period
        p_rot_y += 0.5 * dot_period
        
    cell_x = np.mod(p_rot_x, dot_period) - dot_period * 0.5
    cell_y = np.mod(p_rot_y, dot_period) - dot_period * 0.5
    dist_sq = cell_x * cell_x + cell_y * cell_y
    th_manga = np.clip(dist_sq / (0.5 * dot_period * dot_period), 0.0, 1.0)
    
    # 4. IGN temporal blue noise
    magic = np.array([0.06711056, 0.00583715, 52.9829189])
    t_offset = np.fmod(float(frame) * 0.6180339887, 1.0)
    dot_prod = x * magic[0] + y * magic[1] + t_offset
    noise_val = np.fmod(magic[2] * np.fmod(dot_prod, 1.0), 1.0) - 0.5
    
    dark_boost = 1.0 + 1.60 * (1.0 - luma_lifted)
    bright_taper = np.clip((luma_lifted - 0.72) / (0.96 - 0.72), 0.0, 1.0)
    bright_taper = 1.0 - (bright_taper * bright_taper * (3.0 - 2.0 * bright_taper))
    fine_dither = noise_val * (1.0 / 16.0) * 0.65 * dark_boost * bright_taper
    target_luma = np.clip(luma_lifted + fine_dither, 0.0, 1.0)
    
    # 5. Halftone dot
    dot_val = np.clip(0.5 + (target_luma - th_manga) / dot_softness, 0.0, 1.0)
    
    # HARD-LOCK: Re-map halftone dot so ink floor is strictly DARK_LIFT_MIN
    dot_luma = dark_lift_min + (1.0 - dark_lift_min) * dot_val
    
    # 6. Sobel edge detection
    # Approximate sobel
    gx = np.zeros_like(c)
    gy = np.zeros_like(c)
    gx[:, 1:-1] = c[:, 2:] - c[:, :-2]
    gy[1:-1, :] = c[2:, :] - c[:-2, :]
    grad = np.sqrt(gx*gx + gy*gy)
    w_edge = np.clip((grad - 0.035) / (0.180 - 0.035), 0.0, 1.0)
    w_edge = w_edge * w_edge * (3.0 - 2.0 * w_edge)
    
    # Edge enhanced
    edge_dithered = np.clip(luma_lifted + fine_dither, dark_lift_min, 1.0)
    
    # Final mix
    final_luma = np.clip(dot_luma * (1.0 - w_edge) + edge_dithered * w_edge, dark_lift_min, 1.0)
    
    # Dark dither pulse
    dark_dither = noise_val * (dark_lift_min * 0.40) * (1.0 - luma_lifted)
    final_luma = np.clip(final_luma + dark_dither, dark_lift_min, 1.0)
    
    return final_luma

if __name__ == "__main__":
    ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png"
    mc_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip2_minecraft.png"
    
    for name, p in [("ds", ds_path), ("mc", mc_path)]:
        f0 = sim_shader_full(p, frame=0)
        f1 = sim_shader_full(p, frame=1)
        d = np.abs(f1 - f0)
        print(f"=== {name} ===")
        print(f"Min: {f0.min():.4f} (8-bit: {int(f0.min()*255)}), Max: {f0.max():.4f}")
        print(f"Zero count: {(f0 < 0.01).sum()}")
        print(f"Dead black count (<0.07): {(f0 < 0.07).sum()}")
        print(f"Mean delta: {d.mean():.4f}")
        print(f"Agitation ratio (>0.02): {(d > 0.02).mean()*100:.2f}%")
        
        # Save crops and zooms
        h, w = f0.shape
        cy, cx = h//2, w//2
        crop_box = slice(cy-100, cy+100), slice(cx-150, cx+150)
        zoom_box = slice(cy-35, cy+35), slice(cx-35, cx+35)
        
        c0 = (f0[crop_box] * 255).astype(np.uint8)
        z0 = (f0[zoom_box] * 255).astype(np.uint8)
        z1 = (f1[zoom_box] * 255).astype(np.uint8)
        z_avg = (((f0[zoom_box] + f1[zoom_box]) * 0.5) * 255).astype(np.uint8)
        
        Image.fromarray(c0).save(os.path.join(brain_dir, f"sim_{name}_fixed_crop.png"))
        Image.fromarray(z0).resize((70*4, 70*4), Image.NEAREST).save(os.path.join(brain_dir, f"sim_{name}_fixed_z0.png"))
        Image.fromarray(z1).resize((70*4, 70*4), Image.NEAREST).save(os.path.join(brain_dir, f"sim_{name}_fixed_z1.png"))
        Image.fromarray(z_avg).resize((70*4, 70*4), Image.NEAREST).save(os.path.join(brain_dir, f"sim_{name}_fixed_avg.png"))
