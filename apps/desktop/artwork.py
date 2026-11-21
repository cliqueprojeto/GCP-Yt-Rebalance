"""Ilustrações geradas localmente (gradientes, chips de formato e ícones).

Tudo é desenhado com Pillow na inicialização, em versões clara e escura,
para evitar imagens grandes no pacote.
"""
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from runtime import BASE
from ui_icons import glyph

# Paletas por ferramenta: (início, fim) no claro e no escuro, cor do ícone.
BANNERS = {
    "download": dict(light=("#E9E2FF", "#D9CCFF"), dark=("#2A2350", "#1C1A3A"), icon=("#7C4DFF", "#A98BFF"), accent="#8B5CF6"),
    "karaoke": dict(light=("#DDF3FC", "#C4E9F9"), dark=("#0F3446", "#0E2233"), icon=("#0284C7", "#38BDF8"), accent="#22B8F0"),
    "stems": dict(light=("#FCE4EF", "#F7CFE1"), dark=("#43183A", "#2A1530"), icon=("#DB2777", "#F472B6"), accent="#EC4899"),
    "convert": dict(light=("#E2E9FF", "#CFDBFF"), dark=("#1B2A55", "#151F3D"), icon=("#2F55D4", "#7C9BFF"), accent="#4F7BFF"),
}


def _font(size, bold=True):
    for name in ("Inter-Bold.otf" if bold else "Inter-Regular.otf",):
        path = BASE / "assets/fonts" / name
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                pass
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _gradient(width, height, start, end):
    a = tuple(int(start[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(end[i:i + 2], 16) for i in (1, 3, 5))
    sw, sh = max(2, width // 10), max(2, height // 10)
    small = Image.new("RGB", (sw, sh))
    px = small.load()
    for y in range(sh):
        for x in range(sw):
            t = (x / (sw - 1) * .65 + y / (sh - 1) * .35)
            px[x, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return small.resize((width, height), Image.Resampling.BICUBIC)


def _chip(draw, xy, text, mode, accent):
    x, y = xy
    font = _font(22)
    w = draw.textlength(text, font=font) + 30
    fill = (255, 255, 255, 215) if mode == "light" else (12, 16, 34, 170)
    outline = accent + ("70" if mode == "light" else "99")
    draw.rounded_rectangle((x, y, x + w, y + 40), radius=14, fill=fill, outline=outline, width=2)
    draw.text((x + 15, y + 8), text, font=font, fill=accent if mode == "light" else "#E8E4FF")


@lru_cache(maxsize=32)
def banner(kind, mode, chips=(), width=720, height=300):
    spec = BANNERS[kind]
    img = _gradient(width, height, *spec[mode]).convert("RGBA")
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    tint = spec["accent"]
    g.ellipse((width * .62, -height * .5, width * 1.25, height * .7), fill=tint + ("38" if mode == "light" else "40"))
    g.ellipse((-width * .2, height * .55, width * .35, height * 1.5), fill=tint + ("26" if mode == "light" else "30"))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(28)))
    draw = ImageDraw.Draw(img)
    # Ícone central em bloco translúcido
    cx, cy, box = width // 2, height // 2, max(96, min(150, int(height * .46)))
    tile = Image.new("RGBA", (box + 60, box + 60), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.rounded_rectangle((30, 38, box + 30, box + 38), radius=34, fill=(0, 0, 0, 60 if mode == "dark" else 28))
    tile = tile.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(tile, (cx - box // 2 - 30, cy - box // 2 - 30))
    draw.rounded_rectangle((cx - box // 2, cy - box // 2, cx + box // 2, cy + box // 2), radius=34,
                           fill=(255, 255, 255, 235) if mode == "light" else (24, 28, 56, 230),
                           outline=tint + "55", width=2)
    icon_color = spec["icon"][0 if mode == "light" else 1]
    icon_name = {"download": "download", "karaoke": "mic", "stems": "layers", "convert": "convert"}[kind]
    icon = glyph(icon_name, icon_color, 18, 2.1).resize((76, 76), Image.Resampling.LANCZOS)
    img.alpha_composite(icon, (cx - 38, cy - 38))
    spots = [(28, 26), (width - 150, 30), (width - 170, height - 70)]
    for (x, y), text in zip(spots, chips):
        _chip(draw, (x, y), text, mode, icon_color)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height + 60), radius=34, fill=255)
    img.putalpha(mask)
    return img


@lru_cache(maxsize=8)
def hero_art(mode, width=420, height=300):
    """Ilustração do card principal: pilha de cartões com ícone de download."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    back = ("#DCD3FF", "#C9DCFB") if mode == "light" else ("#2B2F57", "#26304F")
    for i, (angle, color) in enumerate(((-9, back[0]), (8, back[1]))):
        card = Image.new("RGBA", (200, 160), (0, 0, 0, 0))
        ImageDraw.Draw(card).rounded_rectangle((0, 0, 199, 159), radius=26, fill=color)
        card = card.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        img.alpha_composite(card, (width // 2 - card.width // 2 + (-46 if i == 0 else 46), height // 2 - card.height // 2 - 6))
    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((width / 2 - 80, height - 62, width / 2 + 80, height - 36), fill=(60, 40, 140, 70 if mode == "light" else 120))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(8)))
    main = _gradient(150, 150, "#A855F7", "#EC4899").convert("RGBA")
    mask = Image.new("L", (150, 150), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 149, 149), radius=34, fill=255)
    tile = Image.new("RGBA", (150, 150), (0, 0, 0, 0))
    tile.paste(main, (0, 0), mask)
    icon = glyph("download", "#FFFFFF", 18, 2.4).resize((84, 84), Image.Resampling.LANCZOS)
    tile.alpha_composite(icon, (33, 30))
    img.alpha_composite(tile, (width // 2 - 75, height // 2 - 88))
    return img


@lru_cache(maxsize=8)
def logo_tile(size=96):
    """Logotipo em bloco com gradiente, a partir do ícone oficial."""
    path = BASE / "assets/branding/taskbar-256.png"
    try:
        return Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    except OSError:
        return glyph("audio", "#8B5CF6", size // 4)
