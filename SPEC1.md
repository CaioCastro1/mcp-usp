# usp-mcp — documento de partida

> **Isto não é um design.** É o estado do conhecimento em 27/08/2026 mais um protocolo de
> descoberta. O objetivo do projeto é responder perguntas reais sobre a vida acadêmica na
> USP; a API é meio, não ponto de partida. Nenhuma decisão de superfície de ferramentas
> deve ser tomada antes da Fase 1.

## 0. Como ler este documento

Três status, com pesos diferentes:

- **Fatos verificados** — foram observados empiricamente. Pode construir em cima.
- **Invariantes** — não são objeto de descoberta. São restrições de segurança e de
  privacidade; valem mesmo que o dado sugira o contrário.
- **Abertas** — fecham com dado coletado, não com opinião nem com o que a API oferece.

Se durante a implementação você (Claude Code ou humano) sentir vontade de fechar uma
questão aberta por conveniência, registre a decisão e o motivo neste arquivo em vez de
resolver em silêncio.

---

## 1. Fatos verificados (27/08/2026)

### 1.1 Restrição de ambiente que determina onde se trabalha

**A restrição depende do ambiente, e a diferença importa** — corrigido em 31/08/2026,
ver §9.

`uspdigital.usp.br` e `edisciplinas.usp.br` **não são alcançáveis** do sandbox em nuvem do
Cowork nem da VM local que ele expõe — ambos saem por um proxy de egress com allowlist que
só libera um conjunto pequeno de domínios (registries de pacote, `api.anthropic.com`).
Sintoma: `curl` devolve `000`, ou `403` no túnel CONNECT; DNS falha na VM local.

**Mas do Claude Code rodando na máquina do dono, são alcançáveis.** Medido em 31/08/2026:
DNS resolve (`edisciplinas.usp.br` → `200.144.235.136`), TCP/443 conecta, HTTPS numa página
pública devolve `200`, e o web service devolve `invalidtoken` para token vazio. Nenhuma
variável de proxy no ambiente.

A consequência abaixo continua valendo, mas **por outro motivo**: não é a rede que separa
uma sessão de agente do teste real, é a credencial. O token é pessoal, cada chamada fica no
log da conta, e por isso a camada `live` fica atrás de `USP_MCP_LIVE=1` — decisão de quem
é dono da conta, não limitação de infraestrutura.

Consequência: **todo teste contra a USP roda no terminal do Caio.** O desenvolvimento
assistido tem que acontecer com acesso à rede dele, ou contra fixtures.

### 1.2 RUCard — cardápio dos bandejões

| Item | Valor |
|---|---|
| Base | `https://uspdigital.usp.br/rucard/servicos` |
| Método | **POST** form-urlencoded (`GET` → HTTP 500) |
| Auth | campo `hash` no body |
| Chave | `596df9effde6f877717b4e81fdb2ca9f` — embutida no app oficial, compartilhada, não por usuário |
| Erro | HTTP 500 com HTML do Tomcat, não JSON |

- `POST /menu/{id}` → objeto `{message, meals, observation}`; `meals` tem os 7 dias da
  semana corrente (seg→dom), cada dia com `date` (`DD/MM/AAAA`), `lunch` e `dinner`, e cada
  refeição com `menu` (texto livre, itens separados por `\n`, às vezes ` - `, às vezes com
  HTML) e `calories` (string). Dia fechado: `calories = "0"` e `menu` = `"Fechado"` **ou**
  `"FECHADO"` — a grafia varia por RU (6 usa capitalizado, 7/8/9 usam caixa alta), então a
  comparação tem que ser case-insensitive. Não há café da manhã: só `lunch` e `dinner`,
  mesmo nos RUs cujo `workinghours` publica `breakfast`.
- `POST /restaurants` → 10 campi, 18 RUs, com fichas (endereço, horários, preços, caixas).
  **Todos os valores são strings**, inclusive ids, coordenadas, preços com vírgula decimal e
  booleanos. Vazio é `""`. `/menu` **não** segue a mesma regra — lá `message.error` é
  booleano de verdade. `hasCashier` vem `"false"` nos 18 RUs, inclusive nos 14 que têm
  `cashiers` preenchido: campo sempre errado, e string truthy em JS. Usar o tamanho de
  `cashiers`. É a resposta mais **estática** do projeto: 27.661 B **byte-idênticos** em
  27/08 e 31/08/2026 — e a mais cara (~6.900 tokens), o que a torna tabela de apoio e
  nunca resposta.
- Não há parâmetro de data. Só semana corrente. Histórico exige persistir por conta.
  **A semana vira na segunda, ou antes dela**: em 31/08/2026 (segunda), às 19:22, a
  resposta já era 31/08→06/09, enquanto a captura de 27/08 trazia 24/08→30/08. O
  instante exato da virada continua sem medida, e é por isso que o cache do cliente não
  confia só em TTL — ver §9, 31/08/2026 (Fase 2 do RUCard).
- Ids de interesse do Caio: **6 CENTRAL, 9 QUÍMICAS, 8 FÍSICA, 7 PUSP-CB**. Os outros 14
  RUs existem mas estão fora de escopo por decisão dele. O 7 não serve jantar (não há
  horário publicado, e os 7 jantares vêm fechados) — distinguir "fechado hoje" de "nunca
  serve essa refeição" exige cruzar `/menu` com `workinghours`.
- **O 9 (QUÍMICAS) é o único dos quatro que abre no fim de semana**: `workinghours`
  publica sábado (almoço 11:15–14:15 e jantar 17:30–19:00) e domingo (só almoço), e o
  cardápio das duas semanas capturadas concorda item a item. Nos 6, 7 e 8 sábado e
  domingo vêm vazios nas três refeições. Medido em 31/08/2026; a nota da Fase 1 dizia
  "jantar em 6, 8 e 9" sem mencionar fim de semana, o que deixava o 9 parecer igual aos
  outros.
- **`breakfast` aparece em três RUs, não dois**: 6 e 7 em dia de semana (07:00–08:30) e
  **9 só no fim de semana** (sábado 07:30–09:00, domingo 08:30–09:30). O 8 não publica
  café em dia nenhum. O `/menu` continua não tendo café: a pergunta "o que tem no café"
  tem serviço e não tem fonte (Invariante 6 — dizer isso, não devolver vazio).
- As duas rotas concordam entre si quando cruzadas, nas duas capturas — nenhum caso de
  cardápio com comida em dia sem horário publicado, nem o inverso. Isso **não** é
  garantia: é o que sustenta usar `workinghours` como fonte da distinção, e o código
  declara o desacordo em vez de escolher um lado calado se ele aparecer.
- A resolução deve ser **por id**; o `name`/`alias` que a API devolve varia de grafia e
  serve só para exibição.

### 1.3 e-Disciplinas — Moodle

- Versão: **5.0.8+ (Build 20260722)**, site "Moodle USP: e-Disciplinas".
- O serviço **Moodle mobile web service** está habilitado e expõe ~400 funções, incluindo
  o conjunto completo de leitura *e* de escrita.
- `login/token.php` com usuário e senha **não funciona**: devolve `invalidlogin` mesmo com
  credencial correta, porque a conta autentica por SSO (Senha Única) e não há senha local
  para o Moodle comparar. Não insista nesse caminho.
- `/user/managetoken.php` lista os tokens **mas não mostra o valor** nesta versão — a
  primeira coluna é o *nome* do token (ex. `Webservice-iTEgf`, 16 caracteres). Um token real
  tem 32 caracteres hexadecimais.
- O valor sai pelo fluxo de launch do app, autenticado por sessão do navegador:
  `/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=1234&urlscheme=moodlemobile`
  → redirect para `moodlemobile://token=<base64>` → decodificar → `siteid:::token:::privatetoken`.
  **Não use `urlscheme=http`**: nessa forma o base64 cai na posição de host da URL e o Chrome
  normaliza host para minúsculas, corrompendo o token (base64 é sensível a caixa).
- O token do Caio expira em **17/11/2026**. É revogável em `managetoken.php` → Reconfigurar.
- **Faltas ficam fora deste token.** `mod_attendance_*` pertence a outro serviço (há um
  token "Attendance" separado na conta). Integrar presença é um segundo escopo.
- `core_calendar_get_calendar_export_token` devolve um hash que compõe uma URL de feed iCal
  (`/calendar/export_execute.php?userid=…&authtoken=…`). A URL **é a credencial** — quem tem
  o link lê o calendário.

### 1.4 Ainda não verificado, apenas recordado — confirmar antes de usar

- Os parâmetros do `export_execute.php` (`preset_what` ∈ {all, courses, user}, `preset_time`
  ∈ {recentupcoming, monthnow, weeknow, custom}).
- Que o `authtoken` do iCal derive do hash da senha (implicaria quebrar ao trocar a senha).
- Qualquer coisa sobre o JupiterWeb: **nenhum endpoint foi testado**. Não prometa Jupiter
  antes de mapear se existe JSON ou se é só HTML.

---

## 2. Invariantes

Não negociáveis, independentemente do que a descoberta sugerir.

1. **Read-only por padrão.** Escrita só existe atrás de env var explícita
   (`USP_MCP_ALLOW_WRITES=1`), e mesmo assim nunca implícita numa ferramenta de leitura.

2. **A superfície é allowlist, não denylist.** Só chega ao Moodle função que está numa
   lista explícita de permitidas. Isto mudou de forma em 31/08/2026, por dado — ver §9.
   Denylist como *única* camada não funciona aqui, por três motivos verificados:

   - **`tool_mobile_call_external_functions` anula qualquer filtro de nome.** Confirmado no
     fonte do Moodle 5.0 (`admin/tool/mobile/classes/external.php`): o único portão é
     `service_function_exists($request['function'], $token->externalserviceid)` — "essa
     função pertence ao serviço do token?" — e o serviço deste token contém as 447. Qualquer
     função passa por dentro dela, incluindo `mod_assign_submit_for_grading`. Um filtro sobre
     `wsfunction` não bloqueia nada enquanto essa função for alcançável.
   - **O campo `type` do Moodle não é fronteira de segurança.** `core_course_set_favourite_courses`
     se declara `read` e grava; `tool_mobile_get_tokens_for_qr_login`, que este mesmo item
     bloqueia, também se declara `read`.
   - **Glob não é blindagem.** `mod_forum_add_discussion*` casa com `add_discussion` e
     `add_discussion_post`, e deixa passar `mod_forum_update_discussion_post` e
     `mod_forum_delete_post`.

   **Bloqueio permanente, sem flag que libere** — segunda camada, sobre a allowlist:
   - `tool_mobile_call_external_functions` — o bypass acima. Se um só nome entrar nesta
     lista, é este.
   - `mod_quiz_start_attempt`, `mod_quiz_save_attempt`, `mod_quiz_process_attempt` — podem
     queimar uma tentativa de prova real. (`mod_quiz_finish_attempt` **não existe** neste
     site; finalizar é `process_attempt` com `finishattempt=true`.)
   - `tool_mobile_get_autologin_key`, `tool_mobile_get_tokens_for_qr_login`,
     `tiny_premium_get_api_key`, `mod_lti_get_tool_launch_data` — mintam ou vazam
     credencial; um MCP não tem motivo para escalar acesso. A `tiny_premium` devolve
     `get_config('tiny_premium','apikey')` sem exigir capability nenhuma.
   - `mod_assign_save_submission`, `mod_assign_submit_for_grading`,
     `mod_assign_start_submission`, `mod_assign_remove_submission` — entrega em nome do
     usuário. `start_submission` liga o cronômetro de entrega cronometrada: é o análogo
     exato de `start_attempt` e estava de fora. Se algum dia entrarem, entram como comando
     dedicado com confirmação humana, nunca como efeito colateral.
   - `mod_lesson_launch_attempt`, `mod_lesson_process_page`, `mod_lesson_finish_attempt` e
     as entregas de `mod_workshop` — mesmo raciocínio das tentativas de quiz.
   - `core_message_send_instant_messages`, `core_message_send_messages_to_conversation`,
     `mod_forum_add_discussion`, `mod_forum_add_discussion_post`,
     `mod_forum_update_discussion_post`, `mod_forum_delete_post`,
     `enrol_self_enrol_user` — falam com terceiros em nome do usuário. Note os **dois**
     caminhos de envio de mensagem: bloquear só `send_instant_messages` deixa o outro aberto.

   **Acrescentados em 14/09/2026, por auditoria.** As 447 funções do site foram varridas
   por verbo de escrita (57 candidatas) e classificadas contra as cinco categorias acima.
   Quinze caíam dentro delas e não estavam nomeadas. Isto **não reabre** a decisão de
   31/08 de que esta lista não é exaustiva — ela continua não sendo, e a allowlist segue
   sendo a superfície. O que muda é que as categorias que a lista **afirma** cobrir
   passam a cobrir:
   - `mod_choice_submit_choice_response`, `mod_choicegroup_submit_choicegroup_response`,
     `mod_feedback_process_page`, `mod_questionnaire_submit_questionnaire_response` —
     entregam em nome do usuário em atividade que não é `assign`. A enquete de grupo é a
     mais cara das quatro: ela **muda a matrícula** em grupo de trabalho.
   - `mod_feedback_launch_feedback`, `mod_scorm_launch_sco` — queimam tentativa, mesmo
     raciocínio de `mod_lesson_launch_attempt`.
   - `mod_data_add_entry`, `mod_glossary_add_entry`, `core_blog_add_entry` — publicam
     conteúdo assinado pelo usuário e visível a terceiros.
   - `core_comment_add_comments`, `core_rating_add_rating`, `core_notes_create_notes`,
     `core_message_create_contact_request` — falam com terceiros em nome do usuário,
     mesma classe dos dois caminhos de mensagem acima.
   - `core_completion_mark_course_self_completed`,
     `core_completion_update_activity_completion_status_manually` — afirmam progresso que
     o usuário não fez; a primeira declara um curso inteiro concluído. Nenhuma das duas
     tem desfazer pela API.

   **Olhadas e deixadas de fora, com motivo** (registrado em `tests/moodle/test_politica.py`,
   para a próxima varredura não reabrir as mesmas perguntas): as funções de nota e prazo
   (`mod_assign_save_grade*`, `*_save_feedback`, `save_user_extensions`) são capacidade de
   quem corrige e não da conta de aluno — se um dia o projeto servir conta de monitor, elas
   entram por decisão de §9; o calendário pessoal; dispositivo, arquivos privados e pedido
   de dados do próprio usuário; e a emissão de certificado, que é consequência da conclusão
   e não caminho para ela.

   Motivo do bloqueio: essas funções serão chamadas por um modelo interpretando linguagem
   ambígua. "Manda ver a lista de exercícios" não deve ter caminho até `submit_for_grading`.

3. **Nenhum segredo no repositório.** Token e hash por env var. `.env` no gitignore.
   Fixtures higienizadas (nome, e-mail, `userid`, ids de turma, notas) antes de qualquer
   commit.

4. **Credencial pessoal nunca sai da máquina do dono.** Dado autenticado (Moodle) só no
   entrypoint local. Um servidor hospedado do projeto não recebe token de Senha Única de
   ninguém — nem com consentimento, nem "só pra testar".

5. **Não martelar a USP.** Cardápio muda por semana; ementa por semestre. Cache com TTL
   coerente com a taxa de mudança do dado, não com a frequência das perguntas.

6. **Erro legível vence silêncio.** Token vencido, hash rotacionada e serviço fora devem
   produzir mensagem que diz o que fazer. Nunca devolver lista vazia que parece "não tem
   nada para entregar".

7. **Sem limite silencioso.** Se uma resposta for truncada, paginada ou amostrada, isso
   aparece na saída.

8. **Projeto não-oficial.** README declara que não há vínculo com a USP. Antes de divulgar
   amplamente, ler os termos de uso dos sistemas envolvidos — são APIs não documentadas, e
   "está público" não equivale a "liberado para redistribuir".

---

## 3. Fase 1 — descoberta

Objetivo: **ver o dado real antes de desenhar qualquer ferramenta.** Saída desta fase é uma
pasta `fixtures/` e anotações; não é código de produção.

### 3.1 Regra de ouro

**Não varra a lista de funções.** Um sweep sobre as ~400 funções chama, em algum momento,
`submit_for_grading` e `start_attempt` com o token do dono. Teste por allowlist explícita,
uma chamada por função, com parâmetros reais. Cada chamada também fica no log de web
service da conta — uma passada é uma passada, não um laço.

### 3.2 Ordem de captura

Cada resposta salva crua em `fixtures/<funcao>.json`.

| # | Função | Pergunta que ela deveria responder | Anotar |
|---|---|---|---|
| 1 | `core_webservice_get_site_info` | quem sou, o que está liberado | `userid`, versão, funções |
| 2 | `core_enrol_get_users_courses` | quais disciplinas eu curso | `courseid`; **cuidado**: devolve tudo em que há matrícula, acumulando semestres antigos — ver 3.2.1 |
| 3 | `core_course_get_contents` (1 courseid) | o que tem dentro da disciplina | **tamanho da resposta**; HTML embutido; se material exige chamada extra |
| 4 | `mod_assign_get_assignments` | quais entregas existem e quando vencem | formato de data; quantos assigns |
| 5 | `mod_assign_get_submission_status` (1 assign) | eu já entreguei? tem nota? | se é 1 chamada por assign ou dá em lote |
| 6 | `core_calendar_get_action_events_by_timesort` | o que vence nos próximos dias | cobertura: aparece prova presencial? |
| 7 | `gradereport_overview_get_course_grades` | como estou em cada disciplina | legibilidade vs `gradereport_user_get_grade_items` |
| 8 | `gradereport_user_get_grade_items` (1 courseid) | notas item a item | idem |
| 9 | `core_course_get_updates_since` | o que mudou desde ontem | sinal ou ruído? |
| 10 | `mod_forum_get_forum_discussions` (fórum de avisos) | o professor avisou algo | onde vive o aviso na prática |
| 11 | `core_calendar_get_calendar_export_token` | feed iCal | e depois: baixar o `.ics` e contar `VEVENT` |
| 12 | RUCard `/restaurants` e `/menu/{6,7,8,9}` | cardápio | confirmar nomes reais e formato por RU |

#### 3.2.1 "Minhas disciplinas" não é o que a API devolve

`core_enrol_get_users_courses` lista **toda** matrícula, e num Moodle de universidade isso
acumula semestres. O número que sai dali não é "disciplinas deste semestre". Descobrir qual
filtro separa o corrente do histórico — `visible`, `startdate`/`enddate`, `lastaccess`, ou
atividade recente — é ele mesmo um resultado da Fase 1, e provavelmente a primeira regra de
negócio do projeto. Não assuma; olhe os campos que vieram.

Para cada resposta, registrar três números: **bytes**, **estimativa de tokens** e **quantas
chamadas foram necessárias** para responder à pergunta da linha. Esses três números decidem
mais sobre o desenho do que qualquer preferência estética.

### 3.3 Higienização

Antes de commitar fixtures: substituir nome, e-mail, `userid`, `fullname` de turma e notas
por valores sintéticos estáveis (mesmo id → mesmo valor falso), preservando a **forma**. A
forma é o que interessa para teste.

---

## 4. Questões abertas

Fechar com dado da Fase 1. Nenhuma delas deve ser respondida agora.

**Sobre o valor real**

- Que **fração** das disciplinas do semestre corrente usa o Moodle de forma viva — prazo
  publicado, material postado, aviso em fórum? Se for pequena, um MCP de prazos vale bem
  menos do que parece, e o gargalo real pode estar no Jupiter ou no quadro da sala.
  **Medir, não estimar** — inclusive o total de disciplinas.
- O calendário cobre prova presencial, ou só entrega online? Se não cobre, "o que vence"
  mente por omissão e precisa dizer o que não sabe.
- O feed iCal já entrega a maior parte do valor sem código nenhum? Se sim, o escopo Moodle
  do MCP encolhe para o que o iCal não tem: "já entreguei?", nota, material.

**Sobre custo e forma**

- ~~`get_contents` é suficiente para achar material, ou exige N chamadas por módulo?~~ **Fechada em 28/08 e completada em 12/09** (§9): basta para `resource` e `url`, e **não** para `assign` — o anexo do enunciado só existe em `mod_assign_get_assignments`. São duas chamadas por disciplina, e a segunda só sai quando a primeira acha um módulo de entrega.
- `submission_status` é por assign? Quantos assigns por semestre? Isso define se "já
  entreguei" é uma chamada ou trinta.
- Qual das duas visões de nota é estável e legível o suficiente para virar texto curto?
- Qual o tamanho típico de cada resposta em tokens? Define se a ferramenta resume ou
  devolve cru — e resumir no servidor é decisão de design, não detalhe.

**Sobre operação**

- Existe rate limit observável? Existe log visível para professor ou admin?
- Jupiter tem JSON em algum lugar, ou é scraping? (Se for scraping: assumir manutenção
  semestral explícita ou não prometer.)

---

## 5. Fase 2 — desenho, só depois da Fase 1

Critério para uma ferramenta existir:

1. Responde uma pergunta que o dono **faz de verdade**, com o vocabulário dele.
2. Resolve em **uma chamada de ferramenta** do ponto de vista do modelo.
3. Cabe em **pouco contexto** — resposta curta, ou resumida no servidor com o cru
   disponível sob demanda.

O nome vem da pergunta, não da função do Moodle. `o_que_vence` é bom nome; `get_action_events_by_timesort` não é.

Perguntas candidatas — **as perguntas, não as ferramentas** (o mapeamento pergunta→ferramenta
é resultado da Fase 1, e várias podem colapsar numa só ou desaparecer):

- O que eu tenho que entregar até domingo, e o que disso eu já entreguei?
- Como estou de nota nessa disciplina?
- O professor avisou alguma coisa desde ontem?
- Onde está o PDF da aula de hoje?
- Qual o link da aula online?
- O que tem no bandejão hoje, e onde vale a pena almoçar?
- Essa disciplina tem quantos créditos e qual o pré-requisito?

**Não decidir agora:** o número de ferramentas, os nomes, o formato de saída, nem se Moodle
e bandejão pertencem ao mesmo servidor.

---

## 6. Empacotamento — decisão parcial, com justificativa

Uma coisa já está decidida porque é consequência dos Invariantes 3 e 4, não de gosto:

