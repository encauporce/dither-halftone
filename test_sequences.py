import numpy as np
from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

def eval_sequence(seq, P=4.5):
    N = 100
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    
    frames = []
    for dx, dy in seq:
        u = ((x + dx) + (y + dy)) * 0.70710678
        v = ((x + dx) - (y + dy)) * 0.70710678
        cu = np.mod(u, P) - P*0.5
        cv = np.mod(v, P) - P*0.5
        th = np.clip((cu*cu + cv*cv)/(0.5*P*P), 0.0, 1.0)
        d = np.clip(0.5 + (0.5 - th)/0.12, 0.0, 1.0)
        frames.append(d)
        
    avg = np.mean(frames, axis=0)
    std = avg.std()
    
    # consecutive delta
    deltas = [np.abs(frames[i] - frames[(i+1)%len(frames)]).mean() for i in range(len(frames))]
    return std, np.mean(deltas), avg

seqs = {
    "2-phase (2,2)": [(0,0), (2,2)],
    "2-phase (2,0)": [(0,0), (2,0)],
    "2-phase (1,2)": [(0,0), (1,2)],
    "4-phase box": [(0,0), (2,2), (2,0), (0,2)],
    "4-phase knight": [(0,0), (2,1), (0,2), (2,3)],
}

for name, s in seqs.items():
    std, d_mean, avg = eval_sequence(s)
    print(f"{name:<20} | Std={std:.4f} | Delta={d_mean:.4f}")
    im = Image.fromarray((avg*255).astype(np.uint8)).resize((400, 400), Image.NEAREST)
    im.save(os.path.join(brain_dir, f"test_seq_{name.replace(' ', '_').replace('(', '').replace(')', '').replace(',', '')}.png"))
