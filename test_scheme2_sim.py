import numpy as np
from PIL import Image, ImageDraw
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"
ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png"

m16 = np.array([
    12.0,  8.0,  9.0, 13.0,
     7.0,  0.0,  1.0,  5.0,
     6.0,  2.0,  3.0,  4.0,
    11.0, 10.0, 14.0, 15.0
], dtype=np.float32).reshape((4, 4))
m16_norm = (m16 + 0.5) / 16.0

def run_scheme2_sim(img_path, hp_gain=1.8, dark_boost=1.5, frame=0):
    img = Image.open(img_path).convert('L')
    c = np.array(img, dtype=np.float32) / 255.0
    h, w = c.shape
    
    DARK_LIFT_MIN = 0.050
    DARK_LIFT_GAMMA = 0.60
    SHADOW_TOE_BOOST = 0.12
    TEMPORAL_DARK_BOOST = 1.60
    DOT_SOFTNESS = 0.06
    A_SPATIAL = 0.65
    EDGE_BOOST = 1.15
    
    toe = np.sqrt(np.maximum(c, 0.0)) * ((1.0 - c) ** 2.0) * SHADOW_TOE_BOOST
    norm_curve = np.clip((c ** DARK_LIFT_GAMMA) + toe, 0.0, 1.0)
    luma_lifted = DARK_LIFT_MIN + (1.0 - DARK_LIFT_MIN) * norm_curve
    
    yy, xx = np.indices((h, w), dtype=np.float32)
    in_bx = xx.astype(np.int32) & 3
    in_by = yy.astype(np.int32) & 3
    
    shift_x = 2 if (frame % 2 == 1) else 0
    shift_y = 2 if (frame % 2 == 1) else 0
    
    p_mac_x = (in_bx + shift_x) & 3
    p_mac_y = (in_by + shift_y) & 3
    th_macro = m16_norm[p_mac_y, p_mac_x]
    
    magic = np.array([0.06711056, 0.00583715, 52.9829189])
    t_offset = np.fmod(float(frame) * 0.6180339887, 1.0)
    dot_xy = xx * magic[0] + yy * magic[1] + t_offset
    noise_val = np.fmod(magic[2] * np.fmod(dot_xy, 1.0), 1.0) - 0.5
    
    dark_boost_t = 1.0 + TEMPORAL_DARK_BOOST * (1.0 - luma_lifted)
    bright_taper = np.clip((luma_lifted - 0.72) / (0.96 - 0.72), 0.0, 1.0)
    bright_taper = 1.0 - (bright_taper * bright_taper * (3.0 - 2.0 * bright_taper))
    fine_dither = noise_val * (1.0 / 16.0) * A_SPATIAL * dark_boost_t * bright_taper
    
    # 8-neighbor mean and high-pass
    cp = np.pad(c, 1, mode='edge')
    tl = cp[0:h, 0:w]; t  = cp[0:h, 1:w+1]; tr = cp[0:h, 2:w+2]
    l  = cp[1:h+1, 0:w];                     r  = cp[1:h+1, 2:w+2]
    bl = cp[2:h+2, 0:w]; b  = cp[2:h+2, 1:w+1]; br = cp[2:h+2, 2:w+2]
    mean_neighbor = (tl + t + tr + l + r + bl + b + br) / 8.0
    high_pass = c - mean_neighbor
    
    # Scheme 2 High-Pass Injection directly into halftone input
    hp_eff = high_pass * hp_gain * (1.0 + dark_boost * (1.0 - luma_lifted))
    target_luma = np.clip(luma_lifted + fine_dither + hp_eff, 0.0, 1.0)
    
    dot_val = np.clip(0.5 + (target_luma - th_macro) / DOT_SOFTNESS, 0.0, 1.0)
    
    # Sobel
    gx = (tr + 2.0 * r + br) - (tl + 2.0 * l + bl)
    gy = (bl + 2.0 * b + br) - (tl + 2.0 * t + tr)
    grad = np.sqrt(gx * gx + gy * gy)
    
    # Linear edge or Weber edge
    # Let's test standard linear edge so we isolate Scheme 2's pure effect on halftone dots
    w_edge = np.clip((grad - 0.035) / (0.180 - 0.035), 0.0, 1.0)
    w_edge = w_edge * w_edge * (3.0 - 2.0 * w_edge)
    
    edge_enhanced = np.clip(luma_lifted + high_pass * (EDGE_BOOST - 1.0), 0.0, 1.0)
    edge_dithered = np.clip(edge_enhanced + fine_dither, 0.0, 1.0)
    
    final_luma = np.clip(dot_val * (1.0 - w_edge) + edge_dithered * w_edge, 0.0, 1.0)
    return final_luma

# Test with different gains: 0.0 (baseline), 1.2, 1.8
f_base = run_scheme2_sim(ds_path, hp_gain=0.0)
f_s2_med = run_scheme2_sim(ds_path, hp_gain=1.2)
f_s2_high = run_scheme2_sim(ds_path, hp_gain=1.8)

# Crop dark fissure region
crop_box = slice(350, 550), slice(750, 1150)
zoom_box = slice(400, 480), slice(800, 880)

Image.fromarray((f_base[zoom_box] * 255).astype(np.uint8)).resize((320, 320), Image.NEAREST).save(os.path.join(brain_dir, 'sim_s2_base_zoom.png'))
Image.fromarray((f_s2_med[zoom_box] * 255).astype(np.uint8)).resize((320, 320), Image.NEAREST).save(os.path.join(brain_dir, 'sim_s2_med_zoom.png'))
Image.fromarray((f_s2_high[zoom_box] * 255).astype(np.uint8)).resize((320, 320), Image.NEAREST).save(os.path.join(brain_dir, 'sim_s2_high_zoom.png'))

comp = Image.new('RGB', (1000, 380), (255, 255, 255))
draw = ImageDraw.Draw(comp)
draw.text((20, 15), 'Baseline (HP Gain = 0)', fill=(200, 0, 0))
draw.text((360, 15), 'Scheme 2 (HP Gain = 1.2)', fill=(0, 120, 0))
draw.text((700, 15), 'Scheme 2 (HP Gain = 1.8)', fill=(0, 80, 200))

comp.paste(Image.open(os.path.join(brain_dir, 'sim_s2_base_zoom.png')).convert('RGB'), (15, 45))
comp.paste(Image.open(os.path.join(brain_dir, 'sim_s2_med_zoom.png')).convert('RGB'), (350, 45))
comp.paste(Image.open(os.path.join(brain_dir, 'sim_s2_high_zoom.png')).convert('RGB'), (685, 45))

comp.save(os.path.join(brain_dir, 'sim_scheme2_gains_compare.png'))
print('Saved Scheme 2 simulation.')