- **Dado autenticado e pessoal (Moodle) → entrypoint local (stdio).** O token fica na
  máquina de quem usa. Cada pessoa traz o seu.
- **Dado público e cacheável (bandejão, e Jupiter se existir) → pode ser servidor HTTP
  hospedado.** Cache compartilhado, ninguém manda credencial, e funciona até de dentro de
  ambientes com allowlist restritiva, porque quem faz o fetch é o servidor.

Aberto: linguagem e runtime, transporte exato, hospedagem, se há um core compartilhado ou
dois projetos. Decidir depois de saber o tamanho e a forma das respostas.

### 6.1 O formato que corresponde a esta decisão tem nome — pesquisado em 03/09/2026

A decisão acima descreve, sem saber, o **MCP Bundle** (`.mcpb`): servidor local
empacotado, stdio, instalado com um clique, sem OAuth. "O token fica na máquina de
quem usa, cada pessoa traz o seu" é a definição dele. Análise em
`notas/mcpb-e-distribuicao.md`; **nada foi testado** — é leitura de documentação, e a
distinção importa (item 9 do `CLAUDE.md`).

O que ele resolve: o `manifest.json` declara `user_config`, o Claude Desktop **gera a
tela de configuração sozinho**, e `"sensitive": true` mascara o campo. O valor chega
ao processo como **variável de ambiente** — `"env": {"MOODLE_TOKEN":
"${user_config.moodle_token}"}` —, exatamente o que `usp_mcp/env.py` já lê. Nenhuma
linha do código muda.

O que ele custa: a documentação recomenda **Node.js** porque ele vem junto com o
Claude Desktop; Python é suportado (`compatibility.runtimes.python`, ou o tipo UV) mas
exige runtime na máquina do usuário. O Claude Desktop roda em macOS e Windows, não
Linux.

**Conector remoto segue fora para o Moodle, e agora por três motivos:** a rede da USP
não sai da nuvem (§1.1), o token não pode ir (Invariante 4) e conector remoto
autenticado exige OAuth 2.0 — que o e-Disciplinas não oferece; ele dá token pessoal
de web service. Para RUCard e Jupiter, que são dado público, o remoto continua
viável e é onde ele faria sentido.

---

## 7. Anexo A — viés a evitar

Numa conversa anterior foi esboçada uma tabela de 8 ferramentas derivada **da lista de
funções que a API oferece**. Está registrada aqui só para ser confrontada com a Fase 1, e a
expectativa honesta é que ela encolha:

`minhas_disciplinas`, `o_que_vence`, `notas`, `novidades`, `avisos_do_professor`,
`material`, `busca`, `link_da_aula`.

**Não construa a partir dessa lista.** Ela responde à pergunta "o que a API deixa fazer?",
que é a pergunta errada. A pergunta certa é "o que eu quero saber?", e ela ainda não foi
respondida com dado.

---

## 8. Anexo B — comandos que funcionaram

> **Este fluxo tem chamador desde 10/09/2026: `./scripts/token.sh`.** Ele executa os
> sete passos guiado, decodifica sem imprimir o valor, confirma o token contra a USP
> em uma chamada e só então grava no `.env`. O que está escrito abaixo continua sendo
> a fonte — é o que o script faz, e é o que consertar quando ele quebrar.

Token do Moodle (no navegador logado, com DevTools → Network aberto):

```
https://edisciplinas.usp.br/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=1234&urlscheme=moodlemobile
```

Copiar a URL da linha `token=…` e decodificar:

```bash
pbpaste | python3 -c 'import base64,re,sys
u=sys.stdin.read().strip(); b=u.split("token=",1)[1].rstrip("/")
b=re.sub(r"[^A-Za-z0-9+/=_-]","",b).replace("-","+").replace("_","/")
p=base64.b64decode(b+"="*(-len(b)%4)).decode().split(":::")
print("siteid: ",p[0]); print("wstoken:",p[1])'
```

Chamada genérica (sempre imprimir o erro cru, nunca engolir):

```bash
ws() {  # ws <funcao> [param=valor ...]
  local fn="$1"; shift
  local args=(); for kv in "$@"; do args+=(--data-urlencode "$kv"); done
  curl -s "https://edisciplinas.usp.br/webservice/rest/server.php" \
    --data-urlencode "wstoken=$MOODLE_TOKEN" \
    --data-urlencode "wsfunction=$fn" \
    --data-urlencode "moodlewsrestformat=json" "${args[@]}"
}
ws core_webservice_get_site_info | python3 -m json.tool | head -40
ws core_enrol_get_users_courses "userid=$MOODLE_USERID" > fixtures/users_courses.json
```

Bandejão:

```bash
curl -s -X POST https://uspdigital.usp.br/rucard/servicos/menu/6 -d "hash=$RUCARD_HASH"
```

---

## 9. Registro de decisões

Anexar aqui, com data, toda questão da seção 4 que for fechada, o dado que a fechou, e o que
foi descartado. Um documento de partida que não vira registro de decisão é um documento que
mente na segunda semana.

### 27/08/2026 — número fabricado, removido

A primeira versão deste documento dizia "se 2 de 6 disciplinas publicam prazo no Moodle".
**Esse número foi inventado**, não medido: nem o "2" nem o "6" vinham de dado nenhum — o "6"
foi inferência frouxa a partir das skills de revisão existentes, que são dez e cobrem
semestres diferentes. Reescrito como fração a medir. Registro fica como aviso: número
plausível sem fonte é o modo mais fácil de um documento de descoberta virar documento de
viés.

### 27/08/2026 — Fase 1, linha 12 (RUCard) executada

Fixtures em `fixtures/rucard/`, análise em `notas/fase1-rucard.md`. §1.2 corrigido em três
pontos com dado: forma do `/menu` (é objeto, não lista), grafia instável de "Fechado", e
ausência de café da manhã. Medição de custo: `/restaurants` = 27.661 B (~6.900 tokens),
cada `/menu` = 2,3–3,6 kB (~600–900 tokens); "bandejão hoje nos 4 RUs" custa **4 chamadas**
e ~3.000 tokens crus para entregar 8 refeições, porque não existe endpoint multi-RU e o
payload sempre traz a semana inteira. Esses números vão para a Fase 2; nenhuma ferramenta
foi desenhada aqui.

Não fechou nenhuma questão da seção 4 — todas elas dependem do Moodle.

### 28/08/2026 — Fase 1, linhas 1–6 do Moodle

Fixtures cruas em `fixtures/moodle/raw/` (gitignorado), análise em `notas/fase1-moodle.md`.

**§3.2.1 fecha: o filtro é `startdate`/`enddate`.** De 74 matrículas, **10** são do semestre
corrente (03–04/08 a 12–14/12/2026). Dois filtros independentes — `enddate` no futuro e
`startdate` nos últimos 120 dias — dão o mesmo conjunto exato. Descartados com motivo:
`visible` vale `true` nas 74 e não separa nada; `shortname` não marca semestre de forma
confiável (`PSI3322-2026-REOF` começou em fevereiro); `lastaccess` ≤ 30d dá 12, um
superconjunto útil para outra pergunta.

**A fração viva, medida:** das 10 disciplinas, **4 têm entrega** no Moodle e **6 aparecem no
calendário** (entrega ou quiz); 4 não aparecem em nenhuma das duas. Substitui o "2 de 6"
fabricado que o registro anterior retratou. Ainda falta medir material e aviso de fórum
antes de tratar como resposta final.

**O calendário e prova presencial — corrigido em 28/08/2026, ver registro abaixo.** A
primeira versão desta entrada dizia que o calendário não cobre prova presencial. Está
errado, e o dado que refuta já estava na mesma captura.

**§1.3 corrigido:** são **447** funções expostas, não "~400". `downloadfiles=1` e
`uploadfiles=1` — o token pode escrever; quem impede é o Invariante 1, não a API.

**Custo — o número que mais decide desenho.** `mod_assign_get_assignments` sem parâmetro
devolve as 74 disciplinas: **1 MB, ~251k tokens**. Com os 10 `courseids`: 38 kB, ~9,5k —
**96,2% menor**. E `get_action_events_by_timesort` gasta **541 kB / ~135k tokens** para 35
eventos, porque cada evento embute um objeto `course` de 9,5 kB (88% do payload) repetido a
cada evento da mesma disciplina; os campos que respondem à pergunta somam **132 bytes por
evento**. ~1000:1.

Consequência que já não é opinião: **resumir no servidor é requisito**, e toda chamada
precisa de escopo explícito. Uma ferramenta que repasse essas respostas cruas é inviável,
não só cara.

**`get_contents` é suficiente para material** (fecha questão do §4): os 22 arquivos de um
curso já vêm com URL direta; só fóruns e assigns pedem chamada própria, e têm função
dedicada de qualquer forma. Custo: ~14,5k tokens por disciplina — sob demanda, nunca varrer.

### 28/08/2026 — `MOODLE_USERID` sai da configuração

Medido, não suposto. `core_enrol_get_users_courses` com userid **errado** devolve `[]`, HTTP
200, sem erro — a falha silenciosa do Invariante 6. Com userid **ausente**, devolve
`invalidparameter`. O modo perigoso é o valor errado, não o valor faltando.

E é a única função que precisa de `userid`: `mod_assign_get_assignments`,
`core_calendar_get_action_events_by_timesort` e `gradereport_overview_get_course_grades`
inferem do token (as duas últimas devolvem resposta idêntica com e sem o parâmetro).

Como `core_webservice_get_site_info` entrega o `userid` a partir do token em uma chamada,
configurar o valor à mão só adiciona um jeito de errar calado. Removido do `.env.example`;
deriva em runtime. O que se perde sem ele é só a lista de disciplinas — que por sua vez é a
raiz de tudo, porque é dela que saem os `courseids` que dão escopo às demais chamadas e
evitam a resposta de 251k tokens.

### 28/08/2026 — correção: o calendário **cobre** prova presencial, quando o professor modela

Retrato de uma conclusão minha da entrada anterior. Eu classifiquei os 35 eventos por
`modulename` (só `assign` e `quiz`) e `eventtype` (só `due`/`close`) e inferi daí que prova
presencial não aparece. A inferência é inválida: os dois eventos **"Prova Presencial - 1"
(28/09) e "Prova Presencial - 2" (30/11)**, de PTC3314, estavam literalmente na resposta que
eu já tinha em mãos. O professor os criou como `assign` com `duedate`. Taxonomia de tipo não
diz o que o evento é — diz só como foi modelado.

A conclusão certa é mais fraca e mais útil: **a cobertura não é estrutural, é prática de
professor.** Quem lança a prova como atividade do Moodle aparece; quem anuncia no fórum, não.
PSI3323 é o contraexemplo na mesma captura: o fórum "Avisos" traz **"Grupos para a Prova
Prática P1"** (25/08), e o único evento de calendário da disciplina é a entrega de relatório
de 21/08. A prova não está no calendário dessa disciplina.

Consequência para o desenho: **"o que vence" não pode se basear só no calendário**, e a
declaração de incerteza do Invariante 6 continua necessária — mas o motivo é outro. Não é
que o calendário seja cego por construção; é que ele reflete o que cada professor decidiu
registrar, e isso varia dentro do mesmo semestre.

### 28/08/2026 — Fase 1, linhas 5, 7–11: as respostas baratas

Contraste forte com as gordas da entrada anterior. Todas via `scripts/capture.sh`, que
imprime só a medida e nunca o payload.

| linha | chamada | bytes | ~tokens |
|---|---|---:|---:|
| 5 | `mod_assign_get_submission_status` (1 assign) | 1.027 | ~260 |
| 7 | `gradereport_overview_get_course_grades` | 3.489 | ~870 |
| 8 | `gradereport_user_get_grade_items` (1 curso) | 1.292 | ~320 |
| 9 | `core_course_get_updates_since` (7 dias) | 415 | ~100 |
| 10 | `mod_forum_get_forum_discussions` (1 fórum) | 8.583 | ~2.150 |
| 11 | feed iCal `.ics` (all/recentupcoming) | 18.141 | ~4.500 |

**Linha 5 — "já entreguei" e "tem nota" são perguntas separadas.** `submission_status`
devolve `submission.status = "submitted"` com `timemodified`, mas **não traz nota**: não há
`feedback` no payload. É uma chamada por assign (~260 tokens cada); os 20 assigns do semestre
custariam ~5k tokens em 20 idas — barato em token, caro em latência.

**Linhas 7 e 8 — as duas visões não competem, se complementam.** O `overview` é a mais
barata do projeto por unidade de informação: 70 cursos em ~870 tokens, três campos por linha
(`courseid`, `grade`, `rawgrade`). Serve para "como estou em tudo". O `grade_items` traz 24
campos por item de **um** curso e é o único que responde "como estou nessa disciplina, item a
item". A escolha é por pergunta, não por qualidade.

**Linha 9 — é sinal, não ruído, e é a chamada mais barata de todas.** Com janela de 7 dias,
devolve 3 instâncias em ~100 tokens, e diz *o que* mudou por cmid: `discussions`,
`submissions`, `configuration`, `contentfiles`. Não devolve conteúdo — devolve ponteiro. É a
função ideal para decidir se vale gastar uma chamada cara. Com janela de 24h veio vazia, o
que é resultado legítimo, não falha.

**Linha 10 — o fórum de avisos é onde mora o que o calendário não sabe.** 4 discussões no
"Avisos" de PSI3323, ~2.150 tokens. É lá que está o anúncio da prova prática. O curso tem
dois fóruns `news`, um deles vazio.

**Linha 11 — o iCal entrega quase tudo por ~1/30 do custo.** 37 eventos em 18 kB contra 35
eventos em 541 kB do `get_action_events_by_timesort`. E os parâmetros que o §1.4 registrava
como "apenas recordados" estão **confirmados**: `preset_what` ∈ {all, courses} e `preset_time`
∈ {recentupcoming, monthnow, custom} respondem HTTP 200. `custom` traz mais (54 eventos),
`monthnow` menos (26). `preset_what=courses` deu resposta idêntica a `all` — byte a byte —
porque não há evento pessoal nesta conta; não é prova de que os dois sejam equivalentes em
geral.

Isso ataca de frente a questão do §4 "o feed iCal já entrega a maior parte do valor sem
código nenhum?". A resposta que o dado sustenta: **para "o que vence", sim.** O que o iCal
não tem é "já entreguei" (linha 5), nota (7 e 8) e aviso de fórum (10) — e é exatamente aí
que sobra escopo para o MCP.

### 31/08/2026 — projeção medida: 2,6% do payload é resposta

Pergunta que motivou: "existe alguma higienização para tornar tudo menos caro?". Não — são
duas operações diferentes, e vale não confundir. A **higienização do §3.3 é privacidade**:
troca nome, userid e nota por sintético, e o payload continua do mesmo tamanho. O que
barateia é **projeção**: descartar campo que não responde pergunta nenhuma.

Medido com `scripts/reduzir.py` sobre as fixtures reais:

| resposta | cru | projetado | sobra |
|---|---:|---:|---:|
| o que vence (35 eventos) | 528,3 kB | 7,1 kB | **1,3%** |
| minhas disciplinas (10 de 74) | 102,3 kB | 1,2 kB | **1,2%** |
| conteúdo de 1 disciplina | 56,7 kB | 6,7 kB | 11,7% |
| entregas do semestre | 37,2 kB | 2,2 kB | 5,9% |
| avisos de 1 fórum | 8,4 kB | 2,9 kB | 35,1% |
| `site_info` | 30,7 kB | 0,1 kB | **0,3%** |
| **total** | **763,5 kB** | **20,2 kB** | **2,6%** |

Em token: **~195.000 → ~5.200**.

O número que mais importa não é o total, é a **dispersão**. Ela diz o que cada resposta é:

- **1–2% sobrando** (eventos, disciplinas, `site_info`) — não é compressão, é **remoção de
  repetição**. O calendário repetia um objeto `course` de 9,5 kB por evento; `site_info` era
  447 nomes de função. Jogar fora não perde nada, porque nunca houve informação ali.
- **35% sobrando** (avisos de fórum) — aqui o payload **é** o conteúdo: texto que um
  professor escreveu. O que caiu foi HTML e metadado. Não dá para espremer mais sem perder
  resposta.

A regra que sai disso: **quanto mais uma resposta comprime, menos ela estava respondendo.**
Uma projeção que corta 99% é transporte descartado; uma que corta 65% já está no limite do
que dá para tirar sem mentir.

Ressalva honesta: projeção **não é grátis por definição**. As acima descartam descrição de
evento e metadado de entrega — decisões defensáveis para as perguntas do §5, mas decisões.
O que é grátis é só a parte de deduplicação.

Consequência para a Fase 2: **o semestre inteiro projetado cabe em ~5.200 tokens.** Isso
reabre uma possibilidade que os números crus tinham matado — não é preciso escolher entre
poucas ferramentas caras e muitas baratas. Cabe entregar bastante coisa de uma vez, desde
que o servidor projete antes.

### 31/08/2026 — Jupiter: existe superfície estruturada, e não é onde se esperava

Fecha parcialmente a questão do §4 "Jupiter tem JSON em algum lugar, ou é scraping?".
Reconhecimento em `notas/jupiter-recon.md`, 20 fixtures em `fixtures/jupiter/`, 26
requisições. Verifiquei por conta própria as duas afirmações que mais mudam decisão, numa
disciplina que o reconhecimento não tinha amostrado (PTC3312).

**Não é REST/JSON. É DWR** — RPC Java sobre HTTP, no bean `ControlePublicoDWR`, em
`POST /jupiterweb/dwr/call/plaincall/ControlePublicoDWR.obter.dwr`. Devolve objeto com
campos nomeados dentro de um envelope JavaScript, não HTML de tabela. Para PSI3323: 3.707 B
contra 42.769 B do HTML equivalente — **11,5× menor e sem parser**.

**É stateless e público** — sem cookie, sem handshake, com `scriptSessionId` inventado.
Encaixa no "servidor HTTP hospedado" do §6, sem credencial de ninguém.

**A fronteira não está onde a intuição põe.** O dado *estático* (ementa, créditos,
pré-requisito, grade curricular) tem RPC. O dado *do semestre* não: `obterTurma` traz dia,
hora, sala, professor e vagas — público, e é justamente o que o Moodle não tem — mas a
página de busca de turma **não carrega interface DWR nenhuma**. Horário é scraping de HTML
com 48 tabelas, 148 `<tr>` e **zero `id`**, ancorável só por rótulo de texto.

**Erro com HTTP 200, e caro.** Sigla inexistente devolve **HTTP 200 com 7.176 B de stack
trace do Tomcat** — maior que a resposta de sucesso, e vazando classe interna do servidor.
Quem checar status code produz exatamente o silêncio que o Invariante 6 proíbe; e quem
repassar o corpo cru ao modelo gasta mais token errando do que acertando. A detecção tem que
ser por conteúdo (`localizedMessage`), nunca por status.

Decisão que isto sustenta: **fazer ementa/créditos/pré-requisito/grade via DWR** — a
pergunta "quantos créditos e qual o pré-requisito?" do §5 custa 2 chamadas e ~1.010 tokens.
**Não prometer horário de aula** sem assumir a manutenção semestral explícita que o §4 exige.

**Invariante 8 continua aberto, e mais do que parecia.** Não há `robots.txt` (a rota devolve
302 para login, que é o 404 do balanceador — ausência de diretiva, não permissão). Não há
termo de uso nas páginas públicas. O nome `ControlePublicoDWR` é sinal de intenção, não
autorização escrita: antes de divulgar, perguntar à STI, não deduzir do nome de uma classe
Java.

**Buraco principal registrado:** há uma só amostra de `obterTurma`, e não se sabe como o
bloco de horário se comporta com turma teórica+prática ou disciplina anual — que é
exatamente a parte frágil. Rate limit não foi observado em 26 requisições, o que **não
prova** que não exista. E há uma discrepância não explicada: `codcur` aparece como 3033 no
DWR e 3032 no HTML de requisitos da mesma habilitação.

### 31/08/2026 — a Fase 2 do Moodle ganha especificação executável

A pergunta era "como verificar o MCP do Moodle" quando o MCP não existe. Resposta
escolhida: escrever a suíte antes, como spec executável de uma **fatia vertical**
— `o_que_vence`, uma ferramenta ponta a ponta — em vez das seis perguntas medidas
na Fase 1. Motivo: seis ferramentas vermelhas ao mesmo tempo é TDD no nome e
waterfall no comportamento.

Runtime: **Python + pytest** (o §6 deixava em aberto). O repo já é bash+python3 e
não tem `package.json`. Fonte de `o_que_vence`: **web service projetado**, não o
feed iCal — o iCal exigiria um segundo segredo e devolve ICS sem `courseid`
utilizável, apesar de custar 1/30.

99 testes em três camadas por marcador: `politica` (58, sem rede nem fixture),
`contrato` (41, contra fixture higienizada), `live` (2, só com `USP_MCP_LIVE=1`).
Roda em 0,46 s. Hoje: 91 vermelhos por construção, 6 verdes, 2 pulados.

**`scripts/higienizar.py` existe** — o §3.3 era prosa e virou código. Ele preserva
a forma, como o §3.3 pede, **e o comprimento em bytes**, que o §3.3 não pede e o
teste de custo exige: encolher um `summary` de 9 kB apagaria justamente o custo
que a projeção existe para resolver. `fixtures/moodle/action_events.json` entrou
no git; o cru continua fora.

**Descoberta que corrige um erro de desenho:** medindo subamostras dos mesmos 35
eventos, a razão de redução varia 63,5× → 81,1× (28%), porque o `course` de 9,5 kB
repetido faz a razão medir composição de amostra, não qualidade da projeção. O que
é estável é **201–205 B por evento projetado** (±2%). Um teste de custo ancorado na
razão seria frouxo ou quebradiço. Ficou em três asserções: teto absoluto com folga
declarada, bytes/evento na faixa medida, e a categórica "nenhum `course` sobrevive"
— esta última é a que trava a regressão de verdade.

Registro de imprecisão: o **1000:1** de `notas/fase1-moodle.md` compara o cru com
os 132 B/evento dos campos mínimos. A projeção implementável é **76:1**, o mesmo
1,3% da entrada anterior. Dois números verdadeiros sobre coisas diferentes; o teste
vive no 76:1.

