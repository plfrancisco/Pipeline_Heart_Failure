"""Gera o relatório em Word (.docx) com a mesma formatação ABNT do PDF.

Reaproveita o HTML de `gerar_relatorio.py`, para o texto das duas versões nunca divergir.
O arquivo pode ser aberto no Word ou importado pelo Google Docs.

Uso: python relatorio/gerar_docx.py <pasta_temporaria_do_pdf> relatorio/relatorio_final.docx
A pasta temporária é a mesma usada em gerar_relatorio.py (precisa conter o corpo.pdf já gerado,
de onde saem as páginas do sumário).
"""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from PIL import Image

import gerar_relatorio as relatorio

FONTE = "Times New Roman"
LARGURA_UTIL_CM = 16.0   # 21 cm - 3 cm (esquerda) - 2 cm (direita)

# Espaço antes de cada bloco da capa e da folha de rosto, em pontos (distribui os blocos na página).
ESPACOS_CAPA = [0, 130, 130, 265]
ESPACOS_ROSTO = [0, 150, 105, 215]


def aplicar_fonte(estilo_ou_run, tamanho=12, negrito=None, italico=None):
    fonte = estilo_ou_run.font
    fonte.name = FONTE
    fonte.size = Pt(tamanho)
    if negrito is not None:
        fonte.bold = negrito
    if italico is not None:
        fonte.italic = italico
    propriedades = estilo_ou_run.element.get_or_add_rPr()
    fontes = propriedades.find(qn("w:rFonts"))
    if fontes is None:
        fontes = OxmlElement("w:rFonts")
        propriedades.append(fontes)
    for atributo in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fontes.set(qn(atributo), FONTE)


def configurar_estilos(documento):
    normal = documento.styles["Normal"]
    aplicar_fonte(normal)
    formato = normal.paragraph_format
    formato.line_spacing = 1.5
    formato.space_before = Pt(0)
    formato.space_after = Pt(0)
    formato.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    idioma = OxmlElement("w:lang")
    idioma.set(qn("w:val"), "pt-BR")
    normal.element.get_or_add_rPr().append(idioma)
    for nome in ("Heading 1", "Heading 2"):
        estilo = documento.styles[nome]
        aplicar_fonte(estilo, negrito=True)
        estilo.font.color.rgb = None
        estilo.font.italic = False
        estilo.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        estilo.paragraph_format.space_before = Pt(18)
        estilo.paragraph_format.space_after = Pt(18)
        estilo.paragraph_format.keep_with_next = True
        estilo.paragraph_format.line_spacing = 1.5


def configurar_pagina(secao):
    secao.page_width, secao.page_height = Cm(21), Cm(29.7)
    secao.top_margin, secao.bottom_margin = Cm(3), Cm(2)
    secao.left_margin, secao.right_margin = Cm(3), Cm(2)
    secao.header_distance = Cm(2)
    secao.footer_distance = Cm(1.25)


def reiniciar_numeracao(secao, inicio):
    propriedades = secao._sectPr
    numeracao = propriedades.find(qn("w:pgNumType"))
    if numeracao is None:
        numeracao = OxmlElement("w:pgNumType")
        propriedades.append(numeracao)
    numeracao.set(qn("w:start"), str(inicio))


def numero_de_pagina_no_cabecalho(secao):
    """Número da página no canto superior direito (campo PAGE, não texto digitado)."""
    secao.header.is_linked_to_previous = False
    paragrafo = secao.header.paragraphs[0]
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragrafo.paragraph_format.line_spacing = 1.0
    run = paragrafo.add_run()
    aplicar_fonte(run)
    # Um campo do Word tem três partes: início, instrução (PAGE) e fim.
    for tipo, texto in (("begin", None), (None, " PAGE "), ("end", None)):
        if tipo:
            campo = OxmlElement("w:fldChar")
            campo.set(qn("w:fldCharType"), tipo)
            run._r.append(campo)
        else:
            instrucao = OxmlElement("w:instrText")
            instrucao.set(qn("xml:space"), "preserve")
            instrucao.text = texto
            run._r.append(instrucao)


