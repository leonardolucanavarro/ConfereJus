# ConfereJus

## Revisão assistida de fundamentos em disputas contratuais empresariais

O ConfereJus é um protótipo acadêmico que ajuda a conferir a relação entre trechos de um documento e decisões judiciais de uma base selecionada. O projeto tem foco em conflitos sobre descumprimento de contratos empresariais: boa-fé, comportamento das partes, cláusula penal, obrigações pecuniárias e questões processuais relacionadas às disputas contratuais.

O usuário envia um documento ou cola seu conteúdo. O sistema separa o material em trechos, compara cada trecho com os registros da base e apresenta as fontes selecionadas, o trecho relacionado, os termos que motivaram a seleção e o link oficial para conferência.

**Estado atual:** aplicativo executável localmente, com comparação por trechos e base inicial de cinco decisões do STJ. A hospedagem pública ainda não está concluída. Este README descreve as funções implementadas, não todas as funcionalidades pretendidas para o produto.

## Problema e público-alvo

Encontrar uma decisão sobre o mesmo assunto não demonstra, por si só, que ela se aplica aos fatos ou sustenta o pedido de uma peça. O projeto busca organizar essa etapa de conferência para estudantes e profissionais que trabalham com disputas contratuais empresariais.

O ConfereJus surgiu de uma proposta inicial de busca de jurisprudência. A experiência de pesquisa jurídica do grupo em uma atividade relacionada à CAMARB motivou a mudança para uma ferramenta orientada à revisão de documentos e fundamentos. O foco foi delimitado para evitar a promessa de atender indistintamente a todas as áreas do Direito.

## Proposta de diferenciação

O recorte do projeto combina:

- **Especialização de escopo:** disputas contratuais empresariais, em vez de pesquisa geral sobre todo o Direito.
- **Ponto de partida no documento:** os resultados são relacionados a trechos efetivamente enviados pelo usuário.
- **Seleção explicável:** cada resultado permite conferir o trecho relacionado e os termos compartilhados com a fonte.
- **Base rastreável:** os registros contêm identificação do processo, órgão julgador, relator, data, síntese e endereço oficial.
- **Filtro de correspondência mínima:** o aplicativo pode retornar menos de três fontes ou nenhuma, sem completar a lista artificialmente.

Essas características descrevem a proposta e a implementação do protótipo. Não constituem comprovação de exclusividade ou superioridade sobre Jusbrasil, Jus IA ou outras plataformas. Não foram realizados testes comparativos que autorizem essa conclusão.

## Funcionalidades disponíveis

- Envio de PDF com texto extraível, DOCX ou TXT.
- Inserção direta de texto na interface.
- Extração de parágrafos e tabelas de arquivos DOCX.
- Registro da questão a examinar, do assunto, da posição da parte e de fatos adicionais.
- Segmentação do documento e comparação textual por trecho.
- Normalização de maiúsculas, acentos e algumas expressões explicitamente cadastradas, como “cláusula penal” e “multa contratual”.
- Ordenação de até três decisões que atendam ao filtro mínimo.
- Exibição da similaridade textual, síntese cadastrada, trecho relacionado, termos compartilhados e link oficial.
- Mensagem específica quando nenhum registro da base atende aos critérios mínimos.
- Remoção dos resultados anteriores quando as entradas são alteradas, exigindo nova comparação.

**Os campos de contexto ainda não alteram o ranking.** Eles organizam a revisão e sua apresentação. Nesta versão, somente os trechos do documento determinam a correspondência automática. O preenchimento de contexto jurídico não deve gerar resultados para um documento sem relação com o assunto.

## Como usar

1. Abra o aplicativo e escolha **Enviar arquivo** ou **Colar texto**.
2. Envie o material ou cole o trecho que deseja examinar.
3. Preencha **Qual argumento ou pedido você quer examinar?**. Esse campo é obrigatório na interface atual.
4. Selecione o assunto predominante e a posição da parte representada. Informe fatos adicionais se forem úteis à sua conferência.
5. Clique em **Comparar fundamentos**.
6. Examine as fontes exibidas, o trecho relacionado e a seção **Por que esta decisão foi selecionada?**.
7. Abra a fonte oficial e confira fatos, fundamento, alcance e pertinência da decisão ao seu caso.

Alterar os campos não executa automaticamente uma nova análise: clique novamente no botão.

### Exemplo de teste

Texto do documento:

> O credor deve evitar o agravamento do próprio prejuízo, adotando medidas razoáveis para mitigar a perda conforme a boa-fé objetiva.

Questão informada:

> Conferir os fundamentos sobre o dever de mitigar o prejuízo.

Selecione **Boa-fé e comportamento das partes**. Com a base inicial revisada, espera-se encontrar o REsp 758.518/PR como uma fonte relacionada. A correspondência neste exemplo não comprova desempenho geral nem determina a solução jurídica de um caso concreto.

Para conferir a ausência de resultados, utilize um texto fora do tema, como “O telescópio fotografou estrelas e galáxias distantes”. A base não deve devolver decisões apenas porque os campos de contexto contêm termos jurídicos.

