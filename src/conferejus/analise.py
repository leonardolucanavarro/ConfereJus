"""Recuperacao por trechos e contexto explicito; nao realiza julgamento juridico."""

import io
import re
import unicodedata
from pathlib import Path

import pandas as pd
from docx import Document
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


CAMINHO_BASE = Path(__file__).resolve().parents[2] / "data" / "jurisprudencias.csv"
LIMIAR_SIMILARIDADE = 0.12
MINIMO_TERMOS_COMUNS = 2
MAXIMO_CARACTERES = 120_000
MAXIMO_TRECHOS = 400

# Lista local e explicita: nao exige baixar modelos ou pacotes adicionais.
# Negacoes como 'nao' e 'sem' NAO sao removidas.
PALAVRAS_COMUNS = set("""
a o as os um uma uns umas de da do das dos em na no nas nos
para por pelo pela pelos pelas e ou que se com ao aos sua seu suas seus
esta este estas estes esse essa esses essas isso isto aquilo ser estar
foi foram sera sao eh e ha ter tem tinha como quando onde qual quais
mais muito tambem apenas pode podem deve devem caso casos artigo art
contrato contratos contratual contratuais empresarial empresariais direito
civil partes parte processo recurso especial stj jurisprudencia jurisprudencias
decisao decisoes tese teses analise revisao documento documentos
""".split())

# Somente aproximacoes terminologicas declaradas, nao equivalencias juridicas.
EQUIVALENCIAS = (
    (r"\bclausulas? penais\b|\bclausula penal\b", "multa contratual"),
    (r"\binadimplemento\b", "descumprimento"),
    (r"\badimplemento\b", "cumprimento"),
    (r"\bindenizacoes\b", "indenizacao"),
    (r"\bprejuizos\b", "prejuizo"),
    (r"\bmultas\b", "multa"),
)

# Regras de organizacao textual. Nao sao uma ontologia nem filtros de validade.
# Nenhum processo ou ID recebe tratamento especial.
ROTULOS_QUESTOES = {
    "multa_reducao": "Redução ou manutenção da multa",
    "multa_solidariedade": "Multa e solidariedade",
    "multa_cumulacao": "Cumulação de multa e indenização",
    "multa_alcance": "Hipóteses de incidência da multa",
    "limite_responsabilidade": "Limitação de responsabilidade",
    "mitigacao": "Mitigação do prejuízo",
    "supressio": "Supressio e confiança legítima",
    "reconvencao": "Revisão ou rescisão por reconvenção",
    "revisao": "Revisão e desequilíbrio contratual",
    "adimplemento_substancial": "Adimplemento substancial",
    "resilicao": "Resilição e encerramento da relação",
    "excecao": "Exceção do contrato não cumprido",
    "representacao": "Indenização na representação comercial",
    "lucros": "Prova de lucros cessantes",
    "cobranca": "Prova documental para cobrança",
}

ASSUNTO_QUESTOES = {
    "Cláusula penal e multas": {"multa_reducao", "multa_solidariedade", "multa_cumulacao", "multa_alcance", "limite_responsabilidade"},
    "Boa-fé e comportamento das partes": {"mitigacao", "supressio", "resilicao", "excecao"},
    "Revisão contratual": {"revisao", "reconvencao"},
    "Perdas e danos": {"lucros", "mitigacao", "multa_cumulacao", "limite_responsabilidade", "representacao"},
    "Inadimplemento e resolução contratual": {"adimplemento_substancial", "resilicao", "excecao", "representacao", "reconvencao"},
}


