import io
from pathlib import Path

import pandas as pd
from docx import Document
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


CAMINHO_BASE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "jurisprudencias.csv"
)


def extrair_texto_arquivo(arquivo):
    """Extrai texto de arquivos PDF, DOCX ou TXT."""
    extensao = Path(arquivo.name).suffix.lower()
    conteudo = arquivo.getvalue()

    if extensao == ".pdf":
        leitor = PdfReader(io.BytesIO(conteudo))
        return "\n".join(
            pagina.extract_text() or ""
            for pagina in leitor.pages
        ).strip()

    if extensao == ".docx":
        documento = Document(io.BytesIO(conteudo))
        return "\n".join(
            paragrafo.text
            for paragrafo in documento.paragraphs
        ).strip()

    if extensao == ".txt":
        try:
            return conteudo.decode("utf-8").strip()
        except UnicodeDecodeError:
            return conteudo.decode("latin-1").strip()

    raise ValueError("Formato não aceito. Utilize PDF, DOCX ou TXT.")


def carregar_jurisprudencias():
    """Carrega a base verificada de decisões judiciais."""
    return pd.read_csv(CAMINHO_BASE, sep=";")


def analisar_documento(texto, area, criterios, limite=3):
    """
    Compara o documento com a base de jurisprudências.

    O índice técnico combina:
    - 75% de aderência textual;
    - 15% de autoridade da fonte;
    - 10% de atualidade da decisão.
    """
    base = carregar_jurisprudencias()

    base["texto_comparacao"] = (
        base["area"].fillna("")
        + " "
        + base["tema"].fillna("")
        + " "
        + base["tese_resumida"].fillna("")
        + " "
        + base["palavras_chave"].fillna("")
    )

    consulta = " ".join(
        [texto, area, " ".join(criterios)]
    )

    vetorizador = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        max_features=5000,
    )

    textos = base["texto_comparacao"].tolist() + [consulta]
    matriz = vetorizador.fit_transform(textos)

    base["aderencia"] = cosine_similarity(
        matriz[-1],
        matriz[:-1],
    ).flatten()

    autoridade = (
        pd.to_numeric(
            base["grau_autoridade"],
            errors="coerce",
        ).fillna(1)
        / 3
    )

    anos = pd.to_datetime(
        base["data_julgamento"],
        errors="coerce",
    ).dt.year

    menor_ano = anos.min()
    maior_ano = anos.max()

    if maior_ano == menor_ano:
        atualidade = pd.Series(
            1.0,
            index=base.index,
        )
    else:
        atualidade = (
            (anos - menor_ano)
            / (maior_ano - menor_ano)
        ).fillna(0)

    base["indice_tecnico"] = (
        base["aderencia"] * 0.75
        + autoridade * 0.15
        + atualidade * 0.10
    )

    def gerar_recomendacao(aderencia):
        if aderencia >= 0.18:
            return "Manter e reforçar"
        if aderencia >= 0.08:
            return "Complementar"
        return "Substituir ou revisar"

    base["recomendacao"] = base["aderencia"].apply(
        gerar_recomendacao
    )

    base["aderencia_percentual"] = (
        base["aderencia"] * 100
    ).round(1)

    base["indice_percentual"] = (
        base["indice_tecnico"] * 100
    ).round(1)

    resultado = base.sort_values(
        "indice_tecnico",
        ascending=False,
    ).head(limite)

    return resultado.to_dict(orient="records")