**Achado colateral, e é uma lacuna da Fase 1:** não existe fixture de erro do
Moodle. Varredura por `debuginfo`, `backtrace`, `stacktrace`, `exception` e
`errorcode` deu zero em todas as capturas — só respostas bem-sucedidas. Os testes
de erro legível asseguram o contrato da camada, nunca a forma do erro do Moodle,
que segue **não verificada**. Capturar um `invalidtoken` (token propositalmente
inválido, não toca na conta) está no backlog.

Descartado: suíte contra a API real como canário principal (não descreve o
servidor a construir), suíte end-to-end só pela fronteira MCP (torna a asserção de
custo frouxa e a de allowlist quase impossível de escrever por tabela), e fixture
sintética escrita à mão (a forma sairia da minha leitura das notas, não do
payload).

Desenho completo em `docs/superpowers/specs/2026-08-31-testes-moodle-design.md`.
Acordos de nome com a suíte do Jupiter no §7 de lá.

### 31/08/2026 — o §2.2 era contornável; vira segunda camada de uma allowlist

Catálogo das 447 funções em `notas/moodle-catalogo.md`, produzido **sem nenhuma chamada ao
web service** (a lista saiu do `site_info.json` já capturado; a classificação veio do fonte
`MOODLE_500_STABLE`). 437 das 447 documentadas a partir do código; as 10 restantes são
plugins de contribuição da USP e estão marcadas como inferência.

Conferi contra a nossa própria fixture e contra o fonte, em vez de aceitar o relatório:

**1. `tool_mobile_call_external_functions` existe neste site e anula a denylist inteira.**
Li `admin/tool/mobile/classes/external.php`: o corpo tem um único portão,
`service_function_exists($request['function'], $token->externalserviceid)`. Ele pergunta se
a função pertence ao serviço do token — e o serviço deste token são as 447. Não há checagem
de nome, de tipo nem de capability adicional. `requests[0][function]=mod_assign_submit_for_grading`
passa. **Um MCP que filtre `wsfunction` não bloqueia nada.**

**2. `mod_quiz_finish_attempt` não existe neste site.** Dos 10 nomes que o §2.2 listava, 9
existem e 1 era morto — bloqueávamos um fantasma enquanto o caminho real, `process_attempt`
com `finishattempt=true`, já estava coberto por outro item, por sorte e não por desenho.

**3. O glob não alcançava o que parecia.** `mod_forum_add_discussion*` casa com
`add_discussion` e `add_discussion_post`, e deixa passar `update_discussion_post` e
`delete_post`.

**4. `type: read` não é fronteira de segurança.** `core_course_set_favourite_courses` se
declara leitura e grava; `tool_mobile_get_tokens_for_qr_login`, que o próprio §2.2 bloqueia,
também se declara leitura. Classificar por esse campo é confiar no rótulo do plugin.

Escala do buraco: **178 funções mudam estado**; o §2.2 alcançava 10. Entre as que faltavam:
`mod_assign_start_submission` (liga o cronômetro de entrega cronometrada — análogo exato de
`start_attempt`), `mod_assign_remove_submission`, o ciclo de `mod_lesson`, as entregas de
`mod_workshop`, `core_message_send_messages_to_conversation` (segundo caminho de envio de
mensagem), e `tiny_premium_get_api_key`, que devolve uma API key **sem exigir capability
nenhuma**.

**Decisão: a superfície passa a ser allowlist**, com o §2.2 reescrito como segunda camada.
Manter uma lista de 168 proibidos através de upgrades do Moodle e de plugins que a USP
instala por conta é promessa que quebra na primeira atualização — e quebra em silêncio.

Também fecha um item do §1.4: **o `authtoken` do iCal deriva do hash da senha**, confirmado
em `calendar/lib.php` (`sha1($user->id . password . $CFG->calendar_exportsalt)`). Se isso
rotaciona numa conta de SSO sem senha local continua sendo inferência, não fato.

### 31/08/2026 — Fase 2 do Moodle implementada contra a suíte; a fatia vertical fecha

A suíte de `tests/moodle/` (99 testes, escrita antes da implementação e descrita em
`docs/superpowers/specs/2026-08-31-testes-moodle-design.md`) saiu de **91 vermelhos, 6
verdes, 2 pulados** para **97 verdes, 0 vermelhos, 2 pulados**. Os 2 pulados são a camada
`live`, e o skip diz o motivo por escrito: `USP_MCP_LIVE` desmarcada, e do sandbox a rede da
USP não é alcançável (§1.1). Nenhum teste, nenhuma fixture e nenhum marcador foi alterado —
verificável em `git diff --name-only 8125f20..HEAD -- tests/ fixtures/`, que sai vazio.

Cinco módulos, um commit cada: `politica`, `projecao`, `cliente`, `o_que_vence`, `server`.

**O que a implementação mediu, e que confirma o desenho.** A projeção fecha em **7.170 B**
para os 35 eventos da fixture — **204,9 B por evento**, dentro da faixa de 180–230 que a
suíte fixou a partir de quatro amostras, e a 28% do teto de 10.000 B. O texto que chega ao
modelo tem **2.728 caracteres** para 35 eventos com janela de 30 dias, contra o teto de
4.000. Partindo de 531.851 B de fixture crua, a ferramenta inteira entrega a resposta em
~2,7 kB de texto.

**Duas escolhas de campo foram decididas pelo orçamento de bytes, não por gosto**, e ficam
registradas porque não são óbvias no código:

- `activityname` em vez de `name`. O `name` do Moodle é a frase pronta para exibição
  ("*X* está marcado(a) para esta data"), redundante com `disciplina` + `tipo`. Trocar um
  pelo outro move a medida de 204 para 226 B/evento — ainda dentro da faixa, mas comendo
  quase toda a folga sem responder nada a mais.
- `url` em vez de `viewurl`. Mesmo destino prático; `viewurl` custa ~41 B a mais por evento
  e sozinho leva a medida a 245 B/evento, **fora** da faixa.

**§6 fecha em parte, e por consequência e não por escolha:** a linguagem e o runtime da
Fase 2 são **Python 3 + stdlib, sem dependência nova**. O transporte do cliente é
`urllib.request`; o SDK do MCP não é dependência de teste e seu import mora dentro de
`server.main()`, não no topo do módulo. Isso não foi preferência estética: um import de topo
quebraria a coleta da suíte inteira por causa de um pacote que as funções puras nem usam.
Continuam abertos hospedagem e se haverá core compartilhado com o servidor público.

**§5 continua aberto de propósito.** Isto implementou **uma** ferramenta, `o_que_vence`, e
não o mapeamento pergunta→ferramenta. `politica.ALLOWLIST` tem exatamente um nome e a suíte
trava esse número (T7); `server.listar_ferramentas()` expõe exatamente uma ferramenta e a
suíte trava esse número (T42). Crescer qualquer um dos dois é entrada nova aqui no §9, não
"só mais uma".

**O que NÃO foi verificado, e continua não sendo.** A limitação declarada no §6 do documento
de desenho vale integralmente depois da implementação: **não existe fixture de erro do
Moodle**. Os testes de erro do cliente asseguram o contrato da camada — que erro de
credencial vira `TokenInvalido` com instrução, que HTML de manutenção com HTTP 200 vira
`RespostaIlegivel`, que timeout vira `MoodleIndisponivel` — e **nunca** a forma real do erro
do Moodle, que segue não verificada. O caminho de transporte HTTP real e o adaptador stdio
do `main()` também não têm teste: nenhum roda offline. Capturar um `invalidtoken` real é
barato e seguro e continua no backlog.

### 31/08/2026 — a camada `live` rodou verde: a API não mudou desde 28/08

`USP_MCP_LIVE=1 pytest -m live` no terminal do dono: **2 passed, 97 deselected em
3,34 s**. É o canário do §5 do documento de desenho fechando o circuito — a fixture é
de 28/08 e congela, e sem esta camada a USP poderia mudar a API por baixo com a suíte
verde. Não mudou: as chaves de topo e os campos do primeiro evento da resposta real
ainda batem com a fixture. Uma chamada, `limitnum=5`, dentro da Regra de Ouro do §3.1.

Com isso a suíte inteira está verificada: **97 offline + 2 live = 99 de 99**.

**E o caminho até aqui expôs um buraco na própria suíte.** O comando falhava com
"MOODLE_TOKEN está vazio" numa máquina onde o `.env` estava preenchido, porque **nada
no lado Python carregava o `.env`** — só `scripts/ws.sh` sourceia o arquivo (`set -a`,
linha 15). O erro era legível e apontava a cura errada: mandava copiar o
`.env.example` para quem já tinha o `.env`. É o bug do §9 de 28/08 outra vez, agora
dentro da ferramenta de teste em vez de na resposta da API.

Duas consequências, ambas corrigidas em `tests/moodle/conftest.py`:

- **O `.env` agora é carregado pela suíte**, procurando na raiz e subindo até o
  checkout com o `.git` de verdade — um worktree novo não tem `.env`, exatamente como
  não tem o cru. Parser de stdlib: `python-dotenv` seria a primeira dependência de
  runtime do projeto, e o formato é `CHAVE=valor` com comentário. `setdefault` e não
  atribuição, para que quem já está no ambiente ganhe — é o que impede o carregador de
  ligar a camada live por baixo de quem não pediu.
- **`test_a_fixture_versionada_nao_contem_segredo_do_env` passava no vácuo.** Ela varre
  a fixture procurando os segredos do ambiente, e o ambiente não tinha nenhum para
  procurar: a asserção era verdadeira sobre lista vazia. Agora os três segredos estão
  carregados quando ela roda, e ela segue verde — a fixture está limpa de fato, não por
  omissão. Vale como aviso: um teste de segurança que não pode falhar não verifica nada
  (§6 do `CONVENTIONS.md`).

### 31/08/2026 — o token chega ao servidor pelo `.env`; e o `main()` não casava com o SDK

**Decisão: `usp_mcp/env.py` carrega o `.env`, e os dois lados usam** — a suíte
(`conftest`) e o entrypoint stdio (`server.chamar_ferramenta`). O `.env` do §8,
gitignorado, continua sendo a única casa do token, e o `.mcp.json` vai para o git sem
segredo nenhum.

**Descartado:** o token vir do bloco `env` da configuração do cliente MCP. Ele
duplicaria o segredo num arquivo de configuração fácil de commitar por acidente, e
exigiria `export MOODLE_TOKEN` no shell — que é exatamente a etapa que ninguém faz e
que produziu o erro enganoso do registro anterior. O `setdefault` do carregador
preserva o melhor dos dois: **quem já está no ambiente ganha**, então um cliente MCP
que passe a variável continua sobrescrevendo o arquivo.

**O achado que fecha o argumento do registro anterior.** O `main()` — o único caminho
sem teste offline — **não funcionava**. Foi escrito contra a API antiga do SDK
(`Server` com decoradores `@servidor.list_tools()` / `@servidor.call_tool()`), e no
`mcp` 2.1.1 instalado esses decoradores não existem: a API é `MCPServer` com
`@servidor.tool(...)` e `run(transport="stdio")`. A suíte estava 99/99 verde com esse
caminho quebrado, porque nenhum teste o alcançava.

Isto é a demonstração do que o §6 do documento de desenho já declarava: **verde na
suíte não é verde nos caminhos que a suíte não alcança.** O aviso estava escrito antes
de o bug aparecer, e o bug apareceu exatamente onde o aviso apontava.

**Verificado depois do conserto**, e sem tocar a rede da USP:

- `initialize` por stdio responde `{"name": "usp-mcp-moodle", "version": "0.1.0"}`,
  protocolo `2024-11-05`.
- `tools/list` devolve uma ferramenta, `o_que_vence`, com `dias` (int, default 14) e
  `limite` (int | null) no schema.
- `python -m usp_mcp.moodle.server --auto-verificar` confere ferramenta, `.env`,
  presença do token (forma, nunca valor), SDK, e que o `inputSchema` declarado casa com
  a assinatura que o adaptador registra — a divergência que só apareceria em uso real.

**O que continua não verificado:** `tools/call`. Ele fala com a USP, e a rede da USP não
é alcançável do sandbox (§1.1). É a última coisa que falta, e só roda no terminal do
dono.

### 31/08/2026 — o MCP respondeu com dado real; §1.1 estava errado para este ambiente

**A fatia vertical funciona ponta a ponta.** `o_que_vence` chamada por um cliente MCP de
verdade, pelo `.mcp.json` versionado, devolveu 6 vencimentos reais em 14 dias — PTC3360,
PSI3472, PME3344 e PTC3314 — em 767 caracteres de texto. É o critério 2 do §5 cumprido de
fato: uma chamada do ponto de vista do modelo, resposta que cabe em pouco contexto. O
`tools/call`, último caminho não verificado do registro anterior, fecha aqui.

**§1.1 estava errado para este ambiente, e o erro custou trabalho.** O documento afirmava
como fato que a rede da USP não é alcançável do sandbox, e isso foi repetido em várias
decisões desta sessão sem nunca ter sido medido aqui. Medição: DNS resolve
(`edisciplinas.usp.br` → `200.144.235.136`), TCP/443 conecta, HTTPS público devolve `200`,
nenhuma variável de proxy no ambiente. A afirmação continua válida para o sandbox em nuvem
do Cowork; **não** vale para o Claude Code na máquina do dono. §1.1 e o item 9 do
`CLAUDE.md` reescritos.

O que a correção muda no desenho: **não é a rede que separa uma sessão de agente do teste
real, é a credencial.** O token é pessoal e cada chamada fica no log da conta. A camada
`live` atrás de `USP_MCP_LIVE=1` continua certa — por consentimento do dono, não por
limitação de infraestrutura. Registro fica como aviso: fato herdado de documento e nunca
remedido é indistinguível de fato verificado, e este atrasou a verificação de ponta a ponta
sem necessidade.

**A fixture de erro existe** (`fixtures/moodle/erro_invalidtoken.json`, 142 B). Capturada com
`wstoken=""` — token propositalmente vazio, que não usa credencial e não toca conta nenhuma.
Fecha a limitação declarada no §6 do documento de desenho, para este modo de falha. A
resposta real:

- HTTP **200** com corpo de erro — confirma a decisão de checar o corpo e não o status.
- `errorcode: invalidtoken`, `message: "Token inválido - token não encontrado"`.
- Sem `debuginfo`, sem `backtrace`. Três chaves só.
- **`exception: core\exception\moodle_exception`**, com namespace — não o `moodle_exception`
  pelado que os testes montados à mão supunham. O cliente passa ileso porque casa em
  `errorcode` e nunca em `exception`; T52 agora trava esse critério.

Os outros modos de falha (`accessexception`, HTML de manutenção com 200, timeout) seguem
sendo contrato de camada, com a forma real não verificada.

Suíte: **98 offline + 2 live**, com T52 novo.

### 31/08/2026 — limite silencioso de 20 no calendário: bug real, corrigido

**O `limitnum` do `core_calendar_get_action_events_by_timesort` tem default 20, e a API
não avisa que parou.** Medido na mesma janela de 365 dias: **20 eventos sem o parâmetro,
30 com `limitnum=50`**. A `o_que_vence` não mandava `limitnum` — então perdia dez entregas
reais e ainda reportava `truncado=False`.

É o Invariante 7 sendo violado pelo código escrito para respeitá-lo, e vale registrar por
que passou: **a suíte não podia pegar.** O duplo de cliente devolve o que o teste manda, e
o corte acontecia do lado do Moodle. Todas as asserções de truncamento olhavam a saída;
nenhuma olhava o parâmetro enviado — que era onde o defeito morava. T53 agora asserta sobre
o parâmetro, T54 sobre a declaração do teto, T55 sobre o aviso não ser decorativo.

**Correção:** manda `limitnum=50` (o teto do serviço) e, quando a resposta vem com o teto
cheio, declara na saída que pode haver mais. A API não informa se há mais depois do último
item, então declarar a dúvida é a única saída honesta — presumir que acabou é o bug de novo.
Verificado contra a API real: a janela de 365 dias passou a devolver 30, `truncado=False`.

**O teto é 50**, e isso saiu de um erro capturado: `limitnum=-5` responde
`"Limit must be between 1 and 50 (inclusive)"`.

### 31/08/2026 — `errorcode` nem sempre é um código

Fato da API que contraria o nome do campo, e que só apareceu ao capturar erro de verdade.
Duas fixtures novas, ambas na função da allowlist, read-only (Regra de Ouro §3.1):

| Fixture | `errorcode` | `message` |
|---|---|---|
| `erro_invalidparameter.json` | `invalidparameter` | `Valor inválido de parâmetro detectado` |
| `erro_limite_fora_da_faixa.json` | `Limit must be between 1 and 50 (inclusive)` | `error/Limit must be...` |

No segundo, **`errorcode` é uma frase em inglês, não um identificador**, e o `message` vem
prefixado de `error/` — sinal de que o Moodle não achou a string de idioma correspondente.
Quem tratar `errorcode` como enum quebra aqui.

O cliente sobrevive porque compara por igualdade exata com `invalidtoken` e repassa o resto
cru (Invariante 6). T56 trava que `invalidparameter` **não** vire `TokenInvalido` — as duas
respostas têm a mesma forma de três chaves, e um casamento por "contém `invalid`" mandaria
renovar um token que está perfeito. T57 trava o critério contra o `errorcode` que é frase.

**Não capturáveis sob demanda, e continuam sem forma verificada:** HTML de manutenção com
HTTP 200 (exige a USP em manutenção) e timeout (exige a USP fora do ar). Os testes desses
dois seguem assegurando contrato de camada, e é o máximo que dá para afirmar.

Suíte: **103 offline + 2 live**.

### 31/08/2026 — gate de pré-commit, e ele reprovou a si mesmo primeiro

`scripts/gate.sh` fecha o `<TODO>` do §4 do `CONVENTIONS.md` e do §3 do `CLAUDE.md`.
Três checagens: segredo do `.env` em arquivo rastreado, o cru seguindo gitignorado, e a
suíte offline. A camada `live` fica de fora de propósito — um gate que depende da USP
estar de pé reprova commit por motivo errado, e gasta credencial a cada commit.

**A primeira versão passava sem ter verificado nada.** Ela procurava o `.env` em
`cwd/.env`, e num worktree esse arquivo não existe: o dicionário de segredos saía vazio,
o laço não tinha o que procurar, e a checagem reportava OK. Descoberto plantando o
`MOODLE_TOKEN` de propósito num arquivo rastreado — o gate aprovou.

O detalhe que vale registrar: **é exatamente o mesmo erro que o `conftest` tinha**,
cometido no mesmo dia por quem acabara de consertá-lo. A lição não é "lembre do
worktree", é que **buscar `.env` tem um jeito certo e ele agora está num lugar só**
(`usp_mcp.env.achar_env`). Toda cópia nova do algoritmo é uma chance de repetir isto.

Duas consequências no desenho do gate:

- **Checagem que não pode rodar REPROVA**, e diz por quê. Sem `.env` em lugar nenhum, o
  gate não reporta OK — ele falha dizendo "esta checagem não verificou nada". É o
  Invariante 6 aplicado à ferramenta de verificação.
- **Isenção por par `(variável, arquivo)`, nunca por variável.** `RUCARD_HASH` está
  deliberadamente no `.env.example` e no §1.2 deste documento, porque é o hash embutido
  no app oficial do RUCard e sem ele o §8 não é reproduzível. Isentar a variável inteira
  transformaria o gate em teatro para ela; por par, a mesma hash em qualquer outro
  arquivo reprova — verificado.

**O gate foi verificado sabotando cada checagem uma a uma**, e as três reprovam:
`MOODLE_TOKEN` plantado no README, `RUCARD_HASH` em arquivo não previsto, `.gitignore`
sem a linha do cru, e a `ALLOWLIST` esvaziada. Um gate que não pode falhar não verifica
nada (§6 do `CONVENTIONS.md`), e a única forma de saber é tentando fazê-lo falhar.

Registro adicional, porque a primeira tentativa de sabotagem falhou em ser sabotagem:
desligar a checagem de `BLOQUEIO_PERMANENTE` **não** quebrou nenhum teste, e está certo.
Com allowlist, o default já é negar — a segunda camada do §2.2 documenta o motivo e
protege contra erro futuro NA allowlist, mas não é o que nega hoje. É a arquitetura do
Invariante 2 funcionando como anunciado.
### 31/08/2026 — suíte do Jupiter escrita antes da implementação; o gate passa a existir

Desenho em `docs/superpowers/specs/2026-08-31-testes-jupiter-design.md`, plano em
`docs/superpowers/plans/2026-08-31-suite-testes-jupiter.md`. **40 funções de teste, 68
casos: 56 falham, 10 passam, 2 pulam, em 0,39 s.** As 56 falhas são todas
`NotImplementedError` — verificado com `--tb=line`, motivo a motivo, não por contagem
de traceback. Os 10 verdes são a guarda de fixture e o teste do próprio gate de rede.

