from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"
img = Image.open(os.path.join(brain_dir, "ds1_real_fixed.png"))
w, h = img.size
crop = img.crop((w//2 - 175, h//2 - 125, w//2 + 175, h//2 + 125))
crop.save(os.path.join(brain_dir, "live_ds1_real_fixed_crop.png"))
print("Saved live_ds1_real_fixed_crop.png")
