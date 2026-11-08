"""Gera os derivados da logo a partir do original (que nunca é alterado).

    python scripts/gerar-logos.py

Requer Pillow e NumPy (só para gerar; o app não depende deles).

Entrada : frontend/images/Loja de Pães logo.png   (2000x2000, fundo creme #FFF4EA)
Saída   : frontend/src/assets/logo-loja-de-paes.png               recorte com 24 px de margem, fundo creme
          frontend/src/assets/logo-loja-de-paes-transparente.png  o mesmo recorte, creme transparente
          frontend/public/icone-32.png, icone-180.png             o "L" sobre fundo creme (ícone da aba)

A arte é de uma cor só (vinho). Por isso o creme sai por "cor para transparência": a opacidade de
cada pixel é a fração de vinho que ele tem. As bordas ficam suaves e sem halo; a sombra clara que
rodeia o traço (opacidade abaixo de ~15%) é descartada, para não aparecer como névoa em fundo escuro.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
ORIGINAL = next((RAIZ / "frontend" / "images").glob("Loja de P*logo.png"))
ASSETS = RAIZ / "frontend" / "src" / "assets"
PUBLIC = RAIZ / "frontend" / "public"

CREME = np.array([255, 244, 234], dtype=np.float64)
VINHO = np.array([96, 14, 9], dtype=np.float64)
CAIXA_ARTE = (474, 738, 1628, 1094)  # caixa da arte no original: 1154 x 356
MARGEM = 24
CORTE = 0.15  # opacidade abaixo disso é sombra, não traço


def opacidade(rgb: np.ndarray) -> np.ndarray:
    eixo = CREME - VINHO
    alfa = ((CREME - rgb) @ eixo) / float(eixo @ eixo)
    return np.clip((alfa - CORTE) / (1.0 - CORTE), 0.0, 1.0)


def recorte(imagem: Image.Image, caixa: tuple[int, int, int, int]) -> Image.Image:
    return imagem.crop(caixa)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    original = Image.open(ORIGINAL).convert("RGB")
    x0, y0, x1, y1 = CAIXA_ARTE
    caixa = (x0 - MARGEM, y0 - MARGEM, x1 + MARGEM, y1 + MARGEM)

    # 1) recorte com fundo creme (pixels do original, sem mexer)
    recorte(original, caixa).save(ASSETS / "logo-loja-de-paes.png", optimize=True)

    # 2) o mesmo recorte, creme transparente
    rgb = np.asarray(recorte(original, caixa), dtype=np.float64)
    alfa = opacidade(rgb)
    saida = np.zeros(rgb.shape[:2] + (4,), dtype=np.uint8)
    saida[..., 0], saida[..., 1], saida[..., 2] = (int(c) for c in VINHO)
    saida[..., 3] = np.round(alfa * 255).astype(np.uint8)
    Image.fromarray(saida, "RGBA").save(ASSETS / "logo-loja-de-paes-transparente.png", optimize=True)

    # 3) ícone da aba: o "L", sobre fundo creme. O "o" que encosta no traço é apagado na máscara.
    base_x, base_y = 470, 730
    todo = opacidade(np.asarray(original, dtype=np.float64))
    todo[base_y + 98 : base_y + 226, base_x + 136 : base_x + 215] = 0.0
    letra = todo[base_y + 18 : base_y + 342, base_x + 18 : base_x + 205]
    altura, largura = letra.shape
    lado = int(max(altura, largura) * 1.22)
    tela = np.tile(CREME, (lado, lado, 1))
    topo, esquerda = (lado - altura) // 2, (lado - largura) // 2
    area = tela[topo : topo + altura, esquerda : esquerda + largura]
    area[:] = CREME * (1 - letra[..., None]) + VINHO * letra[..., None]
    icone = Image.fromarray(np.round(tela).astype(np.uint8), "RGB")
    for tamanho in (32, 180):
        icone.resize((tamanho, tamanho), Image.LANCZOS).save(PUBLIC / f"icone-{tamanho}.png", optimize=True)

    print("ok:", *(p.name for p in sorted(ASSETS.glob("logo-*.png"))), "icone-32.png", "icone-180.png")


if __name__ == "__main__":
    main()
