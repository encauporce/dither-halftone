import numpy as np
from PIL import Image, ImageDraw
import os

brain_dir = r"C:\Users\chuan\.gemini\antigravity\brain\d97b9f29-a537-409d-b432-b06e88281223"

# Pixel coordinates inside 4x4
# Ring 0: (1,1), (2,1), (1,2), (2,2) -> 4 pixels
ring0_coords = [(1,1), (2,1), (1,2), (2,2)]

# Ring 1: 8 edge pixels: (1,0), (2,0), (3,1), (3,2), (2,3), (1,3), (0,2), (0,1)
ring1_coords = [(1,0), (2,0), (3,1), (3,2), (2,3), (1,3), (0,2), (0,1)]

# Ring 2: 4 corner pixels: (0,0), (3,0), (3,3), (0,3)
ring2_coords = [(0,0), (3,0), (3,3), (0,3)]

def generate_ring_threshold_matrix(seed):
    rng = np.random.RandomState(seed)
    
    mat = np.zeros((4, 4), dtype=np.float32)
    
    # Permute Ring 0
    p0 = rng.permutation(4)
    for rank, idx in enumerate(p0):
        x, y = ring0_coords[idx]
        mat[y, x] = rank # 0 .. 3
        
    # Permute Ring 1
    p1 = rng.permutation(8)
    for rank, idx in enumerate(p1):
        x, y = ring1_coords[idx]
        mat[y, x] = 4 + rank # 4 .. 11
        
    # Permute Ring 2
    p2 = rng.permutation(4)
    for rank, idx in enumerate(p2):
        x, y = ring2_coords[idx]
        mat[y, x] = 12 + rank # 12 .. 15
        
    return (mat + 0.5) / 16.0

def test_ring_preservation_on_gradient():
    grad_h, grad_w = 200, 320
    grad_arr = np.tile(np.linspace(0.1, 0.9, grad_w, dtype=np.float32), (grad_h, 1))
    
    # 1. Fixed standard matrix
    m16 = np.array([
        12.0,  8.0,  9.0, 13.0,
         7.0,  0.0,  1.0,  5.0,
         6.0,  2.0,  3.0,  4.0,
        11.0, 10.0, 14.0, 15.0
    ], dtype=np.float32).reshape((4, 4))
    m16_norm = (m16 + 0.5) / 16.0
    
    yy, xx = np.indices((grad_h, grad_w), dtype=np.int32)
    in_bx = xx % 4
    in_by = yy % 4
    bx = xx // 4
    by = yy // 4
    
    # Fixed th map
    th_fixed = m16_norm[in_by, in_bx]
    
    # Ring-preserved random growth th map
    th_ring = np.zeros((grad_h, grad_w), dtype=np.float32)
    
    num_bx = grad_w // 4
    num_by = grad_h // 4
    for b_y in range(num_by):
        for b_x in range(num_bx):
            seed = int(b_x * 12345 + b_y * 67891) & 0x7fffffff
            mat = generate_ring_threshold_matrix(seed)
            th_ring[b_y*4:(b_y+1)*4, b_x*4:(b_x+1)*4] = mat
            
    # Halftone outputs at softness = 0.08
    dot_softness = 0.08
    dot_fixed = np.clip(0.5 + (grad_arr - th_fixed) / dot_softness, 0.0, 1.0)
    dot_ring = np.clip(0.5 + (grad_arr - th_ring) / dot_softness, 0.0, 1.0)
    
    # Map to [0.08, 1.0]
    luma_fixed = 0.08 + 0.92 * dot_fixed
    luma_ring = 0.08 + 0.92 * dot_ring
    
    # Save visual comparison
    im_fixed = Image.fromarray((luma_fixed * 255).astype(np.uint8))
    im_ring = Image.fromarray((luma_ring * 255).astype(np.uint8))
    
    cx, cy = grad_w // 2, grad_h // 2
    z_fixed = im_fixed.crop((cx-40, cy-40, cx+40, cy+40)).resize((320, 320), Image.NEAREST)
    z_ring = im_ring.crop((cx-40, cy-40, cx+40, cy+40)).resize((320, 320), Image.NEAREST)
    
    comp = Image.new('RGB', (660, 360), (240, 240, 240))
    comp.paste(z_fixed.convert('RGB'), (0, 40))
    comp.paste(z_ring.convert('RGB'), (340, 40))
    
    draw = ImageDraw.Draw(comp)
    draw.text((10, 10), "Fixed: All Dots Lean in Same Direction", fill=(180, 0, 0))
    draw.text((350, 10), "Ring-Preserved: Random Growth Direction, Clean Dots", fill=(0, 120, 0))
    
    comp.save(os.path.join(brain_dir, "test_ring_random_growth_zoom.png"))
    print("Saved test_ring_random_growth_zoom.png")

if __name__ == "__main__":
    test_ring_preservation_on_gradient()
