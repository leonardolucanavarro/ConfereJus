# ConfereJus

## Revisão assistida de fundamentos em disputas contratuais empresariais

O ConfereJus é um protótipo acadêmico que ajuda a conferir a relação entre trechos de um documento e decisões judiciais de uma base selecionada. O projeto tem foco em conflitos sobre descumprimento de contratos empresariais: boa-fé, comportamento das partes, cláusula penal, obrigações pecuniárias, revisão, extinção contratual e questões processuais relacionadas.

O usuário envia um documento ou cola seu conteúdo. O sistema separa o material em trechos, compara cada trecho com os registros da base e apresenta as fontes selecionadas, o trecho relacionado, os termos que motivaram a seleção e o link oficial para conferência.

**Estado atual — 11/11/2026:** aplicativo executável localmente, base de **20 decisões do STJ**, login opcional com Google testado no ambiente local e **32 testes automatizados aprovados**. A hospedagem pública ainda não está concluída. As preferências vinculadas à conta e a entrada por áudio ainda não estão disponíveis.

Este README descreve as funções implementadas e separa as evoluções planejadas. Os testes aprovados verificam os comportamentos descritos na seção de testes, não a correção jurídica de todas as respostas.

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
- Login opcional com Google, saudação com o nome do usuário e saída da conta, testados localmente.
- Arquivo de testes automatizados para o mecanismo, a extração e a estrutura da base.

**Os campos de contexto ainda não alteram o ranking.** Eles organizam a revisão e sua apresentação. Nesta versão, somente os trechos do documento determinam a correspondência automática. O preenchimento de contexto jurídico não deve gerar resultados para um documento sem relação com o assunto.

O login não é condição para utilizar a análise na interface configurada. Nesta etapa, autenticar-se não cria histórico de revisões, não salva documentos e não implementa preferências persistentes.

## Como usar

1. Abra o aplicativo. Você pode utilizar a análise sem entrar na conta ou escolher **Entrar com Google**, quando o login estiver configurado.
2. Escolha **Enviar arquivo** ou **Colar texto** e insira o material que deseja examinar.
3. Preencha **Qual argumento ou pedido você quer examinar?** Esse campo é obrigatório na interface atual.
4. Selecione o assunto predominante e a posição da parte representada. Informe fatos adicionais se forem úteis à sua conferência.
5. Clique em **Comparar fundamentos**.
6. Examine as fontes exibidas, o trecho relacionado e a seção **Por que esta decisão foi selecionada?**
7. Abra a fonte oficial e confira fatos, fundamento, alcance e pertinência da decisão ao seu caso.

Alterar os campos não executa automaticamente uma nova análise: clique novamente no botão. Para sair do perfil autenticado, utilize **Sair da conta**. Isso encerra o login no aplicativo, não necessariamente a sessão da conta Google no navegador.

### Exemplo de teste

Texto do documento:

> O credor deve evitar o agravamento do próprio prejuízo, adotando medidas razoáveis para mitigar a perda conforme a boa-fé objetiva.

Questão informada:

> Conferir os fundamentos sobre o dever de mitigar o prejuízo.

Selecione **Boa-fé e comportamento das partes**. Com a base atual, espera-se encontrar o REsp 758.518/PR como uma fonte relacionada. A correspondência neste exemplo não comprova desempenho geral nem determina a solução jurídica de um caso concreto.

Para conferir a ausência de resultados, utilize um texto fora do tema, como “O telescópio fotografou estrelas e galáxias distantes”. A base não deve devolver decisões apenas porque os campos de contexto contêm termos jurídicos.

## Instalação e execução local

### Pré-requisitos

- Git, para obter o repositório.
- Gerenciador de projetos Python **uv** instalado e acessível no terminal.
- Python compatível com o projeto, que declara **Python 3.12 ou superior**. Respeite também a versão definida em `.python-version`.
- Internet para baixar o código, instalar dependências, utilizar o login Google e abrir as fontes oficiais.

