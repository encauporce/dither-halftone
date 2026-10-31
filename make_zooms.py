import sys
sys.path.append(r'C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader')
import verify_anti_ghosting as v
import numpy as np
from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

def save_zooms(name, path, crop_y, crop_x, crop_h=120, crop_w=120):
    f0 = v.sim_full_pipeline(path, frame_num=0)
    f1 = v.sim_full_pipeline(path, frame_num=1)
    
    box = (slice(crop_y, crop_y+crop_h), slice(crop_x, crop_x+crop_w))
    z0 = (f0[box] * 255).astype(np.uint8)
    z1 = (f1[box] * 255).astype(np.uint8)
    z_avg = (((f0[box] + f1[box]) * 0.5) * 255).astype(np.uint8)
    
    im0 = Image.fromarray(z0).resize((crop_w*3, crop_h*3), Image.NEAREST)
    im1 = Image.fromarray(z1).resize((crop_w*3, crop_h*3), Image.NEAREST)
    im_avg = Image.fromarray(z_avg).resize((crop_w*3, crop_h*3), Image.NEAREST)
    
    im0.save(os.path.join(brain_dir, f"{name}_f0_zoom.png"))
    im1.save(os.path.join(brain_dir, f"{name}_f1_zoom.png"))
    im_avg.save(os.path.join(brain_dir, f"{name}_avg_zoom.png"))
    print(f"Saved zooms for {name}")

if __name__ == "__main__":
    mc_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip2_minecraft.png"
    ds_path = r"C:\Users\chuan\.gemini\antigravity\scratch\hisense_a7_video_shader\raw_clip3_ds1.png"
    
    img_mc = Image.open(mc_path)
    w, h = img_mc.size
    save_zooms("mc_fixed_agitation", mc_path, h//2 - 60, w//2 - 60)
    
    img_ds = Image.open(ds_path)
    w, h = img_ds.size
    save_zooms("ds_fixed_agitation", ds_path, h//2 - 60, w//2 - 60)
