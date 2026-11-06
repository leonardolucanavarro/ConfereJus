from datetime import date
from pathlib import Path

import streamlit as st

from conferejus.analise import analisar_documento, extrair_texto_arquivo


st.set_page_config(page_title="ConfereJus | Disputas contratuais", layout="wide")

st.markdown("""
<style>
    .stApp { background: #091e2b; color: #e8efef; }
    [data-testid="stHeader"] { background: #091e2b; }
    .block-container { max-width: 1160px; padding-top: 5rem; padding-bottom: 3rem; }
    h1, h2, h3, h4, p, label { color: #e8efef; }
    h1 { font-family: Georgia, serif; font-weight: 400; font-size: 2.35rem; }
    h2, h3 { font-weight: 500; }
    .brand-name { font-family: Georgia, serif; font-size: 1.9rem; margin: 0; }
    .eyebrow { color: #8ab8ad; letter-spacing: .13em; font-size: .72rem; }
    .intro { color: #b0c3c9; max-width: 730px; line-height: 1.6; }
    .section-label { color: #91b9b0; font-size: .8rem; letter-spacing: .07em; margin-top: 1rem; }
    [data-testid="stCaptionContainer"] p { color: #a9bec5; }
    [data-testid="stVerticalBlockBorderWrapper"] { border-color: #29434c; }
    textarea, input { color: #142f39 !important; background: #f1f4f3 !important; -webkit-text-fill-color: #142f39 !important; }
    textarea::placeholder, input::placeholder { color: #62767c !important; -webkit-text-fill-color: #62767c !important; opacity: 1; }
    [data-baseweb="select"] > div { background: #f1f4f3 !important; color: #142f39 !important; }
    [data-baseweb="select"] span { color: #142f39 !important; }
    [data-baseweb="tag"] { background: #d4e5df !important; }
    [role="listbox"], [role="option"] { background: #f1f4f3 !important; color: #142f39 !important; }
    [data-testid="stFileUploaderDropzone"] { background: #f1f4f3; }
    [data-testid="stFileUploaderDropzone"] * { color: #24434c !important; }
    [data-testid="stBaseButton-primary"] { background: #007766 !important; border-color: #007766 !important; color: white !important; }
    [data-testid="stBaseButton-primary"] * { color: white !important; }
    [data-testid="stLinkButton"] a { background: #d9e9e3 !important; border-color: #d9e9e3 !important; }
    [data-testid="stLinkButton"] a * { color: #153e38 !important; }
    [data-testid="stMetricValue"] { color: #a6cfc2; }
    hr { border-color: #29434c; }
</style>
""", unsafe_allow_html=True)

logo = Path(__file__).resolve().with_name("logo.png")
col_logo, col_brand = st.columns([1, 9])
with col_logo:
    if logo.exists():
        # A light background keeps the original dark logo legible.
        from PIL import Image

        with Image.open(logo) as imagem:
            imagem_rgba = imagem.convert("RGBA")
            fundo = Image.new("RGBA", imagem_rgba.size, "#9bb8ad")
            fundo.alpha_composite(imagem_rgba)
            st.image(fundo.convert("RGB"), width=76)
with col_brand:
    st.markdown('<p class="brand-name">ConfereJus</p><div class="eyebrow">DISPUTAS CONTRATUAIS EMPRESARIAIS</div>', unsafe_allow_html=True)

st.divider()
st.title("Revisão de fundamentos contratuais")
st.markdown('<p class="intro">Parta do seu documento e delimite a controvérsia. Consulte decisões da base selecionada e confira sua pertinência antes de utilizá-las na argumentação.</p>', unsafe_allow_html=True)

with st.expander("Escopo e método desta versão"):
    st.write("O projeto está sendo direcionado a conflitos sobre descumprimento de contratos empresariais: inadimplemento, cláusula penal, perdas e danos, boa-fé e revisão contratual.")
    st.write("Nesta versão, a comparação utiliza similaridade de palavras e expressões com seis resumos de decisões do STJ. Parte do acervo ainda trata de relações civis ou de consumo: confira o contexto de cada decisão antes de aplicá-la a uma relação empresarial.")
    st.write("Não há pesquisa automática nos tribunais, validação das citações do documento nem determinação de que uma decisão favorece sua tese. O contexto informado orienta a consulta textual; não equivale a uma interpretação jurídica automatizada.")
    st.caption("Use documentos fictícios, públicos ou devidamente anonimizados nos testes. Não envie material confidencial nesta fase.")

principal, lateral = st.columns([1.65, 1], gap="large")
with principal:
    st.markdown('<div class="section-label">01 / DOCUMENTO</div>', unsafe_allow_html=True)
    st.subheader("Material para revisão")
    modo = st.radio("Forma de envio", ["Enviar arquivo", "Colar texto"], horizontal=True)
    arquivo = None
    texto = ""
    if modo == "Enviar arquivo":
        arquivo = st.file_uploader("Selecione o documento", type=["pdf", "docx", "txt"])
        st.caption("PDF com texto selecionável, Word ou TXT. PDFs escaneados ainda não têm leitura por OCR.")
    else:
        texto = st.text_area("Trecho ou documento", height=290, placeholder="Insira o texto que deseja comparar com a base de decisões.")

    st.markdown('<div class="section-label">02 / QUESTÃO EM DISCUSSÃO</div>', unsafe_allow_html=True)
    objetivo = st.text_area("Qual argumento ou pedido você quer examinar?", height=110, placeholder="Ex.: Quero examinar os fundamentos para reduzir a multa diante do cumprimento parcial do contrato.")
    st.caption("O objetivo será acrescentado à consulta textual. Descreva a questão de forma específica.")