**Escopo: fatia vertical de uma pergunta**, a candidata do §5 ("quantos créditos e qual
o pré-requisito?"). Grade curricular, navegação unidade→curso e horário de turma ficam
de fora. O argumento veio da suíte irmã do Moodle: cobrir três superfícies de uma vez
deixaria os testes vermelhos por semanas, que é TDD no nome e waterfall no comportamento.

**Uma asserção foi desenhada e descartada por medição.** A suíte ia fixar razão de
redução contra o cru. Medida nas duas amostras: 1,73 e 1,98 — e, mais grave, **a razão do
Jupiter é ~1,8×, não os 11,5× do recon**, que comparam DWR com HTML. Contra o próprio DWR
quase não há o que reduzir: o payload *é* a resposta. Bytes por campo varia 68% porque 90%
do peso é texto livre. O que é estável é o núcleo estruturado da saída: 179 B e 164 B,
spread de 9%. A trava de regressão virou **categórica** — o conjunto de chaves da saída é
exatamente o declarado.

Regra que sai disso, e vale para toda asserção futura: **antes de fixar um teste sobre um
número das notas, conferir contra o que ele foi medido.** A suíte do Moodle cometeu o
mesmo erro na mesma noite, com 1000:1 (payload cru vs campos mínimos) contra 76:1 (a
projeção que ela de fato implementa).

**Três achados de ferramenta que custaram medição:**

1. Com o módulo **ausente**, o pytest aborta a coleta (`Interrupted: N errors during
   collection`) e **os testes verdes não rodam**. Daí o esqueleto de `usp_mcp/jupiter/`
   que levanta `NotImplementedError`: ele não decide nada de Fase 2, e faz o vermelho
   virar contável.
2. **Varredura de fonte passa espuriamente contra esqueleto.** Três testes provam uma
   ausência no fonte (nada de `eval`, de token, de choke point); contra arquivo vazio os
   três ficariam verdes verificando nada. Toda leitura de fonte passa por um guarda que
   recusa o sentinela `ESQUELETO-FASE2`.
3. **Construir o objeto sob teste numa fixture do pytest transforma falha em erro de
   setup.** 23 casos vinham como `ERROR` em vez de `FAILED`, o que anulava o ganho do
   item 1. O cliente passa a nascer no corpo de cada teste.

**Gate do projeto passa a existir:** `.venv/bin/python -m pytest`. Fecha o `<TODO>` do §3
do `CLAUDE.md` e os dois do `CONVENTIONS.md`, que estavam abertos desde o bootstrap.

**Acordos com a suíte do Moodle**, para as duas não colidirem no merge: `tests/{jupiter,
moodle}/` simétricos; `server.py` por subpacote e nenhum na raiz; `@pytest.mark.live` +
`USP_MCP_LIVE=1` com skip explicado; eixos `politica`/`contrato`/`live`.

**Continua aberto:** a discrepância `codcur` 3032 vs 3033, que T33 declara e não resolve;
o pareamento disciplina↔requisito, nunca amostrado junto na Fase 1 — T31 testa a
composição de duas chamadas e diz isso no próprio código; o charset do percent-encoding
do DWR (§8 do recon), por isso T15 asserta sobre o observável e não sobre bytes de
acento; e o Invariante 8, que não é testável em código.

**O que esta decisão NÃO abre:** a Fase 2. Nenhuma função tem corpo. A suíte vermelha é a
especificação que a implementação vai ter que satisfazer, e o §4.10 continua valendo.

### 31/08/2026 — Fase 2 do Jupiter implementada contra a suíte

A suíte vermelha registrada acima virou especificação e foi satisfeita. **173
verdes, 4 pulados** (os dois canários `live` de cada trilha), 0 falhas. **Nenhum
teste foi alterado para passar** — a regra do §6 do `CONVENTIONS.md` aplicada ao
caso em que a tentação é máxima, porque quem escreveu a suíte foi a mesma sessão.

Módulos: `usp_mcp/jupiter/{erros,politica,dwr,cliente,ferramentas,server}.py`.
`.mcp.json` registra `usp-jupiter`.

**A allowlist do Jupiter tem duas camadas, e a segunda não é redundante.** O
`ControlePublicoDWR` recebe o nome da consulta como **primeiro parâmetro de
string** — é RPC genérico. Filtrar só a consulta não bloqueia nada, porque
`executarBatch` faz a consulta viajar dentro do lote: é o análogo exato do
`tool_mobile_call_external_functions` do Moodle, registrado no §9 acima. Por isso
o bloqueio é por **método** e ignora `permitir_escrita` — não há flag que libere.

**O envelope DWR é lido por parser, não por conversão de regex.** A tentação era
transformar chave-sem-aspas em JSON com uma substituição. A resposta carrega
ementa e bibliografia escritas por docentes: um texto contendo `, algo:`
corromperia o valor **em silêncio**. O parser distingue o que está dentro de
string do que é estrutura — que é precisamente o que o regex não faz. E lê sem
executar: o corpo vem da rede.

**Assimetria com o Moodle que vale registrar, porque é o §6 aparecendo na suíte.**
A fronteira MCP do Jupiter é testável **ponta a ponta offline** (T44): sem
credencial, basta injetar o transporte e a fixture responde. A do Moodle não
consegue — falta um token que não pode entrar em teste. É a mesma razão pela qual
o §6 mantém o Jupiter como candidato a servidor hospedado e o Moodle como
entrypoint local. Falar stdio hoje, no Jupiter, é conveniência de canalização,
não decisão fechada.

**O que a ferramenta declara não saber**, em vez de omitir (Invariante 7): sem
`codcur`+`codhab` ela **não afirma** que não há pré-requisito — diz que não
consultou, porque a resposta é condicional ao curso (§5.2 do recon). Quando
recebe 3032 ou 3033, avisa que os dois códigos aparecem para a mesma habilitação
em superfícies diferentes e que a relação **não foi verificada** (§5.1). E a
descrição que o modelo lê diz explicitamente que a ferramenta **não** traz
horário, sala nem vagas — sem isso o modelo promete o que ficou fora da fatia.

**Continua aberto:** horário de aula (scraping de uma amostra só, com manutenção
semestral não assumida); grade curricular e navegação unidade→curso, que são as
fatias seguintes; o significado de `verdis`; o charset do percent-encoding do
DWR; e o Invariante 8, que não é testável em código.

**Verificado contra a USP.** `USP_MCP_LIVE=1 ... -m live` em `tests/jupiter`:
**2 passed, 1 skipped**. Medido em separado para não confiar só no verde: HTTP 200
em 117 ms (PSI3323, 3.707 B) e 196 ms (PME3344, 2.448 B) — os mesmos tamanhos das
fixtures, o que confirma que a forma não mudou desde a Fase 1.

**Fecha um "não verificado" do §8 do recon.** O pareamento disciplina↔pré-requisito
nunca tinha sido amostrado junto, e o T31 declara isso porque testa a composição com
stubs. Exercitado ao vivo: `MAT2454` no curso `3033-0` devolve `MAT2453 (Cálculo
Diferencial e Integral I)`, com créditos 4+0 e 60 h calculadas. A cadeia de duas
chamadas DWR funciona contra a USP, não só contra fixture.

**Erro desta sessão, registrado porque quase virou fato.** Eu afirmei em três
documentos que os canários não podiam rodar "porque a sessão não alcança
`uspdigital.usp.br`, §1.1" — e o §1.1 **já estava corrigido** desde 31/08: a
restrição vale para o sandbox em nuvem, não para o Claude Code na máquina do dono,
que é onde a sessão rodava. Li a metade errada da seção e transformei uma limitação
inexistente em ressalva escrita. A lição não é sobre rede: **uma restrição de
ambiente citada de memória vale menos que um `curl`**, e o custo de conferir era um
comando.

### 31/08/2026 — o `main()` do Jupiter ganha teste, e a sabotagem achou um teste fraco

O backlog registrava desde a implementação da Fase 2 que o adaptador stdio do
Jupiter não tinha teste — o mesmo buraco que, na trilha do Moodle, escondeu um
`main()` escrito contra a API antiga do SDK com a suíte **99/99 verde**. Fechado
por `tests/jupiter/test_server_stdio.py` (T45-T48): a suíte roda `main()` de
verdade contra o SDK instalado, substituindo **só** `run()`, que bloquearia no
stdin. Tudo antes dela é código de produção casando com o SDK real.

**Cada asserção foi verificada por sabotagem**, porque teste escrito depois da
implementação passa na primeira tentativa e isso não prova nada:

| Sabotagem na produção | Quem ficou vermelho |
|---|---|
| `from mcp.server import Server` (o bug histórico do Moodle) | T45, T46, T47 — `'Server' object has no attribute 'tool'` |
| assinatura do adaptador perde `ingles` | T46 — schema derivado ≠ declarado |
| `run(transport="sse")` | T45 |
| mensagem de SDK ausente perde o comando que cura | T48 |
| `{"sigla": codhab}` no mapeamento de parâmetros | **ninguém** |

**A quinta linha é o achado.** O dublê de transporte devolve a fixture aconteça o
que acontecer, então consultar a disciplina `"0"` ainda formatava PSI3323 e o teste
seguia verde. É o **mesmo erro** do limite silencioso de 20 do calendário,
registrado neste §9 mais acima: asserção sobre a saída onde só a asserção sobre o
que **saiu no fio** significa alguma coisa. T47 passou a olhar `string:PSI3323` no
corpo da requisição, e aí a sabotagem virou vermelha. A regra virou o item 11 do
§4 do `CLAUDE.md`.

Verificado nos dois cenários que importam: **177 passed, 4 skipped** com o SDK
instalado, e **174 passed, 7 skipped** com o pacote `mcp` desinstalado de verdade
— não simulado. A distinção não é preciosismo: a primeira tentativa de simular
"SDK ausente" plantou um módulo que levanta `ImportError`, e `pytest.importorskip`
**não pula** nesse caso, de propósito, para não mascarar instalação quebrada.
Pacote inexistente levanta `ModuleNotFoundError` e pula. Simulação errada teria
"provado" o contrário do fato.

**O que continua sem teste:** `run()` em si, isto é, o handshake stdio real. Isso
testaria o SDK, não este projeto, e a verificação que importa segue sendo plugar
num cliente e perguntar. O `main()` do **Moodle** continua descoberto pelo mesmo
motivo de sempre — falta um token que não pode entrar em teste. A assimetria é a
mesma do §6, e agora ela tem uma consequência medida: a fronteira do Jupiter é
testável ponta a ponta offline, a do Moodle não.

### 31/08/2026 — estado sai do `CLAUDE.md`; ele guarda regra, não notícia

O `CLAUDE.md` afirmava, em negrito e no §1, que a Fase 2 não tinha começado e que
**não havia servidor MCP nenhum** — enquanto dois rodavam, verificados contra a USP,
com o §9 registrando os dois. O `README.md` dizia o mesmo. Ficaram assim por dois
dias e nenhuma das sessões que os leram notou: é a falha silenciosa característica
de documento de estado, porque nada quebra.

**A causa não é desatenção, é lugar errado.** O `CLAUDE.md` é lido por toda sessão
antes da primeira pergunta e é o único documento que ninguém revisita ao terminar
uma tarefa — o §9 recebe a decisão, o backlog recebe o achado, e o §1 do
`CLAUDE.md` fica falando do mundo de dois dias atrás para quem ainda não sabe o
suficiente para desconfiar.

**Decidido:** o `CLAUDE.md` não guarda estado. Nada sobre fase aberta, o que já foi
construído, quantos testes passam. Ele guarda o que não envelhece — produto em 30
segundos, onde as coisas moram, comandos, regras críticas, fluxo. O estado vive em
quatro lugares que já têm dono e ritual de atualização: o §9 (decisão, com o dado),
o `README.md` (um parágrafo para quem chega), o backlog (dívida aberta) e o
`./scripts/gate.sh` (o que de fato está verde, em segundos e sem confiar em texto).

**Descartado:** manter o estado no `CLAUDE.md` com nota de "atualize ao terminar".
O repositório já tinha essa instrução, em forma de Definição de Pronto, e ela não
impediu nada — instrução escrita não compete com o fato de que ninguém reabre o §1
ao fechar uma tarefa. Regra que depende de lembrança perde para regra que depende
de lugar.

### 31/08/2026 — a segunda ferramenta do Moodle é material, e a pergunta veio do dono

As três candidatas que sobravam do §5 foram postas ao dono com o custo medido de
cada uma. A resposta descarta duas e reescreve a terceira:

- **Nota** — "eles usam pouco". Descartada apesar de ser a chamada mais barata do
  projeto por unidade de informação (70 cursos em ~870 tokens). Barato não é
  critério; o §5 pede a pergunta que o dono **faz de verdade**.
- **Aviso do professor** — "não queria usar". Descartada.
- **"Já entreguei"** — "devo usar um pouco mais". Fica como candidata, não como
  próxima.
- **Material** — a pergunta real, e não estava na forma em que o §5 a registrava.
  Não é "onde está o PDF da aula de hoje": é **descobrir os arquivos do espaço da
  disciplina**, porque muitos são regras da disciplina, listas de exercícios e
  provas anteriores. O valor está no acervo, não no arquivo de hoje.

**Medido antes de desenhar**, em cima da captura da Fase 1 e sem gastar chamada
nova da conta (`course_contents_142033.json`, 58.049 B). Detalhe em
`notas/fase1-moodle.md`:

| | |
|---|---|
| Composição | 22 `resource` + 7 `url` = **29 entradas em `contents`** |
| Mimetype | **19 PDF**, 1 docx, 1 jpeg, 1 octet-stream, 7 sem (os links externos) |
| Cru | 58.049 B, ~14.512 tokens por disciplina |
| **Projetado** | **6.486 B, ~1.621 tokens — 11,2% do cru** |

A projeção é o que torna a ferramenta viável: 1,6k por disciplina cabe folgado,
14,5k não. Varrer as 10 segue inviável (145k) — **sob demanda, uma por vez**, e a
ferramenta exige escopo explícito como toda chamada deste projeto.

**Decidido: duas ferramentas, nesta ordem, não uma.** A primeira lista; a segunda,
depois, traz o conteúdo do arquivo para o modelo ler. O motivo de separar não é
cautela genérica — é que a segunda tem dois problemas não resolvidos que a
primeira não tem, e juntá-las seguraria a que já dá para entregar.

**`fileurl` não carrega o token: 0 de 29 entradas.** A resposta como capturada não
tem segredo dentro. Mas para **baixar**, o token precisa ir junto na URL, e aí o
Invariante 3 morde: devolver URL pronta põe a credencial no contexto do modelo e
em todo log por onde ela passar. Enquanto isso não tiver desenho, a ferramenta de
listagem devolve o que identifica o arquivo, não uma URL autenticada.

**Continua não verificado**, e registrado como tal em vez de suposto: (a) se o
download com token anexado funciona — é o padrão do Moodle, este repo nunca mediu,
e custa uma chamada da conta, que é decisão do dono; (b) se `get_contents` expande
o conteúdo de um `mod_folder` — PSI3323 não tem nenhum, então a amostra não
responde, e uma disciplina que agrupe as listas numa Pasta é exatamente o caso que
importa.

**Descartado:** usar `mod_resource_get_resources_by_courses` ou
`core_search_get_results`. O primeiro é mais estreito e exigiria uma segunda
chamada para os `url`; o segundo não foi testado. `get_contents` já responde em
uma chamada, e a questão do §4 sobre ele fechou em 28/08.

### 31/08/2026 — Fase 2 do RUCard implementada contra a suíte; os três sistemas têm servidor

**Decisão: uma ferramenta, `bandejao`, sobre os quatro RUs da Cidade Universitária.**
Ela responde a pergunta do §5 inteira — "o que tem no bandejão hoje, e onde vale a pena
almoçar?" — em uma chamada de ferramenta, com os quatro RUs lado a lado. A comparação
**não** virou uma segunda ferramenta: "o que tem" e "onde vale a pena" são a mesma
pergunta feita por alguém com fome, e separá-las obrigaria o modelo a duas chamadas para
uma decisão.

**O que sustenta, medido em 31/08/2026** (dado público, sem credencial pessoal — segunda
captura, quatro dias depois da Fase 1):

| Fato | Medida |
|---|---|
| `/menu/{6,7,8,9}` | HTTP 200; 2.928 / 2.303 / 3.084 / 3.624 B |
| Semana devolvida na segunda 31/08 às 19:22 | **31/08→06/09** (a de 27/08 era 24/08→30/08) |
| `/restaurants` | 27.661 B, **byte-idêntico** ao de 27/08 |
| `GET` na mesma rota | HTTP 500, `text/html`, 3.240 B de HTML do Tomcat |
| Grafia de fechado | 6 `Fechado`; 7, 8 e 9 `FECHADO` — estável nas duas semanas |
| HTML ou ` - ` no `menu` | zero em 2 semanas × 7 dias × 2 refeições × 4 RUs |
| Cru para responder um dia nos 4 RUs | 39.615 B (~9.900 tokens) |
| Saída da ferramenta, pior caso (4 RUs × 2 refeições) | **3.367 B** estruturados, **1.929 B** de texto em 23 linhas |
| Razão de redução | **11,8x** (17,9x pedindo só almoço; 40,8x pedindo um RU) |

Esta é a razão de redução que a trilha do Jupiter não conseguiu ter: lá o payload DWR
*era* a resposta e a razão real ficou em ~1,8x. Aqui 6/7 do `/menu` é semana que ninguém
pediu, e o catálogo inteiro é tabela de apoio.

**Decisão: o cache tem duas regras, não uma.** TTL protege a USP (3 h para cardápio, 7
dias para catálogo — colado na taxa de mudança do dado, Invariante 5); validação por data
protege a resposta. A rota não aceita parâmetro de data, e a virada da semana não tem hora
conhecida: com TTL sozinho, uma pergunta na segunda-feira receberia o cardápio da semana
passada **com cara de resposta certa**. Quando o dia pedido é posterior à semana que está
em cache, o cliente revalida — **uma vez por janela de TTL**, para que uma pergunta sobre
uma data que a API nunca vai cobrir não vire uma requisição por pergunta. O par de
fixtures do mesmo RU em semanas diferentes (`menu_6.json` e `menu_6_semana_31-08.json`)
existe para que esse teste seja de comportamento, não de dublê.

**Decisão: `FECHADO` tem três leituras, e a ferramenta as separa.** O `/menu` diz a mesma
palavra para três coisas diferentes, e o cruzamento com `workinghours` as distingue:

- `nao_serve` — não há horário publicado para essa refeição nesse dia da semana. O detalhe
  diz se é *em dia nenhum* (o 7 no jantar) ou *só nesse dia* (o 6 no sábado). A diferença
  decide entre voltar amanhã e procurar outro RU.
- `fechado` — há horário publicado para aquele dia da semana **e** o cardápio está
  fechado: feriado, greve, manutenção. É a única situação em que "fechado hoje" é a
  informação certa. Nenhuma das duas semanas capturadas tem um caso (nenhum feriado caiu
  nelas), então o teste desta situação usa entrada fabricada, com o mínimo alterado, e diz
  isso no próprio teste.
- `sem_cardapio_publicado` — só café da manhã: o horário existe, o cardápio não é
  publicado. Responder `[]` aqui seria ler como "não tem café" (Invariante 6).

**Decisão: a opção do dia não é chamada de vegetariana sem a marca.** 100% das refeições
abertas nas duas semanas têm uma linha `Opção: …`; a marca `(V)` aparece em algumas (5 de
10 no RU 6 na semana da Fase 1, 2 de 10 na seguinte, **zero** nos RUs 7, 8 e 9). A saída
traz `opcao` e `opcao_vegetariana_marcada` separados: rotular toda opção como vegetariana
seria afirmar o que a fonte não diz, e é o tipo de erro que só aparece no prato.

**Descartado:** os outros 14 RUs (fora do recorte do §1.2 — a allowlist os nega com motivo
que distingue "existe e está fora de escopo" de "id não verificado"); histórico de semanas
anteriores (não existe na API — prometer exigiria persistir por conta própria, outro
escopo); saldo, extrato e recarga do cartão (área autenticada nunca mapeada — o §2.2 não
deixa adivinhar rota de escrita, e `permitir_escrita` não libera nada aqui porque não há
nada mapeado para liberar); latitude, telefone e foto do RU na saída (ninguém pergunta a
coordenada do bandejão, e todo campo é token gasto em toda resposta).

**Verificado.** `./scripts/gate.sh`: **253 passed, 6 skipped**, 0 falhas — 80 testes novos
(R1–R44, com desdobramentos). Camada `live` do RUCard: **2 passed, 1 skipped**. Handshake
stdio real contra o servidor: `initialize` → `tools/list` → `tools/call` devolveu o
cardápio de hoje dos quatro RUs em 975 caracteres. `--auto-verificar` passa nos três
servidores. O `.mcp.json` registra `usp-rucard`.

**Um furo de Invariante 7 achado na revisão da própria implementação.** Quando
NENHUM RU publica o dia pedido, o aviso da semana aparecia; quando só UM não publicava
— porque ficou na semana anterior —, ele saía da lista **calado**. Três RUs respondidos
e o quarto sumido é a forma mais difícil de notar de um limite silencioso: nada na
resposta indica que faltou alguém. Consertado com teste primeiro (R27b), que exigiu uma
segunda fixture pareada (`menu_9_semana_31-08.json`), e o aviso passou a nomear o
restaurante e a semana que ele publicou, agrupado por semana para não repetir quatro
vezes a mesma frase.

**O gate reprovou este commit primeiro, e estava certo.** A primeira versão do teste R8
trazia o valor real da hash como agulha de busca. A isenção registrada no §9 é por **par**
(variável, arquivo) e vale só para `.env.example` e `SPEC1.md` — o gate apontou
`RUCARD_HASH em tests/rucard/test_politica.py` e barrou. O conserto deixou o teste
melhor: em vez de procurar uma constante escrita à mão, ele procura no fonte a hash que
está **realmente** configurada, falha com `pytest.fail` (e não com `assert x not in y`,
que imprimiria o valor nos dois lados da comparação) e reprova quando a checagem não pôde
rodar. Verificado por sabotagem: com a hash plantada em `catalogo.py`, o teste falha.
Lição registrada porque é reutilizável: **um teste que procura um segredo é um lugar onde
o segredo pode vazar.**

### 31/08/2026 — handshake stdio compartilhado, e o schema que o modelo lia era mais pobre que o escrito

**O furo que motivou.** O backlog registrava três vezes o mesmo achado: o adaptador
`main()` de cada servidor não tem teste, e verde na suíte não é verde nele. Na trilha do
Moodle isso escondeu um `main()` escrito contra a API antiga do SDK com 99/99 testes
passando. Três repetições deixaram de ser dívida e viraram sintoma: a cura não era mais
uma linha de backlog, era um teste.

**Decisão: um teste de handshake, N servidores, por descoberta.** `tests/handshake/` sobe
cada `usp_mcp/*/server.py` como processo, fala JSON-RPC pelos pipes e compara o que sai no
fio com o que `listar_ferramentas()` declara. Os servidores saem de um glob, não de uma
lista escrita à mão: um quarto sistema nasce coberto, em vez de nascer com o mesmo furo
pela quarta vez. H9 falha se a descoberta vier vazia — é o R1/T1 aplicado a esta suíte.

Isto desmente por escrito a justificativa que estava na docstring dos três `main()`:
*"exercitar isto exigiria um cliente MCP falso, o que testaria o SDK e não este projeto"*.
As duas metades estavam erradas. O cliente é JSON-RPC por um pipe, ~90 linhas, e não é
falso — o processo sob teste é o real. E o que se testa não é o SDK: é se **o nosso
adaptador casa com o SDK que está instalado**, que é literalmente o que quebrou uma vez.

**O achado que só apareceu quando o teste existiu.** O SDK **não usa** o `inputSchema` que
`listar_ferramentas()` declara: ele deriva o schema que o modelo vê da **assinatura** da
função registrada em `main()`. Medido nos três servidores, antes do conserto:

| O que estava declarado | O que o modelo recebia |
|---|---|
| `dia`: "'hoje', 'amanhã' ou uma data como 26/08/2026…" | `{"title": "Dia", "type": "string"}` |
| `refeicao`: enum `["almoco","jantar","cafe","todas"]` | `{"title": "Refeicao", "type": "string"}` |
| `restaurantes`: enum `["6","7","8","9"]` | `{"title": "Restaurantes", "type": "array"}` |

Ou seja: **toda descrição de parâmetro dos três servidores e todo `enum` do RUCard eram
texto escrito com cuidado e entregue a ninguém.** O caso do `enum` tem consequência
concreta: sem ele, o modelo não sabe que só existem quatro RUs, inventa um id e recebe
negativa da allowlist depois de uma requisição inútil — o erro certo pela via mais cara.
E nada disso aparecia no `--auto-verificar`, que comparava o schema declarado com a
*assinatura*, e não com o que sai no fio.

**Decisão: o schema declarado vira a fonte, e a ponte é explícita.** `usp_mcp/adaptador.py`
lê a descrição do `inputSchema` declarado e a prende à anotação
(`Annotated[tipo, Field(description=…)]`), resolvendo a anotação como objeto — os
servidores usam `from __future__ import annotations`, que transformaria tudo em string. O
tipo (inclusive `Literal` para enum) fica na assinatura do adaptador, à vista. Descartado:
gerar o tipo a partir do JSON Schema. Seria um conversor para três casos conhecidos, e o
que mantém os dois lados iguais passa a ser verificação (H6–H8), não geração.

`listar_ferramentas()` **continua** sendo declaração pura, chamável sem o SDK — é
invariante deste projeto, e é o que deixa as três suítes testarem vocabulário sem
dependência de protocolo. O que mudou é que agora existe quem verifique que a declaração
chega ao outro lado.

**Verificado por sabotagem**, um defeito de cada tipo, com o restante do repo intacto:

| Sabotagem | Resultado |
|---|---|
| `main()` do Moodle contra a API antiga do SDK (o bug histórico) | 8 falhas — o handshake inteiro daquele servidor |
| Adaptador do Jupiter registra `disciplina_v2` | 5 falhas, 3 passam (o servidor sobe; o contrato não bate) |
| Ponte `anotar` removida do RUCard | 2 falhas — exatamente H7 e H8 |

A graduação importa: os testes discriminam o tipo de defeito em vez de ficarem vermelhos
juntos. E na primeira rodada da sabotagem o caso mais importante apareceu como `ERROR` e
não como `FAILED`, porque a fixture que sobe o processo levantava — o §4 do
`CONVENTIONS.md` já registrava que erro de setup não é vermelho honesto. A fixture passou
a **guardar** o diagnóstico, e quem reprova é o teste.

**Custo.** Um processo por teste custava 67 s e teria feito o gate pesar mais que a suíte
inteira; um processo por servidor, com escopo de sessão, custa ~6 s para 26 testes. O gate
passou de 250 para **283 verdes** (279 desta trilha, mais os T45-T48 do teste em processo
do Jupiter, que entrou na `main` em paralelo e **não** é substituído por este: aquele
alcança o corpo enviado e a mensagem de SDK ausente, este alcança o fio), e continua sem
tocar a rede da USP: `initialize` e
`tools/list` são respondidos sem passar por `chamar_ferramenta`, que é onde mora qualquer
credencial. Por isso esta camada roda no gate e não atrás de `USP_MCP_LIVE=1`.

**Erro de processo desta sessão, registrado porque custou trabalho.** Sabotei os
servidores para verificar os testes **sem ter estagiado o conserto**, e o `git checkout`
que desfaz a sabotagem levou o conserto junto — a suíte voltou a ficar vermelha por um
motivo que eu já havia consertado. A regra que sai daí: **sabotagem se faz sobre árvore
limpa** (`git add` antes), senão a restauração desfaz o que se quer manter.

### 31/08/2026 — `material` implementada; a allowlist vai de 1 para 4, com motivo

Segunda ferramenta do Moodle, contra a suíte escrita antes (20 vermelhos por
`NotImplementedError`, depois satisfeitos). **Nenhum teste foi afrouxado para
passar** — os dois que ficaram vermelhos de propósito, T7 (tamanho da allowlist)
e T42 (número de ferramentas), são travas que existem justamente para forçar esta
entrada, e foram atualizados **depois** dela, não em vez dela.

**A allowlist cresce de 1 para 4, e o motivo é uma tradução.** O modelo recebe
"PSI3323"; o Moodle só entende `courseid`. Resolver isso custa duas funções além
da que responde:

| Função | Para quê | Cru | Projetado |
|---|---|---|---|
| `core_webservice_get_site_info` | `userid` a partir do token | 31.386 B | — |
| `core_enrol_get_users_courses` | a lista, para resolver a sigla | 104.712 B | 7.816 B (74) / 1.026 B (semestre) |
| `core_course_get_contents` | a resposta | 58.049 B | ~6.486 B |

As três são leitura e nenhuma está no bloqueio permanente do §2.2. **A resposta
final da ferramenta sai em ~727 tokens** — menor que a projeção JSON porque o
texto formatado é mais compacto que a serialização.

**Cache obrigatório, não otimização.** Buscar 104 kB de matrículas a cada
pergunta sobre material é reconfirmar a cada pergunta um dado que muda uma vez
por semestre — o Invariante 5 pede TTL colado à taxa de mudança do dado, e daí
`TTL_DISCIPLINAS`. O relógio é injetável para o teste verificar a REGRA e não o
valor da constante.

**A regra de segurança desta fronteira veio de medição, não de princípio.** Os 22
módulos `resource` apontam para `edisciplinas.usp.br/webservice/pluginfile.php`;
os 7 `url` apontam para fora (YouTube, Google Docs, sites de fabricante). Baixar
do primeiro grupo exige anexar o token na URL. Então: **nome, tipo, tamanho e
data do arquivo interno saem; o endereço dele, não** — emiti-lo põe a credencial
a um passo do contexto do modelo e de todo log por onde a resposta passar
(Invariante 3). Link externo sai inteiro, porque recusar tudo seria esconder o
que se sabe. T68 e T69 são os dois lados dessa regra.

**Duas sabotagens sobreviveram à primeira versão da suíte**, e as duas dizem a
mesma coisa que este §9 já registrou duas vezes:

1. `courseid=142033` fixo no lugar da resolução **passou** — porque 142033 *é* o
   courseid de PSI3323, e o teste pedia uma disciplina só. Corrigido pedindo
   duas: valor fixo não acerta as duas. É o mesmo erro do T47 do Jupiter, no
   mesmo dia, depois de eu ter escrito a lição.
2. As outras oito sabotagens (URL interna emitida, ambiguidade resolvida
   sozinha, cache eterno, `userid` chutado, `author` na saída, busca que não
   filtra, aviso suprimido, ferramenta não registrada) ficaram vermelhas na
   primeira tentativa.

**Fecha dois itens do backlog de manhã.** `chamar_ferramenta` do Moodle passou a
aceitar cliente injetável — era isso, e não a falta de token, que impedia o teste
ponta a ponta desta fronteira. Com a injeção, T78-T81 rodam o `main()` do Moodle
contra o SDK real **sem credencial nenhuma**, incluindo `call_tool("material")`
atravessando até a fixture. O §9 de mais cedo registrava a causa errada.

**Limites declarados.** A amostra é PSI3323 e só ela, por decisão do dono: a
projeção de 11,2%, a contagem de 16 seções e a mistura de tipos valem para essa
disciplina, não para as dez. `mod_folder` não aparece nela, então não se sabe se
`get_contents` expande pasta. E a higienização embaralha `fullname`, o que torna
o casamento por **nome** de disciplina não exercitável contra a fixture — T62
testa a regra contra lista sintética e diz isso.

### 31/08/2026 — `material` ao vivo: funciona, e o timeout de 15 s era bug

Primeira execução contra a USP de verdade. **A ferramenta funciona** — e a
primeira tentativa falhou, pelo motivo que nenhum teste offline alcança.

**Bug real, achado na primeira chamada.** `core_enrol_get_users_courses` levou
**14,7 s** para devolver as 74 matrículas (104 kB), contra um
`_TIMEOUT_PADRAO_SEGUNDOS` de **15 s**. Dois por cento de margem: estourou. A
suíte estava 201/201 verde, porque o transporte HTTP real é um dos caminhos que
ela declaradamente não alcança (backlog, 31/08). Elevado para 60 s, com T82
travando o piso em 45 — e o teste guarda o **motivo medido**, não o número, para
que baixar isso exija remedir. O erro que apareceu ao usuário foi legível e disse
a cura, que é o Invariante 6 fazendo o que promete.

**Medido nas três disciplinas, com o conserto:**

| | itens | resposta | tempo |
|---|---|---|---|
| PSI3323 | 29 | ~725 tokens | 0,4 s |
| PTC3314 | 52 | ~849 tokens | 0,4 s |
| PTC3360 | 38 | ~1.154 tokens | 0,3 s |

A projeção se sustenta fora da amostra: nenhuma das três passou de ~1,2k tokens,
e `get_contents` de uma disciplina responde em menos de meio segundo. O custo da
ferramenta é dominado inteiramente pela lista de matrículas — que é justamente o
que o cache de semestre resolve.

**Refuta uma leitura da "fração viva".** O §9 de 28/08 mediu 4 de 10 disciplinas
com entrega e 6 aparecendo no calendário, e isso foi lido como medida de uso.
**PTC3360 tem zero entregas e 38 arquivos publicados.** Entrega e material são
eixos diferentes de vida: uma disciplina pode não usar o Moodle para avaliar e
usá-lo inteiro para distribuir. Isso ataca o item que `notas/fase1-moodle.md`
deixou explícito ("falta medir material postado para as 10") — três medidas, não
dez, mas as três dizem a mesma coisa.

**`mod_folder` não apareceu em nenhuma das três.** Modnames observados ao vivo:
`resource`, `url`, `forum`, `quiz`, `assign`, `choicegroup`. A questão de se
`get_contents` expande pasta **continua aberta** — não observar em três amostras
não é observar ausência, e é exatamente o erro que este §9 já registrou hoje
(ausência de arquivo não é ausência de fato).

**Deriva de dado, observada de graça.** PSI3323 tinha 32 módulos com 1 `assign`
na captura de 28/08 e tem 31 sem `assign` hoje. O espaço da disciplina muda
durante o semestre — a fixture é retrato, não espelho, e teste que dependa da
contagem exata envelhece.

### 31/08/2026 — acento: a normalização apagava a letra em vez de dobrá-la

Achado ao vivo, na primeira pergunta que o dono fez em linguagem natural em vez
de sigla. `_normalizar` fazia `re.sub(r"[^A-Z0-9]", "")` direto: `"Eletrônica"`
virava `ELETRNICA` e `"eletronica"` virava `ELETRONICA`. Os dois deixavam de
casar entre si — e quem pergunta em português digita sem acento.

Corrigido com `unicodedata.normalize("NFD", ...)` **antes** do filtro: o NFD
separa "ô" em "o" + marca combinante, e aí o filtro descarta só a marca. T83 fica
vermelho se alguém remover o NFD por parecer supérfluo — verificado por sabotagem.

**A suíte não pegava, e o motivo é estrutural:** a higienização do §3.3 embaralha
`fullname`, então nenhum teste tinha nome de disciplina real para casar. O bug
morava exatamente no vão entre "o que a fixture preserva" e "o que o usuário
digita". T83 testa contra lista sintética, que é o que dá para fazer sem
desfazer a higienização.

**Confirmado ao vivo depois do conserto:** `"eletronica"` passou de "não achou"
para ambíguo com três candidatas (`PSI3321-REOF-2025`, `PSI3322-2026-REOF`,
`PSI3323-2026`) — que é a resposta certa, e é o Invariante 6 não escolhendo
sozinho. `"laboratorio de eletronica"` resolve direto.

**Continua não resolvendo abreviação:** `"lab de eletronica"` não acha, porque
"lab" não é pedaço de "laboratorio". Casamento aproximado é decisão de escopo,
não correção de bug, e fica fora até alguém pedir.

**Erro de processo desta sessão, registrado porque quase custou a correção.**
Rodei `git checkout` num arquivo com a correção ainda não commitada, para
desfazer uma sabotagem — e apaguei o conserto junto. O teste denunciou na hora
(T83 vermelho). A lição não é sobre git: **sabotagem tem que ser desfeita pelo
inverso exato da sabotagem**, nunca por um comando que restaura "o estado
anterior" quando o estado anterior inclui trabalho novo.


### 31/08/2026 — o PR foi mergeado no meio do trabalho; 4 commits ficaram órfãos

Registrado porque é falha de processo, não de código, e a próxima sessão pode
repetir.

O PR #10 foi aberto quando a branch tinha **5 commits** e mergeado nesse estado.
A sessão continuou e empurrou **4 commits** para a mesma branch — `material`, os
dois bugfixes e o handoff. Eles foram para a branch e **não** para a `main`: um
PR mergeado não recolhe commit novo. Enquanto isso a `main` andou duas vezes
(RUCard no #11, handshake stdio no #12), e a branch ficou simultaneamente à
frente e atrás.

Ninguém notou por horas. O sinal que faltava é banal: `git log origin/main..HEAD`
é uma linha e responde "o que meu trabalho tem que a main não tem". A pergunta do
dono ("tudo foi mergeado, né?") foi o que provocou a checagem — e a resposta
honesta só existiu porque a checagem foi feita em vez de respondida de cabeça.

**Lição operacional:** commit empurrado depois do merge do PR precisa de PR novo.
Não existe "o PR pega o resto".

**O merge da `main` de volta rendeu dois achados que valem mais que o incidente.**

**Primeiro: `material` estava entregando ao modelo uma ferramenta mais pobre que
a declarada.** O §9 acima (handshake) mediu que o SDK deriva o schema da
ASSINATURA e ignora o `inputSchema`. `material` nasceu antes disso e por isso não
usava `usp_mcp.adaptador.anotar` — o modelo recebia `{"title": "Disciplina",
"type": "string"}` no lugar de "Sigla da disciplina como no e-Disciplinas, por
exemplo PSI3323. Espaço e caixa não importam. Casa também com pedaço do nome."
Corrigido aplicando `anotar` às duas ferramentas do Moodle.

**Segundo: o handshake pegou um defeito que a suíte em processo não pegou.** Ao
registrar `_material` copiei o estilo do `_o_que_vence` e escrevi
`disciplina=None`. No SDK é a **ausência de default** que torna o parâmetro
obrigatório no fio — então `disciplina` virou opcional enquanto o `inputSchema` a
declara em `required`, e o modelo via uma ferramenta que aceita ser chamada sem
disciplina nenhuma. T78-T81 passavam: eles comparam nomes de parâmetro, não
obrigatoriedade. H6 falhou na hora, com a mensagem certa.

Isso é evidência direta a favor de manter os **dois** caminhos de teste do
entrypoint: em processo alcança o dicionário montado e a mensagem de SDK ausente;
no fio alcança o que o SDK decide sozinho. Nenhum dos dois é redundante.

Depois do merge: **309 passed, 6 skipped**.

### 01/09/2026 — os conectores da conta saem deste repositório; o corte é do repo, não da conta

O `.mcp.json` deste projeto declara três servidores e só três: `usp-moodle`,
`usp-jupiter`, `usp-rucard`, todos stdio local. Mas toda sessão aberta aqui vinha
carregando **onze conectores claude.ai da conta do dono**, injetados de fora do
repositório. Medido no `remoteMcpServersConfig` da sessão:

| Conector | UUID (é o nome do servidor no fio) | Ferramentas |
|---|---|---|
| Make | `00000000-0000-0000-0000-000000000000` | 81 |
| Atlassian | `00000000-0000-0000-0000-000000000000` | 40 |
| Notion | `00000000-0000-0000-0000-000000000000` | 37 |
| Nekt (`servidor-interno.exemplo`) | `00000000-0000-0000-0000-000000000000` | 34 |
| Gmail | `00000000-0000-0000-0000-000000000000` | 29 |
| Supabase | `00000000-0000-0000-0000-000000000000` | 29 |
| HubSpot | `00000000-0000-0000-0000-000000000000` | 24 |
| Slack | `00000000-0000-0000-0000-000000000000` | 13 |
| Google Drive | `00000000-0000-0000-0000-000000000000` | 11 |
| Google Calendar | `00000000-0000-0000-0000-000000000000` | 9 |
| visualize (Anthropic) | `00000000-0000-0000-0000-000000000000` | 2 |

São **309 ferramentas** de trabalho da Lastro — CRM, e-mail, Slack, Jira, banco de
produção — num repositório pessoal sobre bandejão, prazo de disciplina e ementa. A
superfície não é só ruído de contexto: `send_message`, `execute_sql` e
`apply_migration` de sistemas da empresa ficam a uma chamada de distância de uma
sessão cujo assunto é cardápio de RU.

**A decisão:** `disableClaudeAiConnectors: true` no `.claude/settings.json` do
repositório (versionado). Os onze deixam de ser buscados e conectados; os três
servidores USP, que vêm do `.mcp.json` por stdio, não são tocados.

**O que foi descartado, e por quê.** A alternativa era `permissions.deny` com uma
regra `mcp__<uuid>` por conector, poupando o Notion. Perde em duas frentes: o
conector negado **ainda conecta e ainda ocupa contexto** — só a chamada é
bloqueada —, e a regra é ancorada num UUID opaco que morre calada se a conta
rotacionar o conector. Uma denylist por UUID também viola o Invariante 2 em
espírito: é denylist onde cabia um corte na origem.

**O ponteiro que importa para a próxima sessão:** o gesto é do repositório, e a
descrição do próprio ajuste diz que qualquer fonte com `true` vence — projeto pode
optar por sair, mas um `false` de projeto não derruba um `true` de usuário. Nada
aqui altera a conta: nos outros repositórios da Lastro os conectores continuam
como estavam.

**Adendo do mesmo dia — as skills, e por que metade não tem alavanca aqui.**

Junto com os conectores vinham skills de trabalho. Elas chegam por três vias
diferentes, e só duas obedecem a este repositório:

| Skill | Via | Alavanca |
|---|---|---|
| `lais-html-report` | `~/.claude/skills/` (disco do usuário) | `skillOverrides` ✔ |
| `lais-copywriter`, `lastro-briefing-closers`, `fix-trino-query` | sincronizadas da conta claude.ai | `skillOverrides` (provável) |
| `lais-brand-studio:*` — 11 skills, 5 agentes, 3 servidores MCP | **plugin injetado pelo app** | nenhuma daqui |

O terceiro caso é o que importa registrar, porque custou tempo descobrir. O
resolvedor de estado de skill do Claude Code começa assim:

```js
if (e.type !== "prompt" || e.source === "plugin") return "on"
```

**Skill de plugin é fixada em `on` antes de `skillOverrides` ser lido.** A UI
confirma pelo outro lado: para `source === "plugin"` ela devolve
`{value:"on", source:"plugin"}`, um estado travado. Não existe desligar uma skill
de plugin pelo nome — só desligando o plugin inteiro.

E o `lais-brand-studio` não está instalado no repositório de plugins do CLI: ele é
injetado pelo app da Claude a cada sessão, por caminho temporário
(`claude-hostloop-plugins/…/plugin_013HZzpc4BAdU53jsiY3DLhA`, autor "Lastro",
versão 1.10.3). Sem marketplace, e `enabledPlugins` é documentado no formato
`plugin-id@marketplace-id`. A linha `"lais-brand-studio": false` ficou no
`.claude/settings.json` como tentativa, **não verificada** — se na próxima sessão
as skills `lais-brand-studio:*` ainda aparecerem, a alavanca é o app, não o repo,
e a linha deve sair para não mentir.

**Lição que vale além deste ajuste:** "está no settings.json" não é o mesmo que
"está desligado". Três das quatro vias acima passam por caminhos de código
distintos, e uma delas ignora a configuração por construção. Confirme na sessão
seguinte quais sumiram de fato antes de considerar a limpeza feita.

### 01/09/2026 — o download de arquivo do Moodle, medido: o token não precisa ir na URL

**Fechada a questão (a) do §9 de 31/08**, que estava registrada como "continua não
verificado ... custa uma chamada da conta, que é decisão do dono". O dono pediu.
Custou **zero** chamada de web service: as `fileurl` da fixture higienizada
`course_contents_psi3323.json` são reais — a higienização do §3.3 mexe em nome,
`userid` e nota, não em endereço de arquivo. Só o GET/POST no `pluginfile.php`
saiu para a rede. Medição completa em `notas/fase1-moodle.md`.

**O download funciona, e de quatro formas testadas só duas autenticam:**

| | |
|---|---|
| sem token | HTTP **200** + JSON `errorcode: missingparam` |
| `?token=` na query | 200, `application/pdf`, 87.705 B, `%PDF-` |
| `Authorization: Bearer` | HTTP **200** + JSON `missingparam` — header ignorado |
| **`token` no corpo do POST** | **200, `application/pdf`, 87.705 B** |

**Primeiro achado, e ele corrige uma afirmação deste documento.** O §9 de 31/08 e
a docstring de `material.py` diziam que baixar "exige anexar o token na URL", e
derivavam disso a regra da fronteira. A premissa é falsa: **o corpo do POST
serve**. A regra de não emitir URL de arquivo interno **continua certa** — uma URL
sem token não abre para o usuário, e uma com token põe a credencial no contexto
do modelo (Invariante 3) — mas o motivo muda de "é impossível baixar sem expor" para
"o servidor baixa sem nunca formar uma URL com segredo dentro". Isso **destrava** a
segunda ferramenta em vez de bloqueá-la: ela pode entregar o *conteúdo* sem que o
*endereço autenticado* exista em lugar nenhum. Afirmação não medida virando premissa
de desenho — o mesmo padrão do iCal e da rede da USP, terceira vez registrada.

**Segundo achado, e é armadilha de implementação.** Falha de credencial **não vem
como 4xx**: vem HTTP 200 com `application/json` e `errorcode`. Quem checar status
entrega JSON de erro achando que é PDF. A checagem que vale é content-type +
byte-magic (Invariante 6). O `filesize` de `contents` bateu exato com os bytes
recebidos, então dá para prever custo antes de baixar.

**Terceiro: o custo do texto, medido nos 19 PDFs internos de PSI3323 — não em três.**
15,9 MB e 181 páginas baixados; texto somado **203.675 B (~50.900 tokens), 1,28%
dos bytes**; média **~2.679 tokens por PDF**; extremos 1,7k e 25,3k bytes.
**Zero escaneados: 19 de 19 têm camada de texto**, nenhum exigiria OCR. Foram os 19
e não uma amostra porque "três não provam ausência" já custou duas correções a este
repo — e desta vez a ausência (de PDF sem texto) era exatamente o que se queria provar.

**Consequência de desenho:** um PDF cabe folgado no contexto (~2,7k), a disciplina
inteira não (~50,9k). A segunda ferramenta é **um arquivo por vez**, como a primeira
é uma disciplina por vez, e declara truncamento quando o texto passar do teto
(Invariante 7) — a variação de 15× entre o menor e o maior é o motivo.

**Continua aberto, e não foi medido aqui:** (i) `mod_folder` — PSI3323 não tem
nenhum, e esta medição não acrescentou disciplina; (ii) `pypdf` como **primeira
dependência de runtime** do projeto — foi instalado só para medir e desinstalado
depois, e adotá-lo é decisão de §9 própria, não efeito colateral; (iii) o que fazer
com `.docx`, `.jpeg` e `octet-stream`, que existem no acervo e não são PDF.

### 01/09/2026 — a segunda ferramenta de material entrega o caminho, não o conteúdo

**Decidido: o MCP baixa o arquivo e devolve o caminho local; quem lê é o agente
que chamou.** A pergunta veio do dono — "isso não pode ser resolvido por outras
partes do Claude? o MCP entrega o PDF e o agente decide o que fazer" — e ela
desfez o desenho que esta sessão ia propor (extrair texto com `pypdf` e devolver
o texto). Registrada aqui porque muda a fronteira da ferramenta, não só a
implementação.

**Entregar os bytes pelo canal MCP está descartado, e é medida.** O SDK suporta
(`EmbeddedResource` + `BlobResourceContents.blob`, base64). O custo, projetado
sobre os `filesize` reais dos 19 PDFs de PSI3323:

| | arquivo | base64 no contexto |
|---|---|---|
| menor | 88 kB | ~31.600 tok |
| médio | 838 kB | **~302.000 tok** |
| maior | 6,3 MB | **~2.286.000 tok** |

Contra **~2.679 tok** do texto extraído de um PDF e **~1.621 tok** da listagem
inteira da disciplina. Base64 infla 33% e tokeniza mal: um PDF médio custaria
mais que cem disciplinas listadas. `ResourceLink` não salva o desenho — o
conteúdo continua atravessando o mesmo canal quando for lido.

**Entregar o caminho custa ~50 tokens** — uma linha com nome, páginas, tamanho e
destino em disco. Três ganhos, e o primeiro não é de custo:

1. **O agente vê as figuras.** Decisivo neste acervo: são PDFs de eletrônica —
   circuitos, formas de onda, esquemas. Os slides medidos hoje têm **280–440 B de
   texto por página**; são quase só imagem. `pypdf` devolveria uma casca e nós
   chamaríamos isso de "texto extraído" — Invariante 6 violado com aparência de
   sucesso, que é a pior forma.
2. **Nenhuma dependência de runtime nova.** `pypdf` sai inteiro, e com ele a
   questão aberta que esta mesma sessão tinha acabado de abrir no backlog.
3. **Paginação sob demanda.** Num PDF de 29 páginas o agente pede as que
   interessam, em vez de o servidor despejar 9,6 kB de texto achatado.

**O que a decisão custa, escrito antes de valer:**

- **O servidor passa a escrever em disco.** Não fere o Invariante 1, que é sobre
  escrita na USP — mas é efeito colateral novo e pede diretório confinado, teto de
  tamanho e limpeza declarada. Isso é desenho da implementação, e ela ainda não
  existe.
- **Acopla ao cliente.** Só funciona se quem chamou souber ler arquivo local. O
  Invariante 4 já prende o servidor autenticado ao stdio local, então o cliente é
  sempre local — mas "local" não garante "lê PDF". A saída da ferramenta tem de
  dizer o que devolveu e por quê, para o cliente que não souber (Invariante 6).
- **O Invariante 7 muda de dono nessa fronteira.** Se o agente ler 5 de 29
  páginas, quem declara o truncamento é o cliente. Nós declaramos o total de
  páginas; o recorte é dele.

**A disciplina é a mesma das outras duas ferramentas:** o MCP entrega o dado
escasso e caro de obter, quem interpreta é o modelo. `bandejao` não decide onde
almoçar, `material` não resume a lista — e ler o PDF é interpretação, não acesso.

**Descartado junto:** extrair texto no servidor (perde figura, cria dependência,
achata 29 páginas em um blob), e devolver texto **e** caminho (a dependência volta
inteira para produzir a metade pior).

### 03/09/2026 — `baixar_arquivo` verificada ao vivo, e um PDF escaneado refuta a medição de 01/09

**A ferramenta funciona contra o e-Disciplinas de verdade**, exercitada pelo fio MCP
(não por script), no servidor stdio deste worktree, em **PTC3314** — disciplina
diferente da amostra de desenho, de propósito: uma disciplina só não prova resolução.

| caminho | resultado |
|---|---|
| `material` em PTC3314 | 53 itens (contra 29 de PSI3323) |
| singular, `nome="Lista 2"` | baixou, gravou, devolveu o caminho |
| ambiguidade, `nome="lista"` | recusou nomeando **seção e módulo** dos 2 candidatos |
| `todos=true` | baixou os 2 — e o segundo veio marcado "(já estava em disco)" |
| teto, `nome="senoide"`, `todos=true` | **4 arquivos de 122 a 178 MB, todos nomeados, nenhum baixado** |

O caminho do teto vale registrar: a suíte só o alcança trocando a constante por
`monkeypatch`, e aqui ele foi exercitado por arquivos reais que passam do teto por
duas a três vezes. Os quatro saíram **nomeados** na resposta (Invariante 7), não
contados.

**O achado que refuta o §9 de 01/09.** Aquela entrada registrou, sobre os 19 PDFs de
PSI3323: *"Zero escaneados: 19 de 19 têm camada de texto, nenhum exigiria OCR."* A
medição estava certa para aquela disciplina e **errada como fato do sistema** — a
primeira disciplina nova mostrou o contrário:

| | páginas | texto extraível |
|---|---|---|
| `Lista 1.pdf` (PTC3314) | 16 | **15 B no total — 0 B/página** |
| `Lista 2.pdf` (PTC3314) | 10 | **9 B no total — 0 B/página** |

São resoluções **manuscritas e escaneadas**. Não têm camada de texto nenhuma.

**Isto é a validação mais forte que o desenho podia receber, e ela veio por acaso.**
A alternativa descartada em 01/09 — extrair o texto no servidor com `pypdf` — teria
devolvido **9 bytes** para a Lista 2 e chamado isso de conteúdo: uma casca vazia com
aparência de sucesso, que é a forma do Invariante 6 que mais custa a notar. Entregando
o **caminho**, o agente abriu o PDF como imagem e leu a matemática manuscrita — sem
OCR, sem dependência nova, sem nada no servidor entender de PDF.

O argumento de 01/09 era "extrair texto perde as figuras". O caso real é pior e melhor
que o argumento: há PDFs em que o texto **é** a figura.

**Terceira vez nesta sessão que "amostra não prova ausência" mordeu** — e a primeira
em que mordeu a mim, contra uma medição que eu mesmo tinha acabado de registrar com
19 de 19. A regra não é sobre desconfiar de amostra pequena: 19 não é pequena. É sobre
não converter "não vi" em "não existe" quando a próxima observação é barata.

**Verificado também, sem chamada extra:** o depósito nasce em
`~/.cache/usp-mcp/moodle/<courseid>/<fileid>-<timemodified>/<slug>.pdf`, fora do
repositório (`git status` limpo depois de baixar 4 MB), com o nome legível preservado
e os bytes começando em `%PDF-`.

**Não medido nesta verificação, e registrado como tal:** o tempo de cada chamada. O
cache de disciplinas já estava quente no processo do servidor, então o custo de
~14,7 s da lista de matrículas não apareceu e não foi cronometrado.

### 03/09/2026 — o §6 tinha um nome que eu não sabia: MCP Bundle. E o cache tinha uma cura que eu tinha descartado cedo demais

**Pesquisa, não decisão.** O dono quer que outras pessoas usem isto, e o §6 estava com
"linguagem, runtime, transporte, hospedagem" em aberto desde o começo. Detalhe em
`notas/mcpb-e-distribuicao.md`. **Nada foi testado** — tudo abaixo é leitura de
documentação, e o item 9 do `CLAUDE.md` vale aqui: medir antes de afirmar que funciona.

**O achado principal é que a decisão do §6 já estava certa e não sabia o nome dela.**
"Dado autenticado → entrypoint local, cada pessoa traz o seu token" é a definição de um
**MCP Bundle** (`.mcpb`): zip com o servidor e um `manifest.json`, stdio, um clique para
instalar, sem OAuth. O §6 ganhou uma subseção 6.1 com isso.

**O que muda na prática, e é grande:** hoje, para outra pessoa usar isto, ela clona o
repo, cria venv, instala dependências, copia o `.env.example`, gera o token, cola no
arquivo e edita a configuração do cliente. Com um `.mcpb`, ela dá um clique e digita o
token num campo que o Claude Desktop desenha sozinho a partir do `user_config` do
manifest. E **nenhuma linha do nosso código muda**: o valor chega por variável de
ambiente, que é o que `usp_mcp/env.py` já lê — inclusive com o `setdefault` que faz o
ambiente ganhar do `.env`, comportamento que passa a ser exatamente o necessário.

**O que fecha, e não é reversível por preferência:** conector **remoto** está fora para
o Moodle por três motivos independentes — a rede da USP não sai da nuvem (§1.1), o token
não pode sair da máquina (Invariante 4), e conector remoto autenticado exige **OAuth
2.0**, que o e-Disciplinas não oferece (ele dá token pessoal de web service). O terceiro
é novo e é o mais definitivo: não é questão de querermos, é que não há fluxo para
implementar. Para RUCard e Jupiter o remoto segue viável, e é lá que ele faz sentido.

**O que continua aberto, e virou linha de backlog:** o `.mcpb` recomenda Node.js porque
ele vem junto com o Claude Desktop; o nosso servidor é Python, suportado mas exigindo
runtime do usuário. Quanto isso custa em atrito é **medição, não estimativa** — e a
mesma medição responde onde o `"sensitive": true` guarda o valor, que a spec do manifest
não diz e que o Invariante 3 quer saber.

**Segundo achado, e ele desfaz uma objeção minha de horas antes.** Registrei em 03/09
que o depósito só cresce e que limpeza automática era arriscada, porque poderia sumir
com um arquivo sendo lido. A pesquisa mostrou a peça que faltava: **limpeza no
startup**, que o `mcp-clip` faz para órfãos de instâncias anteriores. No startup o risco
não existe — o servidor sobe antes de qualquer leitura da sessão. A objeção caiu; o TTL
é que não se copia de lá (1 hora, para dado efêmero), porque o nosso dado muda por
semestre e o Invariante 5 pede TTL colado na taxa de mudança.

**Verificado por inspeção, não por documentação:** o protocolo MCP **não trata** de
ciclo de vida de arquivo. Os tipos do SDK instalado, olhados quando avaliamos entregar
blob, não têm noção de cache, quota ou limpeza. O cliente também não tem como saber que
`~/.cache/usp-mcp/` existe — ele recebe uma string e abre um arquivo. **A limpeza é
nossa por construção**, e é o preço de ter escolhido entregar caminho em vez de
conteúdo.

### 03/09/2026 — a busca semântica é do modelo, não do servidor: casamento por palavras construído, medido e revertido

**Decisão: `baixar_arquivo` casa por nome de arquivo e nada mais.** A tentativa
contrária foi construída, verificada ao vivo e revertida no mesmo dia — e o motivo
da reversão é melhor que o da construção, então fica registrado inteiro.

**O que foi construído.** Perguntar pelo assunto não funcionava: "resolução do
capítulo 3" não achava `Lista 2.pdf` em PTC3314, cujo módulo se chama exatamente
"Resolução Exercícios do Capítulo 3 da apostila do curso". A correção teve duas
metades — o rótulo do módulo passou a sair em `material`, e `baixar_arquivo` ganhou
uma segunda tentativa que casava palavra a palavra contra nome e rótulo. As duas
funcionaram ao vivo.

**Por que a segunda metade caiu, e a pergunta veio do dono:** *"não deveria ser um
agente receber os temas e ver qual arquivo parece mais apto?"* Deveria — e é o
argumento que este projeto já usa em outro lugar. O §9 de 01/09 decidiu que o
servidor **entrega o arquivo e não o interpreta**, porque interpretar é do modelo.
Casar "carta de Smith" com `smith.pdf`, "amp op" com "amplificador operacional",
"a prova antiga" com o PDF de 2025 é interpretação — e nenhuma regra de substring
ou de interseção de palavras chega perto de um modelo que leu a lista.

A segunda tentativa não estava errada; estava **redundante com um mecanismo melhor**,
e pior nos casos difíceis. Ganhava uma ida e volta no caso fácil e errava onde o
modelo acertaria, ao custo de vinte linhas, uma frouxidão declarada (`"de"` casava
com 17 dos 29 itens de PSI3323) e uma linha de backlog para vigiá-la.

**O que fica, e é a metade que importa:** `material` emite o rótulo que o professor
deu ao módulo, quando ele diz algo que o nome do arquivo não diz — 20 dos 29 itens
de PSI3323; os 9 redundantes são omitidos. Custo medido: **+253 tokens** no texto
final (786 → 1.039). Isso não é heurística no servidor, é **parar de descartar dado**:
sem o rótulo, nem o modelo nem uma pessoa têm como saber que `LT-RPS-aula11-12.pdf`
é a aula de carta de Smith.

**Descartado junto:** os `summary` de seção, que custariam ~3.569 tokens — mais que
dobrariam a resposta — e são o campo que menos promete. Os títulos de seção medidos
são `AULA 1`, `Geral`, ou datas como `31 agosto - 6 setembro`.

**E a mensagem de "não achei" mudou de função.** Ela não tenta mais adivinhar: diz
que `material` lista cada arquivo com o rótulo do professor, que é onde está o
assunto, e pede para repetir com o nome exato. O erro passou a ser o começo do
caminho certo, em vez de um beco.

**Lição de método, e ela não é sobre esta ferramenta.** A tentação de resolver no
servidor o que o modelo resolve melhor é forte porque parece "mais completo". O
critério que separa os dois casos: **entregar dado que estava sendo descartado é
sempre certo; decidir no lugar do modelo raramente é.** O rótulo do módulo era a
primeira coisa; o casamento por palavras era a segunda.

### 10/09/2026 — o token do Moodle ganhou chamador, e três vazamentos de credencial apareceram no caminho

**O pedido era um README.** O §8 já tinha o fluxo inteiro em prosa; o que faltava era
alguém executar por quem está fazendo o setup. Virou `scripts/token.sh`, sete passos
guiados, com o desenho em `docs/superpowers/specs/2026-09-10-script-token-moodle-design.md`.

**A decisão de escopo:** o script cobre o token e só o token. Um `setup.sh` que fizesse
venv + pip + gate duplicaria três linhas do `README.md` num segundo lugar que envelhece
separado. E ele **confirma o token contra a USP em uma chamada** — decisão do dono. O
argumento contra era o §1.1 (chamada ao vivo é decisão de quem tem a credencial); o que
venceu é que quem roda o script *é* quem acabou de colar a própria credencial de
propósito. Sem a chamada, "gravei o token" não significa "o token funciona", e a pessoa
descobre no primeiro uso, com `invalidtoken` cru.

**O que mudou de desenho por causa de vazamento, e não por causa de conveniência.** Três
achados, nenhum deles no pedido original:

1. **O token não pode ir em `argv`.** `ps aux` é legível por qualquer processo do mesmo
   usuário, então `curl --data-urlencode "wstoken=$T"` publica a credencial para a máquina
   inteira enquanto o processo vive. Medido em 10/09 contra um servidor local: `curl -K -`
   lê a opção do stdin e o campo chega no corpo do POST igual — `wstoken`, `wsfunction` e
   `moodlewsrestformat` no corpo, nada em `argv`. O `token.sh` usa isso no passo 6 e
   variável de ambiente no passo 7. **`scripts/ws.sh` continua com o furo** — está no
   backlog, e consertar lá é mudar o script que toda a descoberta usa.
2. **O base64 cru não pode tocar o disco.** O caminho curto de implementar era gravar o
   valor colado no `.env` e chamar o `fix-token.sh` para normalizar depois. Esse caminho
   escreve o `privatetoken` — terceira parte do payload, que habilita
   `tool_mobile_get_autologin_key`, bloqueio permanente do §2.2 — num arquivo que ninguém
   audita depois de existir. O script decodifica em memória e grava só os 32 hex.
3. **Verificar antes de gravar, não depois.** Assim o `.env` nunca guarda token que não
   autentica, e o caminho de erro não precisa desfazer escrita.

**A ordem dos passos veio de um teste, não de estética.** O fluxo inteiro foi exercitado
offline contra um Moodle de mentira em `127.0.0.1`, e o caminho ruim revelou um furo que
a leitura não tinha pegado: a confirmação de sobrescrita lia de `/dev/tty`, que não
existe no modo `pbpaste | ./scripts/token.sh`. Hoje sem terminal ele **reprova dizendo a
cura** (`--sobrescrever`) em vez de estourar — Invariante 6. Quatro caminhos verificados:
token que autentica, token que o Moodle recusa, forma errada no payload, e sobrescrita
sem terminal. Nos três últimos o `.env` fica **intacto**, e isso é asserção, não intenção.

**A conferência do passaporte avisa e não bloqueia, de propósito.** O `siteid` do payload
é `md5(wwwroot + passport)`, então um passaporte gerado pelo script permite detectar
payload colado de outra tentativa. Essa fórmula está **recordada, não medida** contra o
e-Disciplinas (§1.4) — transformar memória em porta fechada é o jeito de reprovar um setup
legítimo por motivo errado. O script imprime o diagnóstico e diz qual das duas leituras o
passo 6 desempata. **Quem rodar isso com token real fecha a questão**, e aí a conferência
pode virar bloqueio.

**A extração que a suíte cobre, e a que ela não cobre.** A regra do formato saiu de dentro
do `fix-token.sh` e virou `scripts/_decodificar_token.py`, importado pelos dois scripts —
sem isso o `token.sh` nasceria com uma segunda cópia da mesma regra. 17 testes offline,
sobre payload sintético (nenhum token real entra em teste, nem higienizado), incluindo a
asserção de que o `privatetoken` **não aparece no stdout** e a de que `fix-token.sh` com
forma errada deixa o `.env` byte a byte como estava. Duas sabotagens confirmaram que a
suíte reprova quando deve. O que ela **não** alcança está dito no §7 do desenho: abrir
navegador e ler clipboard. O resto — escrever `.env`, falar com o Moodle, cachear o
`userid` — passou a ser alcançável justamente porque o Moodle de mentira substituiu a USP.

**Descartado:** `login/token.php` com senha (§1.3, SSO — não insista), renovar token sem
navegador (o `launch.php` autentica por sessão), e o `setup.sh` que faria tudo.

**Adendo do mesmo dia — o passo 6 medido contra a USP, não contra o dublê.** Uma chamada
com o token que já estava no `.env`, pela construção exata do script. Quatro coisas que
eu tinha escrito defensivamente e agora são medida:

- **`curl -K -` funciona contra o e-Disciplinas real**, não só contra o servidor local:
  31.386 B / ~7.846 tokens de resposta, 447 funções expostas, `userid` idêntico ao
  `.cache/userid`. A construção do passo 6 está verificada ponta a ponta.
- **Os cinco campos que o passo 6 imprime existem na resposta real**: `sitename`,
  `fullname`, `username`, `release`, `userid`. Eu tinha escrito o parser com `.get()` e
  "(não informado)" justamente por não ter medido; a defesa fica, mas deixou de ser palpite.
- **`site_info` não tem campo de expiração.** Nenhuma das 28 chaves do topo casa com
  `expir`/`valid`/`until`. Eu tinha dito ao dono que o script imprimiria a expiração e
  corrigi por leitura da API; agora está medido. Expiração e revogação só em
  `managetoken.php`, que é onde o script aponta.
- **`site_info` não devolve o próprio `wstoken`.** Verificado por asserção antes de
  imprimir qualquer coisa: a resposta inteira foi varrida à procura do valor do token e
  ele não está lá. Importa porque é a única chamada que o setup faz, e uma função de
  diagnóstico que ecoasse a credencial poria ela no contexto de quem depurasse o script.

**O que continua sem medida, e é o resto do fluxo:** os passos 2 a 5 (abrir o
`launch.php` numa sessão logada, copiar o redirect, decodificar um payload real) exigem
navegador autenticado na Senha Única. Eu não executo essa parte de propósito, e o motivo
é o Invariante 3, não falta de acesso: ler o redirect é ler o base64, e o base64 é o
`wstoken` mais o `privatetoken`. Fazer isso pela sessão de IA põe as duas credenciais no
transcrito — permanentemente, e num lugar que ninguém audita depois. O `pbpaste |` do
passo 4 existe exatamente para que a única parte que toca o valor seja a do dono.

### 10/09/2026 — o passo manual morreu: o `urlscheme` do Moodle aceita um esquema nosso

**O script da entrada anterior tinha um passo manual no meio, e o dono reclamou com
razão.** "Abra o DevTools na aba Network e copie a linha bloqueada" não é instrução de
setup — é instrução para quem já sabe. A pergunta era se dava para o script pegar o
token sozinho. Dá.

**O que a leitura do `admin/tool/mobile/launch.php` (5.0 STABLE) resolveu.** Fatos novos
do §1.3, cada um com a linha:

- **Linha 37:** `urlscheme` é validado com `^[a-zA-Z][a-zA-Z0-9-\+\.]*$`. Só caracteres de
  esquema. **Um catcher em localhost é impossível** — não existe `urlscheme` que faça o
  Moodle redirecionar para `http://127.0.0.1:PORTA/?token=…`. Era a minha primeira ideia e
  ela está morta por construção, não por falta de tentativa.
- **Linha 116:** `$location = "$urlscheme://token=$apptoken"` — o base64 sempre na posição
  de host. É a mecânica exata do aviso do `urlscheme=http` que o §1.3 já registrava.
- **O regex aceita um esquema NOSSO.** `uspmcp` passa. Um handler registrado para ele
  recebe o redirect direto do navegador. É a única porta, e ela existe.
- **Linhas 120-145:** com `confirmed=1` o Moodle **não** redireciona — renderiza uma página
  com um link cujo `href` é o `moodlemobile://token=…`, mais um JS que clica nele. O token
  fica **na página, como link**. Isso conserta o caminho manual: "botão direito no link →
  copiar endereço" em vez de DevTools.
- **Linha 89:** `generate_token_for_current_user` devolve o token **existente** se já houver
  um para o serviço. **Corrige o que eu tinha dito ao dono:** rodar o fluxo não cunha um
  segundo token a cada vez, e não há nada para revogar depois de testar.
- **Linha 94:** o `privatetoken` só vem em login novo (`$SESSION->justloggedin`). O payload
  costuma ter 2 partes, não 3 — o decodificador já aceitava `>= 2`, agora por fato e não
  por sorte.
- **Linha 111:** `forcedurlscheme`, se configurado no site, **sobrescreve** nosso esquema.
  Não é observável de fora, e é o principal motivo de o fallback manual continuar existindo.

**Três obstáculos que a leitura não previu e a medição achou.** Cada um matava a ideia em
silêncio, com `open` devolvendo `kLSApplicationNotFoundErr` e nenhuma pista de qual dos
três era:

1. **`osacompile` não gera `CFBundleIdentifier`.** Sem ele o Launch Services registra o
   bundle e nunca reivindica o esquema. O `PlistBuddy` precisa de `Add`, não `Set` — `Set`
   numa chave ausente aborta a invocação inteira e as outras chaves não entram, que foi o
   primeiro falso negativo.
2. **App em `/private/tmp` não é reivindicado.** Em `~/Library/Caches` é: o dump do LS
   passa a dizer `claimed schemes: uspmcp:`. O sinal de que a causa era localização veio de
   comparar o dump nos dois lugares, não de teoria.
3. **Nenhum diálogo aparece** — nem do macOS pelo Launch Services, nem do Chrome seguindo
   um `302` para esquema desconhecido. Verificado nos dois caminhos, e era a incógnita que
   decidia se a automação valia a pena.

**O FIFO preserva o invariante no caminho novo.** O handler escreve num FIFO, que não tem
armazenamento (`stat` confirma tamanho 0 e tipo `Fifo File`), então o base64 cru — que
carrega o `privatetoken` — continua não existindo em arquivo. Se o handler escrevesse num
arquivo temporário, a automação teria custado o §4 do desenho.

**Uma lição de método, e ela é sobre verificação.** A primeira versão da limpeza conferia
se o esquema tinha sido liberado casando a **mensagem de erro** do `open` (`grep 'No
application'`). Numa máquina já limpa ela reportou "ainda atende" — porque `open` sem saída
cai no `else`. Um verificador que não distingue "sujo" de "saída inesperada" não verifica
nada, e assustou o dono com um problema inexistente. Hoje ele asserta a **condição**: a
contagem de claims do esquema no dump do LS voltou a zero. É o §6 do `CONVENTIONS.md`
aplicado ao próprio verificador.

**Medido ponta a ponta**, contra um Moodle de mentira que emite o mesmo `302` da linha 149,
com pty para o script ver um terminal: 151 bytes capturados idênticos ao que o servidor
mandou, decodificados, verificados, gravados, `userid` cacheado, e limpeza fechando com
zero claims e zero diretório. Mais o passo 6 contra a USP real, no adendo anterior.

**O que continua sem medida:** `forcedurlscheme` no e-Disciplinas, que só uma rodada real
diz, e a fórmula do passaporte. As duas fecham na primeira execução com token de verdade,
sem custo extra — a rodada é a mesma.

**Descartado:** o catcher em localhost (linha 37 proíbe), e um teste da captura na suíte do
gate — registrar handler no Launch Services é mudar a máquina de quem commita.

### 11/09/2026 — o token obtido pelo script, contra o e-Disciplinas de verdade

**Primeira ponta a ponta real.** `./scripts/token.sh --manual --sobrescrever` com o
payload vindo do clipboard: decodificou, autenticou, gravou. `core_webservice_get_site_info`
devolveu `Moodle USP: e-Disciplinas`, a conta do dono e `5.0.8+ (Build: 20260722)` — a
mesma versão que o §1.3 registrava. O `userid` saiu da própria resposta e foi para
`.cache/userid`; nenhum valor de token apareceu em tela em nenhum momento.

**O caminho que funcionou é o manual com `confirmed=1`,** e ele é o que o §9 de 10/09
descreveu a partir das linhas 120-145: o Moodle renderiza uma página com um link cujo
`href` é o `moodlemobile://token=…`, e "botão direito → copiar endereço do link" substitui
o DevTools. O clipboard chegou com 113 bytes na forma exata (`moodlemobile://token=` mais
92 caracteres de base64), e o modo `pbpaste | ./scripts/token.sh` consumiu direto.

**Três fatos do `launch.php` confirmados por medição, não mais por leitura:**

1. **Linha 89 — `generate_token_for_current_user` devolve o token EXISTENTE.** O valor
   gravado veio **byte a byte igual** ao que já estava no `.env` (comparado por hash, sem
   imprimir nenhum dos dois). Não se cunha token novo a cada rodada, e **não há nada para
   revogar depois de testar**. Isso corrige em definitivo o aviso que este documento e o
   próprio script davam em 10/09, e a mensagem de sobrescrita foi reescrita.
2. **Linha 94 — o `privatetoken` só vem em login novo.** O payload tinha **2 partes**, não
   3. O decodificador aceita `>= 2` desde o começo; agora isso é fato e não tolerância.
3. **O `.env` sobreviveu linha por linha** — só a linha do token mudou.

**A conferência do passaporte é mais fraca do que o desenho supunha, e a rodada mostrou
por quê.** Ela avisou "não confere", e estava certa: o payload veio de uma URL de
`launch.php` aberta numa tentativa anterior (passaporte `8141678839`), enquanto o script
tinha acabado de gerar outro (`2694381761`). Um payload de outra invocação **da mesma
conta** é perfeitamente válido — o Moodle devolve o mesmo token — e não confere por
construção. Ou seja: **no caminho manual a conferência quase sempre vai avisar, e o aviso
não significa nada**, porque nada obriga a pessoa a abrir exatamente a URL que o script
imprimiu. Ela só carrega informação no caminho automático, onde é o próprio script que
abre a URL que gerou. A mensagem foi reescrita para dizer isso em vez de assustar.

**O que continua sem medida, e é só uma coisa:** a captura automática contra o
e-Disciplinas. Três tentativas reais, três falhas antes de o navegador entregar o
redirect — a primeira na guarda de claim obsoleto (corrigida), a segunda no `open` travado
por modal (corrigida), a terceira sem causa identificada porque ela mora na tela do dono.
Com ela morre junto a questão do `forcedurlscheme`, que **não é observável de fora**:
`tool_mobile_get_public_config` custou uma chamada e não expõe a chave (36 chaves, nenhuma
com `forced`).

**Descartado nesta rodada:** o Chrome como navegador da captura — medido com payload falso
e servidor local, ele não entrega `uspmcp://` sem um clique de confirmação, enquanto o
padrão do sistema entrega em segundos e calado. E o navegador embutido do Claude, que não
alcança `127.0.0.1` e é webview sandboxada.

### 11/09/2026 — o manual vira o padrão, e o automático vira `--auto`

**Decisão do dono, depois da rodada que funcionou.** O `token.sh` passa a fazer o caminho
manual por padrão; a captura automática fica atrás de `--auto`.

O critério é o de sempre neste projeto: **o que está medido ganha do que é elegante.** O
manual está verificado contra o e-Disciplinas e leva ~20 s. O automático funciona contra
dublê e nunca entregou contra a USP — três tentativas reais, três falhas antes de o
navegador seguir o redirect. Deixá-lo como padrão custaria **120 s de espera em toda
execução** num caminho que pode nem existir neste site: o `forcedurlscheme` (linha 111) não
é observável de fora, e `tool_mobile_get_public_config` não expõe a chave.

Isso não é abandonar o automático — ele fica no repositório, testado offline, com o que
falta medir escrito no backlog. É recusar prometer no padrão o que não foi verificado. Se
alguém rodar `--auto` e a captura entregar, a decisão se inverte com uma linha aqui.

**O que a troca custa:** um clique direito e uma colagem, por instalação. O que ela evita:
dois minutos de espera silenciosa, e um `README.md` afirmando uma automação que pode não
funcionar na máquina de quem leu.

### 11/09/2026 — o gate rodava a suíte dentro de um clone que continha o teste do gate

`tests/test_gate.py::D5` clona o repositório e roda o `gate.sh` no clone. A checagem 3
roda a suíte, e a suíte do clone contém `test_gate.py` — que clona de novo. **Recursão**,
com cada nível custando mais que o timeout do nível acima.

**Ficou latente por um dia.** Enquanto o `test_gate.py` só existia na `main`, o clone que
D5 faz (do HEAD da branch em trabalho) não o continha. O merge de 11/09 pôs o arquivo no
HEAD, e D5 passou a estourar os próprios 300 s. Medido: **326 s com um vermelho**, contra
**40,8 s verde** depois da correção. O sintoma apareceu como "o gate pendurou", que é o
disfarce mais caro possível.

**A cura é uma quebra explícita e barulhenta**, não um `skip`: `USP_MCP_GATE_SEM_SUITE=1`
faz a checagem 3 não rodar, e `_rodar_gate` do teste passa essa variável. O pulo **grita**
— a linha diz `PULADA`, o rodapé diz `A SUITE NAO RODOU — isto nao e um gate verde`, e o
código de saída não vira 0 por causa dele. Um gate que pula a checagem 3 calado é pior que
a recursão: devolve verde sem ter verificado código nenhum (Invariante 7). D5 passou a
**assertar que o aviso aparece**, para o pulo nunca virar silencioso.

**A lição de método:** um teste que executa a ferramenta que roda o teste precisa de uma
quebra de ciclo declarada no desenho. Aqui ela não existia, e o ciclo só se fechou quando
o arquivo chegou ao HEAD — ou seja, **o teste ficou verde exatamente enquanto não podia
falhar**, e ficou vermelho no primeiro momento em que passou a valer.

### 12/09/2026 — os PDFs presos dentro das entregas: `get_contents` descreve o assign e esconde o arquivo dele

**Veio do uso, não da suíte.** Um agente com o conector plugado pediu o enunciado do EC-1
de PTC3314, leu os 53 itens que `material` devolveu, não achou, e concluiu — corretamente,
a partir do que via — que era *feature faltando*. Era, e a suíte estava 100% verde.

**Medido, e as três linhas juntas é que decidem o desenho:**

| chamada | o que traz sobre o EC-1 | custo |
|---|---|---:|
| `core_course_get_contents` (142036) | o módulo `assign`, com `contents` **vazio** — nos 4 | 106.121 B |
| `description` do módulo | 529 B de datas de abertura e vencimento, **zero `href`** | — |
| `mod_assign_get_assignments` (`courseids[0]`) | `EP1-2026.pdf` (218.344 B), `EP1-2026.odt`, `EP2-2026.pdf`, `EP2-2026.odt` | 8.651 B / ~2.162 tokens |

A segunda linha é a que evita o desenho errado: a tentação era raspar `href` do
`description` e não gastar chamada nenhuma. Não há `href` nenhum lá — o campo traz as
datas que o Moodle renderiza, não o enunciado.

**O achado que fez a mudança ser pequena:** cada anexo chega com `filename`, `filesize`,
`mimetype`, `timemodified` e `fileurl` — **os mesmos nomes de campo** que `contents` usa. A
construção do `Item` virou uma função só (`_item_de`), e a partir daí o anexo entra no
acervo sem caso especial. `baixar_arquivo` passou a achá-lo **sem uma linha de mudança na
lógica dela**: a `fileurl` é `…/pluginfile.php/<contextid>/mod_assign/introattachment/0/…`,
que já passa pela allowlist de download do cliente e pelo `_fileid` existente.

**A allowlist foi a 5, e o prefixo de leitura do P5 também.** `mod_assign_get_assignments`
é a primeira entrada de uma família que tem escrita: `save_submission`,
`submit_for_grading`, `start_submission` e `remove_submission` são vizinhas de nome e estão
no bloqueio permanente do §2.2. Por isso o prefixo novo do P5 é `mod_assign_get_`, com o
`get_` dentro — `mod_assign_` sozinho abriria a porta para as quatro.

**Duas chamadas, e só quando a primeira diz que vale.** `get_contents` já lista os módulos:
sem `assign`, a segunda chamada não sai. É a diferença entre custo sob demanda e martelar a
USP por uma resposta que já se sabe vazia (Invariante 5). O escopo `courseids[0]` não é
otimização: **sem ele** a função devolve as 74 matrículas, 1 MB, ~251k tokens (§9, 28/08).

**O que ficou de fora, por decisão do dono:** o `intro` do assign — o enunciado em texto,
498 B no EC-1. `material` é lista de arquivos; enunciado, prazo, "já entreguei" e nota são
outra pergunta, e o §5 pede que ferramenta nasça de pergunta registrada, não do que a
resposta da API por acaso contém. Está no `BACKLOG-correcoes.md` como candidata própria.

**Dois avisos nasceram junto, os dois do Invariante 7.** A resposta real traz
`warnings: [{warningcode: "1", message: "No access rights in module context"}, …]` para
dois módulos — engolir isso entregaria uma lista com cara de completa. E das 4 entregas de
PTC3314, **2 não têm anexo** (as provas presenciais, que o professor criou como `assign` só
para ter data): o rodapé as nomeia, em vez de repetir o texto antigo, que declarava `assign`
inteiro fora da lista mesmo com metade dele dentro.

**Verificado ao vivo**, não só na suíte: `material(PTC3314, busca="EP")` devolve os 5
arquivos, e `baixar_arquivo` grava `EP1-2026.pdf` (218.344 B, PDF 1.7, 4 páginas) — cujo
texto começa com *"PTC3314 - Ondas e Linhas — 1º Exercício de Simulação Computacional"*. O
canário T120 guarda os cinco campos do anexo contra mudança de API.

**E um efeito colateral que a amostra escondia:** o ODT saía como "arquivo" porque nenhum
`resource` de PSI3323 era ODT. O professor publica o mesmo enunciado nos dois formatos —
os mimetypes do OpenDocument entraram na tabela de tipos.

**A lição de método, e ela dói: o registro já dizia.** A entrada de 28/08 fechou a questão
do §4 com a frase *"`get_contents` é suficiente para material: os 22 arquivos de um curso já
vêm com URL direta; **só fóruns e assigns pedem chamada própria**, e têm função dedicada de
qualquer forma"*. A ressalva estava escrita, medida e datada — e a ferramenta nasceu em
31/08 sem ela, com "suficiente" virando a parte que sobreviveu à leitura. A suíte não podia
pegar: ela cobria `material` com a fixture de PSI3323, que tem **um** módulo `assign`, e
nenhum teste perguntou o que havia dentro dele.

O que fecha o buraco não é mais cobertura do caminho que existe, é a pergunta invertida —
**"esta resposta é tudo?"** — feita contra dado, não contra a memória de quem escreveu a
ferramenta. Custou uma mensagem de quem usou; pela suíte não ia aparecer nunca.

### 12/09/2026 — a cobertura dos anexos, medida nas 19 disciplinas, e um rodapé que precisou de teto

Verificação de largura logo depois da entrada acima, porque "funcionou em PTC3314" não é
"funciona". **Uma chamada** de `mod_assign_get_assignments` com as 19 matrículas de 2026
como escopo (52.454 B, ~13.113 tokens) — o escopo é o que evita 1 MB.

| disciplina | entregas | com anexo |
|---|---:|---:|
| PTC3314 | 4 | 2 (os dois ECs, 4 arquivos) |
| PSI3481 | 2 | 1 (`PSI3481_exercicio_com_nota_2024_IP3.pdf` + `.docx`) |
| PSI3472 | 11 | 1 (`Projeto_PlanejamentoVoosNacionais.pdf`) |
| PTC3312 | 6 | 0 |
| as outras 15 | 0 | — |

**7 arquivos no semestre inteiro, em 3 disciplinas.** Pouco em volume, e exatamente os que
importam: são os enunciados de exercício-programa e projeto. Os dois casos novos foram
conferidos ponta a ponta, e o casamento por `cmid` acertou a seção nos dois.

**O que a largura pegou, e a amostra de uma disciplina não pegaria:** PSI3472 tem **10 das
11** entregas sem anexo (as "Lição aulas N e N+1"), e o rodapé que eu tinha escrito nomeava
as dez. Quatro linhas de nomes enterrando os outros três avisos. O Invariante 7 exige que o
corte seja **dito**, não que não exista: ficaram a contagem (`10 de 11`), três nomes de
amostra e `e mais 7`. T122 trava a contagem e o teto juntos.

**O que a largura NÃO conserta, e vale registrar como limite conhecido:** o casamento de
`baixar_arquivo` é por nome de ARQUIVO (decisão de 03/09), e o nome do enunciado costuma ser
opaco — `EP1-2026.pdf` para o "EC-1", `PSI3481_exercicio_com_nota_2024_IP3.pdf` para o
"exercício de cascata de amplificadores". O assunto está no nome do MÓDULO, que `material`
imprime e o filtro não olha. O fluxo desenhado funciona (listar, ler o rótulo, pedir pelo
nome exato), mas custa uma ida a mais sempre que alguém pede pelo nome da atividade. Está no
backlog; mudar o campo do casamento é decisão de §9, não conserto de passagem.

### 12/09/2026 — o `ws.sh` era o último `[ -f .env ]`, e duas linhas do backlog não tinham dívida nenhuma

Sessão de auditoria ("quais pendências temos"). Saíram duas coisas, e uma delas é sobre o
próprio backlog.

**O `ws.sh`, medido em vez de estimado.** Deste worktree, com o `.env` preenchido no
checkout principal e chamando o script **sem argumento**:

| versão | código de saída | o que diz |
|---|---:|---|
| a de `HEAD` | 1 | `MOODLE_TOKEN vazio. Copie .env.example para .env e preencha.` |
| depois | 2 | `uso: scripts/ws.sh <funcao> [param=valor ...]` |

Sem argumento de propósito: aí o script morre no `$# -lt 1`, que fica **depois** da
checagem do token e **antes** do `curl`. O código de saída separa "o token chegou" (2) de
"não chegou" (1) sem gastar chamada da conta nem tocar a USP — e é condição, não mensagem,
que é o corolário que a linha 62 do backlog pediu.

O erro antigo não era só inconveniente, era a **cura errada**: quem seguisse a mensagem
criaria um `.env` no worktree, e ele sombrearia o de verdade — exatamente o estrago que o
`token.sh` documenta na própria linha 81 e evita desde 11/09.

**Terceira repetição do mesmo defeito, então a cura virou frase.** Procurar o `.env` só no
diretório atual já mordeu a checagem de segredos do gate, o `token.sh`/`fix-token.sh` e
agora o `ws.sh`. O §4 do `CONVENTIONS.md` passa a dizer que **nenhum script procura o
`.env` com `[ -f .env ]`** — a porta é `usp_mcp.env.achar_env`, e é única. Verificado:
depois deste commit não sobrou nenhum em `scripts/` (o de `token.sh:97` é `.env.example`,
outra coisa).

**Descartado:** manter o `[ -f .env ]` como atalho rápido antes de perguntar ao Python.
Economiza uns 40 ms e cria um quarto lugar para o mesmo defeito morar. E descartado
também engolir a falha de import com `2>/dev/null`: sem poder perguntar, seguir em frente
devolveria a cura errada de novo, calada (Invariante 6). Hoje ela imprime o traceback
indentado e para, como o `token.sh` faz.

**Consertar o chão consertou três scripts.** `capture.sh` e `userid.sh` não têm `.env`
próprio: chamam `./scripts/ws.sh`. A linha 72 do backlog afirmava que o `capture.sh` tinha
o seu — não tinha.

**W1 e W2, e por que os dois.** W1 monta um checkout falso (`.git`, `.env`) com um worktree
pendurado nele e prova que o `.env` do principal é achado de lá. W2 monta o mesmo sem
`.env` nenhum e prova que a recusa legível continua de pé. Sozinho, W1 ficaria verde para
uma "cura" que inventasse um token. Cópia e não symlink no `usp_mcp/` do worktree falso,
porque `achar_env` faz `Path(__file__).resolve()` — um symlink acharia o `.env` de verdade
e o teste passaria sem exercitar nada. Gate: 432 passed, 6 skipped.

**O backlog também envelhece, e ninguém o remedia.** Duas linhas foram fechadas sem
trabalho nenhum, porque a dívida já não existia: a de `chamar_ferramenta` não aceitar
`cliente` injetável (marcada **alta** desde 31/08, e o `server.py:169` aceita desde o T80,
o que a linha 17 da mesma tabela já registrava) e a do comentário sobre o sandbox em
`server.py` (o texto não existe mais no arquivo). É o mesmo modo de falha que o §9 de
31/08 registrou para o `CLAUDE.md`, em outro arquivo: **estado escrito uma vez e nunca
mais conferido vira mapa errado**. O custo aqui foi menor porque o backlog não é lido no
começo de toda sessão — mas ele é o que responde "o que atacar primeiro", e ele apontava
para duas ruas sem dívida. Não há cura estrutural registrada; fica o hábito de conferir a
linha contra o código antes de agir sobre ela.

### 14/09/2026 — Jupiter: o curso descobrível é o que não responde

Desenho em `docs/superpowers/specs/2026-09-14-jupiter-requisitos-design.md`. A fatia
aberta era "resolver curso", para destravar o pré-requisito do `disciplina`. Onze
chamadas à mão (dado público, sem credencial) mataram o desenho óbvio antes de ele
existir.

**O caminho DWR de descoberta entrega o código errado.** `pubListarCursoEntrada
{codclg:3}` devolve **3033** para a Elétrica. Com 3033, `pubListarRequisitoDisciplina`
responde **0 linhas** para PSI3323 e PTC3314; com **3032** — que não aparece em lista
nenhuma — responde PSI3322 `[CR]` e PTC3213+PSI3213 `[PR]`. A grade de 3033 tem 67
registros e vai até o 5º semestre; a de 3032 vem **vazia**. São duas metades do mesmo
programa sob códigos diferentes, o que fecha parcialmente a discrepância do §5.1 do
recon: não é erro de digitação nem de superfície, é **geração de currículo**.

**O projeto piloto trocou o vocabulário de disciplina.** Em `MAT2455` (23 currículos),
os sete cursos de ingresso que já migraram — 3023, 3073, 3084, 3093, 3123, 3201, 3251 —
exigem **`2000101` Fundamentos Científicos e Modelagem para Engenharia I**, código só de
dígitos, no lugar de MAT2454+MAT3458. A adoção é **parcial**: 3033 (Elétrica), 3045
(Mecânica) e 3152 (Ambiental) seguem no vocabulário antigo. Regra do tipo "filtre pelo
curso vigente" acerta metade da Poli e erra a outra. Os pares 3021/3022/**3023**,
3072/**3073**, 3092/**3093** são a mesma coisa em gerações diferentes.

> **Correção lavrada no mesmo dia, algumas horas depois.** O parágrafo acima dizia que
> esses sete currículos traziam **zero linha** e que o piloto existia "antes de o
> requisito ser cadastrado". Era falso, e a fonte do erro era minha: o parser de
> exploração exigia letras na sigla (`[A-Z]{2,4}\d{3,4}`) e era **cego a `2000101`**.
> Quem derrubou a afirmação foi o primeiro ciclo de TDD: o T54, escrito sobre a premissa
> errada, falhou com a linha que eu jurava não existir. Duas lições, e a segunda é a
> cara: (a) classificar antes de olhar a distribuição dos valores apaga justamente a
> categoria inesperada; (b) **o `//` entre medir e registrar é onde o erro entra** — este
> §9 recebeu o fato às 16h e o desmentiu às 18h, e o que separou os dois foi um teste que
> falhou, não uma releitura. Medição de exploração não é fato até um teste dependê-la.

**A ausência tem quatro formas e nenhuma é "não precisa de nada":** bloco com zero linhas
(MAT2455 em 3023), zero blocos na página inteira (**PTC3313: 26.623 B, nenhum curso**),
curso não informado, e sigla inexistente. PTC3314, PTC3360 e PTC3361 aparecem só sob 3032,
6º período — da ênfase (7º) e do módulo (9º) em diante, estruturas que viram curso novo,
esse endpoint não registra nada.

**Três tipos de exigência, e o `stamtrrcp` é o discriminador.** Cruzando HTML e DWR no
mesmo par: `PR`+`stamtrrcp=N` = "Requisito" (duro), `PR`+`stamtrrcp=S` = "Requisito fraco"
(matricula devendo), `CR`+`N` = "Indicação de Conjunto" (cursa junto). **Mapeamento de 3
pontos, não lei.** O tipo é propriedade do currículo, não do par: MAT2454 é duro em 3250
(Minas) e fraco em 3032 (Elétrica). O `formatar()` que está na `main` imprime os três sob
"Pré-requisito:" e descarta `stamtrrcp` — o correquisito vira exigência prévia, e "fraco"
some. Dois defeitos, um deles resposta errada.

**Dois "não verificado" do §8 do recon fecham:** `pubObterInfoCurso {3033,0}` devolve
**objeto vazio** (196 B) e não serve de fonte de vigência — nenhum payload do Jupiter tem
campo de vigência, e a lista de ingresso é a única âncora que existe.

**Hipótese rejeitada, registrada para ninguém tentar de novo:** `codclg` como prefixo de
`codcur`. Oito dos 47 colegiados (`1 2 3 5 6 7 8 9`) são prefixo de outro, então `27223`
pode ser da unidade `2` ou da `27`. Derivar unidade de código de curso é chute. Testar
*pertencimento* nos ≤2 candidatos, não.

**Decisão:** a pergunta passa a ser respondida pela **sigla**, não pelo curso — ferramenta
`requisitos(sigla)` sobre `listarCursosRequisitos`, que devolve todos os currículos com
tipo e período, cada um rotulado como curso de ingresso ou não. A ferramenta `curso` de
navegação unidade→curso **sai desta fatia**: a medição mostrou que ela não destrava o
pré-requisito, destrava a grade curricular, que é outra pergunta.

**Erro de método desta sessão.** O primeiro script de recon colapsou todo rótulo que não
fosse "Conjunto" em `PR`, e por isso eu não vi o terceiro tipo — "Requisito fraco", que é
30 das 33 linhas das fixtures. O que o revelou foi rodar o parser contra a fixture salva e
**ler a saída**, não a suposição. Classificar antes de olhar a distribuição dos valores
apaga exatamente a categoria que não se esperava.

### 14/09/2026 — a ferramenta `requisitos`, e três defeitos que a suíte não via

Implementação da fatia desenhada acima, por TDD. **463 verdes, 8 pulados** (os canários
`live` das três trilhas), gate limpo. Módulo novo `usp_mcp/jupiter/requisitos.py`
(recorte), mais `ferramentas.requisitos` e a segunda ferramenta na fronteira.

**O primeiro RED derrubou um fato desta mesma sessão**, registrado em detalhe na correção
acima: os sete currículos que eu tinha dado como vazios exigem `2000101`, e o cego era o
meu parser de exploração. O teste que falhou foi escrito a partir do §9 errado — ou seja,
**o §9 errado é que produziu o teste que o corrigiu**. Vale como método: registrar o fato
por escrito é o que permite que ele seja testado e derrubado; medição que fica só na janela
da conversa não tem como falhar em lugar nenhum.

**O handshake achou o segundo.** `main()` registrava `listar_ferramentas()[0]` — com uma
ferramenta só, correto; com duas, a segunda ficava **declarada e nunca anunciada no fio**.
A suíte em processo (T45-T48) estava verde: ela lê o que `main()` registrou, e `main()`
registrou o que ela esperava. Quem viu foi `tests/handshake/`, que compara o anunciado com
o declarado. É a terceira vez que a assimetria "declarado × anunciado" morde neste repo, e
a primeira em que o teste já existia antes do bug.

**O terceiro fui eu que criei e o handshake matou em 4 minutos.** Ao registrar a segunda
ferramenta, deduplicei o `try/except ErroJupiter` num decorator. O SDK deriva o schema da
**assinatura**, e o wrapper `*args/**kwargs` fez o modelo ver uma ferramenta de dois
parâmetros chamados `args` e `kwargs` — H6 e H7 vermelhos na mesma rodada. A duplicação do
`except` voltou, agora com o motivo escrito ao lado: **abstração que atravessa a fronteira
do SDK custa o schema.**

**Dois defeitos de resposta, não de omissão, corrigidos:** correquisito saía sob o rótulo
"Pré-requisito:" (PSI3322 pode ser cursada JUNTO com PSI3323, e o aluno adiaria um ano), e
`stamtrrcp` era descartado, então "Requisito fraco" — dá para matricular devendo — era
indistinguível do duro. Os dois estavam na `main` desde 31/08, com a suíte verde: nenhum
teste olhava o RÓTULO, só a presença da sigla.

**Superfície.** A allowlist DWR foi de 2 para 4 consultas (`pubListarCursoEntrada` e
`pubListarColegiado`, ambas só para marcar pertencimento à lista de ingresso), e a trava do
T23 subiu junto — ela exige decisão registrada por consulta nova, e foi ela que travou o
commit até este parágrafo existir. Uma allowlist **nova, de caminho**, guarda o GET de HTML:
`listarCursosRequisitos` é o único caminho permitido, e `obterTurma` é o caso que mostra por
quê — mesmo host, mesmo parâmetro, e traz nome de professor e sala.

**Custo medido na saída real:** 30.720 B → **511 B** (PTC3314), 66.116 B → **5.855 B**
(MAT2455, 23 currículos). Canários T74-T75 verdes contra a USP.

**O que a ferramenta declara não saber:** em que currículo você está. Ela mostra todos e
marca qual é curso de ingresso — sem chamar de "extinto" o que não é ingresso, porque
ênfase e módulo também ficam de fora da lista e o JupiterWeb não distingue os três.

### 14/09/2026 — a superfície pública do Jupiter cobre só a metade de entrada do curso

Quatro chamadas a `pubGradeCurricular`, uma por curso de ingresso da Poli, escolhidas à
mão. A pergunta era se a fatia `curso` — adiada em 14/09 por não destravar o
pré-requisito — destrava ao menos "o que falta pra formar".

| curso | disciplinas | semestres ideais |
|---|---|---|
| 3033 Ciclo Básico - Eng Elétrica | 67 | **1–5** |
| 3123 Habilitação: Eng de Computação | 28 | **1–4** |
| 3084 Habilitação: Eng de Produção | 33 | **1–5** |
| 3045 Habilitação: Eng Mecânica | 30 | **1–4** |

**Nenhum passa do 5º semestre**, nem os que se chamam "Habilitação". Some-se ao que já
havia sido medido no mesmo dia: `pubListarCursoEntrada` só lista curso de **ingresso**;
`pubGradeCurricular` do 3032 (que carrega os requisitos da Elétrica) vem **vazia**; e
`listarCursosRequisitos` de PTC3313 devolve 26 kB com **zero** currículo.

**A conclusão, e ela é uma limitação do produto, não uma tarefa pendente:** a superfície
pública estruturada do JupiterWeb é o **catálogo de entrada**. Da ênfase (7º semestre) e
do módulo (9º) em diante — exatamente onde o dono está — não há grade, não há requisito e
não há código de curso alcançável. O §5.4 do recon já dizia que o Jupiter público é
"catálogo institucional, não perfil de aluno"; agora está medido que ele nem sequer é o
catálogo **inteiro**.

**Consequência de escopo, decidida aqui:** a fatia `curso` **não será construída** para
responder "o que falta pra formar". Ela responderia isso para um calouro e devolveria um
currículo que termina antes das matérias do dono começarem — o mesmo erro da fatia de
requisitos, evitado desta vez por quatro chamadas em vez de uma implementação. Se algum
dia ela existir, será por outra pergunta ("essa disciplina é obrigatória no ciclo
básico?"), registrada no §5 como todas as outras.

**O que isso deixa em aberto, e é a limitação a declarar:** nota, histórico, evolução do
curso e saldo do RUCard **não têm caminho público**. Todos exigem a área logada, que não
oferece token — só sessão de navegador, com dois cookies (§ nota do recon de 14/09) e
timeout não medido. Enquanto essa medição não acontecer, o projeto **não responde** essas
perguntas, e é melhor dizer isso do que ter ferramenta que responde pela metade.

### 14/09/2026 — o projeto vira pacote instalável, e são **três** entry points, não um

O B1 do ROADMAP diz que "rodar fora do Claude Code" e o onboarding são o **mesmo**
trabalho, e que o degrau que fecha os dois é publicar como pacote com entry point — o
que o comparável `loyaniu/moodle-mcp` já faz (`[project.scripts] moodle-mcp =
"moodle_mcp.server:main"`). Feito: `pyproject.toml` com `usp-mcp-jupiter`,
`usp-mcp-moodle` e `usp-mcp-rucard`.

**A decisão de desenho foi quantos entry points**, e a alternativa era um só com
argumento de sistema, espelhando o `scripts/servidor.sh`. Perdeu por três motivos:

1. Um entry point com argumento exige um **despachante novo em Python** que
   reimplementa o que o lançador já faz — descobrir os sistemas pelo glob, recusar o
   nome errado antes de subir o interpretador, citar os válidos na negativa. Passariam
   a existir duas respostas para "quais sistemas existem", em duas linguagens. É o
   molde exato do defeito do `[ -f .env ]`, que este §9 registra três vezes (gate,
   `token.sh`, `ws.sh` — 12/09/2026).
2. Os três `main()` já existem e já são exercitados **como processo real**
   (`tests/handshake/`, L1/L2). Três console scripts apontando para eles custam **zero
   linha de runtime nova**; o despachante custaria um módulo novo exatamente na casca
   stdio — o lugar onde este projeto já teve um `main()` quebrado com a suíte verde
   (31/08/2026).
3. O nome do comando fica **idêntico ao `serverInfo.name`** que o servidor responde no
   `initialize`. P4 trava a fórmula do lado do pacote; L2 já travava a do lado do fio.

O preço de três é lembrar do quarto quando um quarto sistema nascer. Curado como o
repo cura isso em todo lugar: **P1 deriva o conjunto esperado do glob
`usp_mcp/*/server.py`** e reprova se a tabela divergir.

**`pytest` não é dependência de runtime, e agora há teste dizendo isso.** O núcleo dos
três sistemas é stdlib pura (31/08/2026) e é por isso que o import do SDK mora dentro
de `main()`; `dependencies = ["mcp>=2,<3"]` e nada mais. P2 reprova se `pytest`
aparecer e reprova se o `pyproject.toml` divergir do `requirements.txt` — que **não
some**, porque os três `main()` citam `requirements.txt` pelo nome na mensagem de SDK
ausente e há teste sobre essa frase.

**O dado, medido à mão em venv limpo (Python 3.14.7, fora do checkout):**

| passo | resultado |
|---|---|
| `pip install -e <checkout>` | `usp-mcp-0.1.0`, 28 pacotes, `mcp==2.2.0` |
| `pytest` no venv de runtime | **ausente** (0 ocorrências em `pip list`) |
| comandos criados | `usp-mcp-jupiter`, `usp-mcp-moodle`, `usp-mcp-rucard` |
| `initialize` de `/tmp`, cliente MCP real | `usp-mcp-rucard` / `usp-mcp-jupiter` / `usp-mcp-moodle`, `version='0.1.0'` nos três |
| `tools/list` de `/tmp` | `[bandejao]`, `[disciplina, requisitos]`, `[o_que_vence, material, baixar_arquivo, diagnostico]` |

Nenhuma chamada à USP: o handshake para antes de `chamar_ferramenta`, que é onde mora
qualquer credencial — a mesma razão pela qual esta camada roda no gate.

**Um falso-verde foi achado escrevendo o próprio teste, e vale registrar porque a cura
não é óbvia.** P6 localizava o console script por `Path(sys.executable).resolve().parent`.
O `.venv/bin/python` é um **symlink** para o interpretador do sistema, então `.resolve()`
sai do venv e aponta para um `bin/` que nunca teve os comandos — P6 pulava, dentro do
ambiente onde ele é o único teste que verifica a instalação. Salvou o fato de o pulo ser
`skipif` com motivo escrito, e não um `if` calado: apareceu como `sss` na primeira
execução. A porta certa é `sysconfig.get_path("scripts")`.

**O que isto NÃO fez, e é o §6.1:** o `.mcpb` continua não testado. O pacote é o degrau
**anterior** a ele, não o substituto — as duas perguntas que travam o bundle (quanto
atrito o runtime Python devolve numa máquina limpa, e onde o `"sensitive": true` do
`user_config` guarda o valor) só se respondem com instalação real no Claude Desktop, e
nenhuma delas fica mais perto por causa deste commit. Está no
`docs/decisions/BACKLOG-correcoes.md`.

**Também não medido, e o README diz isso com todas as letras:** `pipx`, `uvx` e instalar
direto da URL do repositório. São portas que o `pyproject.toml` abre; "abre" e "foi
usado" são coisas diferentes, que é a mesma distinção do item 9 do `CLAUDE.md`. Quem
rodar primeiro, registre aqui.

**Licença continua fora** (A1, adiado em 14/09 com "nenhuma por enquanto"). O
`pyproject.toml` não declara nenhuma, de propósito e com o motivo escrito no arquivo:
declarar uma seria decidir por conta própria o que voltou para o dono. O A1 já registra
que empacotar torna a lacuna mais visível, não menos.

### 14/09/2026 — conector remoto descartado, e o que fechou a questão

**Pergunta do dono:** dá para tudo funcionar no chat do Claude, no celular e no Cowork,
por conta de cada pessoa? **Resposta: não, e a questão fica fechada.** Duas condições que
ele pôs tornam o caminho inviável juntas: se for para o chat tem de ser **tudo**, não
metade, e **token de ninguém será guardado**.

**O que foi medido, em 14/09:**

1. **O Claude não passa segredo por usuário fora de OAuth.** Os modos de autenticação de
   conector remoto são `oauth_dcr`, `oauth_cimd`, `oauth_anthropic_creds`,
   `custom_connection`, `static_headers` e `none`. O `static_headers` parece a saída
   ("cada um cola a sua chave") e não é: a credencial é **do administrador da
   organização, compartilhada por todos**. Credencial em query string é proibida pela
   própria spec de autorização do MCP. Sobra OAuth, e OAuth contra um servidor **nosso**.
2. **O e-Disciplinas não tem OAuth.** Medido por requisição não autenticada:
   `/local/oauth/login.php` responde 404. O único OAuth da USP é o da Senha Única
   (`uspdigital.usp.br/wsusuario/oauth`, OAuth 1.0a, o que as bibliotecas `uspdev/
   senhaunica-*` usam). Ele identifica a pessoa e **não** dá acesso ao Moodle.
3. **Nenhum servidor consegue cunhar o token sozinho.** O `launch.php` devolve por
   esquema de URL próprio, e o §1.3 já mediu que trocar por `https` corrompe o valor (o
   base64 cai na posição de host e o navegador minusculiza). E `/login/token.php`, que
   resolveria com usuário e senha, não serve aqui: a USP é `typeoflogin=3`, SSO, sem
   senha local para comparar (§1.3).

**A conclusão que amarra os três:** para o Moodle responder por conta num servidor
remoto, a pessoa teria de obter o token na máquina dela, como hoje, e **entregá-lo a
nós**. Isso é custódia de credencial de terceiro, que a segunda condição do dono proíbe e
que o Invariante 4 já proibia. Não existe arquitetura que evite, e foi procurada.

**O que fica descartado por consequência, e não por falta de vontade:** o conector remoto
autenticado. O §6 seguia registrando que para RUCard e Jupiter, que são dado público, o
remoto "continua viável". Continua **tecnicamente** viável, e passa a estar fora de
escopo pela primeira condição: um conector com três das sete ferramentas é o parcial que
o dono recusou.

**O que NÃO muda:** o entrypoint local segue sendo o caminho, e o `.mcpb` do §6.1 segue
sendo o degrau seguinte do empacotamento. Ele é local por definição, então nada aqui o
alcança.

**Se a questão for reaberta um dia**, o que muda o resultado é uma destas três: a USP
passar a oferecer OAuth no e-Disciplinas, o Claude passar a entregar segredo por usuário
sem OAuth, ou a decisão de custódia mudar. Nenhuma das três depende de trabalho nosso.

---
### 14/09/2026 — o RUCard passou a publicar comunicado dentro do cardápio

Chamada ao vivo `bandejao(hoje, almoco)` às 14h: três dos quatro RUs (7, 8 e 9)
terminam o campo `lunch.menu` com `**Os Restaurantes Universitários não fornecem
copos descartáveis. Tragam suas canecas.**` — negrito markdown, linha em branco antes,
nos cinco dias úteis da semana. Fixture pública capturada:
`fixtures/rucard/menu_7_semana_14-09.json` (2.784 B).

A ferramenta imprimia a linha como prato, três vezes na mesma resposta (~75 tokens
de lixo e um "prato" que não existe). É o caso que a docstring de `_itens_e_opcao`
previa como "tolerância, não teste" — para HTML e ` - `, que nunca vieram; o que
veio foi outro.

**Decisão:** linha em negrito de ponta a ponta, ou frase de 6+ palavras terminada em
ponto/exclamação, é comunicado: sai dos itens e entra em `avisos` **uma vez por texto
distinto**, nomeando os RUs. Campo novo `avisos_publicados` por refeição (trava R36
atualizada). Regra de 2 pontos medidos, não lei: comunicado sem negrito e sem ponto
final passa como prato, e isso está escrito no código. Testes R42–R42g.
### 14/09/2026 — `disciplina` responde por seção, e deixa o pré-requisito com `requisitos`

Revisão de má prática nos servidores públicos. Medido em `server.formatar` sobre as
fixtures: "quantos créditos tem PTC3314" é respondida pelo cabeçalho (139 B) e a
ferramenta entregava 3.880 B — 28×; 38% disso era a lista de competências dos objetivos.
O teste de custo (T34) media o dicionário, não o texto, e `ingles=True` (6.452 B) não era
medido em lugar nenhum.

**Decisão:** (a) parâmetro `secoes` (`ementa`, `objetivos`, `programa`, `bibliografia`,
`avaliacao`, `todas`), padrão só `ementa`, cabeçalho sempre, e o que ficou de fora
declarado na última linha (Invariante 7); (b) `codcur`/`codhab` **saem** de `disciplina`:
o §9 de 14/09 já tinha medido que o único código descobrível devolve zero linha, e manter
o parâmetro era oferecer ao modelo o caminho que não responde, com três avisos para
explicar por quê; (c) `pubListarRequisitoDisciplina` sai da allowlist (4 → 3) e
`ClienteJupiter.listar_requisito` some — a fixture DWR dela fica no disco como evidência,
fora da `FATIA`; (d) parágrafo repetido na fonte (bibliografia de PTC3314) sai uma vez;
(e) tetos novos sobre o **texto**: 1.200 B padrão, 5.000 B `todas`, 8.500 B `todas`+inglês.

**Descartado:** um enum de "nível de detalhe" (`resumo`/`completo`). Perguntas reais pedem
uma seção específica ("o que cai", "como é a avaliação"), e o array deixa o modelo pedir
exatamente essa. Testes T80–T80g, T85–T87, T34b–T34d; T31, T33, T76, T78 e T79 removidos
com o caminho que exercitavam.
