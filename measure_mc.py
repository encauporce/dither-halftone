from PIL import Image
import numpy as np
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"
mc_path = os.path.join(brain_dir, "mc_real_fixed.png")

img = Image.open(mc_path)
arr = np.array(img)
w, h = img.size

# Crop center around crosshair
crop_box = (w//2 - 175, h//2 - 125, w//2 + 175, h//2 + 125)
crop = img.crop(crop_box)
crop_arr = np.array(crop)

print("=== REAL ON-DEVICE MINECRAFT METRICS ===")
print(f"Crop Min: {crop_arr.min()}, Max: {crop_arr.max()}")
print(f"Exact 0 count: {(crop_arr == 0).sum()} (Total: {crop_arr.size})")
print(f"Below 15 count: {(crop_arr < 15).sum()}")

crop_out = os.path.join(brain_dir, "live_mc_real_fixed_crop.png")
crop.save(crop_out)

# Zoom center 80x80 -> 320x320
zoom = crop.crop((175-40, 125-40, 175+40, 125+40)).resize((320, 320), Image.NEAREST)
zoom_out = os.path.join(brain_dir, "live_mc_real_fixed_zoom.png")
zoom.save(zoom_out)
print(f"Saved {crop_out} and {zoom_out}")
