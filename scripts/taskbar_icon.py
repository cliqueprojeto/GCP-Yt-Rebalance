"""Identidade unificada da versão 0.3: logo, janela, atalhos e instaladores."""
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
target = root / "assets/branding"
image = Image.new("RGBA", (512,512))
d = ImageDraw.Draw(image)
d.rounded_rectangle((3,3,509,509), radius=108, fill="#39216F", outline="#AE86FF", width=14)
d.polygon([(224,60),(288,60),(288,163),(357,163),(256,270),(155,163),(224,163)],fill="#FFFFFF")
for x,h in [(94,55),(154,115),(216,75),(278,150),(340,105),(402,55)]:
    d.rounded_rectangle((x-14,370-h//2,x+14,370+h//2),radius=14,fill="#D8C4FF")
for size in (16,32,64,128,256,512):
    image.resize((size,size),Image.Resampling.LANCZOS).save(target/f"taskbar-{size}.png")
image.save(target/"taskbar.ico",sizes=[(s,s) for s in (16,32,48,64,128,256)])
image.save(target/"taskbar.icns")
print("Variante de taskbar gerada: seta e onda de alto contraste, sem alterar o original")
