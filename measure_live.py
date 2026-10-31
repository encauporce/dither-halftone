from PIL import Image
import numpy as np
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"
live_path = os.path.join(brain_dir, "ds1_live_fixed.png")

img = Image.open(live_path)
arr = np.array(img)
w, h = img.size
print(f"Image size: {w}x{h}")
print(f"Overall Min: {arr.min()}, Max: {arr.max()}")
print(f"Exact 0 count: {(arr == 0).sum()} (Total: {arr.size})")
print(f"Below 15 count: {(arr < 15).sum()}")

# Crop center 350x250
cx, cy = w // 2, h // 2
crop = img.crop((cx - 175, cy - 125, cx + 175, cy + 125))
crop_arr = np.array(crop)
print(f"Crop Min: {crop_arr.min()}, Max: {crop_arr.max()}")
print(f"Crop Exact 0 count: {(crop_arr == 0).sum()} (Total: {crop_arr.size})")
print(f"Crop Below 15 count: {(crop_arr < 15).sum()}")

crop_out = os.path.join(brain_dir, "live_ds1_fixed_crop.png")
crop.save(crop_out)

# Zoom center 80x80 -> 320x320
zoom = crop.crop((175 - 40, 125 - 40, 175 + 40, 125 + 40)).resize((320, 320), Image.NEAREST)
zoom_out = os.path.join(brain_dir, "live_ds1_fixed_zoom.png")
zoom.save(zoom_out)
print(f"Saved {crop_out} and {zoom_out}")