def identificar_questoes(texto):
    """Reconhece expressoes declaradas; nao infere o direito aplicavel."""
    t = normalizar_texto(texto)
    regras = {
        "multa_solidariedade": bool(re.search(r"solidari", t) and re.search(r"multa|penal", t)),
        "multa_cumulacao": bool(re.search(r"cumul|duplicidade", t) and re.search(r"multa|penal", t)),
        "multa_alcance": bool(re.search(r"interpretacao restritiva|hipoteses? de incidencia|hipotese expressamente prevista", t)),
        "limite_responsabilidade": bool(re.search(r"limita\w* (?:contratual de )?responsabilidade|clausula limitativa", t)),
        "mitigacao": bool(re.search(r"mitiga|mitigar|agravamento do (?:proprio )?prejuizo", t)),
        "supressio": bool(re.search(r"supressio|confianca legitima|inercia qualificada|cobranca retroativa", t)),
        "reconvencao": bool(re.search(r"reconvencao|reconvencional|contestacao", t)),
        "adimplemento_substancial": bool(re.search(r"(?:adimplemento|cumprimento) substancial", t)),
        "excecao": bool(re.search(r"excecao (?:do |de )?contrato nao cumprido|exceptio|ordem das prestacoes", t)),
        "representacao": bool(re.search(r"representacao comercial|representante comercial", t)),
        "lucros": bool(re.search(r"lucros cessantes|lucro hipotetico", t)),
        "cobranca": bool(re.search(r"monitoria|prova documental|memoria de calculo", t)),
    }
    regras["multa_reducao"] = bool(
        re.search(r"multa|penal", t)
        and re.search(r"reducao|reduzir|reduzid|excessiv|coercitiv|manter|manutencao", t)
        and not regras["multa_solidariedade"] and not regras["multa_cumulacao"]
        and not regras["limite_responsabilidade"]
    )
    regras["revisao"] = bool(re.search(r"revisao|imprevisao|onerosidade|desequilibrio", t)
                              and not regras["reconvencao"] and not regras["multa_reducao"])
    regras["resilicao"] = bool(re.search(r"resilicao|denuncia imotivada|rescisao unilateral|rompimento abrupto", t)
                                and not regras["representacao"])
    return {chave for chave, presente in regras.items() if presente}


def _sentido_pedido_multa(objetivo):
    """Apenas o pedido informado, nunca a posicao credora/devedora, define a busca."""
    t = normalizar_texto(objetivo)
    if not re.search(r"multa|penal", t):
        return "indefinido"
    contra_reducao = r"(?:nao|afastar|afastando|evitar|impedir|incabivel)\b(?:\W+\w+){0,4}\W+(?:reducao|reduzir)\b"
    contra_manutencao = r"(?:nao|afastar|afastando|evitar|impedir)\b(?:\W+\w+){0,4}\W+(?:manter|manutencao)\b"
    manter = bool(re.search(contra_reducao, t))
    reduzir = bool(re.search(contra_manutencao, t))
    restante = re.sub(contra_reducao, " ", t)
    restante = re.sub(contra_manutencao, " ", restante)
    reduzir |= bool(re.search(r"\breduzir\b|\breducao\b", restante))
    manter |= bool(re.search(r"\bmanter\b|\bmanutencao\b|\bpreservar\b", restante))
    if reduzir == manter:
        return "indefinido"
    return "reduzir" if reduzir else "manter"


def _sentido_cadastro_multa(registro):
    t = normalizar_texto(str(registro["tema"]) + ". " + str(registro["tese_resumida"]))
    manter = bool(re.search(r"\b(?:mantida|preservada)\b.{0,45}\bmulta\b|\bmanutencao\b.{0,30}\bmulta\b", t))
    reduzir = bool(re.search(r"reducao de oficio|\bdeve(?:ra)?\b.{0,35}\breduzir\b", t))
    if manter == reduzir:
        return "indefinido"
    return "reduzir" if reduzir else "manter"


