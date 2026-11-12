"""Exporta o resultado da revisao para DOCX em memoria, sem rede ou credenciais."""

import io
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Inches, Pt, RGBColor

from .analise import LIMIAR_SIMILARIDADE, MINIMO_TERMOS_COMUNS


_INCOMPATIVEIS_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def _texto(valor):
    return _INCOMPATIVEIS_XML.sub("\ufffd", "" if valor is None else str(valor))


def _campo(documento, rotulo, valor, padrao="Não informado"):
    paragrafo = documento.add_paragraph()
    paragrafo.add_run(rotulo + ": ").bold = True
    paragrafo.add_run(_texto(valor) if valor not in (None, "", []) else padrao)
    return paragrafo


def _trecho(documento, rotulo, valor):
    p = documento.add_paragraph()
    p.add_run(rotulo).bold = True
    p.paragraph_format.keep_with_next = True
    p = documento.add_paragraph(_texto(valor), style="Trecho do documento")
    return p


def _link_fonte(documento, endereco, rotulo="Abrir fonte cadastrada no STJ"):
    """So cria hyperlink HTTPS para dominio do STJ; nunca abre o endereco."""
    url = str(endereco or "").strip()
    try:
        partes = urlparse(url)
        host = (partes.hostname or "").lower()
        seguro = (
            partes.scheme == "https" and (host == "stj.jus.br" or host.endswith(".stj.jus.br"))
            and not partes.username and not partes.password and partes.port in (None, 443)
            and not any(c.isspace() or ord(c) < 32 for c in url)
            and "\\" not in url
        )
    except ValueError:
        seguro = False
    p = documento.add_paragraph()
    if not seguro:
        p.add_run("Link oficial não disponível ou fora do domínio permitido.").italic = True
        return
    relacao = p.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), relacao)
    trecho = OxmlElement("w:r")
    propriedades = OxmlElement("w:rPr")
    cor = OxmlElement("w:color")
    cor.set(qn("w:val"), "00685D")
    sublinhado = OxmlElement("w:u")
    sublinhado.set(qn("w:val"), "single")
    propriedades.extend([cor, sublinhado])
    trecho.append(propriedades)
    texto = OxmlElement("w:t")
    texto.text = rotulo
    trecho.append(texto)
    link.append(trecho)
    p._p.append(link)


def _formatar_documento(documento):
    secao = documento.sections[0]
    secao.page_width, secao.page_height = Inches(8.5), Inches(11)
    secao.top_margin = secao.bottom_margin = Inches(0.8)
    secao.left_margin = secao.right_margin = Inches(0.85)
    secao.footer_distance = Inches(0.35)
    normal = documento.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.12
    normal.paragraph_format.widow_control = True
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "pt-BR")
    normal.element.get_or_add_rPr().append(lang)
    for nome, tamanho in (("Title", 24), ("Subtitle", 12), ("Heading 1", 15), ("Heading 2", 12)):
        estilo = documento.styles[nome]
        estilo.font.name = "Calibri"
        estilo.font.size = Pt(tamanho)
        estilo.font.color.rgb = RGBColor(0, 0, 0)
        estilo.font.underline = False
        estilo.paragraph_format.space_before = Pt(14 if nome.startswith("Heading") else 0)
        estilo.paragraph_format.space_after = Pt(8)
        estilo.paragraph_format.keep_with_next = True
        for borda in list(estilo.element.xpath("./w:pPr/w:pBdr")):
            borda.getparent().remove(borda)
    citado = documento.styles.add_style("Trecho do documento", 1)
    citado.base_style = normal
    citado.paragraph_format.left_indent = Inches(0.18)
    citado.paragraph_format.right_indent = Inches(0.18)
    rodape = secao.footer.paragraphs[0]
    rodape.add_run("ConfereJus  |  Protótipo acadêmico  |  Página ")
    campo = OxmlElement("w:fldSimple")
    campo.set(qn("w:instr"), "PAGE")
    rodape._p.append(campo)
    for run in rodape.runs:
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0, 0, 0)


