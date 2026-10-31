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

def test_full_frame(mode='refl4'):
    # Test on death stranding raw frame
    ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png"
    img = Image.open(ds_path).convert('L')
    c = np.array(img, dtype=np.float32) / 255.0
    h, w = c.shape
    
    # Darkness lift
    toe = np.sqrt(np.maximum(c, 0.0)) * ((1.0 - c) ** 2.0) * 0.12
    norm_curve = np.clip((c ** 0.60) + toe, 0.0, 1.0)
    luma_lifted = 0.08 + (1.0 - 0.08) * norm_curve
    
    yy, xx = np.indices((h, w), dtype=np.int32)
    in_bx = xx % 4
    in_by = yy % 4
    bx = xx // 4
    by = yy // 4
    
    # Safe float hash
    block_f = bx.astype(np.float32) * 12.9898 + by.astype(np.float32) * 78.233
    h_val = np.fmod(np.abs(np.sin(block_f) * 43758.5453), 1.0)
    
    th_map = np.zeros((h, w), dtype=np.float32)
    
    if mode == 'fixed':
        th_map = m16_norm[in_by, in_bx]
    elif mode == 'refl4': # 4 reflections (preserve H/V aspect)
        sym_idx = np.clip(np.floor(h_val * 4.0).astype(np.int32), 0, 3)
        for s in range(4):
            mask = (sym_idx == s)
            if not np.any(mask): continue
            lx = in_bx[mask]
            ly = in_by[mask]
            if s == 0:   rx, ry = lx, ly
            elif s == 1: rx, ry = 3 - lx, ly
            elif s == 2: rx, ry = lx, 3 - ly
            else:        rx, ry = 3 - lx, 3 - ly
            th_map[mask] = m16_norm[ry, rx]
    elif mode == 'd4': # 8 symmetries
        sym_idx = np.clip(np.floor(h_val * 8.0).astype(np.int32), 0, 7)
        for s in range(8):
            mask = (sym_idx == s)
            if not np.any(mask): continue
            lx = in_bx[mask]
            ly = in_by[mask]
            if s == 0:   rx, ry = lx, ly
            elif s == 1: rx, ry = 3 - ly, lx
            elif s == 2: rx, ry = 3 - lx, 3 - ly
            elif s == 3: rx, ry = ly, 3 - lx
            elif s == 4: rx, ry = 3 - lx, ly
            elif s == 5: rx, ry = lx, 3 - ly
            elif s == 6: rx, ry = ly, lx
            else:        rx, ry = 3 - ly, 3 - lx
            th_map[mask] = m16_norm[ry, rx]
            
    # Softness = 0.07
    dot_val = np.clip(0.5 + (luma_lifted - th_map) / 0.07, 0.0, 1.0)
    final_luma = 0.08 + 0.92 * dot_val
    return final_luma

f_fixed = test_full_frame('fixed')
f_refl4 = test_full_frame('refl4')
f_d4 = test_full_frame('d4')

h, w = f_fixed.shape
cx, cy = w // 2, h // 2

crop_box = (cx - 175, cy - 125, cx + 175, cy + 125)
zoom_box = (cx - 40, cy - 40, cx + 40, cy + 40)

im_fix = Image.fromarray((f_fixed * 255).astype(np.uint8))
im_r4  = Image.fromarray((f_refl4 * 255).astype(np.uint8))
im_d4  = Image.fromarray((f_d4 * 255).astype(np.uint8))

z_fix = im_fix.crop(zoom_box).resize((320, 320), Image.NEAREST)
z_r4  = im_r4.crop(zoom_box).resize((320, 320), Image.NEAREST)
z_d4  = im_d4.crop(zoom_box).resize((320, 320), Image.NEAREST)

# 3-way comparison
comp = Image.new('RGB', (980, 360), (240, 240, 240))
comp.paste(z_fix.convert('RGB'), (0, 40))
comp.paste(z_r4.convert('RGB'), (330, 40))
comp.paste(z_d4.convert('RGB'), (660, 40))

from PIL import ImageDraw
draw = ImageDraw.Draw(comp)
draw.text((10, 10), "1. Fixed (All Leaning Same)", fill=(180, 0, 0))
draw.text((340, 10), "2. 4-Way Reflection (Aspect-Preserved)", fill=(0, 120, 0))
draw.text((670, 10), "3. 8-Way D4 (Full Rotations)", fill=(0, 0, 180))

out_p = os.path.join(brain_dir, "comparison_fixed_vs_refl4_vs_d4.png")
comp.save(out_p)
print(f"Saved {out_p}")