with lateral:
    st.markdown('<div class="section-label">CONTEXTO DA REVISÃO</div>', unsafe_allow_html=True)
    tema = st.selectbox("Assunto predominante", ["Inadimplemento e resolução contratual", "Cláusula penal e multas", "Perdas e danos", "Boa-fé e comportamento das partes", "Revisão contratual", "Mais de um assunto / não sei"])
    posicao = st.selectbox("Posição da parte representada", ["Credora da obrigação discutida", "Devedora da obrigação discutida", "Obrigações recíprocas / ambas", "Ainda não definida"])
    contexto = st.text_area("Fatos relevantes (opcional)", height=140, placeholder="Qual obrigação foi descumprida? Houve cumprimento parcial? O que a outra parte alega?")
    st.caption("A posição e os fatos serão registrados no resumo da revisão e incluídos na consulta. O método atual não distingue automaticamente argumentos favoráveis e contrários.")

iniciar = st.button("Comparar fundamentos", type="primary")

entrada = (modo, texto, arquivo.getvalue() if arquivo else None, arquivo.name if arquivo else None, tema, posicao, objetivo, contexto)
if st.session_state.get("entrada_revisada") != entrada:
    st.session_state.pop("revisao", None)

if iniciar:
    if not (arquivo is not None if modo == "Enviar arquivo" else texto.strip()):
        st.warning("Envie um documento ou cole um texto para continuar.")
    elif not objetivo.strip():
        st.warning("Descreva o argumento ou pedido que deseja examinar.")
    else:
        try:
            with st.spinner("Extraindo o texto e consultando a base selecionada..."):
                documento = extrair_texto_arquivo(arquivo) if arquivo else texto.strip()
                if not documento.strip():
                    st.warning("Não foi encontrado texto extraível. Se o PDF for escaneado, utilize uma versão com texto ou cole a transcrição.")
                else:
                    # Keep compatibility with the existing analysis function.
                    consulta_contextual = f"{documento}\n\nQuestão: {objetivo.strip()}\nPosição: {posicao}\nFatos: {contexto.strip()}"
                    criterios = [] if tema == "Mais de um assunto / não sei" else [tema]
                    resultados = analisar_documento(consulta_contextual, "Direito Contratual Empresarial", criterios)
                    st.session_state["revisao"] = {"resultados": resultados, "objetivo": objetivo.strip(), "tema": tema, "posicao": posicao}
                    st.session_state["entrada_revisada"] = entrada
        except Exception:
            st.error("Não foi possível processar o material. Confira se o arquivo está legível e se a base está disponível. Se o problema persistir, consulte o terminal do VS Code.")

revisao = st.session_state.get("revisao")
if revisao:
    st.divider()
    st.subheader("Decisões para conferência")
    st.write(f"Questão informada: {revisao['objetivo']}")
    st.caption(f"{revisao['tema']} · {revisao['posicao']}")
    st.info("Os resultados abaixo são candidatos à leitura, não conclusões sobre sua tese. A pontuação mede proximidade textual: não é probabilidade de êxito, força do precedente ou validação jurídica.")
    # Display textual similarity rather than the old mixed 'technical index'.
    resultados = sorted(revisao["resultados"], key=lambda item: item["aderencia_percentual"], reverse=True)
    if not resultados:
        st.warning("Nenhum resultado foi devolvido pela base.")
    for resultado in resultados:
        with st.container(border=True):
            titulo, pontuacao = st.columns([3, 1])
            titulo.markdown(f"#### {resultado['processo']}")
            data_original = str(resultado["data_julgamento"])
            try:
                data_formatada = date.fromisoformat(data_original[:10]).strftime("%d/%m/%Y")
            except ValueError:
                data_formatada = data_original
            titulo.caption(f"{resultado['tribunal']} · {resultado['orgao_julgador']} · {data_formatada}")
            pontuacao.metric("Similaridade textual", f"{resultado['aderencia_percentual']:.1f}%".replace(".", ","))
            st.write(f"Tema da decisão: {resultado['tema']}")
            st.write(resultado["tese_resumida"])
            st.caption("Resumo cadastrado na base, não elaborado a partir do documento enviado. Confira na fonte os fatos, o alcance do entendimento e sua relação com o pedido.")
            st.link_button("Abrir fonte oficial", resultado["fonte_url"])
    with st.expander("Como interpretar esta seleção"):
        st.write("O mecanismo atual seleciona até três candidatos usando 75% de similaridade textual, 15% de um valor cadastrado de autoridade e 10% de atualidade relativa ao acervo. Nesta tela, os candidatos selecionados são apresentados por similaridade textual. O valor de autoridade é igual para as seis decisões e não distingue precedentes vinculantes.")
        st.write("A seleção ainda pode trazer fontes pouco relacionadas. Não conclua pela manutenção ou substituição de uma citação apenas pela pontuação. A filtragem e a comparação por trechos serão aprimoradas na próxima etapa.")

st.divider()
st.caption("ConfereJus · Protótipo acadêmico em desenvolvimento · Revisão profissional indispensável.")
