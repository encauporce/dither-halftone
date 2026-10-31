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

def apply_d4(lx, ly, s):
    # s in 0..7
    if s == 0:   return lx, ly
    elif s == 1: return 3 - ly, lx
    elif s == 2: return 3 - lx, 3 - ly
    elif s == 3: return ly, 3 - lx
    elif s == 4: return 3 - lx, ly
    elif s == 5: return lx, 3 - ly
    elif s == 6: return ly, lx
    else:        return 3 - ly, 3 - lx

def sim_d4_clean(raw_path, use_d4=True):
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
    
    # Float hash for symmetry
    block_f = bx.astype(np.float32) * 12.9898 + by.astype(np.float32) * 78.233
    h_val = np.fmod(np.abs(np.sin(block_f) * 43758.5453), 1.0)
    sym_idx = np.floor(h_val * 8.0).astype(np.int32)
    sym_idx = np.clip(sym_idx, 0, 7)
    
    th_map = np.zeros((h, w), dtype=np.float32)
    if not use_d4:
        th_map = m16_norm[in_by, in_bx]
    else:
        for s in range(8):
            mask = (sym_idx == s)
            if not np.any(mask): continue
            lx = in_bx[mask]
            ly = in_by[mask]
            rx, ry = apply_d4(lx, ly, s)
            th_map[mask] = m16_norm[ry, rx]
            
    dot_val = np.clip(0.5 + (luma_lifted - th_map) / 0.08, 0.0, 1.0)
    final_luma = 0.08 + 0.92 * dot_val
    return final_luma

if __name__ == "__main__":
    mc_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip2_minecraft.png"
    ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png"
    
    for name, p in [("mc", mc_path), ("ds1", ds_path)]:
        fixed = sim_d4_clean(p, use_d4=False)
        d4_clean = sim_d4_clean(p, use_d4=True)
        
        im_f = Image.fromarray((fixed * 255).astype(np.uint8))
        im_d4 = Image.fromarray((d4_clean * 255).astype(np.uint8))
        
        h, w = fixed.shape
        cx, cy = w // 2, h // 2
        
        zf = im_f.crop((cx-40, cy-40, cx+40, cy+40)).resize((320, 320), Image.NEAREST)
        zd = im_d4.crop((cx-40, cy-40, cx+40, cy+40)).resize((320, 320), Image.NEAREST)
        
        comp = Image.new('RGB', (660, 360), (240, 240, 240))
        comp.paste(zf.convert('RGB'), (0, 40))
        comp.paste(zd.convert('RGB'), (340, 40))
        
        draw = ImageDraw.Draw(comp)
        draw.text((10, 10), f"Fixed Vertical Grid: Identical Leaning", fill=(180, 0, 0))
        draw.text((350, 10), f"Vertical Grid + Random Growth: D4 Rotations", fill=(0, 120, 0))
        
        out_p = os.path.join(brain_dir, f"test_d4_clean_{name}_zoom.png")
        comp.save(out_p)
        print(f"Saved {out_p}")
