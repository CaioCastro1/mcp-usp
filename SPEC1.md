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

`uspdigital.usp.br` e `edisciplinas.usp.br` **não são alcançáveis** do sandbox em nuvem do
Cowork nem da VM local que ele expõe — ambos saem por um proxy de egress com allowlist que
só libera um conjunto pequeno de domínios (registries de pacote, `api.anthropic.com`).
Sintoma: `curl` devolve `000`, ou `403` no túnel CONNECT; DNS falha na VM local.

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
  `cashiers`.
- Não há parâmetro de data. Só semana corrente. Histórico exige persistir por conta.
- Ids de interesse do Caio: **6 CENTRAL, 9 QUÍMICAS, 8 FÍSICA, 7 PUSP-CB**. Os outros 14
  RUs existem mas estão fora de escopo por decisão dele. O 7 não serve jantar (não há
  horário publicado, e os 7 jantares vêm fechados) — distinguir "fechado hoje" de "nunca
  serve essa refeição" exige cruzar `/menu` com `workinghours`.
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
