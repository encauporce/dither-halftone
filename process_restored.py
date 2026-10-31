from PIL import Image
import numpy as np
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

def process(name, filename):
    p = os.path.join(brain_dir, filename)
    if not os.path.exists(p):
        return
    img = Image.open(p)
    w, h = img.size
    print(f"{name}: {w}x{h}")
    
    crop = img.crop((w//2 - 175, h//2 - 125, w//2 + 175, h//2 + 125))
    crop_out = os.path.join(brain_dir, f"{name}_crop.png")
    crop.save(crop_out)
    
    zoom = crop.crop((175-40, 125-40, 175+40, 125+40)).resize((320, 320), Image.NEAREST)
    zoom_out = os.path.join(brain_dir, f"{name}_zoom.png")
    zoom.save(zoom_out)
    
    arr = np.array(crop)
    print(f"{name} crop min: {arr.min()}, max: {arr.max()}, exact 0 count: {(arr==0).sum()}")

if __name__ == "__main__":
    process("ds1_vertical_restored", "ds1_restored_live.png")
    process("mc_vertical_restored", "mc_restored_live.png")