## Instalação e execução local

### Pré-requisitos

- Git, para obter o repositório.
- Gerenciador de projetos Python **uv** instalado e acessível no terminal.
- Python compatível com o projeto, que declara **Python 3.12 ou superior**. Respeite também a versão definida em `.python-version`.
- Internet para baixar o código, instalar dependências e abrir as fontes oficiais.

Não é necessário contratar uma API de IA ou configurar uma chave para executar a comparação atual.

### Primeira execução

Execute um comando por vez no terminal:

```powershell
git clone https://github.com/leonardolucanavarro/ConfereJus.git
cd ConfereJus
uv sync --locked
uv run streamlit run app.py
```

Se você já tem o repositório no computador, não precisa cloná-lo novamente: abra o terminal na pasta `ConfereJus` e execute os dois últimos comandos.

O Streamlit informa o endereço em **Local URL**, normalmente `http://localhost:8501`. Se a porta estiver ocupada, poderá usar outra, como `8502`. Abra o endereço efetivamente indicado no terminal.

Mantenha o processo em execução durante o uso. Para encerrá-lo, clique no terminal e pressione **Ctrl + C**. Para abrir novamente, execute `uv run streamlit run app.py` na pasta do projeto.

**O endereço localhost só representa a execução local.** Ele não é o link público a ser compartilhado. O endereço público será incluído aqui quando a hospedagem estiver concluída e testada.

### Problemas comuns

| Situação | Como conferir |
| --- | --- |
| `uv` não reconhecido | Verifique a instalação e a disponibilidade do uv no terminal. Se acabou de instalá-lo, reabra o terminal. |
| `app.py` não encontrado | Confirme que o terminal está na pasta `ConfereJus`, não na pasta Downloads ou em outro projeto. |
| Base não encontrada | Confira a existência de `data/jurisprudencias.csv` e a estrutura de pastas do repositório. |
| Falha de importação | Execute `uv sync --locked` e utilize `uv run streamlit run app.py`, não uma instalação Python de outro projeto. |
| PDF sem texto extraível | Utilize um PDF textual ou uma transcrição. A leitura de imagens por OCR não está implementada. |
| Nenhum resultado | O acervo pode não conter correspondência suficiente. Isso não demonstra inexistência de jurisprudência sobre o assunto. |
| Erro ao abrir fonte oficial | Confira a conexão e a disponibilidade do STJ. Os links dependem de serviço externo. |

## Funcionamento da análise

1. **Extração:** o sistema obtém o texto do arquivo ou utiliza o conteúdo colado.
2. **Segmentação:** separa frases e parágrafos. Unidades longas são divididas em janelas de até 100 palavras, com sobreposição de 20 palavras.
3. **Normalização:** reduz variações de escrita e aplica uma lista local de aproximações terminológicas. Palavras frequentes são desconsideradas na comparação. Negações, como “não” e “sem”, são preservadas, mas isso não equivale à compreensão de seu efeito jurídico.
4. **Representação:** TF-IDF transforma os textos em vetores de termos e combinações de até duas palavras. O vocabulário é ajustado à base cadastrada.
5. **Comparação:** a similaridade do cosseno mede a proximidade entre cada trecho e o tema, a síntese e as palavras-chave de cada fonte.
6. **Filtro:** ao menos um trecho deve compartilhar dois termos relevantes com a fonte e alcançar similaridade mínima de 0,12. Os parâmetros são experimentais e precisam de avaliação com amostra maior.
7. **Seleção:** para cada decisão, utiliza-se o melhor trecho elegível. As decisões são ordenadas por essa similaridade e o retorno é limitado a três fontes.

Datas e valores cadastrados de autoridade **não aumentam a pontuação no mecanismo atual**. A coluna legada `grau_autoridade` permanece no CSV por compatibilidade, sem uso na seleção.

A porcentagem apresentada **não mede probabilidade de êxito, qualidade do documento, força jurídica, aplicabilidade do precedente ou veracidade de uma citação**. Textos com conclusões opostas podem compartilhar vocabulário e receber correspondência elevada. O sistema não conclui automaticamente que uma fonte apoia ou contraria o argumento.

## Base de jurisprudências

A base ativa contém cinco registros extraídos de informações oficiais do STJ:

| ID | Processo | Tema cadastrado e enquadramento |
| --- | --- | --- |
| J001 | REsp 758.518/PR | Boa-fé e mitigação do prejuízo. Fundamento contratual geral, originado de disputa imobiliária. |
| J002 | REsp 1.202.514/RS | Supressio e confiança legítima. Contexto original de serviços jurídicos e cobrança retroativa de correção monetária. |
| J003 | REsp 2.000.288/MG | Revisão ou rescisão e reconvenção. Apoio processual judicial, não regra automaticamente transportável à arbitragem. |
| J005 | REsp 1.867.551/RJ | Cláusula penal compensatória e obrigação pecuniária solidária em contexto empresarial. |
| J006 | REsp 2.013.493/SP | Interpretação restritiva da cláusula penal em contratos empresariais paritários. |

