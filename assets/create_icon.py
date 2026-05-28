from PIL import Image, ImageDraw
import os

def rounded_rect(draw, xy, r, fill):
    x1, y1, x2, y2 = xy
    draw.rectangle([x1+r, y1, x2-r, y2], fill=fill)
    draw.rectangle([x1, y1+r, x2, y2-r], fill=fill)
    draw.ellipse([x1, y1, x1+2*r, y1+2*r], fill=fill)
    draw.ellipse([x2-2*r, y1, x2, y1+2*r], fill=fill)
    draw.ellipse([x1, y2-2*r, x1+2*r, y2], fill=fill)
    draw.ellipse([x2-2*r, y2-2*r, x2, y2], fill=fill)

def make_size(s):
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    rounded_rect(d, [0, 0, s-1, s-1], s // 6, (32, 78, 120))

    ml = int(s * 0.20)
    mt = int(s * 0.12)
    mr = int(s * 0.84)
    mb = int(s * 0.88)
    fold = int(s * 0.24)

    white = (236, 242, 248)
    d.polygon([
        (ml, mt), (mr - fold, mt),
        (mr, mt + fold),
        (mr, mb), (ml, mb)
    ], fill=white)

    d.polygon([
        (mr - fold, mt), (mr, mt + fold), (mr - fold, mt + fold)
    ], fill=(170, 200, 225))

    d.line(
        [(ml, mt), (mr-fold, mt), (mr, mt+fold), (mr, mb), (ml, mb), (ml, mt)],
        fill=(190, 210, 230), width=max(1, s // 64)
    )

    sy = mt + int((mb - mt) * 0.35)
    sh = max(3, int((mb - mt) * 0.18))
    d.rectangle([ml, sy, mr - fold // 2, sy + sh], fill=(196, 50, 50))

    lc = (190, 202, 214)
    lh = max(1, s // 32)
    gap = max(2, s // 20)
    for i in range(3):
        ly = sy + sh + gap + i * (lh + gap)
        if ly + lh < mb - int(s * 0.06):
            d.rectangle([ml + int(s * 0.04), ly, mr - fold - int(s * 0.04), ly + lh], fill=lc)

    return img


def make_wizard_small():
    """BMP 55x58 para WizardSmallImageFile de Inno Setup."""
    w, h = 55, 58
    bg = (32, 78, 120)
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)

    ml, mt, mr, mb = 8, 6, 46, 52
    fold = 12
    white = (236, 242, 248)
    d.polygon([
        (ml, mt), (mr - fold, mt),
        (mr, mt + fold),
        (mr, mb), (ml, mb)
    ], fill=white)
    d.polygon([(mr-fold, mt), (mr, mt+fold), (mr-fold, mt+fold)], fill=(170, 200, 225))
    sy = mt + int((mb - mt) * 0.35)
    sh = max(2, int((mb - mt) * 0.18))
    d.rectangle([ml, sy, mr - fold // 2, sy + sh], fill=(196, 50, 50))

    return img


if __name__ == "__main__":
    os.makedirs("assets", exist_ok=True)

    # ICO — ícono de la app y del instalador
    sizes = [256, 128, 64, 48, 32, 16]
    imgs = [make_size(s) for s in sizes]
    imgs[0].save("assets/icon.ico", format="ICO", append_images=imgs[1:])
    print(f"Creado assets/icon.ico con tamaños: {sizes}")

    # BMP para el wizard de Inno Setup (debe ser RGB, sin alpha)
    wiz = make_wizard_small()
    wiz.save("assets/wizard_small.bmp", format="BMP")
    print("Creado assets/wizard_small.bmp (55x58)")
