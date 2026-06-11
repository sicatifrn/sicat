from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from app.models import FichaCatalografica
import textwrap


PUBLIC_DIR = Path(__file__).parent.parent / "public"
IMAGENS_DIR = PUBLIC_DIR / "imagens"
IMAGENS_DIR.mkdir(parents=True, exist_ok=True)

def gerar_id_curto(ano: int, sequencia: int) -> str:
    return f"FICHA-{ano}-{sequencia:06d}"

def carregar_fonte(tamanho: int):
    fontes = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        "arial.ttf",
    ]
    for fonte in fontes:
        try:
            return ImageFont.truetype(fonte, tamanho)
        except Exception:
            continue
    return ImageFont.load_default()

def carregar_fonte_negrito(tamanho: int):
    fontes = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
        "arialbd.ttf",
    ]
    for fonte in fontes:
        try:
            return ImageFont.truetype(fonte, tamanho)
        except Exception:
            continue
    return carregar_fonte(tamanho)

def formatar_nome_catalografico(nome: str) -> str:
    partes = [parte for parte in str(nome or "").strip().split() if parte]
    if len(partes) <= 1:
        return " ".join(partes)
    return f"{partes[-1]}, {' '.join(partes[:-1])}"

def escrever_linhas(draw, texto: str, x: int, y: int, fonte, largura: int, altura_linha: int) -> int:
    for linha in textwrap.wrap(texto, width=largura, replace_whitespace=False):
        draw.text((x, y), linha, fill="black", font=fonte)
        y += altura_linha
    return y

def descricao_trabalho(ficha: FichaCatalografica) -> str:
    tipo = ficha.tipo_trabalho or "Trabalho acadêmico"
    nivel = (ficha.nivel_ensino or "").lower()
    if tipo == "TCC":
        tipo = "Trabalho de Conclusão de Curso"
    return (
        f"{tipo} ({nivel}) – Instituto Federal de Educação, Ciência e Tecnologia do "
        f"Rio Grande do Norte, {ficha.cidade}, {ficha.data_ano}."
    )

def assuntos_catalograficos(ficha: FichaCatalografica) -> str:
    palavras = [p.strip().rstrip(".") for p in (ficha.palavras_chave or "").split(",") if p.strip()]
    assuntos = [f"{indice + 1}. {palavra}." for indice, palavra in enumerate(palavras)]
    assuntos.append("I. Título.")
    return " ".join(assuntos)

def gerar_imagem_png(ficha: FichaCatalografica) -> str:
    IMAGENS_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 1200, 820
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    font_title = carregar_fonte_negrito(24)
    font_text = carregar_fonte(22)
    font_small = carregar_fonte(18)
    font_footer = carregar_fonte(20)

    margin_x = 70
    margin_y = 50
    box_margin = 34

    title_text = "Dados Internacionais de Catalogação na Publicação (CIP)"
    title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, margin_y), title_text, fill="black", font=font_title)

    box_y_start = margin_y + 70
    box_x_start = margin_x
    box_x_end = width - margin_x
    box_y_end = height - margin_y - 110
    box_width = box_x_end - box_x_start

    draw.rectangle([(box_x_start, box_y_start), (box_x_end, box_y_end)], outline="black", width=2)

    y_position = box_y_start + box_margin
    line_height = 30
    content_x = box_x_start + box_margin

    autor_formatado = formatar_nome_catalografico(ficha.autor_nome_completo)
    titulo_completo = ficha.titulo if not ficha.subtitulo else f"{ficha.titulo} : {ficha.subtitulo}"

    linhas = [
        autor_formatado,
        f"{titulo_completo} / {ficha.autor_nome_completo}. – {ficha.data_ano}.",
        "1 arquivo digital : il. ; PDF.",
        descricao_trabalho(ficha),
    ]

    if ficha.orientador_nome_completo:
        linhas.append(f"Orientador(a): {ficha.orientador_nome_completo}.")

    if ficha.coorientador_nome_completo:
        linhas.append(f"Coorientador(a): {ficha.coorientador_nome_completo}.")

    linhas.append(assuntos_catalograficos(ficha))

    for linha in linhas:
        y_position = escrever_linhas(draw, linha, content_x, y_position, font_text, 82, line_height)
        y_position += 8

    cdu_text = "SIBi/IFRN                                                                        CDU 000"
    cdu_y = box_y_end - box_margin - 40
    draw.text((content_x, cdu_y), cdu_text, fill="black", font=font_text)

    rodape_1 = "Sistema Integrado de Bibliotecas do IFRN"
    if ficha.revisor_nome:
        rodape_2 = f"Elaborada pelo(a) Bibliotecário(a) {ficha.revisor_nome}"
    else:
        rodape_2 = "Elaborada pelo(a) Bibliotecário(a)"

    for indice, nota_text in enumerate([rodape_1, rodape_2]):
        nota_bbox = draw.textbbox((0, 0), nota_text, font=font_footer)
        nota_width = nota_bbox[2] - nota_bbox[0]
        nota_x = box_x_start + (box_width - nota_width) // 2
        nota_y = box_y_end + 22 + (indice * 30)
        draw.text((nota_x, nota_y), nota_text, fill="black", font=font_footer)

    assinatura_text = f"Validação: {ficha.id_curto}"
    assinatura_bbox = draw.textbbox((0, 0), assinatura_text, font=font_small)
    assinatura_width = assinatura_bbox[2] - assinatura_bbox[0]
    draw.text((box_x_end - assinatura_width, height - margin_y), assinatura_text, fill="black", font=font_small)

    filename = f"{ficha.id_curto}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    img_path = IMAGENS_DIR / filename

    img.save(img_path, format="PNG")

    return f"imagens/{filename}"

