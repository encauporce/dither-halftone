import numpy as np
from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"
ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png"

img = Image.open(ds_path).convert('L')
c = np.array(img, dtype=np.float32) / 255.0
h, w = c.shape

# Current linear Sobel
cp = np.pad(c, 1, mode='edge')
tl = cp[0:h, 0:w]; t  = cp[0:h, 1:w+1]; tr = cp[0:h, 2:w+2]
l  = cp[1:h+1, 0:w];                     r  = cp[1:h+1, 2:w+2]
bl = cp[2:h+2, 0:w]; b  = cp[2:h+2, 1:w+1]; br = cp[2:h+2, 2:w+2]
gx = (tr + 2.0 * r + br) - (tl + 2.0 * l + bl)
gy = (bl + 2.0 * b + br) - (tl + 2.0 * t + tr)
grad_linear = np.sqrt(gx * gx + gy * gy)

# 1. Baseline w_edge
w_edge_linear = np.clip((grad_linear - 0.035) / (0.180 - 0.035), 0.0, 1.0)
w_edge_linear = w_edge_linear * w_edge_linear * (3.0 - 2.0 * w_edge_linear)

# 2. Scheme 1: Weber / Relative Sobel
# In Weber contrast: delta_I / (I + bias)
# Let's test a few formulations
# Formulation A: grad / (c + 0.05)
# When c is bright (~0.8), denominator is ~0.85, grad / 0.85 ~ 1.18 * grad.
# When c is dark (~0.05), denominator is ~0.10, grad / 0.10 ~ 10 * grad.
grad_weber_A = grad_linear / (c + 0.05)
# Calibrated so that in bright areas (c=0.8), grad=0.035 gives grad_weber = 0.035 / 0.85 = 0.041
# And grad=0.18 gives grad_weber = 0.18 / 0.85 = 0.21
w_edge_weber_A = np.clip((grad_weber_A - 0.06) / (0.35 - 0.06), 0.0, 1.0)
w_edge_weber_A = w_edge_weber_A * w_edge_weber_A * (3.0 - 2.0 * w_edge_weber_A)

# Formulation B: Perceptual Sobel on Lifted/Gamma Luma
# Instead of computing Sobel on linear c, compute Sobel on sqrt(c) or c^0.60!
c_perceptual = np.sqrt(np.maximum(c, 0.0))
cp_p = np.pad(c_perceptual, 1, mode='edge')
tl_p = cp_p[0:h, 0:w]; t_p  = cp_p[0:h, 1:w+1]; tr_p = cp_p[0:h, 2:w+2]
l_p  = cp_p[1:h+1, 0:w];                         r_p  = cp_p[1:h+1, 2:w+2]
bl_p = cp_p[2:h+2, 0:w]; b_p  = cp_p[2:h+2, 1:w+1]; br_p = cp_p[2:h+2, 2:w+2]
gx_p = (tr_p + 2.0 * r_p + br_p) - (tl_p + 2.0 * l_p + bl_p)
gy_p = (bl_p + 2.0 * b_p + br_p) - (tl_p + 2.0 * t_p + tr_p)
grad_perceptual = np.sqrt(gx_p * gx_p + gy_p * gy_p)
w_edge_perceptual = np.clip((grad_perceptual - 0.050) / (0.240 - 0.050), 0.0, 1.0)
w_edge_perceptual = w_edge_perceptual * w_edge_perceptual * (3.0 - 2.0 * w_edge_perceptual)

# Formulation C: Adaptive threshold: EDGE_MIN adapts with brightness
# edge_min(c) = 0.015 + 0.035 * c
# edge_max(c) = 0.060 + 0.140 * c
# In dark areas (c=0.05): threshold is [0.017, 0.067]
# In bright areas (c=0.8): threshold is [0.043, 0.172]
th_min = 0.012 + 0.035 * c
th_max = 0.050 + 0.150 * c
w_edge_adaptive = np.clip((grad_linear - th_min) / (th_max - th_min), 0.0, 1.0)
w_edge_adaptive = w_edge_adaptive * w_edge_adaptive * (3.0 - 2.0 * w_edge_adaptive)

# Let's inspect dark areas specifically (where c < 0.15)
dark_mask = (c < 0.15)
print(f"Total dark pixels (c < 0.15): {dark_mask.sum()} ({dark_mask.mean()*100:.1f}%)")
print(f"Linear edge activation in dark: {w_edge_linear[dark_mask].mean()*100:.2f}% (active >0.5: {(w_edge_linear[dark_mask] > 0.5).mean()*100:.2f}%)")
print(f"Weber A activation in dark:     {w_edge_weber_A[dark_mask].mean()*100:.2f}% (active >0.5: {(w_edge_weber_A[dark_mask] > 0.5).mean()*100:.2f}%)")
print(f"Perceptual activation in dark:  {w_edge_perceptual[dark_mask].mean()*100:.2f}% (active >0.5: {(w_edge_perceptual[dark_mask] > 0.5).mean()*100:.2f}%)")
print(f"Adaptive th activation in dark: {w_edge_adaptive[dark_mask].mean()*100:.2f}% (active >0.5: {(w_edge_adaptive[dark_mask] > 0.5).mean()*100:.2f}%)")

# Check flat dark areas to ensure NO false triggers on flat noise
flat_dark = (c < 0.06) & (grad_linear < 0.01)
print(f"Flat dark false trigger (>0.1):")
print(f"  Linear: {(w_edge_linear[flat_dark] > 0.1).mean()*100:.2f}%")
print(f"  Weber A: {(w_edge_weber_A[flat_dark] > 0.1).mean()*100:.2f}%")
print(f"  Adaptive th: {(w_edge_adaptive[flat_dark] > 0.1).mean()*100:.2f}%")
