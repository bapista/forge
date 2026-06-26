#!/usr/bin/env python3
"""Render the FORGE app icon: emerald tile (Apple specular depth) + white anvil.
Brand: #34d399 -> #1d9e75 (forest emerald, matches desktop app + Cipher family).
Supersampled 4x then downscaled for crisp edges. Emits master 1024 + Electron sizes."""
from PIL import Image, ImageDraw, ImageFilter

S = 4                      # supersample factor
W = 1024 * S
RAD = 224 * S
ACC = (0x34, 0xd3, 0x99)   # top-left
ACC2 = (0x1d, 0x9e, 0x75)  # bottom-right
OUT_DIR = "/home/bapista/forge/desktop/build"
SCRATCH = "/tmp/claude-1000/-home-bapista/4457eae7-76cd-4769-be15-1c556c0e4a49/scratchpad"

# anvil polygons in 1024-space, shifted down +10 for vertical centering
DY = 10
SLAB = [(250, 452), (432, 410), (740, 410), (740, 470), (396, 470)]
PED = [(446, 470), (586, 470), (556, 556), (640, 590),
       (666, 652), (366, 652), (392, 590), (476, 556)]


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def diagonal_gradient(size, c0, c1):
    """Per-row blend is too coarse; do a true diagonal via a small gradient
    image rotated. Cheap approach: compute on a downscaled grid then resize."""
    g = Image.new("RGB", (256, 256))
    px = g.load()
    for y in range(256):
        for x in range(256):
            t = (x + y) / (255 * 2)
            px[x, y] = lerp(c0, c1, t)
    return g.resize((size, size), Image.BILINEAR)


def radial(size, cx, cy, r, inner_a, outer_a):
    """White radial alpha mask (for specular highlight)."""
    g = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(g)
    steps = 80
    for i in range(steps, 0, -1):
        rr = r * i / steps
        a = int(outer_a + (inner_a - outer_a) * (1 - i / steps))
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=a)
    return g


def scaled(poly):
    return [((x) * S, (y + DY) * S) for x, y in poly]


def build():
    # base emerald tile
    tile = diagonal_gradient(W, ACC, ACC2).convert("RGBA")

    # bottom depth shade
    shade = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for y in range(W):
        t = y / W
        if t > 0.55:
            a = int(72 * (t - 0.55) / 0.45)
            sd.line([(0, y), (W, y)], fill=(6, 59, 42, a))
    tile = Image.alpha_composite(tile, shade)

    # specular highlight, top-center
    spec_mask = radial(W, W // 2, 0, int(W * 0.9), 78, 0)
    spec = Image.new("RGBA", (W, W), (255, 255, 255, 0))
    spec.putalpha(spec_mask)
    tile = Image.alpha_composite(tile, spec)

    # anvil shadow
    shadow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    sh = ImageDraw.Draw(shadow)
    sh.polygon(scaled([(x, y + 10) for x, y in SLAB]), fill=(6, 20, 13, 90))
    sh.polygon(scaled([(x, y + 10) for x, y in PED]), fill=(6, 20, 13, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14 * S))
    tile = Image.alpha_composite(tile, shadow)

    # anvil (white)
    anvil = Image.new("RGBA", (W, W), (255, 255, 255, 0))
    ad = ImageDraw.Draw(anvil)
    ad.polygon(scaled(SLAB), fill=(255, 255, 255, 255))
    ad.polygon(scaled(PED), fill=(255, 255, 255, 255))
    tile = Image.alpha_composite(tile, anvil)

    # inner light edge
    edge = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ed = ImageDraw.Draw(edge)
    ed.rounded_rectangle([3 * S, 3 * S, W - 3 * S, W - 3 * S], radius=RAD - 3 * S,
                         outline=(255, 255, 255, 46), width=3 * S)
    tile = Image.alpha_composite(tile, edge)

    # round the corners (mask)
    mask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W, W], radius=RAD, fill=255)
    tile.putalpha(mask)

    return tile.resize((1024, 1024), Image.LANCZOS)


def main():
    icon = build()
    icon.save(f"{OUT_DIR}/icon.png")
    icon.save(f"{SCRATCH}/forge_preview.png")
    for sz in (16, 32, 48, 64, 128, 256, 512):
        icon.resize((sz, sz), Image.LANCZOS).save(f"{OUT_DIR}/icon_{sz}.png")
    print("wrote icon.png (1024) + sizes 16..512")


if __name__ == "__main__":
    main()
