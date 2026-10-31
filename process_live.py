from PIL import Image
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

def process_screencap(name, live_file, crop_y, crop_x, crop_h=250, crop_w=350):
    path = os.path.join(brain_dir, live_file)
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    img = Image.open(path)
    w, h = img.size
    print(f"{name} original size: {w}x{h}")
    
    # Crop
    crop_box = (crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)
    crop = img.crop(crop_box)
    crop_out = os.path.join(brain_dir, f"{name}_crop.png")
    crop.save(crop_out)
    
    # Zoom center 80x80 -> 320x320
    cx = crop_w // 2
    cy = crop_h // 2
    z_box = (cx - 40, cy - 40, cx + 40, cy + 40)
    z_crop = crop.crop(z_box)
    zoom = z_crop.resize((z_crop.width * 4, z_crop.height * 4), Image.NEAREST)
    zoom_out = os.path.join(brain_dir, f"{name}_zoom.png")
    zoom.save(zoom_out)
    print(f"Saved: {crop_out} and {zoom_out}")

if __name__ == "__main__":
    img_mc = Image.open(os.path.join(brain_dir, "live_manga45_mc.png"))
    w, h = img_mc.size
    process_screencap("live_mc_manga45", "live_manga45_mc.png", h // 2 - 125, w // 2 - 175)
    
    img_ds = Image.open(os.path.join(brain_dir, "live_manga45_ds1.png"))
    w, h = img_ds.size
    process_screencap("live_ds1_manga45", "live_manga45_ds1.png", h // 2 - 125, w // 2 - 175)