def _ordenar_com_contexto(candidatos, documento, objetivo, assunto, posicao, fatos, vetorizador, matriz_base, registros):
    """Reordena somente fontes que passaram no filtro do documento original."""
    questoes_documento = identificar_questoes(documento)
    questoes_objetivo = identificar_questoes(objetivo)
    foco = questoes_objetivo or questoes_documento
    origem_foco = "questão informada" if questoes_objetivo else "documento"
    # Fatos refinam a correspondencia somente quando ha vocabulario no documento.
    fatos_ancorados = fatos if len(_termos(fatos) & _termos(documento)) >= MINIMO_TERMOS_COMUNS else ""
    if not foco and fatos_ancorados:
        foco = identificar_questoes(fatos_ancorados)
        origem_foco = "fatos informados com termos presentes no documento"
    if not foco:
        foco = ASSUNTO_QUESTOES.get(assunto, set())
        origem_foco = "assunto selecionado, sem questão específica reconhecida no texto"
    pedido = _sentido_pedido_multa(objetivo)
    consultas = vetorizador.transform([objetivo, fatos_ancorados])
    afinidades = cosine_similarity(consultas, matriz_base)
    # Reordenacao textual experimental, separada da similaridade exibida.
    peso_objetivo = 0.25 if objetivo.strip() else 0.0
    peso_fatos = 0.10 if fatos_ancorados else 0.0
    indice_colunas = {str(r["id"]): i for i, r in enumerate(registros)}
    for registro in candidatos:
        coluna = indice_colunas[str(registro["id"])]
        questoes_fonte = identificar_questoes(registro["tema"])
        if not questoes_fonte:
            questoes_fonte = identificar_questoes(registro["tese_resumida"])
        comuns = foco & questoes_fonte
        registro["questoes_foco"] = [ROTULOS_QUESTOES[q] for q in sorted(foco)]
        registro["questoes_fonte"] = [ROTULOS_QUESTOES[q] for q in sorted(questoes_fonte)]
        registro["origem_foco"] = origem_foco
        registro["prioridade_assunto"] = 2 if comuns else (0 if foco and questoes_fonte else 1)
        registro["prioridade_sentido"] = 1
        registro["relacao_pedido"] = "Sentido do pedido não classificado"
        registro["explicacao_pedido"] = "Não foi reconhecida uma relação de sentido pelas regras disponíveis. Confira a síntese e seus requisitos."
        if "multa_reducao" in comuns and pedido != "indefinido":
            sentido_fonte = _sentido_cadastro_multa(registro)
            if sentido_fonte != "indefinido":
                concorda = pedido == sentido_fonte
                registro["prioridade_sentido"] = 2 if concorda else 0
                registro["relacao_pedido"] = "Direção textual compatível" if concorda else "Contraponto a conferir"
                acao = "redução" if sentido_fonte == "reduzir" else "manutenção"
                registro["explicacao_pedido"] = (
                    f"O pedido informado busca {('redução' if pedido == 'reduzir' else 'manutenção')} da multa. "
                    f"O cadastro descreve {acao} da penalidade em seu próprio contexto. "
                    "Essa comparação é uma regra textual, não uma conclusão sobre o caso. "
                    "Confira os requisitos e os limites da fonte: a classificação não verifica se eles estão presentes no seu documento."
                )
        registro["afinidade_objetivo"] = round(float(afinidades[0, coluna]) * 100, 1)
        registro["afinidade_fatos"] = round(float(afinidades[1, coluna]) * 100, 1)
        registro["pontuacao_ordenacao"] = (
            registro["aderencia"] * (1 - peso_objetivo - peso_fatos)
            + float(afinidades[0, coluna]) * peso_objetivo
            + float(afinidades[1, coluna]) * peso_fatos
        )
        registro["assunto_informado"] = assunto
        registro["posicao_informada"] = posicao
        registro["fatos_usados_na_ordenacao"] = bool(fatos_ancorados)
        registro["explicacao_foco"] = (
            "Questões em comum com o foco: " + ", ".join(ROTULOS_QUESTOES[q] for q in sorted(comuns)) + "."
            if comuns else "Não foi reconhecida coincidência específica com o foco pelas regras disponíveis."
        )
        registro["metodo"] = "Filtro lexical no documento; ordenação experimental por questão específica, sentido textual do pedido e afinidade com objetivo e fatos ancorados. Sem bônus por data, autoridade ou posição da parte."
    # Questao diferente nao ocupa o lugar de uma fonte sobre o foco reconhecido.
    # Fontes sem coincidencia especifica nao sao apresentadas como pertinentes.
    if foco:
        candidatos = [r for r in candidatos if r["prioridade_assunto"] == 2]
    return sorted(candidatos, key=lambda r: (-r["prioridade_assunto"], -r["prioridade_sentido"], -r["pontuacao_ordenacao"], str(r["id"])))