O registro J004, relativo a atraso de imóvel e dano moral, foi retirado da base ativa na revisão de escopo. Os IDs remanescentes não foram renumerados, preservando a rastreabilidade das alterações no Git.

Cada registro inclui identificação, síntese, palavras-chave e endereço oficial. As colunas `contexto_origem` e `limites_aplicacao` registram cautelas de uso. **Essas duas colunas ainda não aparecem na interface nem participam automaticamente do ranking.**

As sínteses são textos previamente cadastrados, não conclusões produzidas a partir do documento do usuário. Os links podem levar a informativos oficiais ou PDFs que contêm a nota correspondente, e não necessariamente ao inteiro teor do acórdão. O aplicativo não atualiza o acervo automaticamente nem garante que um entendimento permaneça atual.

## Limites de arquivos e processamento

- Arquivos de até **20 MB**, embora o componente de envio possa mostrar um limite visual superior.
- PDFs de até **200 páginas**.
- Até **120 mil caracteres** de entrada e até **400 trechos** processáveis por análise.
- Sem OCR para imagens ou PDFs escaneados.
- Extração de DOCX restrita a parágrafos e tabelas lidos pela biblioteca utilizada. Outros elementos, como caixas de texto, podem não ser recuperados.

Os limites protegem o processamento do protótipo. Um arquivo aceito pelo componente de upload ainda pode ser recusado ao iniciar a análise.

## Privacidade e uso responsável

A comparação atual não depende de uma API externa de IA e não inclui gravação deliberada dos documentos em banco de dados ou na base de jurisprudências. O aplicativo mantém entradas e resultados no estado da sessão durante o uso. Isso não constitui garantia de eliminação imediata de todos os dados ou uma auditoria de segurança.

Após a publicação, o processamento ocorrerá na infraestrutura da hospedagem. Antes de receber material confidencial, será necessário verificar configurações, políticas, retenção e controles aplicáveis. **Nesta fase, utilize materiais fictícios, públicos ou devidamente anonimizados.**

Não envie documentos de clientes, dados pessoais ou arquivos confidenciais ao repositório público. Backups locais e a pasta Downloads não fazem parte dos arquivos que devem ser publicados. Nunca inclua senhas, tokens ou chaves no GitHub.

O resultado é apoio à conferência e não substitui a leitura das fontes nem a avaliação de profissional habilitado.

## Tecnologias e estrutura

- **Python:** linguagem do projeto.
- **Streamlit:** interface web.
- **pandas:** leitura e organização da base CSV.
- **scikit-learn:** TF-IDF e similaridade do cosseno.
- **pypdf:** extração de texto de PDF.
- **python-docx:** leitura de DOCX.
- **uv:** ambiente, instalação e controle das dependências.

As dependências declaradas em `pyproject.toml` incluem pandas, pypdf, python-docx, scikit-learn e Streamlit. O arquivo `uv.lock` registra a resolução das dependências para reprodução do ambiente.

| Arquivo ou pasta | Função |
| --- | --- |
| `app.py` | Interface, entrada de documentos e apresentação dos resultados. |
| `src/conferejus/analise.py` | Extração, carregamento da base, segmentação e comparação. |
| `data/jurisprudencias.csv` | Acervo ativo de jurisprudências. |
| `logo.png` | Identidade visual utilizada pela interface. |
| `pyproject.toml` | Metadados, dependências e configuração do projeto. |
| `uv.lock` | Versões resolvidas das dependências. |
| `.python-version` | Referência da versão Python do ambiente. |
| `README.md` | Apresentação e instruções de uso. |

## Evoluções planejadas — ainda não disponíveis

- Ampliação e revisão do acervo especializado, com testes de pertinência.
- Uso efetivo do contexto e de regras específicas de aplicação na análise, sujeito a implementação e validação.
- Conferência limitada de referências citadas contra o cadastro. Referência não encontrada deverá ser tratada como não verificada, não como falsa.
- Relatório de análise para download.
- Entrada de áudio com transcrição editável e confirmação do usuário.
- Cadastro, login e preferências individuais, sem pressupor armazenamento de documentos.
- Hospedagem pública e testes em outros dispositivos.
- Documentação específica do uso de IA e definição da licença de distribuição.

Doutrinas e eventuais parcerias editoriais são possibilidades futuras. Não integram a base ou as funcionalidades atuais.

## Desenvolvimento e autoria

Responsável cadastrado nos metadados do projeto: **Leonardo Lucarelli Navarro**. O histórico de commits registra as alterações versionadas e seus respectivos autores.

O desenvolvimento utiliza assistência de IA para apoio à programação e documentação. Isso é diferente de utilizar uma API generativa durante a análise dos documentos: o mecanismo atual executa comparação textual e regras locais. O relato detalhado dessa assistência será documentado em `relatorio-uso-ia.md`.

O repositório é público para acompanhamento e avaliação acadêmica. A licença de distribuição ainda será definida em arquivo próprio. A visibilidade pública do código não deve ser confundida com uma licença já concedida.
