from PIL import Image, ImageDraw, ImageFont
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

# User's previous bug screencap zoom vs new live zoom
old_mc_zoom = os.path.join(brain_dir, "live_mc_d4_10s_zoom.png")
new_mc_zoom = os.path.join(brain_dir, "live_mc_manga45_zoom.png")

old_ds_zoom = os.path.join(brain_dir, "live_d4_ds1_zoom.png")
new_ds_zoom = os.path.join(brain_dir, "live_ds1_manga45_zoom.png")

def make_side_by_side(old_path, new_path, out_path, title_left, title_right):
    im_left = Image.open(old_path).convert("RGB")
    im_right = Image.open(new_path).convert("RGB")
    
    # target height 320
    target_h = 320
    im_left = im_left.resize((int(im_left.width * target_h / im_left.height), target_h), Image.NEAREST)
    im_right = im_right.resize((int(im_right.width * target_h / im_right.height), target_h), Image.NEAREST)
    
    total_w = im_left.width + im_right.width + 20
    total_h = target_h + 40
    
    canvas = Image.new("RGB", (total_w, total_h), (240, 240, 240))
    canvas.paste(im_left, (0, 40))
    canvas.paste(im_right, (im_left.width + 20, 40))
    
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), title_left, fill=(200, 0, 0))
    draw.text((im_left.width + 30, 10), title_right, fill=(0, 130, 0))
    
    canvas.save(out_path)
    print(f"Created: {out_path}")

if __name__ == "__main__":
    if os.path.exists(old_mc_zoom) and os.path.exists(new_mc_zoom):
        make_side_by_side(old_mc_zoom, new_mc_zoom, 
                          os.path.join(brain_dir, "comparison_mc_manga45_vs_bug.png"),
                          "Old (Fixed Orientation / Bug)", "New Live (45 deg Manga Screentone)")
    if os.path.exists(old_ds_zoom) and os.path.exists(new_ds_zoom):
        make_side_by_side(old_ds_zoom, new_ds_zoom, 
                          os.path.join(brain_dir, "comparison_ds1_manga45_vs_bug.png"),
                          "Old (Brick Screen-door / Noise)", "New Live (45 deg Manga Screentone)")