A comparação atual não utiliza uma API externa de IA nem exige uma chave de IA paga. As credenciais Google descritas abaixo têm outra finalidade: configurar a autenticação.

### Primeira execução

Execute um comando por vez no terminal:

```powershell
git clone https://github.com/leonardolucanavarro/ConfereJus.git
cd ConfereJus
uv sync --locked
uv run streamlit run app.py --server.port 8501
```

Se você já tem o repositório no computador, não precisa cloná-lo novamente: abra o terminal na pasta `ConfereJus` e execute os dois últimos comandos.

Abra o endereço informado em **Local URL**, normalmente `http://localhost:8501`. A porta 8501 é explicitamente utilizada para corresponder à configuração local de login. Se estiver ocupada, encerre a instância anterior ou configure outra porta, ajustando também os endereços de retorno do login.

Mantenha o processo em execução durante o uso. Para encerrá-lo, clique no terminal e pressione **Ctrl+C**. Para abrir novamente, execute o comando do Streamlit na pasta do projeto.

**O endereço localhost representa apenas a execução local.** Ele não é o link público a ser compartilhado. O endereço público será incluído aqui quando a hospedagem estiver concluída e testada.

### Configuração local do login com Google

Esta configuração é destinada a quem instala ou hospeda o aplicativo. O visitante do futuro site público não precisará criar um projeto Google Cloud ou instalar programas para usar a interface.

O fluxo utiliza a autenticação do Streamlit com Google como provedor de identidade. O suporte está declarado nas dependências por meio de `streamlit[auth]`.

1. Crie ou selecione um projeto no Google Cloud e configure o aplicativo no **Google Auth Platform**.
2. Para permitir contas externas à organização, configure o público como **Externo**. Enquanto estiver em testes, confira os usuários autorizados nas configurações do provedor.
3. Crie um cliente OAuth do tipo **Aplicativo da Web**.
4. Para o fluxo local atual, deixe as origens JavaScript vazias e cadastre este URI de redirecionamento: `http://localhost:8501/oauth2callback`.
5. Na raiz do repositório, crie a pasta `.streamlit` e, dentro dela, o arquivo `secrets.toml`.
6. Confira que `.streamlit/secrets.toml` está no `.gitignore`. Não versione esse arquivo nem arquivos JSON com credenciais.
7. Gere um segredo aleatório para assinatura dos cookies, executando localmente:

