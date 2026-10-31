import numpy as np
from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

def sim_diagonal_phase_shift(P=4.5):
    N = 100
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    
    # f0
    u0 = (x + y) * 0.70710678
    v0 = (x - y) * 0.70710678
    cu0 = np.mod(u0, P) - P*0.5
    cv0 = np.mod(v0, P) - P*0.5
    th0 = np.clip((cu0*cu0 + cv0*cv0)/(0.5*P*P), 0.0, 1.0)
    d0 = np.clip(0.5 + (0.5 - th0)/0.12, 0.0, 1.0)
    
    # f1: shift ONLY u by 0.5 * P (diagonal shift in screen space)
    u1 = u0 + 0.5 * P
    v1 = v0
    cu1 = np.mod(u1, P) - P*0.5
    cv1 = np.mod(v1, P) - P*0.5
    th1 = np.clip((cu1*cu1 + cv1*cv1)/(0.5*P*P), 0.0, 1.0)
    d1 = np.clip(0.5 + (0.5 - th1)/0.12, 0.0, 1.0)
    
    avg = (d0 + d1) * 0.5
    delta = np.abs(d1 - d0)
    
    print(f"Only u shift: Std={avg.std():.4f}, Delta={delta.mean():.4f}")
    
    im0 = Image.fromarray((d0*255).astype(np.uint8)).resize((400, 400), Image.NEAREST)
    im1 = Image.fromarray((d1*255).astype(np.uint8)).resize((400, 400), Image.NEAREST)
    im_avg = Image.fromarray((avg*255).astype(np.uint8)).resize((400, 400), Image.NEAREST)
    
    im0.save(os.path.join(brain_dir, "test_diag_f0.png"))
    im1.save(os.path.join(brain_dir, "test_diag_f1.png"))
    im_avg.save(os.path.join(brain_dir, "test_diag_avg.png"))

if __name__ == "__main__":
    sim_diagonal_phase_shift()
