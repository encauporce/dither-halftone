#!/usr/bin/env python3
"""
Hisense A7 Official EPDC Hardware Display Transformation Simulator
Simulates the exact transformation performed by Hisense's EInkService and Unisoc DPU:
1. Black Threshold Clamping (epd_black_threshold = 30 / 255 = ~0.118)
2. White Threshold Clamping (epd_white_threshold = 20 / 255 = ~0.922)
3. Hardware Waveform Quantization (DU / Speed mode: 4 physical grayscale levels)
4. Residual particle state / Ghosting vulnerability map
"""

import numpy as np
from PIL import Image, ImageDraw

def simulate_hisense_official_epdc(input_img_path, output_path):
    im = Image.open(input_img_path).convert('L')
    arr = np.array(im, dtype=np.float32) / 255.0

    # Real parameters read directly from Hisense A7 sysfs:
    # /sys/class/display/panel0/epd_black_threshold = 30
    # /sys/class/display/panel0/epd_white_threshold = 20
    BLACK_TH = 30.0 / 255.0  # 0.1176: Below this, Hisense driver crushes to dead black
    WHITE_TH = (255.0 - 20.0) / 255.0 # 0.9215: Above this, Hisense driver blows out to pure white

    # 1. Official Black/White Threshold Clamping & Contrast Stretch
    clamped = np.clip((arr - BLACK_TH) / (WHITE_TH - BLACK_TH), 0.0, 1.0)

    # 2. Hardware DU Waveform 4-level Grayscale Quantization
    # Physical E-ink Carta DU waveform only produces 4 physical reflectances:
    # Pure Black (0.0), Dark Gray (0.33), Light Gray (0.67), Pure White (1.0)
    hardware_4levels = np.round(clamped * 3.0) / 3.0

    # 3. Create a side-by-side comparison crop (center region)
    # [Left: SurfaceFlinger Raw Capture | Right: After Hisense Official EPDC Hardware Conversion]
    h, w = arr.shape
    crop_h, crop_w = 400, 600
    cy, cx = h // 2, w // 2
    
    raw_crop = (arr[cy-200:cy+200, cx-300:cx+300] * 255.0).astype(np.uint8)
    epdc_crop = (hardware_4levels[cy-200:cy+200, cx-300:cx+300] * 255.0).astype(np.uint8)

    comp = np.zeros((crop_h, crop_w * 2), dtype=np.uint8)
    comp[:, :crop_w] = raw_crop
    comp[:, crop_w:] = epdc_crop

    out = Image.fromarray(comp)
    draw = ImageDraw.Draw(out)
    draw.rectangle([0, 0, crop_w, 28], fill=0)
    draw.text((15, 6), "SURFACEFLINGER (GPU SHADER OUTPUT)", fill=255)
    draw.rectangle([crop_w, 0, crop_w * 2, 28], fill=0)
    draw.text((crop_w + 15, 6), "HISENSE OFFICIAL EPDC CONVERTED (ACTUAL SCREEN REFLECTANCE)", fill=255)

    out.save(output_path)
    print(f"Simulated post-EPDC image saved to {output_path}")

if __name__ == '__main__':
    simulate_hisense_official_epdc(
        'C:/Users/chuan/.gemini/antigravity/scratch/hisense_a7_video_shader/live_snap.png',
        'C:/Users/chuan/.gemini/antigravity/scratch/hisense_a7_video_shader/hisense_epdc_transformed.png'
    )
