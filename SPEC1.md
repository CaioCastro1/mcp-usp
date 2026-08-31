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

- `get_contents` é suficiente para achar material, ou exige N chamadas por módulo?
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