def normalizar_texto(texto):
    texto = unicodedata.normalize("NFKD", str(texto).casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    for expressao, substituicao in EQUIVALENCIAS:
        texto = re.sub(expressao, substituicao, texto)
    return texto


def _termos(texto):
    return {
        termo for termo in re.findall(r"\b[a-z]{2,}\b", normalizar_texto(texto))
        if termo not in PALAVRAS_COMUNS
    }


def extrair_texto_arquivo(arquivo):
    """Le PDF textual, DOCX (incluindo tabelas) e TXT, sem OCR."""
    extensao = Path(arquivo.name).suffix.lower()
    conteudo = arquivo.getvalue()
    if len(conteudo) > 20 * 1024 * 1024:
        raise ValueError("Utilize um arquivo de ate 20 MB nesta versao.")
    if extensao == ".pdf":
        leitor = PdfReader(io.BytesIO(conteudo))
        if len(leitor.pages) > 200:
            raise ValueError("Utilize um PDF de ate 200 paginas nesta versao.")
        texto = "\n\n".join(pagina.extract_text() or "" for pagina in leitor.pages)
    elif extensao == ".docx":
        documento = Document(io.BytesIO(conteudo))
        blocos = [p.text for p in documento.paragraphs]
        for tabela in documento.tables:
            blocos.extend(" | ".join(c.text for c in linha.cells) for linha in tabela.rows)
        texto = "\n\n".join(blocos)
    elif extensao == ".txt":
        try:
            texto = conteudo.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = conteudo.decode("latin-1")
    else:
        raise ValueError("Formato nao aceito. Utilize PDF, DOCX ou TXT.")
    if len(texto) > MAXIMO_CARACTERES:
        raise ValueError("O texto excede 120 mil caracteres. Envie uma secao menor.")
    return texto.strip()


def carregar_jurisprudencias():
    """Valida a estrutura do cadastro; nao certifica o teor juridico das fontes."""
    base = pd.read_csv(CAMINHO_BASE, sep=";", encoding="utf-8-sig").fillna("")
    obrigatorias = {"id", "processo", "tribunal", "orgao_julgador", "data_julgamento", "tema", "tese_resumida", "palavras_chave", "fonte_url"}
    faltantes = obrigatorias - set(base.columns)
    if faltantes:
        raise ValueError("Colunas ausentes na base: " + ", ".join(sorted(faltantes)))
    if base["id"].duplicated().any():
        raise ValueError("Existem identificadores repetidos na base.")
    return base


def _separar_documento_contexto(texto):
    # Compatibilidade com o app atual, que acrescenta estes campos ao documento.
    # Contexto nunca cria sozinho a elegibilidade de uma decisao.
    marcador = "\n\nQuestão:"
    documento, separador, contexto = texto.partition(marcador)
    return documento.strip(), contexto.strip() if separador else ""


def _segmentar(texto):
    unidades = re.split(r"\n\s*\n|(?<=[.!?;])\s+", texto)
    trechos = []
    for unidade in unidades:
        unidade = unidade.strip()
        palavras = list(re.finditer(r"\S+", unidade))
        # Janelas de ate 100 palavras, com 20 palavras de sobreposicao.
        for inicio in range(0, len(palavras), 80):
            grupo = palavras[inicio:inicio + 100]
            trecho = unidade[grupo[0].start():grupo[-1].end()]
            if len(_termos(trecho)) >= MINIMO_TERMOS_COMUNS:
                trechos.append(trecho)
            if inicio + 100 >= len(palavras):
                break
    if len(trechos) > MAXIMO_TRECHOS:
        raise ValueError("Muitos trechos para esta versao. Envie uma secao menor.")
    return trechos


def analisar_documento(texto, area, criterios, limite=3, *, objetivo="", assunto="", posicao="", fatos=""):
    """Seleciona fontes por proximidade lexical a trechos, nao por apoio a tese.

    Area e criterios sao preservados na assinatura para compatibilidade.
    Nao sao acrescentados ao documento nem considerados filtros juridicos.
    Os novos campos nomeados reordenam apenas correspondencias do documento.
    O limiar e experimental e devera ser validado com uma amostra maior.
    """
    if not isinstance(texto, str) or not texto.strip() or limite <= 0:
        return []
    if len(texto) > MAXIMO_CARACTERES:
        raise ValueError("O texto excede 120 mil caracteres. Envie uma secao menor.")
    for campo in (objetivo, assunto, posicao, fatos):
        if not isinstance(campo, str):
            raise ValueError("Os campos de contexto devem conter texto.")
        if len(campo) > MAXIMO_CARACTERES:
            raise ValueError("Um campo de contexto excede 120 mil caracteres.")
    documento, contexto = _separar_documento_contexto(texto)
    trechos = _segmentar(documento)
    if not trechos:
        return []
    base = carregar_jurisprudencias()
    if base.empty:
        return []
    textos_base = [
        f"{linha['tema']} {linha['tese_resumida']} {linha['palavras_chave']}"
        for linha in base.to_dict(orient="records")
    ]
    vetorizador = TfidfVectorizer(
        preprocessor=normalizar_texto,
        lowercase=False,
        stop_words=sorted(PALAVRAS_COMUNS),
        token_pattern=r"(?u)\b[a-z]{2,}\b",
        ngram_range=(1, 2),
        sublinear_tf=True,
        max_features=15_000,
    )
    if not any(_termos(t) for t in textos_base):
        return []
    # Ajustado apenas ao acervo: documento novo nao altera o vocabulario da base.
    matriz_base = vetorizador.fit_transform(textos_base)
    matriz_trechos = vetorizador.transform(trechos)
    similaridades = cosine_similarity(matriz_trechos, matriz_base)
    termos_trechos = [_termos(t) for t in trechos]
    candidatos = []
    for coluna, registro in enumerate(base.to_dict(orient="records")):
        termos_fonte = _termos(textos_base[coluna])
        elegiveis = [
            i for i, termos in enumerate(termos_trechos)
            if len(termos & termos_fonte) >= MINIMO_TERMOS_COMUNS
            and similaridades[i, coluna] >= LIMIAR_SIMILARIDADE
        ]
        if not elegiveis:
            continue
        melhor = max(elegiveis, key=lambda i: similaridades[i, coluna])
        valor = float(similaridades[melhor, coluna])
        comuns = sorted(termos_trechos[melhor] & termos_fonte)
        registro.update({
            "aderencia": valor,
            "aderencia_percentual": round(valor * 100, 1),
            "trecho_relacionado": trechos[melhor],
            "numero_trecho": melhor + 1,
            "termos_relacionados": comuns,
            "justificativa": "O trecho compartilha com o cadastro da fonte os termos normalizados: " + ", ".join(comuns) + ". A selecao nao determina se a decisao apoia ou contraria o argumento.",
            "alerta": "Leia o inteiro teor para conferir fatos, fundamento e alcance. Negacoes e conclusoes opostas ainda podem compartilhar vocabulario.",
            "metodo": "TF-IDF por trechos e filtro lexical; sem bonus por data ou autoridade.",
            # Campos legados evitam quebrar interfaces antigas. Nao sao novos indices.
            "indice_tecnico": valor,
            "indice_percentual": round(valor * 100, 1),
            "recomendacao": "Conferir pertinencia no caso concreto",
        })
        candidatos.append(registro)
    if any((objetivo.strip(), assunto.strip(), posicao.strip(), fatos.strip())):
        registros = base.to_dict(orient="records")
        candidatos = _ordenar_com_contexto(candidatos, documento, objetivo, assunto, posicao, fatos, vetorizador, matriz_base, registros)
        return candidatos[:int(limite)]
    return sorted(candidatos, key=lambda item: (-item["aderencia"], str(item["id"])))[:int(limite)]


# Conferencia bibliografica local, independente da recuperacao por assunto.
# As siglas suportadas nao cobrem todas as classes ou formas de citacao.
_PADRAO_REFERENCIA = re.compile(
    r"(?<![\w/])"
    r"(?P<incidentes>(?:(?:AgInt|AgRg|EDcl)\s+(?:no|nos|na|nas)\s+)*)"
    r"(?P<classe>AREsp|REsp)\b\s*"
    r"(?:(?:n\.?\s*[º°o]?\.?|n[uú]mero)\s*)?"
    r"(?P<numero>\d{1,3}(?:\.\d{3})+|\d+)"
    r"(?:\s*/\s*(?P<uf>[a-z]{2}))?"
    r"(?![\w/]|\.\d)",
    re.IGNORECASE,
)
_UFS_REFERENCIAS = set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())
MAXIMO_REFERENCIAS = 200