def cabecalho_vazio(secao):
    secao.header.is_linked_to_previous = False
    secao.header.paragraphs[0].text = ""


def adicionar_trechos(paragrafo, no, tamanho=12, negrito_base=False, maiusculas=False):
    """Copia o texto de um nó HTML para o parágrafo, preservando negrito, itálico e quebras de linha."""
    for filho in no.children:
        if isinstance(filho, NavigableString):
            texto = re.sub(r"\s+", " ", str(filho))
            if not texto:
                continue
            run = paragrafo.add_run(texto.upper() if maiusculas else texto)
            aplicar_fonte(run, tamanho, negrito=negrito_base or None)
        elif isinstance(filho, Tag):
            if filho.name == "br":
                paragrafo.add_run().add_break()
            elif filho.name in ("b", "strong"):
                adicionar_trechos(paragrafo, filho, tamanho, True, maiusculas)
            elif filho.name in ("i", "em"):
                for run_filho in _runs_de(paragrafo, filho, tamanho, negrito_base, maiusculas):
                    run_filho.font.italic = True
            else:
                adicionar_trechos(paragrafo, filho, tamanho, negrito_base, maiusculas)


def _runs_de(paragrafo, no, tamanho, negrito_base, maiusculas):
    antes = len(paragrafo.runs)
    adicionar_trechos(paragrafo, no, tamanho, negrito_base, maiusculas)
    return paragrafo.runs[antes:]


def novo_paragrafo(documento, alinhamento=None, espaco_antes=0, espaco_depois=0, linha=None,
                   recuo_primeira_linha=None, recuo_esquerda=None, manter_com_proximo=False, estilo=None):
    paragrafo = documento.add_paragraph(style=estilo)
    formato = paragrafo.paragraph_format
    if alinhamento is not None:
        paragrafo.alignment = alinhamento
    formato.space_before = Pt(espaco_antes)
    formato.space_after = Pt(espaco_depois)
    if linha is not None:
        formato.line_spacing = linha
    if recuo_primeira_linha is not None:
        formato.first_line_indent = Cm(recuo_primeira_linha)
    if recuo_esquerda is not None:
        formato.left_indent = Cm(recuo_esquerda)
    formato.keep_with_next = manter_com_proximo
    return paragrafo


def definir_bordas(elemento_pr, **bordas):
    """Aplica bordas (top/bottom/...) em tblPr ou tcPr; cada valor é a espessura em oitavos de ponto."""
    tag = "w:tblBorders" if elemento_pr.tag == qn("w:tblPr") else "w:tcBorders"
    conjunto_de_bordas = OxmlElement(tag)
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        if tag == "w:tcBorders" and lado.startswith("inside"):
            continue
        borda = OxmlElement(f"w:{lado}")
        espessura = bordas.get(lado)
        borda.set(qn("w:val"), "single" if espessura else "nil")
        if espessura:
            borda.set(qn("w:sz"), str(espessura))
            borda.set(qn("w:color"), "000000")
        conjunto_de_bordas.append(borda)
    elemento_pr.append(conjunto_de_bordas)


def adicionar_tabela(documento, no_tabela):
    cabecalho = [c.get_text() for c in no_tabela.find("thead").find_all("th")]
    linhas = [[c for c in tr.find_all("td")] for tr in no_tabela.find("tbody").find_all("tr")]
    tabela = documento.add_table(rows=1 + len(linhas), cols=len(cabecalho))
    tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabela.autofit = True
    definir_bordas(tabela._tbl.tblPr, top=12, bottom=12)
    for coluna, titulo in enumerate(cabecalho):
        celula = tabela.rows[0].cells[coluna]
        _formatar_celula(celula, None, titulo, negrito=True)
        definir_bordas(celula._tc.get_or_add_tcPr(), bottom=6)
    for indice_linha, linha in enumerate(linhas, start=1):
        for coluna, no_celula in enumerate(linha):
            _formatar_celula(tabela.rows[indice_linha].cells[coluna], no_celula, None)
    for linha in tabela.rows:   # impede que uma linha seja cortada entre páginas
        cantsplit = OxmlElement("w:cantSplit")
        linha._tr.get_or_add_trPr().append(cantsplit)