```powershell
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Preencha o arquivo privado com esta estrutura, substituindo os marcadores pelos valores correspondentes e mantendo as aspas:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "SUBSTITUA_POR_UM_SEGREDO_ALEATORIO_GERADO_LOCALMENTE"
client_id = "SUBSTITUA_PELO_ID_DO_CLIENTE_GOOGLE"
client_secret = "SUBSTITUA_PELO_SEGREDO_DO_CLIENTE_GOOGLE"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Os valores acima são marcadores, não credenciais utilizáveis. Não compartilhe o arquivo preenchido, o segredo do cliente ou o segredo dos cookies. Se houver exposição, substitua a credencial e revogue a anterior.

No ambiente configurado, foram testados o login, a saudação, a saída da conta e a permanência do formulário de análise sem autenticação. **No teste local sem credenciais de autenticação, o formulário e a comparação funcionaram normalmente, com o botão de login oculto. Após restaurar a configuração, o login com Google voltou a funcionar.**

Na publicação, será necessário cadastrar o URI do site público com o caminho `/oauth2callback`, guardar as credenciais nas configurações privadas da hospedagem e conferir a liberação do público externo. Configurar o login local não publica o site.

### Problemas comuns

| Situação | Como conferir |
| --- | --- |
| `uv` não reconhecido | Verifique a instalação e a disponibilidade do uv no terminal. Se acabou de instalá-lo, reabra o terminal. |
| `app.py` não encontrado | Confirme que o terminal está na pasta `ConfereJus`, não na pasta Downloads ou em outro projeto. |
| Base não encontrada | Confira a existência de `data/jurisprudencias.csv` e a estrutura de pastas do repositório. |
| Falha de importação | Execute `uv sync --locked` e utilize `uv run` para executar o projeto no ambiente correto. |
| Porta 8501 ocupada | Confira se outra instância do Streamlit continua em execução. Não altere a porta sem ajustar a configuração do login. |
| Erro de redirecionamento no login | Confira se o endereço cadastrado no Google coincide com `redirect_uri`, incluindo protocolo, porta e `/oauth2callback`. |
| Conta recusada no login | Confira o público e os usuários de teste autorizados no Google Auth Platform. |
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

A base ativa contém **20 decisões**, com informações conferidas em fontes oficiais do STJ. O acervo reúne casos empresariais e fundamentos contratuais gerais, além de fontes de apoio processual. Essa diferença está registrada no contexto e nos limites de cada cadastro.

| ID | Processo | Tema cadastrado e enquadramento |
| --- | --- | --- |
| J001 | REsp 758.518/PR | Boa-fé e mitigação do prejuízo. Fundamento contratual geral, originado de disputa imobiliária. |
| J002 | REsp 1.202.514/RS | Supressio e confiança legítima. Serviços jurídicos e cobrança retroativa de correção monetária. |
| J003 | REsp 2.000.288/MG | Revisão ou rescisão e reconvenção. Apoio processual judicial. |
| J005 | REsp 1.867.551/RJ | Cláusula penal compensatória e obrigação pecuniária solidária em contexto empresarial. |
| J006 | REsp 2.013.493/SP | Interpretação restritiva da cláusula penal em contratos empresariais paritários. |
| J007 | REsp 1.803.803/RJ | Função coercitiva da cláusula penal em patrocínio empresarial. |
| J008 | REsp 1.447.247/SP | Controle de cláusula penal manifestamente excessiva e redução de ofício. |
| J009 | REsp 1.581.505/SC | Adimplemento substancial e relevância do descumprimento. Origem em disputa imobiliária. |
| J010 | REsp 945.166/GO | Imprevisão e riscos ordinários na venda futura de soja. |
| J011 | AgInt no AREsp 1.738.129/AM | Lucros cessantes baseados em projeções de atividade empresarial não iniciada. |
| J012 | REsp 1.555.202/SP | Resilição unilateral e investimentos exigidos da contratada. |
| J013 | REsp 981.750/MG | Exceção do contrato não cumprido, ordem das prestações e proporcionalidade. |
| J014 | REsp 2.088.764/SP | Tratativas de distrato e ausência de supressio em contrato de investimento. |
| J015 | REsp 2.109.100/PR | Contrato, aditivos e e-mails como prova para ação monitória. Apoio processual judicial. |
| J016 | REsp 1.699.184/SP | Resilição de arrendamento mercantil por contratante em mora. |
| J017 | REsp 1.984.277/DF | Revisão de aluguel de coworking diante dos efeitos concretos da pandemia. |
| J018 | REsp 2.032.878/GO | Revisão de aluguel em shopping e necessidade de comprovação do desequilíbrio. |
| J019 | REsp 1.989.291/SP | Limitação contratual de responsabilidade entre empresas. |
| J020 | REsp 1.831.947/PR | Representação comercial e antecipação da indenização por rescisão. |
| J021 | REsp 1.335.617/SP | Multa compensatória e duplicidade de reparação por perdas e danos. |

O registro J004, relativo a atraso de imóvel e dano moral, foi retirado da base ativa na revisão de escopo. Os IDs remanescentes não foram renumerados, preservando a rastreabilidade das alterações no Git. Por isso, o último ID é J021, mas o total de decisões é 20.

Cada registro inclui identificação, síntese, palavras-chave e endereço oficial. As colunas `contexto_origem` e `limites_aplicacao` registram cautelas de uso. **Essas duas colunas ainda não aparecem na interface nem participam automaticamente do ranking.** As fontes e os dados completos de cada registro estão em `data/jurisprudencias.csv`.

As sínteses são textos previamente cadastrados, não conclusões produzidas a partir do documento do usuário. Os links podem levar a informativos oficiais, PDFs com várias notas, pesquisa de jurisprudência ou inteiro teor de acórdãos. Nos documentos coletivos, utilize o número do processo para localizar a nota correspondente. O aplicativo não atualiza o acervo automaticamente nem garante que um entendimento permaneça atual.

## Testes automatizados

Na raiz do repositório, após instalar as dependências, execute:

```powershell
uv run python test_conferejus.py
```

A execução local de **11/11/2026** terminou com:

```text
Ran 32 tests
OK
```

O tempo de execução pode variar. A suíte usa `unittest`, incluído no Python, e as bibliotecas já utilizadas pelo projeto. Não consulta a internet, não lê `secrets.toml` e não altera a base.

| Grupo | Quantidade | O que verifica |
| --- | --- | --- |
| Mecanismo isolado | 18 | Recuperação com acervo fictício, ausência de correspondência, separação de contexto, trecho preservado, filtros, ordenação, limites, normalização e ausência de bônus por data ou autoridade. |
| Arquivos e validação | 9 | TXT UTF-8 e Latin-1, DOCX com tabela, PDF vazio, formato não aceito, limites de tamanho e texto, coluna ausente e identificador duplicado em bases de teste. |
| Base real | 5 | Alinhamento e preenchimento de colunas, pelo menos 20 registros e IDs esperados, ausência de processo duplicado, datas válidas, domínios oficiais, recuperação de exemplos sintéticos e texto fora do escopo. |

A verificação dos domínios não abre os links nem comprova sua disponibilidade ou o conteúdo da página. Os exemplos de recuperação são sintéticos e próximos do vocabulário cadastrado. Preservar uma negação também não significa interpretar sua consequência jurídica.

**A aprovação da suíte não certifica a autenticidade ou atualidade jurídica das fontes, não mede precisão geral e não substitui testes manuais.** Permanecem pendentes avaliações mais amplas com documentos variados, conferência dos links no navegador, PDF textual, documentos escaneados e inválidos, interface, autenticação, diferentes dispositivos e hospedagem pública.

Se houver `FAIL` ou `ERROR`, confira o nome do teste e a mensagem antes de modificar o mecanismo ou a expectativa. Não remova um teste apenas para obter `OK`.

## Limites de arquivos e processamento

- Arquivos de até **20 MB**, embora o componente de envio possa mostrar um limite visual superior.
- PDFs de até **200 páginas**.
- Até **120 mil caracteres** de entrada e até **400 trechos** processáveis por análise.
- Sem OCR para imagens ou PDFs escaneados.
- Extração de DOCX restrita a parágrafos e tabelas lidos pela biblioteca utilizada. Outros elementos, como caixas de texto, podem não ser recuperados.

Os limites protegem o processamento do protótipo. Um arquivo aceito pelo componente de upload ainda pode ser recusado ao iniciar a análise.

## Privacidade e uso responsável

A comparação atual não depende de uma API externa de IA e não inclui gravação deliberada dos documentos em banco de dados ou na base de jurisprudências. O aplicativo mantém entradas e resultados no estado da sessão durante o uso. Isso não constitui garantia de eliminação imediata de todos os dados ou uma auditoria de segurança.

O login envolve comunicação com o Google para autenticação e uso das informações de identidade disponibilizadas, como o nome para a saudação. Não é um cadastro com senha própria do ConfereJus. O login implementado não envia deliberadamente o conteúdo do documento ao Google como parte da análise, nem salva documentos em um perfil persistente. A autenticação utiliza cookies e deve ser considerada na revisão de privacidade antes da publicação.

Após a publicação, o processamento ocorrerá na infraestrutura da hospedagem. Antes de receber material confidencial, será necessário verificar configurações, políticas, retenção e controles aplicáveis. **Nesta fase, utilize materiais fictícios, públicos ou devidamente anonimizados.**

Não envie documentos de clientes, dados pessoais ou arquivos confidenciais ao repositório público. Backups locais e a pasta Downloads não fazem parte dos arquivos que devem ser publicados. Nunca inclua senhas, tokens, chaves ou o arquivo `.streamlit/secrets.toml` no GitHub. O `.gitignore` não remove credenciais que já tenham sido versionadas anteriormente.

O resultado é apoio à conferência e não substitui a leitura das fontes nem a avaliação de profissional habilitado.

## Tecnologias e estrutura

- **Python:** linguagem do projeto.
- **Streamlit:** interface web e integração de autenticação.
- **Google Auth Platform:** provedor de identidade para o login opcional.
- **pandas:** leitura e organização da base CSV.
- **scikit-learn:** TF-IDF e similaridade do cosseno.
- **pypdf:** extração de texto de PDF.
- **python-docx:** leitura de DOCX.
- **unittest:** execução dos testes automatizados.
- **uv:** ambiente, instalação e controle das dependências.

O arquivo `pyproject.toml` declara as dependências. O arquivo `uv.lock` registra sua resolução para reprodução do ambiente, incluindo as dependências de autenticação.

| Arquivo ou pasta | Função |
| --- | --- |
| `app.py` | Interface, login opcional, entrada de documentos e apresentação dos resultados. |
| `src/conferejus/analise.py` | Extração, carregamento da base, segmentação e comparação. |
| `data/jurisprudencias.csv` | Acervo ativo de jurisprudências. |
| `test_conferejus.py` | Suíte de 32 testes automatizados. |
| `logo.png` | Identidade visual utilizada pela interface. |
| `pyproject.toml` | Metadados, dependências e configuração do projeto. |
| `uv.lock` | Versões resolvidas das dependências. |
| `.python-version` | Referência da versão Python do ambiente. |
| `.gitignore` | Regras para não incluir arquivos locais e credenciais no versionamento. |
| `.streamlit/secrets.toml` | Configuração privada local da autenticação. Não integra o repositório. |
| `README.md` | Apresentação e instruções de uso. |

## Evoluções planejadas — ainda não disponíveis

- Revisão contínua e eventual ampliação do acervo especializado, com avaliação de pertinência em amostra mais diversa.
- Uso efetivo do contexto e de regras específicas de aplicação na análise, sujeito a implementação e validação.
- Conferência limitada de referências citadas contra o cadastro. Referência não encontrada deverá ser tratada como não verificada, não como falsa.
- Relatório de análise para download.
- Entrada de áudio com transcrição editável e confirmação do usuário, com teste de viabilidade na hospedagem.
- Preferências individuais vinculadas à conta e armazenamento adequado, sem pressupor armazenamento de documentos.
- Hospedagem pública, configuração do login no endereço público e testes com outras contas e dispositivos.
- Documentação específica do uso de IA e definição da licença de distribuição.
- Revisão final das escritas do site e do GitHub, acessibilidade, contraste e apresentação visual.

Doutrinas e eventuais parcerias editoriais são possibilidades futuras. Não integram a base ou as funcionalidades atuais.

## Desenvolvimento e autoria

Responsável cadastrado nos metadados do projeto: **Leonardo Lucarelli Navarro**. O histórico de commits registra as alterações versionadas e seus respectivos autores.

O desenvolvimento utiliza assistência de IA para apoio à programação, aos testes e à documentação. Isso é diferente de utilizar uma API generativa durante a análise dos documentos: o mecanismo atual executa comparação textual e regras locais. O relato detalhado dessa assistência será documentado em `relatorio-uso-ia.md`.

O repositório é público para acompanhamento e avaliação acadêmica. A licença de distribuição ainda será definida em arquivo próprio. A visibilidade pública do código não deve ser confundida com uma licença já concedida.
