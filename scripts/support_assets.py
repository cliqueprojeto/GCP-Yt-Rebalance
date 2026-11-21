"""Gera o QR Code PIX usado na tela "Apoie" (ferramenta de desenvolvimento).

Requer o pacote `qrcode` apenas no ambiente de desenvolvimento; o aplicativo
instalado usa o PNG pronto em assets/support/pix-qr.png.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/desktop"))


def crc16(payload):
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def main():
    import qrcode
    from gui import PIX_CODE
    assert crc16(PIX_CODE[:-4]) == PIX_CODE[-4:], "CRC do código PIX inválido"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=2)
    qr.add_data(PIX_CODE); qr.make(fit=True)
    image = qr.make_image(fill_color="#0B0F1E", back_color="white").convert("RGB")
    target = ROOT / "assets/support/pix-qr.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)
    print(target, image.size)


if __name__ == "__main__":
    main()