def _formatar_celula(celula, no_html, texto, negrito=False):
    paragrafo = celula.paragraphs[0]
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragrafo.paragraph_format.line_spacing = 1.0
    paragrafo.paragraph_format.space_after = Pt(2)
    paragrafo.paragraph_format.space_before = Pt(2)
    paragrafo.paragraph_format.keep_with_next = True
    if no_html is not None:
        adicionar_trechos(paragrafo, no_html, tamanho=10)
    else:
        run = paragrafo.add_run(texto)
        aplicar_fonte(run, 10, negrito=negrito)


def adicionar_figura(documento, no_figura):
    caminho = Path(unquote(urlparse(no_figura.find("img")["src"]).path.lstrip("/")))
    largura_px, altura_px = Image.open(caminho).size
    largura_cm = min(15.5, 7.5 * largura_px / altura_px)
    paragrafo = novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.CENTER, linha=1.0, manter_com_proximo=True)
    paragrafo.add_run().add_picture(str(caminho), width=Cm(largura_cm))


def montar_capa_ou_rosto(documento, html, espacos):
    sopa = BeautifulSoup(html, "html.parser")
    blocos = sopa.select(".capa-bloco > div")
    for indice, bloco in enumerate(blocos):
        eh_natureza = "natureza" in bloco.get("class", [])
        paragrafo = novo_paragrafo(
            documento,
            WD_ALIGN_PARAGRAPH.JUSTIFY if eh_natureza else WD_ALIGN_PARAGRAPH.CENTER,
            espaco_antes=espacos[indice], linha=1.0 if eh_natureza else 1.5,
            recuo_esquerda=8 if eh_natureza else None)
        adicionar_trechos(paragrafo, bloco)


def montar_pre_textuais(documento, html):
    sopa = BeautifulSoup(html, "html.parser")
    for pagina in sopa.select("div.pre"):
        primeiro = True
        for no in pagina.children:
            if not isinstance(no, Tag):
                continue
            classes = no.get("class", [])
            if "sem-numero" in classes:
                paragrafo = novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.CENTER, espaco_depois=18,
                                           manter_com_proximo=True)
                paragrafo.paragraph_format.page_break_before = primeiro
                adicionar_trechos(paragrafo, no, negrito_base=True, maiusculas=True)
                primeiro = False
            elif "resumo" in classes:
                adicionar_trechos(novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.JUSTIFY, linha=1.0), no)
            elif "palavras" in classes:
                adicionar_trechos(novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.JUSTIFY, espaco_antes=12, linha=1.0), no)
            elif "sumario-linha" in classes:
                _linha_do_sumario(documento, no)


