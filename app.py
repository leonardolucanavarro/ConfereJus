from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path

import streamlit as st
from conferejus.relatorio import gerar_relatorio_docx

from conferejus.analise import (
    LIMIAR_SIMILARIDADE,
    MAXIMO_CARACTERES,
    MINIMO_TERMOS_COMUNS,
    OPCOES_ASSUNTOS,
    analisar_documento,
    conferir_referencias,
    preparar_documento,
)


def mostrar_referencias(referencias, erro=""):
    """Exibe conferencia de identificadores sem mistura com o ranking tematico."""
    st.subheader("Referências citadas no documento")
    st.caption("Conferência de identificadores no cadastro local, sem consulta automática aos tribunais.")
    with st.expander("Quais referências são reconhecidas?"):
        st.write("REsp e AREsp, com AgInt, AgRg e EDcl opcionais na forma ‘no’. Outras classes, grafias e citações podem não ser reconhecidas.")
    if erro:
        st.warning("A conferência de referências não foi concluída: " + erro)
        return
    if not referencias:
        st.info("Nenhuma referência foi reconhecida nos formatos suportados. Isso não comprova que o documento esteja sem citações.")
        return
    exatas = sum(r["tipo_correspondencia"] == "identificador_exato" for r in referencias)
    relacionadas = sum(r["tipo_correspondencia"] == "processo_relacionado" for r in referencias)
    ocorrencias = sum(r["quantidade"] for r in referencias)
    st.caption(f"Referências distintas: {len(referencias)} · Ocorrências: {ocorrencias} · Localizadas pelo identificador: {exatas} · Processos relacionados, sem referência exata: {relacionadas} · Não verificadas: {len(referencias) - exatas - relacionadas}.")
    st.info("Uma referência localizada na base não tem seu conteúdo validado. Uma referência não verificada não deve ser tratada como falsa. Confira o inteiro teor, a transcrição e a relação com o argumento.")
    for indice, referencia in enumerate(referencias, start=1):
        with st.expander(f"{indice}. {referencia['identificador']} — {referencia['status']}"):
            st.write("**Referência identificada no documento:**")
            st.text(referencia["citacao"])
            st.write(referencia["explicacao"])
            for registro in referencia["registros_base"]:
                st.write("**Registro da base:** " + str(registro["processo"]))
                if registro.get("tema"):
                    st.write("**Tema cadastrado:** " + str(registro["tema"]))
                if registro.get("fonte_url"):
                    rotulo = "Abrir fonte cadastrada" if referencia["tipo_correspondencia"] == "identificador_exato" else "Abrir fonte do registro relacionado"
                    st.link_button(rotulo, registro["fonte_url"])
            st.write("**Ocorrências e contexto no documento:**")
            for numero, ocorrencia in enumerate(referencia["ocorrencias"], start=1):
                st.caption(f"Ocorrência {numero} de {referencia['quantidade']}")
                # Texto do usuario permanece como texto, sem HTML ou Markdown.
                st.text(ocorrencia["trecho"])
            st.caption(referencia["aviso"])


