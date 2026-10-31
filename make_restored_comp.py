from PIL import Image, ImageDraw
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"
ds_zoom = os.path.join(brain_dir, "ds1_vertical_restored_zoom.png")
mc_zoom = os.path.join(brain_dir, "mc_vertical_restored_zoom.png")

if os.path.exists(ds_zoom) and os.path.exists(mc_zoom):
    im_ds = Image.open(ds_zoom).convert('RGB')
    im_mc = Image.open(mc_zoom).convert('RGB')
    
    comp = Image.new('RGB', (660, 360), (240, 240, 240))
    comp.paste(im_ds, (0, 40))
    comp.paste(im_mc, (340, 40))
    
    draw = ImageDraw.Draw(comp)
    draw.text((10, 10), "Restored: Death Stranding (Vertical Grid)", fill=(0, 100, 0))
    draw.text((350, 10), "Restored: Minecraft (Vertical Grid)", fill=(0, 100, 0))
    
    out_path = os.path.join(brain_dir, "restored_vertical_grid_comparison.png")
    comp.save(out_path)
    print("Saved restored_vertical_grid_comparison.png")