def _linha_do_sumario(documento, no):
    rotulo = no.select_one(".rotulo").get_text()
    numero = no.select_one(".num").get_text()
    nivel1 = "nivel1" in no.get("class", [])
    paragrafo = novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.LEFT, recuo_esquerda=None if nivel1 else 0.6)
    paragrafo.paragraph_format.tab_stops.add_tab_stop(Cm(LARGURA_UTIL_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    run = paragrafo.add_run(f"{rotulo.upper() if nivel1 else rotulo}\t{numero}")
    aplicar_fonte(run, negrito=nivel1)


def montar_parte_textual(documento, html):
    sopa = BeautifulSoup(html, "html.parser")
    raiz = sopa.select_one("div.tex")
    for no in raiz.children:
        if not isinstance(no, Tag):
            continue
        classes = no.get("class", [])
        if no.name == "h1" and "sec" in classes:
            paragrafo = documento.add_paragraph(style="Heading 1")
            adicionar_trechos(paragrafo, no, negrito_base=True, maiusculas=True)
        elif no.name == "h2":
            paragrafo = documento.add_paragraph(style="Heading 2")
            adicionar_trechos(paragrafo, no, negrito_base=True)
        elif no.name == "h1" and "sem-numero" in classes:
            paragrafo = novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.CENTER, espaco_antes=18, espaco_depois=18,
                                       manter_com_proximo=True)
            adicionar_trechos(paragrafo, no, negrito_base=True, maiusculas=True)
        elif no.name == "p" and "texto" in classes:
            paragrafo = novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.JUSTIFY, recuo_primeira_linha=1.25)
            adicionar_trechos(paragrafo, no)
        elif no.name == "ol":
            for letra, item in zip("abcdefghij", no.find_all("li")):
                paragrafo = novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.JUSTIFY, recuo_esquerda=2.0,
                                           recuo_primeira_linha=-0.75)
                paragrafo.paragraph_format.tab_stops.add_tab_stop(Cm(2.0))
                run = paragrafo.add_run(f"{letra})\t")
                aplicar_fonte(run)
                adicionar_trechos(paragrafo, item)
        elif no.name == "p" and "legenda" in classes:
            paragrafo = novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.LEFT, espaco_antes=12, espaco_depois=4,
                                       linha=1.0, manter_com_proximo=True)
            adicionar_trechos(paragrafo, no, tamanho=10, negrito_base=True)
        elif no.name == "p" and "fonte" in classes:
            paragrafo = novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.LEFT, espaco_antes=4, espaco_depois=12, linha=1.0)
            adicionar_trechos(paragrafo, no, tamanho=10)
        elif no.name == "table":
            adicionar_tabela(documento, no)
        elif no.name == "div" and "fig" in classes:
            adicionar_figura(documento, no)
        elif no.name == "div" and "refs" in classes:
            for referencia in no.find_all("p", recursive=False):
                paragrafo = novo_paragrafo(documento, WD_ALIGN_PARAGRAPH.LEFT, espaco_depois=12, linha=1.0)
                adicionar_trechos(paragrafo, referencia)


def main():
    pasta_trabalho = Path(sys.argv[1])
    caminho_saida = Path(sys.argv[2])
    numeros_paginas, _ = relatorio.descobrir_paginas(pasta_trabalho / "corpo.pdf")

    documento = Document()
    configurar_estilos(documento)
    # Seção 1: capa (não é contada nem numerada).
    configurar_pagina(documento.sections[0])
    cabecalho_vazio(documento.sections[0])
    montar_capa_ou_rosto(documento, relatorio.pagina_capa(), ESPACOS_CAPA)

    # Seção 2: elementos pré-textuais. A folha de rosto é a página 1, mas o número não aparece.
    secao_pre = documento.add_section(WD_SECTION.NEW_PAGE)
    configurar_pagina(secao_pre)
    cabecalho_vazio(secao_pre)
    reiniciar_numeracao(secao_pre, 1)
    montar_capa_ou_rosto(documento, relatorio.folha_de_rosto(), ESPACOS_ROSTO)
    montar_pre_textuais(documento, relatorio.pre_textuais(numeros_paginas))

    # Seção 3: parte textual, com o número da página no canto superior direito.
    secao_textual = documento.add_section(WD_SECTION.NEW_PAGE)
    configurar_pagina(secao_textual)
    numero_de_pagina_no_cabecalho(secao_textual)
    montar_parte_textual(documento, relatorio.parte_textual())

    documento.core_properties.title = relatorio.TITULO
    documento.core_properties.author = ", ".join(relatorio.AUTORES)
    documento.save(str(caminho_saida))
    print("salvo:", caminho_saida)


if __name__ == "__main__":
    main()