def mostrar_pagina_legal(pagina):
    """Exibe informacoes publicas exigidas para o uso opcional do login."""
    st.markdown('<p class="brand-name">ConfereJus</p><div class="eyebrow">DISPUTAS CONTRATUAIS EMPRESARIAIS</div>', unsafe_allow_html=True)
    st.divider()
    if pagina == "privacidade":
        st.title("Política de Privacidade")
        st.caption("Última atualização: 16 de novembro de 2026")
        st.write("O ConfereJus é um protótipo acadêmico de apoio à revisão de fundamentos contratuais. Esta política explica quais dados podem ser tratados durante o uso do aplicativo.")
        st.subheader("1. Uso sem conta")
        st.write("A análise pode ser utilizada sem login. O acesso com Google é opcional e serve apenas para identificar o usuário durante a sessão.")
        st.subheader("2. Dados tratados")
        st.write("Quando o login é utilizado, o aplicativo recebe do Google informações básicas de identidade, como nome e endereço de e-mail. O ConfereJus não solicita acesso ao Gmail, Google Drive, contatos ou outros arquivos da conta.")
        st.write("Documentos enviados ou textos colados são processados para realizar a comparação solicitada. O projeto não mantém banco de dados próprio para armazenar documentos, resultados ou credenciais. O relatório é gerado em memória para download pelo usuário.")
        st.subheader("3. Finalidade e cautelas")
        st.write("Os dados são utilizados somente para disponibilizar a sessão, processar a revisão solicitada e gerar o relatório. Utilize material fictício, público ou devidamente anonimizado. Não envie documentos confidenciais, dados pessoais desnecessários ou informações protegidas por sigilo.")
        st.subheader("4. Serviços de terceiros")
        st.write("O aplicativo é hospedado no Streamlit Community Cloud e o login opcional utiliza o Google OpenID Connect. Esses serviços podem tratar dados técnicos e cookies conforme suas próprias políticas.")
        st.subheader("5. Retenção e compartilhamento")
        st.write("O ConfereJus não vende dados e não compartilha o conteúdo analisado para fins comerciais. O projeto não mantém cópia permanente dos documentos em banco próprio. Dados técnicos eventualmente mantidos pela hospedagem ou pelo provedor de login seguem as regras desses serviços.")
        st.subheader("6. Escolhas do usuário")
        st.write("Você pode usar a análise sem entrar em uma conta, encerrar a sessão pelo botão de saída e deixar de enviar qualquer documento. Para dúvidas sobre privacidade ou autenticação, utilize o e-mail de suporte informado na tela de consentimento do Google.")
        st.info("Este protótipo não substitui revisão jurídica profissional e não deve receber material sigiloso.")
    else:
        st.title("Termos de Uso")
        st.caption("Última atualização: 16 de novembro de 2026")
        st.write("Ao utilizar o ConfereJus, você concorda com estes termos aplicáveis ao protótipo acadêmico.")
        st.subheader("1. Finalidade")
        st.write("O ConfereJus apresenta correspondências textuais entre o material enviado e uma base local selecionada de decisões. O serviço tem finalidade acadêmica e demonstrativa.")
        st.subheader("2. Ausência de parecer jurídico")
        st.write("Os resultados, classificações e percentuais não representam probabilidade de êxito, aplicabilidade de precedente, veracidade de citação ou aconselhamento jurídico. Toda fonte deve ser conferida em seu inteiro teor.")
        st.subheader("3. Responsabilidade pelo material")
        st.write("O usuário deve possuir autorização para utilizar o conteúdo enviado e deve evitar dados pessoais, documentos confidenciais ou informações protegidas por sigilo. Recomenda-se o uso de material fictício, público ou anonimizado.")
        st.subheader("4. Disponibilidade e limitações")
        st.write("O protótipo pode apresentar falhas, indisponibilidade ou resultados incompletos. Não há garantia de cobertura integral da jurisprudência, reconhecimento de todas as citações ou adequação a uma finalidade profissional específica.")
        st.subheader("5. Fontes externas")
        st.write("Links para tribunais e serviços de terceiros são fornecidos para conferência. O ConfereJus não controla a disponibilidade nem o conteúdo desses sites.")
        st.subheader("6. Uso adequado")
        st.write("Não utilize o aplicativo para atividades ilícitas, para expor dados de terceiros sem autorização ou como substituto da avaliação de profissional qualificado.")
    st.divider()
    st.link_button("↩️ Voltar ao ConfereJus", "https://conferejus.streamlit.app/")
    st.caption("ConfereJus · Protótipo acadêmico em desenvolvimento")


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
    [data-testid="stCaptionContainer"] p { color: #b5c9cf; }
    button:focus-visible, a:focus-visible, input:focus-visible, textarea:focus-visible {
        outline: 3px solid #8de0cb !important; outline-offset: 3px;
    }
    @media (max-width: 640px) {
        .block-container { padding: 3.5rem 1rem 2rem; }
        h1 { font-size: 1.85rem !important; }
    }
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
    [data-testid="stExpander"] summary,
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:focus,
[data-testid="stExpander"] summary:active {
    background-color: #102b3a !important;
    color: #e8fefe !important;
}

[data-testid="stExpander"] summary * {
    color: #e8fefe !important;
}
[data-testid="stDownloadButton"] button {
    background: #d9e9e3 !important;
    border-color: #d9e9e3 !important;
    color: #153e38 !important;
}
[data-testid="stDownloadButton"] button * {
    color: #153e38 !important;
}
</style>
""", unsafe_allow_html=True)

pagina_publica = st.query_params.get("pagina", "")
if pagina_publica in {"privacidade", "termos"}:
    mostrar_pagina_legal(pagina_publica)
    st.stop()

if "is_logged_in" in st.user:
    if st.user["is_logged_in"]:
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
st.title("Revise os fundamentos do seu documento")
st.markdown('<p class="intro">Envie o material, diga o que quer examinar e confira fontes relacionadas na base selecionada do STJ.</p>', unsafe_allow_html=True)
st.caption("1. Envie o documento  ·  2. Defina a questão  ·  3. Confira as fontes")
st.info("Protótipo acadêmico: utilize material fictício, público ou anonimizado. As sugestões não são conclusões jurídicas.")

with st.expander("Escopo e método desta versão"):
    st.write("O projeto está sendo direcionado a conflitos sobre descumprimento de contratos empresariais: inadimplemento, cláusula penal, perdas e danos, boa-fé e revisão contratual.")
    st.write("O documento é dividido em trechos e comparado aos resumos e termos cadastrados na base do STJ. O mecanismo aproxima algumas expressões equivalentes e exibe o trecho e os termos que motivaram cada seleção. Parte do acervo ainda trata de relações civis ou de consumo: confira seu contexto antes de aplicar uma decisão a uma relação empresarial.")
    st.write("A questão informada orienta a seleção por regras textuais de assunto e pedido. Os fatos só entram na ordenação quando compartilham ao menos dois termos relevantes com o documento. A posição da parte fica registrada, sem bônus automático para credor ou devedor. Em seção separada, os identificadores de referências reconhecidas são comparados ao cadastro local do STJ. Essa conferência não valida o teor das citações nem consulta os tribunais.")
    st.write("Antes da análise, o texto lido fica disponível para conferência. O assunto é sugerido por expressões do documento, sem usar o objetivo ou os fatos adicionais. A sugestão pode ser corrigida manualmente e pode ficar sem definição quando faltarem indicadores ou houver vários temas. Não representa interpretação jurídica ou confiança estatística.")
    st.caption("Use documentos fictícios, públicos ou devidamente anonimizados nos testes. Não envie material confidencial nesta fase.")

principal, lateral = st.columns([1.65, 1], gap="large")
with principal:
    st.markdown('<div class="section-label">01 / DOCUMENTO</div>', unsafe_allow_html=True)
    st.subheader("Seu documento")
    modo = st.radio("Forma de envio", ["Enviar arquivo", "Colar texto"], horizontal=True)
    arquivo = None
    texto = ""
    if modo == "Enviar arquivo":
        arquivo = st.file_uploader("Selecione o documento", type=["pdf", "docx", "txt"])
        st.caption("PDF com texto selecionável, DOCX ou TXT · até 20 MB. PDFs escaneados não têm leitura por OCR.")
        with st.expander("Limites de leitura"):
            st.write("Até 120 mil caracteres e 200 páginas por PDF. Documentos escaneados precisam de uma transcrição ou de uma versão com texto selecionável.")
    else:
        texto = st.text_area("Trecho ou documento", height=290, max_chars=MAXIMO_CARACTERES, placeholder="Insira o texto que deseja comparar com a base de decisões.")

    # Somente esta sessao guarda a leitura. Nada e colocado em cache global.
    if arquivo is not None:
        chave_documento = ("leitura-v1", modo, arquivo.name, sha256(arquivo.getvalue()).hexdigest())
        tem_entrada = True
    else:
        chave_documento = ("leitura-v1", modo, sha256(texto.encode("utf-8")).hexdigest())
        tem_entrada = bool(texto.strip())
    if st.session_state.get("chave_documento") != chave_documento:
        st.session_state["chave_documento"] = chave_documento
        st.session_state["preparacao_documento"] = None
        st.session_state.pop("revisao", None)
        st.session_state.pop("entrada_revisada", None)
        # Reset antes de criar os widgets, somente quando muda o documento.
        st.session_state.pop("modo_assunto", None)
        st.session_state.pop("assunto_manual", None)
        if tem_entrada:
            try:
                with st.spinner("Lendo o documento e preparando a prévia..."):
                    st.session_state["preparacao_documento"] = preparar_documento(
                        arquivo=arquivo, texto=texto if arquivo is None else "",
                    )
            except ValueError as erro:
                st.session_state["preparacao_documento"] = {"erro": str(erro)}
            except Exception:
                st.session_state["preparacao_documento"] = {"erro": "Não foi possível ler o arquivo. Ele pode estar corrompido ou não corresponder ao formato indicado. Envie outro arquivo legível ou cole o texto."}
    preparacao = st.session_state.get("preparacao_documento")
    documento_pronto = bool(preparacao and not preparacao.get("erro") and preparacao.get("texto"))
    if preparacao and preparacao.get("erro"):
        st.error(preparacao["erro"])
    elif preparacao and not documento_pronto:
        st.warning("Não foi encontrado texto extraível. Se o PDF for escaneado, utilize uma versão com texto ou cole a transcrição.")
    elif documento_pronto:
        st.caption(f"Texto disponível para revisão: {preparacao['caracteres']:,} caracteres.".replace(",", "."))
        with st.expander("Conferir o texto lido"):
            st.text(preparacao["previa"])
            if preparacao["previa_truncada"]:
                st.caption("Esta prévia mostra somente os primeiros 4.000 caracteres. A análise utiliza o texto completo lido, respeitando o limite de 120 mil caracteres.")
            else:
                st.caption("Esta prévia contém todo o texto lido. Confira a ordem, os acentos e eventuais trechos ausentes antes de analisar.")

    st.markdown('<div class="section-label">02 / QUESTÃO EM DISCUSSÃO</div>', unsafe_allow_html=True)
    objetivo = st.text_area("Qual argumento ou pedido você quer examinar?", height=110, placeholder="Ex.: Quero examinar os fundamentos para reduzir a multa diante do cumprimento parcial do contrato.")
    st.caption("Exemplo: examinar os fundamentos para reduzir uma multa. O pedido orienta a seleção, mas não cria correspondência sozinho.")

with lateral:
    st.markdown('<div class="section-label">AJUSTES DA REVISÃO</div>', unsafe_allow_html=True)
    st.subheader("Confira o assunto")
    modo_assunto = "Usar sugestão do documento"
    tema = OPCOES_ASSUNTOS[-1]
    if documento_pronto:
        sugestao = preparacao["sugestao"]
        st.write("**Assunto sugerido:** " + sugestao["assunto"])
        modo_assunto = st.radio(
            "Como definir o assunto?", ["Usar sugestão do documento", "Escolher manualmente"],
            key="modo_assunto",
        )
        if modo_assunto == "Escolher manualmente":
            tema = st.selectbox(
                "Assunto predominante", OPCOES_ASSUNTOS,
                index=OPCOES_ASSUNTOS.index(sugestao["assunto"]), key="assunto_manual",
            )
        else:
            tema = sugestao["assunto"]
        with st.expander("Por que este assunto foi sugerido?"):
            st.write(sugestao["explicacao"])
            st.write(sugestao["aviso"])
            if sugestao["assuntos_detectados"]:
                st.write("Assuntos com indicadores: " + ", ".join(sugestao["assuntos_detectados"]) + ".")
            for evidencia in sugestao["evidencias"]:
                st.caption(evidencia["assunto"])
                st.text(evidencia["expressao"])
                st.text(evidencia["trecho"])
            st.caption("São contados indicadores distintos. Repetições da mesma expressão não aumentam o peso. Com vários assuntos, só há sugestão predominante se o líder tiver pelo menos o dobro dos indicadores do segundo. Não é uma porcentagem de confiança.")
    else:
        st.caption("Envie um documento ou cole texto para receber uma sugestão de assunto e conferir a leitura.")
    with st.expander("Contexto adicional (opcional) — posição e fatos"):
        posicao = st.selectbox(
            "Posição da parte representada",
            ["Credora da obrigação discutida", "Devedora da obrigação discutida", "Obrigações recíprocas / ambas", "Ainda não definida"],
            index=3,
        )
        contexto = st.text_area("Fatos relevantes (opcional)", height=140, placeholder="Qual obrigação foi descumprida? Houve cumprimento parcial? O que a outra parte alega?")
        st.caption("A posição apenas fica registrada, sem favorecer automaticamente credor ou devedor. Fatos ligados ao documento podem refinar a ordem.")
    with st.expander("Como o assunto influencia a seleção?"):
        st.write("O assunto é uma alternativa quando não há foco específico reconhecido no objetivo ou no documento. A sugestão usa somente o documento e pode ser corrigida. Não é uma interpretação jurídica.")

iniciar = st.button("Comparar fundamentos", type="primary")
st.caption("Os resultados aparecem em três abas: fontes relacionadas, referências citadas e relatório em Word.")

entrada = ("assunto-v1", chave_documento, modo_assunto, tema, posicao, objetivo, contexto)
if st.session_state.get("entrada_revisada") != entrada:
    st.session_state.pop("revisao", None)

if iniciar:
    if not (arquivo is not None if modo == "Enviar arquivo" else texto.strip()):
        st.warning("Envie um documento ou cole um texto para continuar.")
    elif not documento_pronto:
        st.warning("Confira o aviso de leitura acima antes de analisar. Nenhum resultado foi gerado para este material.")
    elif not objetivo.strip():
        st.warning("Descreva o argumento ou pedido que deseja examinar.")
    else:
        try:
            with st.spinner("Consultando a base selecionada..."):
                documento = preparacao["texto"]
                if not documento.strip():
                    st.warning("Não foi encontrado texto extraível. Se o PDF for escaneado, utilize uma versão com texto ou cole a transcrição.")
                else:
                    # O contexto nunca cria sozinho a elegibilidade de uma fonte.
                    criterios = [] if tema == "Mais de um assunto / não sei" else [tema]
                    resultados = analisar_documento(
                        documento, "Direito Contratual Empresarial", criterios,
                        objetivo=objetivo.strip(), assunto=tema,
                        posicao=posicao, fatos=contexto.strip(),
                    )
                    referencias = []
                    erro_referencias = ""
                    try:
                        referencias = conferir_referencias(documento)
                    except ValueError as erro:
                        # Um limite da conferencia nao apaga a busca por assunto.
                        erro_referencias = str(erro)
                    revisao_atual = {
                        "resultados": resultados, "objetivo": objetivo.strip(),
                        "tema": tema, "posicao": posicao, "contexto": contexto.strip(),
                        "referencias": referencias, "erro_referencias": erro_referencias,
                        "origem_assunto": modo_assunto,
                        "assunto_sugerido": preparacao["sugestao"]["assunto"],
                        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "origem_documento": arquivo.name if arquivo else "Texto colado",
                        "caracteres_documento": len(documento),
                        "documento_sha256": sha256(documento.encode("utf-8")).hexdigest(),
                    }
                    try:
                        revisao_atual["relatorio_docx"] = gerar_relatorio_docx(revisao_atual)
                    except Exception:
                        # Uma falha de exportacao nao apaga os resultados da revisao.
                        revisao_atual["erro_relatorio"] = "Não foi possível gerar o relatório em Word. Os resultados continuam disponíveis abaixo. Confira o módulo de relatório e execute os testes no terminal."
                    st.session_state["revisao"] = revisao_atual
                    st.session_state["entrada_revisada"] = entrada
        except ValueError as erro:
            st.error(str(erro))
        except Exception:
            st.error("Não foi possível processar o material. Confira se o arquivo está legível e se a base está disponível. Se o problema persistir, consulte o terminal do VS Code.")

revisao = st.session_state.get("revisao")
if revisao:
    st.divider()
    st.subheader("Sua revisão")
    st.write("**Questão examinada:** " + revisao["objetivo"])
    st.caption("Assunto utilizado: " + revisao["tema"])
    with st.expander("Ver os dados desta revisão"):
        st.write("Definição do assunto: " + revisao.get("origem_assunto", "Não registrada") + ".")
        st.write("Posição da parte: " + revisao["posicao"])
        st.text(revisao.get("contexto") or "Sem fatos adicionais informados.")
        st.caption("Documento: " + revisao["origem_documento"])
    aba_fontes, aba_referencias, aba_relatorio = st.tabs([
        "Fontes relacionadas (" + str(len(revisao["resultados"])) + ")",
        "Referências citadas (" + str(len(revisao["referencias"])) + ")",
        "Baixar relatório",
    ])
    with aba_fontes:
        st.subheader("Jurisprudências relacionadas ao documento")
        st.info("Leia a fonte antes de utilizar: a similaridade mede proximidade textual, não chance de êxito ou aplicabilidade jurídica.")
        # Preserva a ordem do mecanismo: ela nao e somente a similaridade bruta.
        resultados = revisao["resultados"]
        if resultados and resultados[0].get("questoes_foco"):
            st.caption("Foco de seleção: " + ", ".join(resultados[0]["questoes_foco"]) + ". Origem: " + resultados[0]["origem_foco"] + ".")
        if resultados and all(r.get("relacao_pedido") == "Contraponto a conferir" for r in resultados):
            st.info("As fontes selecionadas trazem possíveis contrapontos ao pedido informado. Nenhuma foi classificada pelas regras atuais como direção textual compatível. Isso não significa que inexista fundamento para o pedido.")
        if not resultados:
            st.info("Nenhuma decisão da base passou pelos filtros de correspondência com o documento e pelo foco reconhecido. Isso não significa que inexista jurisprudência sobre o assunto. Confira a questão informada ou experimente um trecho mais específico.")
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
                pontuacao.caption("Similaridade textual")
                pontuacao.write(f"{resultado['aderencia_percentual']:.1f}%".replace(".", ","))
                st.write(f"Tema da decisão: {resultado['tema']}")
                st.write(resultado["tese_resumida"])
                st.caption("Síntese cadastrada, não gerada a partir do seu documento.")
                st.write("**Relação com o pedido:** " + resultado.get("relacao_pedido", "Sentido não classificado"))
                with st.expander("Pedido, contexto e alcance da fonte"):
                    st.write(resultado.get("explicacao_pedido", "Confira a relação entre a síntese e o pedido."))
                    if resultado.get("contexto_origem"):
                        st.write("**Contexto de origem:** " + resultado["contexto_origem"])
                    if resultado.get("limites_aplicacao"):
                        st.write("**Limites de aplicação:** " + resultado["limites_aplicacao"])
                st.markdown("**Trecho relacionado do seu documento**")
                st.text(resultado["trecho_relacionado"])
                with st.expander("Por que esta decisão foi selecionada?"):
                    st.write("Este trecho apresentou a maior similaridade com o cadastro desta fonte entre os trechos que passaram pelo filtro de relevância.")
                    st.write("Termos em comum após normalização: " + ", ".join(resultado["termos_relacionados"]) + ".")
                    st.write(resultado.get("explicacao_foco", "Comparação textual por trechos."))
                    st.caption("A ordem considera o foco, a direção textual reconhecida para pedidos de redução ou manutenção de multa e a afinidade textual com objetivo e fatos ancorados. A similaridade exibida continua sendo a do trecho original e pode ser menor em uma fonte mais bem posicionada.")
                    st.caption("Expressões como cláusula penal e multa contratual são aproximadas por regras explícitas. Termos em comum não demonstram, sozinhos, concordância entre os argumentos.")
                st.link_button("Abrir fonte oficial", resultado["fonte_url"])
        with st.expander("Como interpretar esta seleção"):
            st.write("O documento é separado em frases e janelas de até 100 palavras, com sobreposição nas unidades longas. Cada trecho é comparado ao tema, à síntese e às palavras-chave das fontes por TF-IDF e similaridade do cosseno. Não há bônus por data ou valor cadastrado de autoridade.")
            st.write(f"Para uma decisão ser elegível, ao menos um trecho do documento deve ter {MINIMO_TERMOS_COMUNS} termos relevantes em comum com a fonte e similaridade de pelo menos {LIMIAR_SIMILARIDADE:.0%}. Objetivo e fatos não criam sozinhos essa elegibilidade. O sistema retorna até três fontes e não completa a lista à força.")
            st.write("Depois do filtro do documento, regras de expressões identificam questões específicas e excluem fontes sobre questões diferentes quando o foco é reconhecido. A questão informada tem precedência sobre o documento para identificar o foco. O assunto selecionado é utilizado apenas se não houver foco mais específico. Regras incompletas podem deixar de reconhecer sinônimos ou excluir fontes úteis, por isso os resultados precisam de conferência.")
            st.write("A ordem prioriza a coincidência de questão e, para pedidos explícitos de redução ou manutenção de multa, a direção textual do cadastro. Em seguida, usa afinidade textual: 25% para o objetivo e 10% para fatos que compartilhem ao menos dois termos relevantes com o documento, quando preenchidos, e o restante para o melhor trecho do documento. São pesos experimentais, não probabilidades jurídicas. A porcentagem exibida não inclui esses pesos e não é uma nota de qualidade.")
            st.write("As classificações de direção compatível e contraponto não demonstram apoio ou contrariedade jurídica. Elas reconhecem expressões do pedido e da síntese, sem resolver os fatos ou os requisitos do precedente. A posição da parte não aumenta pontuação. Contexto de origem e limites cadastrados são exibidos para leitura, não como fatos automaticamente verificados no documento. A conferência de referências compara apenas identificadores: não valida transcrições ou conclusões atribuídas à decisão e não substitui a leitura da fonte.")

    with aba_referencias:
        mostrar_referencias(revisao["referencias"], revisao["erro_referencias"])
    with aba_relatorio:
        st.subheader("Relatório da revisão")
        if revisao.get("relatorio_docx"):
            st.download_button(
                "Baixar relatório em Word", data=revisao["relatorio_docx"],
                file_name="conferejus_revisao.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="baixar_relatorio_docx",
            )
            st.caption("O arquivo registra esta revisão, com objetivo, contexto, referências, fontes e links. Contém trechos do material enviado: revise antes de compartilhar. A conta Google não é incluída. Este não é o relatório acadêmico de uso de IA.")
        elif revisao.get("erro_relatorio"):
            st.warning(revisao["erro_relatorio"])

st.divider()
st.caption("ConfereJus · Protótipo acadêmico em desenvolvimento · Revisão profissional indispensável.")
st.markdown("[Política de Privacidade](?pagina=privacidade) · [Termos de Uso](?pagina=termos)")
