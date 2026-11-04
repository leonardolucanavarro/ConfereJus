import streamlit as st

st.set_page_config(
    page_title="ConfereJus | Auditoria jurídica",
    page_icon="⚖️",
    layout="wide",
)

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(135deg, #06182f 0%, #0b2b50 100%);
            color: #f4f7fb;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            max-width: 1180px;
            padding-top: 2.5rem;
            padding-bottom: 4rem;
        }

        .brand {
            color: #45e0bd;
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 1rem;
        }

        .hero-title {
            color: #ffffff;
            font-size: 3.4rem;
            line-height: 1.05;
            font-weight: 800;
            max-width: 850px;
            margin-bottom: 1rem;
        }

        .hero-title span {
            color: #45e0bd;
        }

        .hero-text {
            color: #c8d6e7;
            font-size: 1.15rem;
            line-height: 1.7;
            max-width: 850px;
            margin-bottom: 2rem;
        }

        .step-card {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(69, 224, 189, 0.22);
            border-radius: 16px;
            padding: 1.3rem;
            min-height: 145px;
        }

        .step-number {
            color: #45e0bd;
            font-size: 0.85rem;
            font-weight: 800;
            text-transform: uppercase;
        }

        .step-title {
            color: #ffffff;
            font-size: 1.1rem;
            font-weight: 700;
            margin: 0.45rem 0;
        }

        .step-text {
            color: #b9c8da;
            font-size: 0.92rem;
            line-height: 1.5;
        }

        div.stButton > button {
            width: 100%;
            background: #45e0bd;
            color: #06182f;
            border: none;
            border-radius: 10px;
            padding: 0.75rem;
            font-weight: 800;
        }

        div.stButton > button:hover {
            background: #72efd2;
            color: #06182f;
        }

        h2, h3, label, p {
            color: #f4f7fb;
        }
           textarea {
            color: #06182f !important;
            background-color: #f4f7fb !important;
        }

        textarea::placeholder {
            color: #68778a !important;
            opacity: 1 !important;
        }
     </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="brand">ConfereJus • Excelência técnica jurídica</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero-title">
        Seu documento não precisa de mais uma busca.
        Precisa de uma <span>auditoria jurídica.</span>
    </div>
    <div class="hero-text">
        O ConfereJus parte da petição, parecer ou contrato produzido pelo advogado,
        identifica as teses apresentadas e avalia se as fontes jurídicas realmente
        sustentam cada argumento. Ao final, indica o que manter, complementar ou substituir.
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        <div class="step-card">
            <div class="step-number">Etapa 01</div>
            <div class="step-title">Envie o documento</div>
            <div class="step-text">Faça upload de um PDF, Word ou texto produzido pelo escritório.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="step-card">
            <div class="step-number">Etapa 02</div>
            <div class="step-title">Direcione a revisão</div>
            <div class="step-text">Escolha os pontos que merecem maior atenção na análise.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="step-card">
            <div class="step-number">Etapa 03</div>
            <div class="step-title">Receba o diagnóstico</div>
            <div class="step-text">Visualize fontes aderentes, riscos e recomendações objetivas.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("## Iniciar auditoria")

modo = st.radio(
    "Como deseja inserir o documento?",
    ["Enviar arquivo", "Colar texto"],
    horizontal=True,
)

documento_enviado = False

if modo == "Enviar arquivo":
    arquivo = st.file_uploader(
        "Envie seu documento",
        type=["pdf", "docx", "txt"],
    )
    documento_enviado = arquivo is not None
else:
    texto = st.text_area(
        "Cole o conteúdo jurídico",
        height=220,
        placeholder="Cole aqui a petição, o parecer, o contrato ou outro documento jurídico...",
    )
    documento_enviado = bool(texto.strip())

area = st.selectbox(
    "Área jurídica predominante",
    [
        "Direito Civil",
        "Direito Empresarial",
        "Direito Contratual",
        "Direito Bancário",
        "Direito Trabalhista",
        "Direito Público",
        "Outra",
    ],
)

criterios = st.multiselect(
    "O que deve receber maior atenção?",
    [
        "Aderência das jurisprudências às teses",
        "Força e atualidade dos precedentes",
        "Coerência da argumentação",
        "Pontos sem sustentação suficiente",
        "Sugestões de fontes complementares",
    ],
    default=[
        "Aderência das jurisprudências às teses",
        "Força e atualidade dos precedentes",
    ],
)

if st.button("Iniciar auditoria técnica"):
    if not documento_enviado:
        st.warning("Envie um arquivo ou cole um texto para iniciar a auditoria.")
    elif not criterios:
        st.warning("Selecione pelo menos um critério de revisão.")
    else:
        st.success("Documento recebido. A estrutura inicial do fluxo está funcionando.")
        st.info(
            "Na próxima etapa, conectaremos esta interface ao mecanismo de análise "
            "e à base pública de jurisprudências."
        )

st.caption(
    "Protótipo acadêmico. Os resultados deverão ser conferidos por um profissional habilitado."
)
