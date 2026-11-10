"""Recuperacao por trechos e regras lexicais; nao realiza julgamento juridico."""

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


def analisar_documento(texto, area, criterios, limite=3):
    """Seleciona fontes por proximidade lexical a trechos, nao por apoio a tese.

    Area e criterios sao preservados na assinatura para compatibilidade.
    Nao sao acrescentados ao documento nem considerados filtros juridicos.
    O limiar e experimental e devera ser validado com uma amostra maior.
    """
    if not isinstance(texto, str) or not texto.strip() or limite <= 0:
        return []
    if len(texto) > MAXIMO_CARACTERES:
        raise ValueError("O texto excede 120 mil caracteres. Envie uma secao menor.")
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
    return sorted(candidatos, key=lambda item: (-item["aderencia"], str(item["id"])))[:int(limite)]