def _dados_referencia(encontro):
    """Normaliza somente identificadores; nao corrige numero, UF ou classe."""
    classes = {"resp": "REsp", "aresp": "AREsp"}
    incidentes = tuple(
        {"agint": "AgInt", "agrg": "AgRg", "edcl": "EDcl"}[sigla.lower()]
        for sigla in re.findall(r"AgInt|AgRg|EDcl", encontro.group("incidentes"), re.IGNORECASE)
    )
    classe = classes[encontro.group("classe").lower()]
    numero = encontro.group("numero").replace(".", "").lstrip("0") or "0"
    uf = (encontro.group("uf") or "").upper()
    rotulo = " no ".join((*incidentes, classe)) + " " + numero + ("/" + uf if uf else "")
    return {
        "classe": classe, "incidentes": list(incidentes), "numero": numero,
        "uf": uf, "identificador": rotulo,
    }


def _chave_referencia(referencia):
    return (tuple(referencia["incidentes"]), referencia["classe"], referencia["numero"], referencia["uf"])


def extrair_referencias(texto):
    """Identifica REsp/AREsp, com AgInt/AgRg/EDcl opcionais, no texto original.

    Nao identifica toda jurisprudencia citada, nao interpreta transcricoes e nao
    valida a existencia do processo. Posicoes referem-se ao texto recebido.
    O contexto legado acrescentado apos '\\n\\nQuestão:' e desconsiderado.
    """
    if not isinstance(texto, str):
        raise ValueError("O documento deve conter texto.")
    if len(texto) > MAXIMO_CARACTERES:
        raise ValueError("O texto excede 120 mil caracteres. Envie uma secao menor.")
    documento = texto.partition("\n\nQuestão:")[0]
    referencias = {}
    for encontro in _PADRAO_REFERENCIA.finditer(documento):
        referencia = _dados_referencia(encontro)
        # Nao tenta aproveitar parte de um numero desproporcional ou truncado.
        if len(referencia["numero"]) > 10:
            continue
        chave = _chave_referencia(referencia)
        if chave not in referencias:
            if len(referencias) >= MAXIMO_REFERENCIAS:
                raise ValueError("Foram identificadas mais de 200 referencias distintas. Envie uma secao menor.")
            referencias[chave] = {**referencia, "citacao": encontro.group(), "ocorrencias": []}
        referencias[chave]["ocorrencias"].append({
            "citacao": encontro.group(), "inicio": encontro.start(), "fim": encontro.end(),
            "trecho": documento[max(0, encontro.start() - 90):min(len(documento), encontro.end() + 90)],
        })
    for referencia in referencias.values():
        referencia["quantidade"] = len(referencia["ocorrencias"])
    return list(referencias.values())


