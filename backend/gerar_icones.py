"""Gera os ícones oficiais do SAMU 192 a partir dos SVGs de static/core/.

Saída:
  assets/icons/samu192.ico   (Windows: 16…256 px)
  assets/icons/samu192.icns  (macOS)
  assets/icons/samu192.png   (Linux / janela, 1024 px) + samu192-512.png
  ../android-app/assets/     (icon-only, icon-foreground, icon-background, splash, splash-dark)

Requisitos: pip install cairosvg pillow   (Linux: sudo apt install libcairo2)
Uso:        python gerar_icones.py
"""
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

BASE = Path(__file__).resolve().parent
SVG_LOGO = BASE / "static" / "core" / "samu-logo.svg"
SVG_PEQUENO = BASE / "static" / "core" / "favicon.svg"
SAIDA = BASE / "assets" / "icons"
ANDROID = BASE.parent / "android-app" / "assets"
VERMELHO, VERMELHO_ESCURO = "#B91C1C", "#7F1D1D"


def render(svg: Path, tamanho: int) -> Image.Image:
    png = cairosvg.svg2png(url=str(svg), output_width=tamanho, output_height=tamanho)
    return Image.open(BytesIO(png)).convert("RGBA")


def centralizado(tela: int, logo: int, fundo) -> Image.Image:
    img = Image.new("RGBA", (tela, tela), fundo)
    marca = render(SVG_LOGO, logo)
    img.alpha_composite(marca, ((tela - logo) // 2, (tela - logo) // 2))
    return img


def desktop() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    grande = render(SVG_LOGO, 1024)
    grande.save(SAIDA / "samu192.png")
    grande.resize((512, 512), Image.LANCZOS).save(SAIDA / "samu192-512.png")

    # Tamanhos pequenos usam o favicon (traços mais grossos, legível em 16 px).
    pequenos = [render(SVG_PEQUENO, s) for s in (16, 24, 32)]
    medios = [render(SVG_LOGO, s) for s in (48, 64, 128)]
    base_ico = render(SVG_LOGO, 256)
    base_ico.save(
        SAIDA / "samu192.ico", format="ICO",
        sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)],
        append_images=pequenos + medios,
    )
    try:
        grande.save(SAIDA / "samu192.icns", format="ICNS")
    except Exception as exc:  # Pillow antigo sem suporte a escrita ICNS
        print(f"  aviso: .icns não gerado ({exc})")


def android() -> None:
    ANDROID.mkdir(parents=True, exist_ok=True)
    centralizado(1024, 860, VERMELHO).save(ANDROID / "icon-only.png")
    centralizado(1024, 600, (0, 0, 0, 0)).save(ANDROID / "icon-foreground.png")
    Image.new("RGBA", (1024, 1024), VERMELHO).save(ANDROID / "icon-background.png")
    splash = centralizado(2732, 900, VERMELHO_ESCURO)
    splash.save(ANDROID / "splash.png")
    splash.save(ANDROID / "splash-dark.png")


if __name__ == "__main__":
    desktop()
    print(f"✅ Ícones desktop em {SAIDA}")
    android()
    print(f"✅ Ícones/splash Android em {ANDROID}")
