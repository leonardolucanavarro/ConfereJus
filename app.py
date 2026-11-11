from datetime import date
from pathlib import Path

import streamlit as st

from conferejus.analise import (
    LIMIAR_SIMILARIDADE,
    MINIMO_TERMOS_COMUNS,
    analisar_documento,
    extrair_texto_arquivo,
)


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
    [data-testid="stText"],
[data-testid="stText"] * {
    color: #e8efef !important;
}
    hr { border-color: #29434c; }
        [data-testid="stBaseButton-secondary"] {
        background: #d9e9e3 !important;
        border-color: #d9e9e3 !important;
        color: #153e38 !important;
    }

    [data-testid="stBaseButton-secondary"] * {
        color: #153e38 !important;
    }
</style>
""", unsafe_allow_html=True)
if st.user.is_logged_in:
    st.write("Olá,", st.user.get("name", "usuário"))
    st.button("Sair da conta", on_click=st.logout)
else:
    st.button("Entrar com Google", on_click=st.login)
    st.caption("Você também pode usar a análise sem entrar na conta.")
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
    st.write("O documento é dividido em trechos e comparado aos resumos e termos cadastrados na base do STJ. O mecanismo aproxima algumas expressões equivalentes e exibe o trecho e os termos que motivaram cada seleção. Parte do acervo ainda trata de relações civis ou de consumo: confira seu contexto antes de aplicar uma decisão a uma relação empresarial.")
    st.write("Não há pesquisa automática nos tribunais, validação das citações nem determinação de que uma decisão favorece sua tese. O contexto preenchido é registrado para orientar sua conferência; nesta etapa, não altera a seleção automática das fontes.")
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
        st.caption("PDF com texto selecionável, Word ou TXT. Até 20 MB e 120 mil caracteres de texto; PDFs de até 200 páginas. Sem OCR para documentos escaneados.")
    else:
        texto = st.text_area("Trecho ou documento", height=290, placeholder="Insira o texto que deseja comparar com a base de decisões.")

    st.markdown('<div class="section-label">02 / QUESTÃO EM DISCUSSÃO</div>', unsafe_allow_html=True)
    objetivo = st.text_area("Qual argumento ou pedido você quer examinar?", height=110, placeholder="Ex.: Quero examinar os fundamentos para reduzir a multa diante do cumprimento parcial do contrato.")
    st.caption("Delimite a questão para orientar a conferência dos resultados. Nesta versão, a seleção automática considera os trechos do documento, não este campo.")

with lateral:
    st.markdown('<div class="section-label">CONTEXTO DA REVISÃO</div>', unsafe_allow_html=True)
    tema = st.selectbox("Assunto predominante", ["Inadimplemento e resolução contratual", "Cláusula penal e multas", "Perdas e danos", "Boa-fé e comportamento das partes", "Revisão contratual", "Mais de um assunto / não sei"])
    posicao = st.selectbox("Posição da parte representada", ["Credora da obrigação discutida", "Devedora da obrigação discutida", "Obrigações recíprocas / ambas", "Ainda não definida"])
    contexto = st.text_area("Fatos relevantes (opcional)", height=140, placeholder="Qual obrigação foi descumprida? Houve cumprimento parcial? O que a outra parte alega?")
    st.caption("O contexto será registrado no resumo da revisão. O mecanismo ainda não utiliza esses campos para distinguir argumentos favoráveis e contrários.")

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
                    # Contexto permanece separado para não criar resultados artificiais.
                    criterios = [] if tema == "Mais de um assunto / não sei" else [tema]
                    resultados = analisar_documento(documento, "Direito Contratual Empresarial", criterios)
                    st.session_state["revisao"] = {"resultados": resultados, "objetivo": objetivo.strip(), "tema": tema, "posicao": posicao, "contexto": contexto.strip()}
                    st.session_state["entrada_revisada"] = entrada
        except ValueError as erro:
            st.error(str(erro))
        except Exception:
            st.error("Não foi possível processar o material. Confira se o arquivo está legível e se a base está disponível. Se o problema persistir, consulte o terminal do VS Code.")

revisao = st.session_state.get("revisao")
if revisao:
    st.divider()
    st.subheader("Jurisprudências relacionadas ao documento")
    st.write(f"Questão informada: {revisao['objetivo']}")
    st.caption(f"{revisao['tema']} · {revisao['posicao']}")
    if revisao.get("contexto"):
        with st.expander("Contexto informado"):
            st.write(revisao["contexto"])
    st.caption("Confira a pertinência de cada decisão considerando os fatos e o pedido do caso. A pontuação representa similaridade textual, não probabilidade de êxito.")
    resultados = sorted(revisao["resultados"], key=lambda item: item["aderencia_percentual"], reverse=True)
    if not resultados:
        st.info("Nenhuma decisão da base atingiu os critérios mínimos de correspondência com os trechos enviados. Isso não significa que inexista jurisprudência sobre o assunto. Experimente um trecho mais específico ou consulte outras fontes.")
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
            st.caption("Síntese cadastrada na base. Consulte a fonte oficial para conferir o inteiro teor e o contexto da decisão.")
            st.markdown("**Trecho relacionado do seu documento**")
            st.text(resultado["trecho_relacionado"])
            with st.expander("Por que esta decisão foi selecionada?"):
                st.write("Este trecho apresentou a maior similaridade com o cadastro desta fonte entre os trechos que passaram pelo filtro de relevância.")
                st.write("Termos em comum após normalização: " + ", ".join(resultado["termos_relacionados"]) + ".")
                st.caption("Expressões como cláusula penal e multa contratual são aproximadas por regras explícitas. Termos em comum não demonstram, sozinhos, concordância entre os argumentos.")
            st.link_button("Abrir fonte oficial", resultado["fonte_url"])
    with st.expander("Como interpretar esta seleção"):
        st.write("O documento é separado em frases e janelas de até 100 palavras, com sobreposição nas unidades longas. Cada trecho é comparado ao tema, à síntese e às palavras-chave das fontes por TF-IDF e similaridade do cosseno. Não há bônus por data ou valor cadastrado de autoridade.")
        st.write(f"Para uma decisão ser exibida, ao menos um trecho deve ter {MINIMO_TERMOS_COMUNS} termos relevantes em comum com a fonte e similaridade de pelo menos {LIMIAR_SIMILARIDADE:.0%}. O sistema retorna até três fontes, ordenadas pelo melhor trecho de cada uma, sem completar a lista à força. Esses limites são experimentais e serão avaliados com mais exemplos.")
        st.write("A similaridade não comprova que o entendimento se aplica ao caso, nem determina se ele apoia ou contraria o argumento. A ferramenta não substitui a leitura da fonte e não valida automaticamente as citações do documento. Objetivo, posição, assunto selecionado e fatos adicionais ficam registrados como contexto, sem alterar o ranking nesta etapa.")

st.divider()
st.caption("ConfereJus · Protótipo acadêmico em desenvolvimento · Revisão profissional indispensável.")