def conferir_referencias(texto):
    """Compara identificadores reconhecidos com os registros locais do STJ.

    Nao consulta a internet, nao altera o ranking e nao verifica autenticidade,
    transcricao, atualidade ou apoio juridico. Ausencia na base nao e falsidade.
    Incidentes diferentes ou UF ausente nunca recebem correspondencia exata.
    """
    referencias = extrair_referencias(texto)
    if not referencias:
        return []
    registros = []
    for registro in carregar_jurisprudencias().to_dict(orient="records"):
        if str(registro["tribunal"]).strip().upper() != "STJ":
            continue
        processo = str(registro["processo"]).strip()
        encontro = _PADRAO_REFERENCIA.fullmatch(processo)
        if encontro:
            registros.append((_dados_referencia(encontro), registro))
    aviso = (
        "Conferência restrita aos identificadores cadastrados na base local do STJ. "
        "Não confirma existência na fonte oficial, autenticidade, teor da citação, "
        "atualidade ou apoio ao argumento. Não localizada não significa falsa."
    )
    for referencia in referencias:
        numero_classe = [
            (dados, registro) for dados, registro in registros
            if (dados["classe"], dados["numero"]) == (referencia["classe"], referencia["numero"])
        ]
        mesma_uf = [(dados, registro) for dados, registro in numero_classe if dados["uf"] == referencia["uf"]]
        exatas = [registro for dados, registro in mesma_uf if _chave_referencia(dados) == _chave_referencia(referencia)]
        referencia.update({"status": "Não verificada na base", "tipo_correspondencia": "ausente", "registros_base": [], "aviso": aviso})
        if not referencia["uf"] or referencia["uf"] not in _UFS_REFERENCIAS:
            referencia["tipo_correspondencia"] = "incompleta" if not referencia["uf"] else "uf_invalida"
            referencia["status"] = "Não verificada: referência incompleta" if not referencia["uf"] else "Não verificada: UF não reconhecida"
            referencia["explicacao"] = "A UF está ausente ou não foi reconhecida. Não foi presumida nem corrigida a partir do cadastro."
        elif len(exatas) == 1:
            referencia["tipo_correspondencia"] = "identificador_exato"
            referencia["status"] = "Referência localizada na base"
            referencia["registros_base"] = exatas
            referencia["explicacao"] = "Classe, número, UF e incidentes reconhecidos coincidem com um registro local. Essa coincidência não verifica o conteúdo atribuído à decisão."
        elif len(exatas) > 1:
            referencia["tipo_correspondencia"] = "ambigua"
            referencia["status"] = "Não verificada: cadastro ambíguo"
            referencia["registros_base"] = exatas
            referencia["explicacao"] = "Mais de um registro tem o mesmo identificador. Confira a duplicidade antes de concluir a correspondência."
        elif mesma_uf:
            referencia["tipo_correspondencia"] = "processo_relacionado"
            referencia["status"] = "Processo relacionado na base"
            referencia["registros_base"] = [registro for _, registro in mesma_uf]
            referencia["explicacao"] = "Classe principal, número e UF coincidem, mas os incidentes (por exemplo, AgInt) são diferentes. Não foi localizada a referência exata citada."
        else:
            referencia["explicacao"] = "Não há correspondência para o identificador reconhecido. A base é limitada: não se pode concluir que a referência seja falsa."
            if numero_classe:
                referencia["explicacao"] += " Há registro com classe e número iguais, mas UF diferente; ele não foi usado para corrigir a citação."
    return referencias


