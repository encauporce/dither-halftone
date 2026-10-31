import numpy as np
from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

m16 = np.array([
    12.0,  8.0,  9.0, 13.0,
     7.0,  0.0,  1.0,  5.0,
     6.0,  2.0,  3.0,  4.0,
    11.0, 10.0, 14.0, 15.0
], dtype=np.float32).reshape((4, 4))
m16_norm = (m16 + 0.5) / 16.0

def run_refl4_full(raw_path, frame=0, dark_lift_min=0.080, dot_softness=0.075):
    img = Image.open(raw_path).convert('L')
    c = np.array(img, dtype=np.float32) / 255.0
    h, w = c.shape
    
    # 1. Dark lift curve
    toe = np.sqrt(np.maximum(c, 0.0)) * ((1.0 - c) ** 2.0) * 0.12
    norm_curve = np.clip((c ** 0.60) + toe, 0.0, 1.0)
    luma_lifted = dark_lift_min + (1.0 - dark_lift_min) * norm_curve
    
    # 2. Coordinates
    yy, xx = np.indices((h, w), dtype=np.int32)
    in_bx = xx % 4
    in_by = yy % 4
    bx = xx // 4
    by = yy // 4
    
    # 3. Master clock shift (15Hz 2-phase swap)
    if (frame % 2) == 1:
        shift_x, shift_y = 2, 2
    else:
        shift_x, shift_y = 0, 0
        
    # 4. Safe float hash for 4-way random growth direction
    block_f = bx.astype(np.float32) * 12.9898 + by.astype(np.float32) * 78.233
    h_val = np.fmod(np.abs(np.sin(block_f) * 43758.5453), 1.0)
    sym_idx = np.clip(np.floor(h_val * 4.0).astype(np.int32), 0, 3)
    
    # Apply reflection to in_block
    loc_x = in_bx.copy()
    loc_y = in_by.copy()
    
    # sym 1: H-flip
    mask1 = (sym_idx == 1)
    loc_x[mask1] = 3 - in_bx[mask1]
    
    # sym 2: V-flip
    mask2 = (sym_idx == 2)
    loc_y[mask2] = 3 - in_by[mask2]
    
    # sym 3: 180 deg
    mask3 = (sym_idx == 3)
    loc_x[mask3] = 3 - in_bx[mask3]
    loc_y[mask3] = 3 - in_by[mask3]
    
    # Shift with master clock
    p_mac_x = (loc_x + shift_x) % 4
    p_mac_y = (loc_y + shift_y) % 4
    
    th_macro = m16_norm[p_mac_y, p_mac_x]
    
    # 5. Temporal IGN blue noise
    magic = np.array([0.06711056, 0.00583715, 52.9829189])
    t_offset = np.fmod(frame * 0.6180339887, 1.0)
    dot_xy = xx.astype(np.float32) * magic[0] + yy.astype(np.float32) * magic[1] + t_offset
    noise_val = np.fmod(magic[2] * np.fmod(dot_xy, 1.0), 1.0) - 0.5
    
    dark_boost = 1.0 + 1.60 * (1.0 - luma_lifted)
    bright_taper = np.clip((luma_lifted - 0.72) / (0.96 - 0.72), 0.0, 1.0)
    bright_taper = 1.0 - (bright_taper * bright_taper * (3.0 - 2.0 * bright_taper))
    fine_dither = noise_val * (1.0 / 16.0) * 0.65 * dark_boost * bright_taper
    target_luma = np.clip(luma_lifted + fine_dither, 0.0, 1.0)
    
    # 6. Halftone dot
    dot_val = np.clip(0.5 + (target_luma - th_macro) / dot_softness, 0.0, 1.0)
    dot_luma = dark_lift_min + (1.0 - dark_lift_min) * dot_val
    
    # 7. Sobel edge protection
    cp = np.pad(c, 1, mode='edge')
    tl = cp[0:h, 0:w]; t  = cp[0:h, 1:w+1]; tr = cp[0:h, 2:w+2]
    l  = cp[1:h+1, 0:w];                     r  = cp[1:h+1, 2:w+2]
    bl = cp[2:h+2, 0:w]; b  = cp[2:h+2, 1:w+1]; br = cp[2:h+2, 2:w+2]
    gx = (tr + 2.0 * r + br) - (tl + 2.0 * l + bl)
    gy = (bl + 2.0 * b + br) - (tl + 2.0 * t + tr)
    grad = np.sqrt(gx * gx + gy * gy)
    w_edge = np.clip((grad - 0.035) / (0.180 - 0.035), 0.0, 1.0)
    w_edge = w_edge * w_edge * (3.0 - 2.0 * w_edge)
    
    edge_enhanced = np.clip(luma_lifted + (c - (tl+t+tr+l+r+bl+b+br)/8.0) * 0.15, dark_lift_min, 1.0)
    edge_dithered = np.clip(edge_enhanced + fine_dither, dark_lift_min, 1.0)
    
    final_luma = np.clip(dot_luma * (1.0 - w_edge) + edge_dithered * w_edge, dark_lift_min, 1.0)
    
    # Micro agitation in dark areas
    dark_dither = noise_val * (dark_lift_min * 0.40) * (1.0 - luma_lifted)
    final_luma = np.clip(final_luma + dark_dither, dark_lift_min, 1.0)
    
    return final_luma

if __name__ == "__main__":
    ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png"
    mc_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip2_minecraft.png"
    
    for name, p in [("ds", ds_path), ("mc", mc_path)]:
        f0 = run_refl4_full(p, frame=0)
        f1 = run_refl4_full(p, frame=1)
        d = np.abs(f1 - f0)
        print(f"=== {name} ===")
        print(f"Min: {f0.min():.4f} (8-bit: {int(f0.min()*255)}), Max: {f0.max():.4f}")
        print(f"Exact zero count: {(f0 < 0.01).sum()}")
        print(f"Agitation delta: {d.mean():.4f}, Ratio (>0.02): {(d > 0.02).mean()*100:.2f}%")
        
        h, w = f0.shape
        cx, cy = w // 2, h // 2
        crop_box = slice(cy-125, cy+125), slice(cx-175, cx+175)
        zoom_box = slice(cy-40, cy+40), slice(cx-40, cx+40)
        
        im_crop = Image.fromarray((f0[crop_box] * 255).astype(np.uint8))
        im_zoom = Image.fromarray((f0[zoom_box] * 255).astype(np.uint8)).resize((320, 320), Image.NEAREST)
        
        im_crop.save(os.path.join(brain_dir, f"test_sim_{name}_refl4_crop.png"))
        im_zoom.save(os.path.join(brain_dir, f"test_sim_{name}_refl4_zoom.png"))
    print("Saved test simulation images.")
