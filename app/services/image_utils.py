"""Utilitários de imagem (redimensionamento de logos para caber nos cards/documentos)."""

import io

from app.core.exceptions import ValidationError


def redimensionar_para_caixa(conteudo: bytes, max_box: tuple[int, int]) -> bytes:
    """Ajusta a imagem para caber dentro de ``max_box`` preservando a proporção
    (sem esticar/distorcer) e exporta PNG com transparência preservada.

    Usado para padronizar a dimensão de logos no card e no cabeçalho dos documentos.
    """
    from PIL import Image, UnidentifiedImageError

    try:
        imagem = Image.open(io.BytesIO(conteudo))
        imagem.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("Arquivo de imagem inválido ou corrompido.") from exc

    if imagem.mode not in ("RGB", "RGBA"):
        imagem = imagem.convert("RGBA")
    imagem.thumbnail(max_box, Image.LANCZOS)

    saida = io.BytesIO()
    imagem.save(saida, format="PNG", optimize=True)
    return saida.getvalue()
