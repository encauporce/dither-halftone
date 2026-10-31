import numpy as np
from PIL import Image, ImageDraw
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

# 4x4 Cluster Halftone Matrix (16 levels)
m16 = np.array([
    12.0,  8.0,  9.0, 13.0,
     7.0,  0.0,  1.0,  5.0,
     6.0,  2.0,  3.0,  4.0,
    11.0, 10.0, 14.0, 15.0
], dtype=np.float32).reshape((4, 4))
m16_norm = (m16 + 0.5) / 16.0

def get_threshold_fixed(lx, ly):
    return m16_norm[ly, lx]

def get_threshold_random_growth(lx, ly, sym_idx):
    # 8 D4 symmetries about center (1.5, 1.5)
    # lx, ly in {0, 1, 2, 3}
    if sym_idx == 0:   # 0 deg
        tx, ty = lx, ly
    elif sym_idx == 1: # 90 deg CW
        tx, ty = 3 - ly, lx
    elif sym_idx == 2: # 180 deg
        tx, ty = 3 - lx, 3 - ly
    elif sym_idx == 3: # 270 deg CW
        tx, ty = ly, 3 - lx
    elif sym_idx == 4: # Horizontal flip
        tx, ty = 3 - lx, ly
    elif sym_idx == 5: # Vertical flip
        tx, ty = lx, 3 - ly
    elif sym_idx == 6: # Transpose (diagonal)
        tx, ty = ly, lx
    else:              # Anti-transpose
        tx, ty = 3 - ly, 3 - lx
    return m16_norm[ty, tx]

def sim_vertical_grid(raw_img_path, randomize_growth=True, dark_lift_min=0.08, dot_softness=0.08, frame=0):
    img = Image.open(raw_img_path).convert('L')
    c = np.array(img, dtype=np.float32) / 255.0
    h, w = c.shape
    
    # 1. Dark lift curve
    toe = np.sqrt(np.maximum(c, 0.0)) * ((1.0 - c) ** 2.0) * 0.12
    norm_curve = np.clip((c ** 0.60) + toe, 0.0, 1.0)
    luma_lifted = dark_lift_min + (1.0 - dark_lift_min) * norm_curve
    
    # 2. Coordinates
    yy, xx = np.indices((h, w), dtype=np.int32)
    
    # 3. 2-Phase 15Hz master clock shift (0,0) <-> (2,2)
    # Applied globally across all blocks so master lattice is 100% synchronous!
    if (frame % 2) == 1:
        shift_x, shift_y = 2, 2
    else:
        shift_x, shift_y = 0, 0
        
    shifted_x = (xx + shift_x)
    shifted_y = (yy + shift_y)
    
    in_block_x = shifted_x % 4
    in_block_y = shifted_y % 4
    
    block_id_x = shifted_x // 4
    block_id_y = shifted_y // 4
    
    # Float hash for random symmetry per block
    # Standard GPU sin-fract PRNG
    block_f = block_id_x.astype(np.float32) * 12.9898 + block_id_y.astype(np.float32) * 78.233
    h_val = np.fmod(np.abs(np.sin(block_f) * 43758.5453), 1.0)
    sym_idx = np.floor(h_val * 8.0).astype(np.int32)
    sym_idx = np.clip(sym_idx, 0, 7)
    
    # Compute threshold map
    th_map = np.zeros((h, w), dtype=np.float32)
    if not randomize_growth:
        th_map = m16_norm[in_block_y, in_block_x]
    else:
        # Vectorized lookup for the 8 symmetries
        for s in range(8):
            mask = (sym_idx == s)
            if not np.any(mask):
                continue
            lx = in_block_x[mask]
            ly = in_block_y[mask]
            if s == 0:   tx, ty = lx, ly
            elif s == 1: tx, ty = 3 - ly, lx
            elif s == 2: tx, ty = 3 - lx, 3 - ly
            elif s == 3: tx, ty = ly, 3 - lx
            elif s == 4: tx, ty = 3 - lx, ly
            elif s == 5: tx, ty = lx, 3 - ly
            elif s == 6: tx, ty = ly, lx
            else:        tx, ty = 3 - ly, 3 - lx
            th_map[mask] = m16_norm[ty, tx]
            
    # 4. IGN temporal blue noise for smooth transitions
    magic = np.array([0.06711056, 0.00583715, 52.9829189])
    t_offset = np.fmod(frame * 0.6180339887, 1.0)
    dot_xy = xx.astype(np.float32) * magic[0] + yy.astype(np.float32) * magic[1] + t_offset
    ign = np.fmod(magic[2] * np.fmod(dot_xy, 1.0), 1.0) - 0.5
    
    dark_boost = 1.0 + 1.60 * (1.0 - luma_lifted)
    bright_taper = np.clip((luma_lifted - 0.72) / (0.96 - 0.72), 0.0, 1.0)
    bright_taper = 1.0 - (bright_taper * bright_taper * (3.0 - 2.0 * bright_taper))
    fine_dither = ign * (1.0 / 16.0) * 0.65 * dark_boost * bright_taper
    target_luma = np.clip(luma_lifted + fine_dither, 0.0, 1.0)
    
    # 5. Halftone dot
    dot_val = np.clip(0.5 + (target_luma - th_map) / dot_softness, 0.0, 1.0)
    
    # HARD-LOCK against dead black
    dot_luma = dark_lift_min + (1.0 - dark_lift_min) * dot_val
    
    # 6. Sobel edge protection
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
    dark_dither = ign * (dark_lift_min * 0.40) * (1.0 - luma_lifted)
    final_luma = np.clip(final_luma + dark_dither, dark_lift_min, 1.0)
    
    return final_luma

if __name__ == "__main__":
    # Test on gradient to visually inspect dot growth
    grad_h, grad_w = 200, 320
    grad_arr = np.tile(np.linspace(0.1, 0.9, grad_w, dtype=np.float32), (grad_h, 1))
    grad_img = Image.fromarray((grad_arr * 255).astype(np.uint8))
    grad_path = os.path.join(brain_dir, "test_grad_input.png")
    grad_img.save(grad_path)
    
    # 1. Fixed vertical dot structure
    res_fixed = sim_vertical_grid(grad_path, randomize_growth=False)
    # 2. Random growth vertical dot structure
    res_rand = sim_vertical_grid(grad_path, randomize_growth=True)
    
    # Save comparisons
    im_fixed = Image.fromarray((res_fixed * 255).astype(np.uint8))
    im_rand = Image.fromarray((res_rand * 255).astype(np.uint8))
    
    # Zoom center 80x80 -> 320x320
    cx, cy = grad_w // 2, grad_h // 2
    z_fixed = im_fixed.crop((cx-40, cy-40, cx+40, cy+40)).resize((320, 320), Image.NEAREST)
    z_rand = im_rand.crop((cx-40, cy-40, cx+40, cy+40)).resize((320, 320), Image.NEAREST)
    
    comp = Image.new('RGB', (660, 360), (240, 240, 240))
    comp.paste(z_fixed.convert('RGB'), (0, 40))
    comp.paste(z_rand.convert('RGB'), (340, 40))
    
    draw = ImageDraw.Draw(comp)
    draw.text((10, 10), "Fixed Growth Direction (Identical Leaning/Weave)", fill=(180, 0, 0))
    draw.text((350, 10), "Random Growth Direction (Organic, Centered Dots)", fill=(0, 120, 0))
    
    out_comp = os.path.join(brain_dir, "comparison_fixed_vs_random_growth.png")
    comp.save(out_comp)
    print("Saved comparison_fixed_vs_random_growth.png")
