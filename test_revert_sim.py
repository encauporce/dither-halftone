import numpy as np
from PIL import Image

m16 = np.array([
    12.0,  8.0,  9.0, 13.0,
     7.0,  0.0,  1.0,  5.0,
     6.0,  2.0,  3.0,  4.0,
    11.0, 10.0, 14.0, 15.0
], dtype=np.float32).reshape((4, 4))
m16_norm = (m16 + 0.5) / 16.0

def test_optb_refl4(img_path, frame):
    img = Image.open(img_path).convert('L')
    c = np.array(img, dtype=np.float32) / 255.0
    h, w = c.shape
    
    # 1. Exact Option B dark lift parameters (DARK_LIFT_MIN = 0.050)
    DARK_LIFT_MIN = 0.050
    DARK_LIFT_GAMMA = 0.60
    SHADOW_TOE_BOOST = 0.12
    TEMPORAL_DARK_BOOST = 1.60
    DOT_SOFTNESS = 0.06
    A_SPATIAL = 0.65
    EDGE_MIN = 0.035
    EDGE_MAX = 0.180
    EDGE_BOOST = 1.15
    
    toe = np.sqrt(np.maximum(c, 0.0)) * ((1.0 - c) ** 2.0) * SHADOW_TOE_BOOST
    norm_curve = np.clip((c ** DARK_LIFT_GAMMA) + toe, 0.0, 1.0)
    luma_lifted = DARK_LIFT_MIN + (1.0 - DARK_LIFT_MIN) * norm_curve
    
    yy, xx = np.indices((h, w), dtype=np.float32)
    ipos_x = xx.astype(np.int32)
    ipos_y = yy.astype(np.int32)
    
    # 4-Way random growth direction per 4x4 block
    bx = np.floor(xx * 0.25)
    by = np.floor(yy * 0.25)
    h_rand = np.fmod(np.abs(np.sin(bx * 12.9898 + by * 78.233) * 43758.5453), 1.0)
    sym_idx = np.clip(np.floor(h_rand * 4.0).astype(np.int32), 0, 3)
    
    in_bx = ipos_x & 3
    in_by = ipos_y & 3
    
    loc_x = in_bx.copy()
    loc_y = in_by.copy()
    loc_x[sym_idx == 1] = 3 - in_bx[sym_idx == 1]
    loc_y[sym_idx == 2] = 3 - in_by[sym_idx == 2]
    loc_x[sym_idx == 3] = 3 - in_bx[sym_idx == 3]
    loc_y[sym_idx == 3] = 3 - in_by[sym_idx == 3]
    
    # 15Hz 2-phase anti-ghosting shift (0,0) <-> (2,2)
    shift_x = 2 if (frame % 2 == 1) else 0
    shift_y = 2 if (frame % 2 == 1) else 0
    
    p_mac_x = (loc_x + shift_x) & 3
    p_mac_y = (loc_y + shift_y) & 3
    th_macro = m16_norm[p_mac_y, p_mac_x]
    
    # IGN temporal blue noise
    magic = np.array([0.06711056, 0.00583715, 52.9829189])
    t_offset = np.fmod(float(frame) * 0.6180339887, 1.0)
    dot_xy = xx * magic[0] + yy * magic[1] + t_offset
    noise_val = np.fmod(magic[2] * np.fmod(dot_xy, 1.0), 1.0) - 0.5
    
    dark_boost = 1.0 + TEMPORAL_DARK_BOOST * (1.0 - luma_lifted)
    bright_taper = np.clip((luma_lifted - 0.72) / (0.96 - 0.72), 0.0, 1.0)
    bright_taper = 1.0 - (bright_taper * bright_taper * (3.0 - 2.0 * bright_taper))
    fine_dither = noise_val * (1.0 / 16.0) * A_SPATIAL * dark_boost * bright_taper
    target_luma = np.clip(luma_lifted + fine_dither, 0.0, 1.0)
    
    # Original Option B dot_val: pure deep black 0.0! NO LIFT! NO CLAMP!
    dot_val = np.clip(0.5 + (target_luma - th_macro) / DOT_SOFTNESS, 0.0, 1.0)
    
    # Sobel
    cp = np.pad(c, 1, mode='edge')
    tl = cp[0:h, 0:w]; t  = cp[0:h, 1:w+1]; tr = cp[0:h, 2:w+2]
    l  = cp[1:h+1, 0:w];                     r  = cp[1:h+1, 2:w+2]
    bl = cp[2:h+2, 0:w]; b  = cp[2:h+2, 1:w+1]; br = cp[2:h+2, 2:w+2]
    gx = (tr + 2.0 * r + br) - (tl + 2.0 * l + bl)
    gy = (bl + 2.0 * b + br) - (tl + 2.0 * t + tr)
    grad = np.sqrt(gx * gx + gy * gy)
    w_edge = np.clip((grad - EDGE_MIN) / (EDGE_MAX - EDGE_MIN), 0.0, 1.0)
    w_edge = w_edge * w_edge * (3.0 - 2.0 * w_edge)
    
    mean_neighbor = (tl + t + tr + l + r + bl + b + br) / 8.0
    high_pass = c - mean_neighbor
    edge_enhanced = np.clip(luma_lifted + high_pass * (EDGE_BOOST - 1.0), 0.0, 1.0)
    edge_dithered = np.clip(edge_enhanced + fine_dither, 0.0, 1.0)
    
    # Exact Option B final mix: pure 0.0 black allowed!
    final_luma = np.clip(dot_val * (1.0 - w_edge) + edge_dithered * w_edge, 0.0, 1.0)
    return final_luma

f0 = test_optb_refl4(r'C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png', 0)
f1 = test_optb_refl4(r'C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png', 1)

print('Min:', f0.min(), 'Max:', f0.max())
print('Zeros at frame 0:', (f0 == 0).sum())
delta = np.abs(f1 - f0)
print('Inter-frame agitation delta:', delta.mean())
print('Pixels actively flipping (>0.05):', (delta > 0.05).mean() * 100, '%')
