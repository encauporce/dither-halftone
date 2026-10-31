import numpy as np
from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

def eval_shift(dx, dy, P=4.5):
    # screen grid
    N = 100
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    
    # f0
    u0 = (x + y) * 0.70710678
    v0 = (x - y) * 0.70710678
    cu0 = np.mod(u0, P) - P*0.5
    cv0 = np.mod(v0, P) - P*0.5
    th0 = np.clip((cu0*cu0 + cv0*cv0)/(0.5*P*P), 0.0, 1.0)
    
    # f1 with shift (dx, dy)
    u1 = ((x + dx) + (y + dy)) * 0.70710678
    v1 = ((x + dx) - (y + dy)) * 0.70710678
    cu1 = np.mod(u1, P) - P*0.5
    cv1 = np.mod(v1, P) - P*0.5
    th1 = np.clip((cu1*cu1 + cv1*cv1)/(0.5*P*P), 0.0, 1.0)
    
    # For a flat gray target = 0.5
    d0 = np.clip(0.5 + (0.5 - th0)/0.12, 0.0, 1.0)
    d1 = np.clip(0.5 + (0.5 - th1)/0.12, 0.0, 1.0)
    
    avg = (d0 + d1) * 0.5
    delta = np.abs(d1 - d0)
    
    # Check FFT or standard deviation of the average to see if there is residual banding
    # Also check if delta is high (strong anti-ghosting agitation)
    std_avg = avg.std()
    mean_delta = delta.mean()
    
    return std_avg, mean_delta, avg

# Let's test different candidate shifts (dx, dy) in pixel space
candidates = [
    (1, 1),
    (2, 2),
    (2, 0),
    (0, 2),
    (2, 1),
    (1, 2),
    (3, 3),
    (1.5, 1.5),
    (2.25, 0),
]

print(f"{'Shift':<12} | {'Avg Std (lower=smoother)':<25} | {'Agitation Delta (higher=better)':<30}")
print("-" * 75)
for dx, dy in candidates:
    std, d_mean, _ = eval_shift(dx, dy)
    print(f"({dx}, {dy}){'':<6} | {std:<25.4f} | {d_mean:<30.4f}")
