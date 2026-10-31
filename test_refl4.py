import numpy as np
from PIL import Image, ImageDraw
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

m16 = np.array([
    12.0,  8.0,  9.0, 13.0,
     7.0,  0.0,  1.0,  5.0,
     6.0,  2.0,  3.0,  4.0,
    11.0, 10.0, 14.0, 15.0
], dtype=np.float32).reshape((4, 4))
m16_norm = (m16 + 0.5) / 16.0

def apply_refl4(lx, ly, s):
    # 4 Klein-4 symmetries (preserve aspect ratio: no 90 deg transposition!):
    # s=0: identity (lx, ly)
    # s=1: horizontal flip (3 - lx, ly)
    # s=2: vertical flip (lx, 3 - ly)
    # s=3: 180 deg rotation (3 - lx, 3 - ly)
    if s == 0:   return lx, ly
    elif s == 1: return 3 - lx, ly
    elif s == 2: return lx, 3 - ly
    else:        return 3 - lx, 3 - ly

def sim_refl4(raw_path, mode='refl4'):
    img = Image.open(raw_path).convert('L')
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
    
    # Float hash
    block_f = bx.astype(np.float32) * 12.9898 + by.astype(np.float32) * 78.233
    h_val = np.fmod(np.abs(np.sin(block_f) * 43758.5453), 1.0)
    
    th_map = np.zeros((h, w), dtype=np.float32)
    if mode == 'fixed':
        th_map = m16_norm[in_by, in_bx]
    elif mode == 'refl4':
        sym_idx = np.floor(h_val * 4.0).astype(np.int32)
        sym_idx = np.clip(sym_idx, 0, 3)
        for s in range(4):
            mask = (sym_idx == s)
            if not np.any(mask): continue
            lx = in_bx[mask]
            ly = in_by[mask]
            rx, ry = apply_refl4(lx, ly, s)
            th_map[mask] = m16_norm[ry, rx]
            
    dot_val = np.clip(0.5 + (luma_lifted - th_map) / 0.08, 0.0, 1.0)
    final_luma = 0.08 + 0.92 * dot_val
    return final_luma

if __name__ == "__main__":
    mc_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip2_minecraft.png"
    ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png"
    
    for name, p in [("mc", mc_path), ("ds1", ds_path)]:
        fixed = sim_refl4(p, mode='fixed')
        refl4 = sim_refl4(p, mode='refl4')
        
        im_f = Image.fromarray((fixed * 255).astype(np.uint8))
        im_r = Image.fromarray((refl4 * 255).astype(np.uint8))
        
        h, w = fixed.shape
        cx, cy = w // 2, h // 2
        
        zf = im_f.crop((cx-40, cy-40, cx+40, cy+40)).resize((320, 320), Image.NEAREST)
        zr = im_r.crop((cx-40, cy-40, cx+40, cy+40)).resize((320, 320), Image.NEAREST)
        
        comp = Image.new('RGB', (660, 360), (240, 240, 240))
        comp.paste(zf.convert('RGB'), (0, 40))
        comp.paste(zr.convert('RGB'), (340, 40))
        
        draw = ImageDraw.Draw(comp)
        draw.text((10, 10), f"Fixed: All Dots Missing Same Corner", fill=(180, 0, 0))
        draw.text((350, 10), f"4-Way Reflection: Random Growth Corner (Aspect-Preserved)", fill=(0, 120, 0))
        
        out_p = os.path.join(brain_dir, f"test_refl4_{name}_zoom.png")
        comp.save(out_p)
        print(f"Saved {out_p}")
