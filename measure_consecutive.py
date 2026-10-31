from PIL import Image
import numpy as np
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

im_a = Image.open(os.path.join(brain_dir, "frame_a.png")).convert('L')
im_b = Image.open(os.path.join(brain_dir, "frame_b.png")).convert('L')

arr_a = np.array(im_a, dtype=np.float32)
arr_b = np.array(im_b, dtype=np.float32)

w, h = im_a.size
crop_box = (w//2 - 175, h//2 - 125, w//2 + 175, h//2 + 125)
zoom_box = (w//2 - 40, h//2 - 40, w//2 + 40, h//2 + 40)

ca = arr_a[h//2-125:h//2+125, w//2-175:w//2+175]
cb = arr_b[h//2-125:h//2+125, w//2-175:w//2+175]

delta = np.abs(cb - ca)

print("=== REAL ON-DEVICE METRICS (Consecutive Screencaps) ===")
print(f"Frame A Min: {ca.min()}, Max: {ca.max()}")
print(f"Frame B Min: {cb.min()}, Max: {cb.max()}")
print(f"Exact 0 count in Frame A crop: {(ca == 0).sum()} (Total: {ca.size})")
print(f"Below 15 count in Frame A crop: {(ca < 15).sum()}")
print(f"Mean inter-frame delta: {delta.mean():.2f}")
print(f"Percentage of pixels oscillating (>5): {(delta > 5).mean()*100:.2f}%")
print(f"High-energy flip ratio (>30): {(delta > 30).mean()*100:.2f}%")

# Save visual crops
za = im_a.crop(zoom_box).resize((320, 320), Image.NEAREST)
zb = im_b.crop(zoom_box).resize((320, 320), Image.NEAREST)
diff_img = Image.fromarray(np.clip(delta[125-40:125+40, 175-40:175+40] * 3, 0, 255).astype(np.uint8)).resize((320, 320), Image.NEAREST)

za.save(os.path.join(brain_dir, "live_consecutive_fa_zoom.png"))
zb.save(os.path.join(brain_dir, "live_consecutive_fb_zoom.png"))
diff_img.save(os.path.join(brain_dir, "live_consecutive_agitation_zoom.png"))

# Side-by-side comparison with old dead-black zoom
old_zoom_path = os.path.join(brain_dir, "live_ds1_manga45_zoom.png")
if os.path.exists(old_zoom_path):
    old_im = Image.open(old_zoom_path).convert('RGB')
    new_im = za.convert('RGB')
    
    comp = Image.new('RGB', (660, 360), (240, 240, 240))
    comp.paste(old_im, (0, 40))
    comp.paste(new_im, (340, 40))
    
    from PIL import ImageDraw
    draw = ImageDraw.Draw(comp)
    draw.text((10, 10), "Old: Dead Black (0V Ground / Frozen)", fill=(200, 0, 0))
    draw.text((350, 10), "New: Hard Lift (Min 20 / 15Hz Agitated)", fill=(0, 130, 0))
    comp.save(os.path.join(brain_dir, "comparison_deadblack_vs_hardlift.png"))
    print("Saved comparison_deadblack_vs_hardlift.png")