def gerar_relatorio_docx(revisao):
    """Gera bytes DOCX de um retrato da revisao, preservando a ordem recebida.

    Nao consulta a base, nao reexecuta o motor, nao salva arquivos e nao incorpora
    a conta Google. Campos inesperados do dicionario nao sao exportados.
    """
    if not isinstance(revisao, dict) or not {"objetivo", "resultados", "referencias"} <= revisao.keys():
        raise ValueError("A revisão precisa conter objetivo, resultados e referências.")
    if not isinstance(revisao["resultados"], list) or not isinstance(revisao["referencias"], list):
        raise ValueError("Resultados e referências devem ser listas.")
    momento = revisao.get("gerado_em")
    if momento:
        try:
            instante = datetime.fromisoformat(momento)
        except (TypeError, ValueError) as erro:
            raise ValueError("Data da revisão inválida.") from erro
        if instante.tzinfo is None:
            raise ValueError("A data da revisão deve informar o fuso horário.")
        instante = instante.astimezone(timezone.utc)
    else:
        instante = datetime.now(timezone.utc)
    documento = Document()
    _formatar_documento(documento)
    propriedades = documento.core_properties
    propriedades.title = "Relatório de revisão de fundamentos contratuais"
    propriedades.subject = "Resultados e referências da revisão no ConfereJus"
    propriedades.author = propriedades.last_modified_by = "ConfereJus"
    propriedades.created = propriedades.modified = instante.replace(tzinfo=None)
    propriedades.comments = ""
    documento.add_paragraph("Relatório de revisão de fundamentos contratuais", style="Title")
    documento.add_paragraph("ConfereJus", style="Subtitle")
    documento.add_paragraph(
        "Este relatório registra a revisão automática exibida no aplicativo. "
        "As fontes sugeridas são pistas para conferência, não uma conclusão jurídica. "
        "A similaridade textual não representa probabilidade de êxito ou força do argumento."
    )
    _campo(documento, "Revisão realizada em", instante.strftime("%d/%m/%Y às %H:%M UTC"))
    resultados, referencias = revisao["resultados"], revisao["referencias"]
    _campo(documento, "Fontes sugeridas", len(resultados))
    _campo(documento, "Referências distintas reconhecidas", len(referencias))

    documento.add_heading("Dados da revisão", level=1)
    _campo(documento, "Objetivo informado", revisao["objetivo"])
    _campo(documento, "Assunto predominante", revisao.get("tema"))
    _campo(documento, "Posição da parte", revisao.get("posicao"))
    _campo(documento, "Fatos informados", revisao.get("contexto"), "Não informados")
    origem = str(revisao.get("origem_documento") or "Texto informado").replace("\\", "/").rsplit("/", 1)[-1]
    _campo(documento, "Origem do documento", origem)
    if revisao.get("caracteres_documento") is not None:
        _campo(documento, "Caracteres do texto analisado", revisao["caracteres_documento"])
    digest = revisao.get("documento_sha256", "")
    if digest:
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError("O identificador SHA-256 do documento é inválido.")
        p = _campo(documento, "SHA-256 do texto analisado", digest)
        for run in p.runs:
            run.font.size = Pt(9)
    documento.add_paragraph(
        "O texto integral não é anexado automaticamente. O arquivo contém fatos e "
        "trechos do material enviado, que podem ser sensíveis. Revise antes de compartilhar."
    )

    documento.add_heading("Referências citadas no documento", level=1)
    documento.add_paragraph(
        "Conferência de identificadores no cadastro local do STJ. Uma referência "
        "localizada não tem seu conteúdo validado; uma referência não verificada não é necessariamente falsa."
    )
    erro_referencias = revisao.get("erro_referencias", "")
    if erro_referencias:
        _campo(documento, "Conferência não concluída", erro_referencias)
    elif not referencias:
        documento.add_paragraph("Nenhuma referência foi reconhecida nos formatos suportados. Isso não comprova que o documento esteja sem citações.")
    for indice, referencia in enumerate(referencias, start=1):
        documento.add_heading(f"Referência {indice}", level=2)
        _campo(documento, "Citação identificada", referencia.get("citacao"))
        _campo(documento, "Situação", referencia.get("status"))
        if referencia.get("explicacao"):
            documento.add_paragraph(_texto(referencia["explicacao"]))
        for registro in referencia.get("registros_base", []):
            _campo(documento, "Registro da base", registro.get("processo"))
            _campo(documento, "Tema cadastrado", registro.get("tema"))
            exata = referencia.get("tipo_correspondencia") == "identificador_exato"
            _link_fonte(documento, registro.get("fonte_url"), "Abrir fonte cadastrada no STJ" if exata else "Abrir fonte do registro relacionado")
        ocorrencias = referencia.get("ocorrencias", [])
        _campo(documento, "Ocorrências no documento", len(ocorrencias))
        for numero, ocorrencia in enumerate(ocorrencias, start=1):
            _trecho(documento, f"Contexto da ocorrência {numero}", ocorrencia.get("trecho", ""))
        if referencia.get("aviso"):
            documento.add_paragraph(_texto(referencia["aviso"]))

    documento.add_heading("Fontes sugeridas por assunto", level=1)
    documento.add_paragraph("Esta seleção é independente da conferência dos identificadores citados. A ordem é a mesma da tela e não depende apenas da porcentagem de similaridade.")
    if not resultados:
        documento.add_paragraph("Nenhuma decisão da base passou pelos filtros do documento e pelo foco reconhecido. Isso não significa que inexista jurisprudência sobre o assunto.")
    for indice, resultado in enumerate(resultados, start=1):
        documento.add_heading(f"Fonte sugerida {indice}", level=2)
        _campo(documento, "Processo", resultado.get("processo"))
        _campo(documento, "Tribunal e órgão julgador", f"{resultado.get('tribunal', '')} · {resultado.get('orgao_julgador', '')}")
        _campo(documento, "Data do julgamento", resultado.get("data_julgamento"))
        if resultado.get("relator"):
            _campo(documento, "Relatoria", resultado["relator"])
        _campo(documento, "Tema cadastrado", resultado.get("tema"))
        percentual = resultado.get("aderencia_percentual")
        if percentual is not None:
            _campo(documento, "Similaridade textual", f"{float(percentual):.1f}%".replace(".", ","))
        _campo(documento, "Síntese cadastrada", resultado.get("tese_resumida"))
        _campo(documento, "Relação com o pedido", resultado.get("relacao_pedido"), "Sentido não classificado")
        if resultado.get("explicacao_pedido"):
            documento.add_paragraph(_texto(resultado["explicacao_pedido"]))
        _campo(documento, "Contexto de origem", resultado.get("contexto_origem"))
        _campo(documento, "Limites de aplicação", resultado.get("limites_aplicacao"))
        _trecho(documento, "Trecho relacionado do documento", resultado.get("trecho_relacionado", ""))
        _campo(documento, "Termos normalizados em comum", ", ".join(resultado.get("termos_relacionados", [])))
        if resultado.get("justificativa"):
            _campo(documento, "Justificativa da seleção", resultado["justificativa"])
        if resultado.get("explicacao_foco"):
            _campo(documento, "Foco reconhecido", resultado["explicacao_foco"])
        if resultado.get("alerta"):
            _campo(documento, "Cautela de leitura", resultado["alerta"])
        _link_fonte(documento, resultado.get("fonte_url"))

    documento.add_heading("Método e limites", level=1)
    documento.add_paragraph(
        f"A seleção usa TF-IDF e similaridade do cosseno por trechos de até 100 palavras. "
        f"Exige ao menos {MINIMO_TERMOS_COMUNS} termos relevantes em comum e similaridade "
        f"mínima de {LIMIAR_SIMILARIDADE:.0%} no documento. Retorna até três fontes, "
        "sem completar a lista à força e sem bônus por data, autoridade ou posição da parte."
    )
    documento.add_paragraph(
        "Após a elegibilidade pelo documento, regras textuais de foco e sentido do pedido "
        "podem filtrar e ordenar as fontes. A afinidade com o objetivo tem peso experimental "
        "de 25%; os fatos têm peso de 10% apenas se compartilham ao menos dois termos "
        "relevantes com o documento; o restante vem do melhor trecho. A porcentagem "
        "exibida não inclui esses pesos. Objetivo e contexto não criam elegibilidade sozinhos."
    )
    documento.add_paragraph(
        "Direção textual compatível e contraponto a conferir são classificações por expressões, "
        "não interpretações jurídicas. As regras são incompletas e podem omitir fontes úteis. "
        "Contexto e limites das fontes são apresentados para leitura, sem verificar automaticamente "
        "se os requisitos da decisão estão presentes no documento."
    )
    documento.add_paragraph(
        "A conferência reconhece REsp e AREsp com AgInt, AgRg e EDcl opcionais nas formas "
        "suportadas. Compara classe, número, UF e incidentes com o cadastro local. Não consulta "
        "os tribunais nem confirma transcrições, autenticidade, atualidade ou apoio ao argumento. "
        "Outras grafias e classes podem não ser reconhecidas. Leia o inteiro teor antes de utilizar uma fonte."
    )
    documento.add_paragraph("Revisão profissional indispensável. Este relatório não é um parecer jurídico nem o relatório acadêmico de uso de IA no desenvolvimento do projeto.")
    memoria = io.BytesIO()
    documento.save(memoria)
    return memoria.getvalue()
