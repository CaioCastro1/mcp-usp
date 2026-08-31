# Catálogo das funções de web service do Moodle da USP (e-Disciplinas)

> **Nenhuma chamada foi feita.** Este documento inteiro foi produzido sem tocar
> `edisciplinas.usp.br/webservice/`, sem `scripts/ws.sh`, sem `scripts/capture.sh` e sem ler o
> token. É a Regra de Ouro do §3.1 aplicada à letra: uma varredura sobre 447 funções passa,
> em algum ponto, por `mod_quiz_start_attempt` e `mod_assign_submit_for_grading` com a
> credencial do dono. O catálogo é documentação a partir de fontes que já existem.

Data: 31/08/2026. Alvo: Moodle 5.0.8+ (Build 20260722), serviço *Moodle mobile web service*,
447 funções habilitadas.

---

## 0. Procedência — o que é fato, o que é inferência

O §9 do SPEC registra um número fabricado que virou viés. Para não repetir, cada afirmação
aqui carrega a fonte.

| marca | significado |
|---|---|
| **[fonte]** | lido no código-fonte do Moodle 5.0 (`MOODLE_500_STABLE` no GitHub `moodle/moodle`): `db/services.php` de cada plugin e o `*_parameters()` das classes externas |
| **[fixture]** | lido em `fixtures/moodle/raw/site_info.json` — a lista das 447, capturada em 28/08/2026 |
| **[notas]** | medido na Fase 1 e registrado em `notas/fase1-moodle.md` / §9 do SPEC |
| **[inferência]** | dedução minha a partir do nome ou do comportamento análogo. **Não verificado.** Não construir em cima sem confirmar |

**O que não deu para verificar.** 10 das 447 funções vêm de plugins de terceiros cujo
`db/services.php` eu não encontrei publicamente (`mod_journal_*` ×4, `mod_diary_*` ×3,
`mod_dialogue_search_users`, `mod_subcourse_view_subcourse`, `tool_certificate_revoke_issue`).
Para essas, **tudo** abaixo é inferência a partir do nome. Estão marcadas `sem-fonte`.

**A versão do código consultado não é exatamente a que roda na USP.** Consultei
`MOODLE_500_STABLE`; o site é `5.0.8+ (Build 20260722)` com plugins de contribuição próprios
(`mod_checklist` versão `2026042400`, `mod_diary` `2026071109`, `mod_choicegroup` `2026013100`
— todas posteriores ao core). Descrição e classificação read/write vieram do core na branch
5.0; divergências de ponto de versão são possíveis e não foram checadas.

---

## 1. Classes de risco usadas neste catálogo

| classe | definição | contagem |
|---|---|---:|
| `livre` | leitura de dado que é do próprio usuário ou estrutural do curso, sem terceiro identificável | **108** |
| `cuidado` | leitura, mas de dado pessoal, de terceiro, de conteúdo avaliativo ou de credencial | **150** |
| `escrita` | muda estado no servidor da USP e **não** está no §2.2 (inclui as 4 que se declaram `read` e escrevem) | **168** |
| `bloqueada-§2.2` | está na lista de bloqueio permanente do SPEC | **11** |
| `sem-fonte` | plugin de terceiro não localizado; classificação impossível sem chamar | **10** |
| | **total** | **447** |

Ao todo **178 funções mudam estado**: 174 declaram `type => 'write'` **[fonte]** mais 4 que se
declaram `read` e escrevem (§2.1). Dessas 178, o §2.2 alcança **10** — as outras **168** são a
linha `escrita` da tabela.

Contagem gerada por script sobre `site_info.json` cruzado com os `db/services.php` **[fixture+fonte]**.
A fronteira `livre`/`cuidado` é julgamento meu, não um campo da API — declarado como
inferência estruturada, não como fato.

---

## 2. Três achados que mudam como o bloqueio tem que ser implementado

Antes do catálogo, porque afetam a leitura dele inteiro.

### 2.1 O campo `type` do Moodle **não é** uma fronteira de segurança

Cada função declara `'type' => 'read'` ou `'write'` no `db/services.php`. Total: 263 `read`,
174 `write` **[fonte]**. É tentador usar esse campo como o filtro do Invariante 1. **Não
funciona**, e há contraexemplos verificados nos dois sentidos:

| função | declara | o que faz de verdade | fonte |
|---|---|---|---|
| `core_course_set_favourite_courses` | `read` | grava a lista de favoritos do usuário | `lib/db/services.php` linha ~767 **[fonte]** |
| `mod_lti_view_lti` | `read` | dispara evento de visualização e **atualiza o status de conclusão** — a própria descrição diz | `mod/lti/db/services.php` **[fonte]** |
| `mod_glossary_prepare_entry_for_edition` | `read` | prepara área de rascunho (cria itemid) | `mod/glossary/db/services.php` **[fonte]** |
| `qtype_stack_library_import` | `read` | "Import a given file from the library" | `db/services.php` do `qtype_stack` **[fonte]** |
| `core_grades_grader_gradingpanel_point_fetch` | `write` | só busca dados do painel (falso positivo, inofensivo) | `lib/db/services.php` **[fonte]** |
| `core_files_get_unused_draft_itemid` | `write` | gera um id de rascunho; inofensivo | `lib/db/services.php` **[fonte]** |

Consequência: **o bloqueio tem que ser por nome, numa lista mantida à mão, não derivado do
campo `type`.**

### 2.2 `tool_mobile_call_external_functions` fura qualquer lista de bloqueio

Esta é a descoberta mais importante do catálogo. A função recebe um array `requests`, cada um
com `function` (nome) e `arguments` (JSON), e executa. O código de 5.0 **[fonte]**,
`admin/tool/mobile/classes/external.php`:

```php
if ($webservicemanager->service_function_exists($request['function'], $token->externalserviceid)) {
    $response = external_api::call_external_function($request['function'], $args, false);
}
```

A **única** verificação é se a função pertence ao mesmo serviço do token — e o serviço do token
do Caio contém as 447. Ou seja: um MCP que bloqueie `mod_quiz_start_attempt` no nome do
parâmetro `wsfunction`, mas deixe passar `tool_mobile_call_external_functions`, não bloqueia
nada. O bypass é uma chamada só:

```
wsfunction=tool_mobile_call_external_functions
&requests[0][function]=mod_assign_submit_for_grading
&requests[0][arguments]={"assignmentid":123,"acceptsubmissionstatement":true}
```

`tool_mobile_call_external_functions` **não está no §2.2** e é o primeiro nome que deveria
entrar.

### 2.3 Uma das quatro funções de quiz bloqueadas pelo §2.2 não existe neste site

`mod_quiz_finish_attempt` **não aparece** nas 447 **[fixture]**. O Moodle 5.0 não expõe esse
nome; finalizar uma tentativa é `mod_quiz_process_attempt` com `finishattempt=true`, e esse
parâmetro está na assinatura **[fonte]**. O §2.2 está certo no efeito (as três que existem
estão bloqueadas) mas bloqueia um nome morto — vale corrigir para o SPEC não dar a impressão
de cobertura que não tem. As outras três existem e estão corretamente listadas.

---

## 3. Domínios prioritários

Profundidade aqui porque são os que tocam as 7 perguntas do §5. Parâmetros extraídos dos
`*_parameters()` do código 5.0 **[fonte]**; `[opt=…]` é `VALUE_DEFAULT` com aquele valor,
`[opcional]` é `VALUE_OPTIONAL`, sem marca é obrigatório.

### 3.1 `core_webservice` — quem sou (1 função)

| função | E/L | risco | parâmetros **[fonte]** |
|---|---|---|---|
| `core_webservice_get_site_info` | leitura | livre | `serviceshortnames` (lista, opcional) |

Devolve `userid`, `username`, `fullname`, versão do site, flags `downloadfiles`/`uploadfiles`
e a lista completa de funções. **É a única forma barata de obter o `userid`** — o §9 já
decidiu que `MOODLE_USERID` sai da configuração e deriva daqui **[notas]**. Custo medido:
31.386 B / ~7.800 tokens, dos quais 447 nomes de função são ~99,7% **[notas]**.

Risco `livre` no sentido de que o dado é do próprio dono. Mas a resposta contém nome completo
e username (nº USP): **fixture precisa de higienização §3.3 antes de commit**.

### 3.2 `core_enrol` — minhas disciplinas e quem mais está nelas (4 funções)

| função | E/L | risco | parâmetros **[fonte]** |
|---|---|---|---|
| `core_enrol_get_users_courses` | leitura | cuidado | `userid` (int, **obrigatório**); `returnusercount` (bool) |
| `core_enrol_get_enrolled_users` | leitura | cuidado | `courseid` (int); `options` (lista name/value) |
| `core_enrol_search_users` | leitura | cuidado | `courseid` (int); `search` (raw); `searchanywhere` (bool); `page`, `perpage`, `contextid` (int, opcionais) |
| `core_enrol_get_course_enrolment_methods` | leitura | livre | `courseid` (int) |

`get_users_courses` é **a raiz de tudo** — dela saem os `courseids` que dão escopo às demais
chamadas e evitam a resposta de 251k tokens do `mod_assign_get_assignments` **[notas]**. É a
única função do conjunto usado na Fase 1 que exige `userid` explícito, e com userid errado
devolve `[]` com HTTP 200 — a falha silenciosa que o Invariante 6 proíbe **[notas]**.
Filtro de semestre corrente: `enddate` no futuro **ou** `startdate` nos últimos 120 dias,
os dois convergem em 10 de 74 **[notas]**.

`get_enrolled_users` e `search_users` devolvem **a turma inteira** com dados de terceiros
(nome, e-mail conforme `maildisplay`, último acesso). Capabilities declaradas:
`moodle/user:viewdetails`, `moodle/course:viewparticipants` **[fonte]**. Nenhuma das 7
perguntas do §5 precisa disso. Recomendação: fora da superfície.

### 3.3 `core_course` — o que tem dentro da disciplina (16 funções)

| função | E/L | risco | parâmetros **[fonte]** |
|---|---|---|---|
| `core_course_get_contents` | leitura | cuidado | `courseid` (int); `options` (lista name/value: `excludemodules`, `excludecontents`, `includestealthmodules`, `sectionid`, `sectionnumber`, `cmid`, `modname`, `modid`) |
| `core_course_get_updates_since` | leitura | cuidado | `courseid` (int); `since` (int, epoch); `filter` (lista de strings) |
| `core_course_check_updates` | leitura | cuidado | `courseid` (int); `tocheck` (lista de `{contextlevel, id, since}`); `filter` (lista) |
| `core_course_get_courses_by_field` | leitura | livre | `field` (alpha: `id`/`ids`/`shortname`/`idnumber`/`category`); `value` (raw, `[opt='']`) |
| `core_course_get_courses` | leitura | livre | `options.ids` (lista de int) |
| `core_course_get_course_module` | leitura | livre | `cmid` (int) |
| `core_course_get_course_module_by_instance` | leitura | livre | `module` (component); `instance` (int) |
| `core_course_get_enrolled_courses_by_timeline_classification` | leitura | cuidado | `classification` (alpha: `past`/`inprogress`/`future`/`all`/`favourites`/`hidden`/`allincludinghidden`); `limit`, `offset`, `sort`, `customfieldname`, `customfieldvalue`, `searchvalue` |
| `core_course_get_enrolled_courses_with_action_events_by_timeline_classification` | leitura | cuidado | idem acima + `eventsfrom`, `eventsto` (int) |
| `core_course_get_recent_courses` | leitura | cuidado | `userid` `[opt=0]`; `limit`, `offset`, `sort` |
| `core_course_search_courses` | leitura | livre | `criterianame` (alpha); `criteriavalue` (raw); `page`, `perpage`; `requiredcapabilities` (lista); `limittoenrolled` (bool); `onlywithcompletion` (bool) |
| `core_course_get_categories` | leitura | livre | `criteria` (lista key/value); `addsubcategories` (bool `[opt=1]`) |
| `core_course_get_user_navigation_options` | leitura | livre | `courseids` (lista de int) |
| `core_course_get_user_administration_options` | leitura | livre | `courseids` (lista de int) |
| `core_course_set_favourite_courses` | **escrita** | escrita | `courses` (lista de `{id, favourite}`) — **declara `read`, ver §2.1** |
| `core_course_view_course` | escrita | escrita | `courseid`; `sectionnumber` `[opt=0]` |

`get_contents` já traz URL direta dos arquivos: os 22 `resource` de PSI3323 não exigiram
chamada extra — só fóruns e assigns pedem função própria, e têm uma **[notas]**. Custo
~14.500 tokens por disciplina; varrer as 10 = ~145k. Sob demanda, uma por vez.

`get_updates_since` é a chamada mais barata do projeto (~100 tokens para 7 dias) e devolve
ponteiro, não conteúdo: diz *qual* cmid mudou e em quê (`discussions`, `submissions`,
`configuration`, `contentfiles`) **[notas]**. É a função certa para decidir se vale gastar
uma chamada cara.

`get_enrolled_courses_by_timeline_classification` com `classification=inprogress` é a
alternativa da própria API ao filtro `startdate`/`enddate` que a Fase 1 derivou à mão
**[fonte]**. **Não foi testada** — não sei se o critério interno do Moodle bate com as 10
disciplinas medidas. Vale uma chamada única, dentro da regra de allowlist do §3.1.

### 3.4 `core_calendar` — o que vence (15 funções)

| função | E/L | risco | parâmetros **[fonte]** |
|---|---|---|---|
| `core_calendar_get_action_events_by_timesort` | leitura | cuidado | `timesortfrom` `[opt=0]`; `timesortto`; `aftereventid` `[opt=0]`; `limitnum` `[opt=20]`; `limittononsuspendedevents` (bool); `userid`; `searchvalue` |
| `core_calendar_get_action_events_by_course` | leitura | cuidado | `courseid`; `timesortfrom`; `timesortto`; `aftereventid`; `limitnum` `[opt=20]`; `searchvalue` |
| `core_calendar_get_action_events_by_courses` | leitura | cuidado | `courseids` (lista); `timesortfrom`; `timesortto`; `limitnum` `[opt=10]`; `searchvalue` |
| `core_calendar_get_calendar_events` | leitura | cuidado | `events` (objeto: `eventids`, `courseids`, `groupids`, `categoryids`); `options` (objeto: `userevents`, `siteevents`, `timestart`, `timeend`, `ignorehidden`) |
| `core_calendar_get_calendar_event_by_id` | leitura | cuidado | `eventid` (int) |
| `core_calendar_get_calendar_day_view` | leitura | cuidado | `year`, `month`, `day`, `courseid`, `categoryid` |
| `core_calendar_get_calendar_monthly_view` | leitura | cuidado | `year`, `month`, `courseid`, `categoryid`, `includenavigation`, `mini`, `day`, `view` |
| `core_calendar_get_calendar_upcoming_view` | leitura | cuidado | `courseid`, `categoryid` |
| `core_calendar_get_calendar_export_token` | leitura | **cuidado — credencial** | *(sem parâmetros)* |
| `core_calendar_get_calendar_access_information` | leitura | livre | `courseid` `[opt=0]` |
| `core_calendar_get_allowed_event_types` | leitura | livre | `courseid` `[opt=0]` |
| `core_calendar_create_calendar_events` | escrita | escrita | `events` (lista com `name`, `description`, `courseid`, `groupid`, `repeats`, `eventtype`, `timestart`, `timeduration`, `visible`, `sequence`) |
| `core_calendar_delete_calendar_events` | escrita | escrita | `events` (lista de `{eventid, repeat}`) |
| `core_calendar_update_event_start_day` | escrita | escrita | `eventid`; `daytimestamp` |
| `core_calendar_submit_create_update_form` | escrita | escrita | `formdata` (raw — form serializado) |

`get_action_events_by_timesort` custa **541 kB / ~135k tokens para 35 eventos**, porque embute
um objeto `course` de 9,5 kB por evento; os campos que respondem à pergunta somam 132 bytes por
evento — proporção ~1000:1 **[notas]**. É o argumento mais forte do projeto a favor de projetar
no servidor.

**`get_calendar_export_token` mina uma credencial permanente.** Verifiquei a derivação no
fonte, `calendar/lib.php` **[fonte]**:

```php
function calendar_get_export_token(stdClass $user): string {
    return sha1($user->id . $DB->get_field('user','password',['id'=>$user->id]) . $CFG->calendar_exportsalt);
}
```

Isso **fecha o item do §1.4** que estava como "apenas recordado": o `authtoken` do iCal **de
fato** deriva do hash da senha. Duas consequências:

1. Quem tem a URL `/calendar/export_execute.php?userid=…&authtoken=…` lê o calendário inteiro,
   sem token de web service e sem sessão. É uma credencial *bearer* em texto plano numa URL.
2. Ela rotaciona quando o hash de senha do usuário muda. **[inferência]** Numa conta de SSO,
   onde não há senha local (o §1.3 já mostrou que `login/token.php` falha por isso), o campo
   `password` provavelmente é um placeholder constante — então a URL nunca rotaciona sozinha.
   Não verificado; seria verificável só olhando o banco, o que não temos.

O feed iCal entrega 37 eventos em 18 kB contra 35 em 541 kB da função de calendário — ~1/30 do
custo **[notas]**. Vale como caminho preferido para "o que vence", **desde que a URL seja
tratada como segredo**: nunca no log, nunca na saída de uma ferramenta, nunca em fixture
commitada.

**Cobertura de prova presencial:** o §9 (28/08) corrigiu isso — o calendário *cobre* prova
presencial quando o professor a modela como `assign` com `duedate` (PTC3314 tem duas), e não
cobre quando o professor anuncia no fórum (PSI3323) **[notas]**. Não é limite estrutural, é
prática de professor.

### 3.5 `mod_assign` — entregas (24 funções)

O domínio mais perigoso do catálogo: 24 funções, **13 de escrita**, e apenas 2 delas
bloqueadas pelo §2.2.

**Leitura**

| função | risco | parâmetros **[fonte]** |
|---|---|---|
| `mod_assign_get_assignments` | cuidado | `courseids` (lista, `[opt=[]]` → **todas as matrículas**); `capabilities` (lista); `includenotenrolledcourses` (bool) |
| `mod_assign_get_submission_status` | cuidado | `assignid` (int); `userid` `[opt=0]`; `groupid` `[opt=0]` |
| `mod_assign_get_grades` | cuidado | `assignmentids` (lista de int); `since` `[opt=0]` |
| `mod_assign_get_submissions` | cuidado | `assignmentids` (lista); `status` (alpha); `since`; `before` |
| `mod_assign_get_participant` | cuidado | `assignid`; `userid`; `embeduser` (bool) |
| `mod_assign_list_participants` | cuidado | `assignid`; `groupid`; `filter`; `skip`; `limit`; `onlyids`; `includeenrolments`; `tablesort` |
| `mod_assign_get_user_flags` | cuidado | `assignmentids` (lista) |
| `mod_assign_get_user_mappings` | cuidado | `assignmentids` (lista) |

`get_assignments` **sem `courseids` devolve as 74 disciplinas: 1 MB, ~251k tokens, 303
assigns**; com os 10 do semestre, 38 kB / ~9,5k — 96,2% menor **[notas]**. O parâmetro tem
default vazio, então **esquecer o escopo é o modo de falha padrão**, não a exceção.

`get_submission_status` responde "já entreguei?" — `submission.status = "submitted"` com
`timemodified` — mas **não traz nota**: não há `feedback` no payload **[notas]**. É uma
chamada por assign (~260 tokens); 20 assigns = ~5k tokens em 20 idas. Barato em token, caro em
latência.

`get_submissions`, `get_grades`, `list_participants`, `get_participant` e `get_user_flags`
aceitam ids de assign e devolvem dados **de todos os participantes** que a capability permitir
— `mod/assign:viewgrades` **[fonte]**. Para as perguntas do §5 são desnecessárias.

**Escrita**

| função | risco | o que faz **[fonte]** | parâmetros |
|---|---|---|---|
| `mod_assign_save_submission` | **bloqueada-§2.2** | grava o conteúdo da entrega | `assignmentid`; `plugindata` (objeto) |
| `mod_assign_submit_for_grading` | **bloqueada-§2.2** | entrega para correção | `assignmentid`; `acceptsubmissionstatement` (bool) |
| `mod_assign_start_submission` | escrita | **inicia a entrega quando o assign tem limite de tempo** — liga o cronômetro | `assignmentid` |
| `mod_assign_remove_submission` | escrita | apaga a entrega | `assignmentid` |
| `mod_assign_save_grade` | escrita | lança nota de um aluno | `assignmentid`; `userid`; `grade` (float); `attemptnumber`; `addattempt`; `workflowstate`; `applytoall`; `plugindata`; `advancedgradingdata` |
| `mod_assign_save_grades` | escrita | lança notas em lote | `assignmentid`; `applytoall`; `grades` (lista) |
| `mod_assign_submit_grading_form` | escrita | submete o formulário de correção | `assignmentid`; `userid`; `jsonformdata` (raw) |
| `mod_assign_set_user_flags` | escrita | trava/destrava aluno, prorroga prazo, muda estado de workflow | `assignmentid`; `userflags` (lista com `locked`, `extensionduedate`, `workflowstate`, `allocatedmarker`) |
| `mod_assign_save_user_extensions` | escrita | prorroga prazo de alunos | `assignmentid`; `userids`; `dates` |
| `mod_assign_lock_submissions` | escrita | impede alunos de editar | `assignmentid`; `userids` |
| `mod_assign_unlock_submissions` | escrita | libera edição | `assignmentid`; `userids` |
| `mod_assign_revert_submissions_to_draft` | escrita | reverte entregas para rascunho | `assignmentid`; `userids` |
| `mod_assign_reveal_identities` | escrita | **quebra o anonimato de correção cega, irreversível** | `assignmentid` |
| `mod_assign_view_assign` | escrita | "Update the module completion status" | `assignid` |
| `mod_assign_view_grading_table` | escrita | dispara evento de log | `assignid` |
| `mod_assign_view_submission_status` | escrita | dispara evento de log | `assignid` |

**`mod_assign_start_submission` é o análogo exato de `mod_quiz_start_attempt` e não está
bloqueado.** O §2.2 justifica o bloqueio do quiz por "queimar uma tentativa de prova real"; um
assign com limite de tempo tem o mesmo problema — a descrição do core é literal: *"Start a
submission for user if assignment has a time limit"* **[fonte]**.

### 3.6 `mod_forum` — onde mora o aviso do professor (18 funções)

**Leitura**

| função | risco | parâmetros **[fonte]** |
|---|---|---|
| `mod_forum_get_forums_by_courses` | cuidado | `courseids` (lista, `[opt=[]]` → todos) |
| `mod_forum_get_forum_discussions` | cuidado | `forumid`; `sortorder` `[opt=-1]`; `page` `[opt=-1]`; `perpage` `[opt=0]`; `groupid` `[opt=0]` |
| `mod_forum_get_discussion_posts` | cuidado | `discussionid`; `sortby` `[opt='created']`; `sortdirection` `[opt='DESC']`; `includeinlineattachments` (bool) |
| `mod_forum_get_discussion_post` | cuidado | `postid` |
| `mod_forum_get_forum_access_information` | livre | `forumid` |
| `mod_forum_can_add_discussion` | livre | `forumid`; `groupid` |

O fórum "Avisos" é onde está o que o calendário não sabe: o anúncio da "Prova Prática P1" de
PSI3323 estava lá, e a prova **não** estava no calendário da disciplina **[notas]**. 4
discussões custam ~2.150 tokens; é a resposta que **menos comprime** de todo o projeto (35%
sobrando após projeção), porque ali o payload *é* o conteúdo **[notas]**.

Risco `cuidado`, não `livre`: os posts trazem nome, foto e id de colegas e do professor.

**Escrita**

| função | risco | o que faz |
|---|---|---|
| `mod_forum_add_discussion` | **bloqueada-§2.2** | abre tópico novo — `forumid`; `subject`; `message`; `groupid`; `options` |
| `mod_forum_add_discussion_post` | **bloqueada-§2.2** (pelo glob `add_discussion*`) | responde num tópico — `postid`; `subject`; `message`; `messageformat`; `options` |
| `mod_forum_update_discussion_post` | escrita | **edita post existente** — `postid`; `subject`; `message` |
| `mod_forum_delete_post` | escrita | **apaga post; se for o post-tópico, apaga a discussão inteira** — `postid` |
| `mod_forum_set_lock_state` | escrita | tranca discussão — `forumid`; `discussionid`; `targetstate` |
| `mod_forum_set_pin_state` | escrita | fixa discussão — `discussionid`; `targetstate` |
| `mod_forum_set_subscription_state` | escrita | inscreve/desinscreve — `forumid`; `discussionid`; `targetstate` |
| `mod_forum_toggle_favourite_state` | escrita | favorita — `discussionid`; `targetstate` |
| `mod_forum_mark_posts_read` | escrita | marca como lido — `postids`; `discussionid` |
| `mod_forum_prepare_draft_area_for_post` | escrita | cria rascunho — `postid`; `area`; `draftitemid`; `filestokeep` |
| `mod_forum_view_forum` | escrita | evento + conclusão — `forumid` |
| `mod_forum_view_forum_discussion` | escrita | evento — `discussionid` |

O glob `mod_forum_add_discussion*` do §2.2 cobre as duas funções de *criar*. **Não cobre
`update_discussion_post` nem `delete_post`** — e apagar o post-tópico apaga a discussão toda
**[fonte]**. Editar e apagar em nome do usuário é o mesmo tipo de dano que o §2.2 quis evitar.

### 3.7 Notas — `gradereport_*` (8) e `core_grades_*` (8)

| função | E/L | risco | parâmetros **[fonte]** |
|---|---|---|---|
| `gradereport_overview_get_course_grades` | leitura | cuidado | `userid` `[opt=0]` |
| `gradereport_user_get_grade_items` | leitura | cuidado | `courseid` `[opt=0]`; `userid` `[opt=0]`; `groupid` `[opt=0]` |
| `gradereport_user_get_grades_table` | leitura | cuidado | idem (HTML montado) |
| `gradereport_user_get_access_information` | leitura | livre | `courseid` |
| `gradereport_grader_get_users_in_report` | leitura | cuidado | notas **de terceiros** — cap. `gradereport/grader:view` |
| `gradereport_singleview_get_grade_items_for_search_widget` | leitura | cuidado | `courseid` |
| `gradereport_overview_view_grade_report` | escrita | escrita | dispara evento |
| `gradereport_user_view_grade_report` | escrita | escrita | dispara evento |
| `core_grades_get_gradeitems` | leitura | cuidado | itens de nota do curso |
| `core_grades_get_gradable_users` | leitura | cuidado | **lista de terceiros** |
| `core_grades_get_enrolled_users_for_selector` | leitura | cuidado | **lista de terceiros** |
| `core_grades_get_groups_for_selector` | leitura | cuidado | marcada `** DEPRECATED **` no próprio core **[fonte]** |
| `core_grades_grader_gradingpanel_point_fetch` / `_store` | escrita | escrita | painel de correção — `_store` **lança nota** |
| `core_grades_grader_gradingpanel_scale_fetch` / `_store` | escrita | escrita | idem, escala |

O `overview` é a chamada mais barata por unidade de informação do projeto: **70 cursos em ~870
tokens**, três campos por linha (`courseid`, `grade`, `rawgrade`) — serve para "como estou em
tudo". O `grade_items` traz 24 campos por item de **um** curso, ~320 tokens, e é o único que
responde "como estou nessa disciplina, item a item". **Não competem, se complementam** — a
escolha é por pergunta **[notas]**.

Atenção ao default: `gradereport_user_get_grade_items` tem `userid [opt=0]` e `courseid
[opt=0]` **[fonte]**. O que acontece com `courseid=0` **não foi verificado** e não vai ser
verificado sem chamar.

### 3.8 `mod_quiz` — leitura sim, tentativa não (19 funções)

| função | E/L | risco | parâmetros **[fonte]** |
|---|---|---|---|
| `mod_quiz_get_quizzes_by_courses` | leitura | livre | `courseids` (lista, `[opt=[]]` → todos) |
| `mod_quiz_get_user_attempts` | leitura | cuidado | `quizid`; `userid`; `status` `[opt='finished']`; `includepreviews` |
| `mod_quiz_get_user_quiz_attempts` | leitura | cuidado | idem |
| `mod_quiz_get_user_best_grade` | leitura | cuidado | `quizid`; `userid` |
| `mod_quiz_get_quiz_access_information` | leitura | livre | `quizid` |
| `mod_quiz_get_attempt_access_information` | leitura | livre | `quizid`; `attemptid` |
| `mod_quiz_get_quiz_feedback_for_grade` | leitura | cuidado | `quizid`; `grade` (float) |
| `mod_quiz_get_quiz_required_qtypes` | leitura | livre | `quizid` |
| `mod_quiz_get_combined_review_options` | leitura | cuidado | `quizid`; `userid` |
| `mod_quiz_get_attempt_data` | leitura | **cuidado — enunciado de prova** | `attemptid`; `page`; `preflightdata` |
| `mod_quiz_get_attempt_summary` | leitura | cuidado | `attemptid`; `preflightdata` |
| `mod_quiz_get_attempt_review` | leitura | cuidado | `attemptid`; `page` |
| `mod_quiz_start_attempt` | escrita | **bloqueada-§2.2** | `quizid`; `preflightdata`; `forcenew` |
| `mod_quiz_save_attempt` | escrita | **bloqueada-§2.2** | `attemptid`; `data`; `preflightdata` |
| `mod_quiz_process_attempt` | escrita | **bloqueada-§2.2** | `attemptid`; `data`; **`finishattempt` (bool)**; `timeup`; `preflightdata` |
| `mod_quiz_view_quiz` | escrita | escrita | `quizid` — evento + conclusão |
| `mod_quiz_view_attempt` | escrita | escrita | `attemptid`; `page`; `preflightdata` |
| `mod_quiz_view_attempt_summary` | escrita | escrita | `attemptid`; `preflightdata` |
| `mod_quiz_view_attempt_review` | escrita | escrita | `attemptid` |

O calendário **vê quiz, que `get_assignments` não vê** — 6 disciplinas no calendário contra 4
com assign **[notas]**. Para "o que vence", `get_quizzes_by_courses` (com `courseids`
explícito) é a leitura correspondente ao lado do assign, e é `livre`.

`get_attempt_data` devolve **o enunciado das questões** da tentativa em curso. Classificar como
`livre` seria erro: mesmo sem escrever nada, expor conteúdo de prova a um modelo de linguagem é
exatamente o cenário que motiva o §2.2. Ficaria `cuidado` no melhor caso; para as perguntas do
§5 não é necessária nenhuma vez.

`mod_quiz_view_attempt` é `escrita` e o §2.2 não a menciona: ela dispara o evento de
visualização de tentativa, que aparece no relatório do professor.

### 3.9 `core_user` — perfil e preferências (16 funções)

| função | E/L | risco | parâmetros **[fonte]** |
|---|---|---|---|
| `core_user_get_users_by_field` | leitura | cuidado | `field` (`id`/`idnumber`/`username`/`email`); `values` (lista) |
| `core_user_get_course_user_profiles` | leitura | cuidado | `userlist` (lista de `{userid, courseid}`) |
| `core_user_get_user_preferences` | leitura | cuidado | `name` `[opt='']`; `userid` `[opt=0]` |
| `core_user_get_private_files_info` | leitura | cuidado | `userid` `[opt=0]` |
| `core_user_view_user_profile` | **escrita** | escrita | `userid`; `courseid` — registra que você olhou o perfil de alguém |
| `core_user_view_user_list` | **escrita** | escrita | `courseid` |
| `core_user_set_user_preferences` | escrita | escrita | `preferences` (lista `{name, value, userid}`) — cap. **`moodle/site:config`** **[fonte]** |
| `core_user_update_user_preferences` | escrita | escrita | `userid`; `emailstop`; `preferences` |
| `core_user_update_picture` | escrita | escrita | `draftitemid`; `delete` (bool); `userid` |
| `core_user_agree_site_policy` | escrita | escrita | *(sem parâmetros)* — **aceita o termo de uso do site em nome do usuário** |
| `core_user_add_user_private_files` | escrita | escrita | `draftid` |
| `core_user_update_private_files` | escrita | escrita | `draftid` |
| `core_user_prepare_private_files_for_edition` | escrita | escrita | — |
| `core_user_add_user_device` | escrita | escrita | `appid`; `name`; `model`; `platform`; `version`; `pushid`; `uuid`; `publickey` |
| `core_user_remove_user_device` | escrita | escrita | `uuid`; `appid` |
| `core_user_update_user_device_public_key` | escrita | escrita | — |

Duas coisas incomodam aqui. `core_user_view_user_profile` e `view_user_list` são **escrita**
com nome de leitura: elas gravam no log da USP que aquela conta consultou aquele perfil. E
`core_user_agree_site_policy` aceita, sem argumento nenhum, um documento jurídico em nome do
dono do token.

Nenhuma função de `core_user` responde qualquer uma das 7 perguntas do §5. O `userid` sai do
`site_info`.

### 3.10 `tool_mobile` — a superfície mais perigosa (8 funções)

| função | tipo decl. | risco | parâmetros **[fonte]** |
|---|---|---|---|
| `tool_mobile_call_external_functions` | write | **escrita — bypass, ver §2.2 deste doc** | `requests` (lista de `{function, arguments, settingraw, settingfilter, settingfileurl, settinglang}`) |
| `tool_mobile_get_autologin_key` | write | **bloqueada-§2.2** | `privatetoken` (alphanum) |
| `tool_mobile_get_tokens_for_qr_login` | **read** | **bloqueada-§2.2** | `qrloginkey`; `userid` |
| `tool_mobile_get_config` | read | cuidado | `section` (alphanumext, `[opt='']`) |
| `tool_mobile_get_public_config` | read | livre | *(sem parâmetros)* |
| `tool_mobile_get_content` | read | cuidado | `component`; `method`; `args` (lista) |
| `tool_mobile_get_plugins_supporting_mobile` | read | livre | *(sem parâmetros)* |
| `tool_mobile_validate_subscription_key` | write | escrita | `key` (raw) |

Duas observações que o §2.2 não registra:

- **`get_tokens_for_qr_login` declara `type => 'read'`** **[fonte]**. Ela minta um token de web
  service e o `privatetoken`, e ainda assim é `read` para o Moodle. Reforço do §2.1: o campo
  `type` não protege ninguém.
- **`tool_mobile_get_content`** aceita `component` + `method` + `args` e devolve conteúdo
  renderizado por um plugin arbitrário **[fonte]**. É um segundo despachante genérico, menos
  poderoso que `call_external_functions` mas da mesma família. **[inferência]** sobre o alcance
  exato: só li a assinatura, não o corpo. Merece cautela até ser lido.

### 3.11 Domínios de apoio — `core_completion`, `core_group`, `core_files`, `core_search`

| função | E/L | risco | parâmetros **[fonte]** |
|---|---|---|---|
| `core_completion_get_activities_completion_status` | leitura | cuidado | `courseid`; `userid` |
| `core_completion_get_course_completion_status` | leitura | cuidado | `courseid`; `userid` — cap. `report/completion:view` |
| `core_completion_mark_course_self_completed` | escrita | escrita | `courseid` |
| `core_completion_update_activity_completion_status_manually` | escrita | escrita | `cmid`; `completed` (bool) |
| `core_group_get_course_user_groups` | leitura | cuidado | `courseid`; `userid`; `groupingid` |
| `core_group_get_course_groups` | leitura | cuidado | `courseid` — cap. `moodle/course:managegroups` |
| `core_group_get_activity_allowed_groups` | leitura | cuidado | `cmid`; `userid` |
| `core_group_get_activity_groupmode` | leitura | livre | `cmid` |
| `core_group_get_course_groupings` | leitura | cuidado | `courseid` |
| `core_group_get_groups_for_selector` | leitura | cuidado | `courseid` |
| `core_files_get_files` | leitura | cuidado | `contextid`; `component`; `filearea`; `itemid`; `filepath`; `filename`; `modified`; `contextlevel`; `instanceid` |
| `core_files_delete_draft_files` | escrita | escrita | área de rascunho do usuário |
| `core_files_get_unused_draft_itemid` | escrita | escrita | inofensiva na prática |
| `core_search_get_results` | leitura | cuidado | busca global — cap. `moodle/search:query` |
| `core_search_get_top_results` | leitura | cuidado | idem |
| `core_search_get_search_areas_list` | leitura | livre | — |
| `core_search_view_results` | escrita | escrita | dispara evento |

`core_completion_get_activities_completion_status` é candidata interessante e **não foi testada
na Fase 1**: ela diz, por cmid, se a atividade está concluída — potencialmente uma leitura
barata para "o que falta". Não sei o custo nem se professores desta USP configuram conclusão.
**[inferência]** de utilidade; medir antes de prometer.

`core_search_get_results` responderia "onde está o PDF da aula de hoje?" numa chamada só.
**Não testada**, e o site pode ter busca global desabilitada — o `moodle/search:query` é
capability, não garantia de que o índice existe.

---

## 4. Domínios secundários — sumário

Nenhum destes responde às perguntas do §5. Estão aqui completos, mas sem parâmetros.

### 4.1 `core_message` — 41 funções, a maior família do catálogo

**17 leituras** de conversas, contatos, notificações e preferências — todas `cuidado`, porque
mensagem privada de terceiro é o dado mais sensível que este token alcança. **24 escritas**,
das quais o §2.2 bloqueia **uma** (`send_instant_messages`).

Os dois caminhos de envio: `core_message_send_instant_messages` (bloqueado) e
**`core_message_send_messages_to_conversation`** (não bloqueado) — envia para uma conversa
já existente **[fonte]**. Ver §6.

Destrutivas não bloqueadas: `delete_message`, `delete_message_for_all_users`,
`delete_conversations_by_id`, `delete_contacts`. Sociais não bloqueadas: `create_contact_request`,
`confirm_contact_request`, `decline_contact_request`, `block_user`, `unblock_user`.
Cosméticas: `mute_conversations`, `unmute_conversations`, `set_favourite_conversations`,
`unset_favourite_conversations`, `mark_*_read` (5), `message_processor_config_form`.

### 4.2 Atividades com ciclo de tentativa avaliada — o mesmo risco do quiz

`mod_lesson` (17): leituras de páginas, tentativas e notas; e **`launch_attempt`,
`process_page`, `finish_attempt`** — o ciclo completo de uma tentativa avaliada, exatamente o
que o §2.2 bloqueia no quiz, **sem nenhum bloqueio equivalente**.

`mod_workshop` (19): leituras de submissões e avaliações de colegas; e **`add_submission`,
`update_submission`, `delete_submission`, `update_assessment`, `evaluate_assessment`,
`evaluate_submission`** — entrega e avaliação por pares, o análogo de `mod_assign`, também sem
bloqueio.

`mod_scorm` (9): leituras de scoes e tracking; **`insert_scorm_tracks`** grava dados de
rastreamento que alimentam nota, **`launch_sco`** dispara evento.

`mod_h5pactivity` (7): só leitura e `view_*`/`log_report_viewed`. Mas o resultado de H5P entra
por **`core_xapi_statement_post`** (ver 4.5).

`mod_feedback` (14) e `mod_questionnaire` (1): pesquisas. **`launch_feedback`**, **`process_page`**
e **`submit_questionnaire_response`** enviam resposta em nome do usuário — irreversível na
prática, mesmo não valendo nota.

`mod_choice` (6) e `mod_choicegroup` (4): escolhas e **inscrição em grupo**.
`submit_choice_response` / `submit_choicegroup_response` ocupam vaga — afetam colegas.
`delete_*_responses` desfazem.

### 4.3 Conteúdo colaborativo — escrita visível para a turma

`mod_glossary` (18): 14 leituras + `add_entry`, `update_entry`, `delete_entry`,
`prepare_entry_for_edition` (declarada `read`, escreve).

`mod_data` (11): leituras + `add_entry`, `update_entry`, `delete_entry`, **`approve_entry`**
(modera entrada de colega), `view_database`.

`mod_wiki` (10): leituras + `new_page`, `edit_page`, e **`get_page_for_editing`** — que apesar
do nome de leitura chama `wiki_set_lock()` **[fonte]**, tomando trava exclusiva da página e
**impedindo colegas de editar** até expirar.

`core_blog` (7), `core_comment` (3), `core_rating` (2), `core_notes` (4): postar, comentar,
avaliar e anotar em nome do usuário, tudo visível para outros. Nada bloqueado.

### 4.4 Recursos e materiais — leituras baratas e inócuas

`mod_resource`, `mod_url`, `mod_page`, `mod_folder`, `mod_book`, `mod_imscp`, `mod_label`
(2 funções cada, exceto `mod_label` com 1): um `get_*_by_courses` (`livre`) e um `view_*`
(`escrita` — evento + conclusão).

Para "onde está o PDF" e "qual o link da aula", `core_course_get_contents` já resolve **[notas]**;
os `get_*_by_courses` são alternativa mais estreita, e `mod_url_get_urls_by_courses` é o
caminho direto para links externos.

### 4.5 Aula online, ferramentas externas e IA

`mod_bigbluebuttonbn` (10): `get_bigbluebuttonbns_by_courses`, `meeting_info`, `can_join`,
`get_recordings*` são leitura. Mas **`get_join_url` é `write` e cria a reunião se não existir**
**[fonte]** — e **`end_meeting` encerra uma reunião ao vivo para todo mundo**.
`update_recording` altera gravação de aula.

`mod_zoom` (2): `get_state` (leitura) e `grade_item_update` (**escrita**, "creates or updates
grade item ... and returns join url" **[fonte]** — o link da aula vem com efeito colateral em
item de nota).

`mod_lti` (3): `get_ltis_by_courses`, `view_lti` (declarada `read`, atualiza conclusão) e
**`get_tool_launch_data`**, que devolve os parâmetros assinados de lançamento para a ferramenta
externa — na prática, uma credencial de acesso a um sistema de terceiro.

`aiplacement_*` (4): `courseassist_explain_text`, `courseassist_summarise_text`,
`editor_generate_text`, `editor_generate_image` — todas **escrita**. Enviam texto do curso para
o provedor de IA configurado pela USP e consomem cota institucional.

`core_ai` (2): `get_policy_status` / **`set_policy_status`** (aceita a política de IA em nome do
usuário).

### 4.6 Administrativo, competências e privacidade

`core_competency` (9) + `tool_lp` (8): leituras de plano de aprendizagem e competências;
`core_competency_grade_competency_in_course` e `delete_evidence` são escrita.

`tool_dataprivacy` (5): `get_access_information`, `get_data_requests` (leitura);
**`create_data_request`**, **`cancel_data_request`**, **`contact_dpo`** — abrem processo formal
de privacidade e mandam e-mail para o Encarregado de Dados da USP. Ver §6.

`tool_policy` (2): `get_user_acceptances` e **`set_acceptances_status`** (aceita/recusa política
em nome do usuário).

`enrol_self` (2): `get_instance_info` (leitura) e `enrol_user` (**bloqueada-§2.2**).
`enrol_guest` (2): `get_instance_info` e **`validate_password`** — declarada `write`, e é um
oráculo de senha de inscrição de visitante.

`core_badges` (3), `core_block` (3), `core_tag` (5), `core_reportbuilder` (5),
`core_filters` (2), `core_table` (1), `core_question` (1), `core_h5p` (1), `core_my` (1),
`core_get_component_strings` (1), `core_xapi` (6), `editor_tiny` (1), `tiny_premium` (1),
`tool_analytics` (1), `tool_moodlenet` (2), `report_insights` (1),
`message_airnotifier` (4), `message_popup` (2), `block_recentlyaccesseditems` (1),
`block_starredcourses` (1), `qtype_stack` (3), `mod_simplecertificate` (1),
`tool_certificate` (1), `mod_checklist` (1), `mod_journal` (4), `mod_diary` (3),
`mod_dialogue` (1), `mod_subcourse` (1): ver a tabela completa no Apêndice A.

Dois merecem destaque fora do sumário e vão para o §6: **`tiny_premium_get_api_key`** e
**`core_xapi_statement_post`**.

---

## 5. Mapa: pergunta do §5 → funções

As 7 perguntas candidatas do §5, com as funções que **poderiam** responder. Isto é mapa de
candidatas, **não é desenho de ferramenta** — o §5 é explícito que o mapeamento é resultado da
Fase 1, e o Anexo A avisa contra derivar ferramenta da lista da API.

| # | pergunta do §5 | funções candidatas | situação |
|---|---|---|---|
| 1 | *O que eu tenho que entregar até domingo, e o que disso eu já entreguei?* | `core_enrol_get_users_courses` (escopo) → `mod_assign_get_assignments` (com `courseids`) + `mod_quiz_get_quizzes_by_courses` + `core_calendar_get_action_events_by_timesort` **ou** o feed iCal; depois `mod_assign_get_submission_status` por assign | **medido** **[notas]**. iCal cobre "o que vence" por 1/30 do custo; "já entreguei" só sai do `submission_status`, 1 chamada por assign. Fórum entra porque nem toda prova está no calendário |
| 2 | *Como estou de nota nessa disciplina?* | `gradereport_user_get_grade_items` (item a item, 1 curso, ~320 tok) e `gradereport_overview_get_course_grades` (tudo, ~870 tok) | **medido** **[notas]**. As duas visões se complementam; escolher por pergunta |
| 3 | *O professor avisou alguma coisa desde ontem?* | `core_course_get_updates_since` (ponteiro, ~100 tok) → `mod_forum_get_forums_by_courses` → `mod_forum_get_forum_discussions` → `mod_forum_get_discussion_posts`; alternativa: `message_popup_get_popup_notifications` | **medido** **[notas]**. `updates_since` é sinal, não ruído; o aviso vive no fórum "Avisos" |
| 4 | *Onde está o PDF da aula de hoje?* | `core_course_get_contents` (URL direta já vem, ~14,5k tok/disciplina); alternativas mais estreitas: `mod_resource_get_resources_by_courses`, `mod_folder_get_folders_by_courses`, `core_search_get_results` | `get_contents` **medido e suficiente** **[notas]**. As alternativas **não testadas** |
| 5 | *Qual o link da aula online?* | `mod_url_get_urls_by_courses`; `core_course_get_contents` (módulos `url` — 7 em PSI3323 **[notas]**); `mod_bigbluebuttonbn_get_bigbluebuttonbns_by_courses`; `mod_zoom_get_state` | **não testada**. Os caminhos "oficiais" de entrar na sala (`mod_bigbluebuttonbn_get_join_url`, `mod_zoom_grade_item_update`) são **escrita** — usar só o `get_contents`/`get_urls` |
| 6 | *O que tem no bandejão hoje?* | **nenhuma função do Moodle** | RUCard, fora deste catálogo **[notas]** |
| 7 | *Essa disciplina tem quantos créditos e qual o pré-requisito?* | **nenhuma função do Moodle responde.** `core_course_get_courses_by_field` traz `summary` em HTML livre, onde a informação *pode* estar | **[inferência]**. Crédito e pré-requisito são do JupiterWeb, que o §1.4 registra como não testado. Não prometer |

Duas perguntas de sete não têm resposta no Moodle. Uma sétima (a 5) só tem resposta parcial e
por caminho indireto. Isso é resultado, não lacuna a preencher com mais funções.

---

## 6. Funções que o SPEC deveria bloquear e ainda não bloqueia

O §2.2 lista 12 nomes (um dos quais não existe neste site, ver §2.3 deste doc). O catálogo tem
**178 funções que mudam estado**, mais um punhado de leituras que entregam credencial. Das 178,
o §2.2 alcança **10**. Sobram **168**.

A conclusão que sai daí antes de qualquer nome específico: **uma lista de bloqueio não escala
para essa superfície.** Manter 168 nomes atualizados através de upgrades do Moodle e de plugins
de contribuição que a USP instala por conta (`mod_checklist`, `mod_diary`, `mod_choicegroup`,
`mod_zoom`, `qtype_stack` — todos com `version` posterior ao core **[fixture]**) é uma promessa
que quebra na primeira atualização. **A postura correta é allowlist**: uma lista curta de
funções permitidas, e tudo o mais negado por default, inclusive nomes que ainda não existem.
O §2.2 vira então a segunda camada — o conjunto que nem uma flag pode ligar.

Dito isso, aqui está o que falta, ordenado por severidade.

### 6.1 Crítico — anula o bloqueio inteiro

| função | tipo decl. | por quê |
|---|---|---|
| **`tool_mobile_call_external_functions`** | write | Executa qualquer função do mesmo serviço por nome, em JSON, em lote. A única checagem no fonte é `service_function_exists(...)` contra o serviço do token, que contém as 447 **[fonte]**. Enquanto ela passar, `mod_quiz_start_attempt` e `mod_assign_submit_for_grading` continuam alcançáveis apesar do §2.2 |

Se apenas um nome for acrescentado ao §2.2, tem que ser este.

**Implicação de implementação:** o bloqueio não pode viver só na camada que monta o parâmetro
`wsfunction`. Precisa valer também para os nomes que aparecem *dentro* de argumentos. A forma
simples de garantir isso é não expor essa função de jeito nenhum.

### 6.2 Credencial — leituras que entregam acesso

O §2.2 já tem essa categoria ("mintam acesso de sessão"), com dois nomes. Faltam quatro.

| função | tipo decl. | por quê |
|---|---|---|
| **`tiny_premium_get_api_key`** | **read** | Devolve `get_config('tiny_premium','apikey')` com `'capabilities' => ''` — **nenhuma capability exigida**, só validação de contexto **[fonte]**. É a chave de API de um serviço pago da instituição, exfiltrável por qualquer token com o mobile service |
| **`core_calendar_get_calendar_export_token`** | read | Devolve `sha1(userid + hash_da_senha + calendar_exportsalt)` **[fonte]**, que compõe uma URL onde **a URL é a credencial**. O §1.3 do SPEC já sabe disso mas o §2.2 não bloqueia. Não precisa ser bloqueio absoluto — precisa ser tratada como segredo: nunca em log, saída de ferramenta ou fixture |
| **`mod_lti_get_tool_launch_data`** | read | Devolve os parâmetros de lançamento assinados para a ferramenta externa. Na prática, credencial de acesso a um sistema de terceiro fora da USP |
| **`enrol_guest_validate_password`** | write | Valida senha de inscrição de visitante. É um oráculo: chamadas repetidas testam senhas de curso |

### 6.3 Entrega e tentativa avaliada — a mesma família que o §2.2 já bloqueou, incompleta

O §2.2 bloqueia entrega em `mod_assign` e tentativa em `mod_quiz`. As atividades abaixo têm
exatamente o mesmo ciclo e nenhum bloqueio.

| função | por quê |
|---|---|
| **`mod_assign_start_submission`** | *"Start a submission for user if assignment has a time limit"* **[fonte]** — liga o cronômetro de uma entrega cronometrada. Análogo direto de `mod_quiz_start_attempt` |
| **`mod_assign_remove_submission`** | apaga a entrega já feita |
| **`mod_lesson_launch_attempt`**, **`mod_lesson_process_page`**, **`mod_lesson_finish_attempt`** | ciclo completo de tentativa avaliada em `mod_lesson`. É `mod_quiz_*` com outro nome |
| **`mod_workshop_add_submission`**, **`update_submission`**, **`delete_submission`**, **`update_assessment`** | entrega e avaliação por pares. Mesmo dano que `mod_assign_save_submission` |
| **`mod_scorm_insert_scorm_tracks`** | grava tracking que alimenta nota |
| **`core_xapi_statement_post`**, **`core_xapi_post_state`**, **`core_xapi_delete_state`**, **`core_xapi_delete_states`** | xAPI é o canal por onde resultado de H5P entra no Moodle. `statement_post` grava resultado de atividade avaliada; os `delete_*` apagam estado salvo **[inferência]** sobre o efeito exato em nota — a semântica xAPI depende da atividade |
| **`mod_feedback_launch_feedback`**, **`mod_feedback_process_page`**, **`mod_questionnaire_submit_questionnaire_response`** | submetem pesquisa em nome do usuário; na prática irreversível |
| **`mod_choice_submit_choice_response`**, **`mod_choicegroup_submit_choicegroup_response`** | ocupam vaga — `choicegroup` **inscreve em grupo de trabalho**, e vaga tomada afeta colegas |
| **`mod_choice_delete_choice_responses`**, **`mod_choicegroup_delete_choicegroup_responses`** | desfazem a escolha |
| **`core_question_update_flag`** | altera o estado de uma questão dentro de uma tentativa de quiz |
| **`mod_checklist_update_item_state`**, **`mod_diary_set_text`**, **`mod_journal_set_text`** | gravam conteúdo do aluno. Plugins de terceiro, **`sem-fonte`** — classificação por nome **[inferência]** |
| **`mod_simplecertificate_create_issue`** | emite certificado |

### 6.4 Fala com terceiros — a categoria do §2.2 está furada

O §2.2 diz "falam com terceiros em nome do usuário" e lista três padrões. Faltam:

| função | por quê |
|---|---|
| **`core_message_send_messages_to_conversation`** | **segundo caminho de envio de mensagem**. O §2.2 bloqueia `send_instant_messages` e deixa este aberto. Manda mensagem para conversa existente — inclusive de grupo |
| **`core_message_create_contact_request`**, **`confirm_contact_request`**, **`decline_contact_request`**, **`block_user`**, **`unblock_user`**, **`delete_contacts`** | agem sobre a relação com outra pessoa; a outra pessoa é notificada |
| **`core_message_delete_message`**, **`delete_message_for_all_users`**, **`delete_conversations_by_id`** | destrutivas e irreversíveis; `for_all_users` apaga do lado do outro |
| **`mod_forum_update_discussion_post`**, **`mod_forum_delete_post`** | editam e apagam post público. Apagar o post-tópico apaga a discussão inteira **[fonte]**. O glob `add_discussion*` do §2.2 não alcança nenhuma das duas |
| **`core_comment_add_comments`**, **`core_comment_delete_comments`** | comentário público em nome do usuário |
| **`core_rating_add_rating`** | avalia o trabalho de um colega |
| **`core_notes_create_notes`**, **`core_notes_delete_notes`** | anotação sobre outra pessoa, visível a professores |
| **`core_blog_add_entry`**, **`update_entry`**, **`delete_entry`** | publicação em nome do usuário |
| **`mod_glossary_add_entry`**, **`update_entry`**, **`delete_entry`**; **`mod_data_add_entry`**, **`update_entry`**, **`delete_entry`**, **`approve_entry`**; **`mod_wiki_new_page`**, **`edit_page`** | conteúdo colaborativo visível à turma. `mod_data_approve_entry` **modera** a entrada de um colega |
| **`mod_wiki_get_page_for_editing`** | nome de leitura, chama `wiki_set_lock()` **[fonte]** — toma trava exclusiva e **bloqueia colegas de editar** |
| **`mod_bigbluebuttonbn_end_meeting`** | **encerra uma reunião ao vivo para todos os participantes** |
| **`mod_bigbluebuttonbn_get_join_url`** | `write`; **cria a reunião se não existir** **[fonte]**. Nome de leitura, efeito de criação |
| **`mod_bigbluebuttonbn_update_recording`** | altera gravação de aula |
| **`mod_zoom_grade_item_update`** | "creates or updates grade item ... and returns join url" **[fonte]** — pedir o link da aula mexe em item de nota |
| **`tool_dataprivacy_contact_dpo`**, **`create_data_request`**, **`cancel_data_request`** | abrem processo formal de proteção de dados e mandam e-mail para o Encarregado da USP. `create_data_request` inclui pedido de **exclusão de dados**. Um modelo interpretando "apaga meus dados dessa disciplina" tem caminho até aqui |

### 6.5 Consentimento — aceitar coisa em nome de gente

Categoria que o §2.2 não tem e deveria.

| função | por quê |
|---|---|
| **`core_user_agree_site_policy`** | aceita o termo de uso do site. Sem parâmetro nenhum **[fonte]** |
| **`tool_policy_set_acceptances_status`** | aceita ou recusa políticas específicas |
| **`core_ai_set_policy_status`** | aceita a política de IA |
| **`core_completion_mark_course_self_completed`** | declara a disciplina como concluída — sinal que o professor vê |
| **`core_completion_update_activity_completion_status_manually`** | marca atividade como concluída manualmente |

### 6.6 Notas de terceiros — só falham se o token não tiver a capability

O Caio é aluno, então **[inferência]** essas devem falhar por permissão. Mas monitoria, PAE ou
qualquer papel de apoio muda isso sem aviso, e um MCP não deveria nem poder tentar.

`mod_assign_save_grade`, `mod_assign_save_grades`, `mod_assign_submit_grading_form`,
`mod_assign_set_user_flags`, `mod_assign_save_user_extensions`, `mod_assign_lock_submissions`,
`mod_assign_unlock_submissions`, `mod_assign_revert_submissions_to_draft`,
**`mod_assign_reveal_identities`** (quebra correção cega, irreversível),
`core_grades_grader_gradingpanel_point_store`, `core_grades_grader_gradingpanel_scale_store`,
`mod_workshop_evaluate_assessment`, `mod_workshop_evaluate_submission`,
`core_competency_grade_competency_in_course`, `core_competency_delete_evidence`,
`report_insights_action_executed`, `tool_certificate_revoke_issue` (**`sem-fonte`**,
classificação por nome **[inferência]**).

### 6.7 A família `_view_*` — 40 escritas que parecem leitura

Cerca de 40 funções chamadas `*_view_*` declaram `type => 'write'`. Elas não gravam conteúdo,
mas fazem duas coisas que importam:

1. **atualizam o status de conclusão da atividade** — a descrição de `mod_assign_view_assign` no
   core é literalmente *"Update the module completion status"* **[fonte]**;
2. **gravam no log da USP**, que professor e admin conseguem ver (o §4 do SPEC pergunta
   justamente se existe log visível — existe, e essas funções escrevem nele).

Consequência prática: chamar `mod_forum_view_forum_discussion` para "ler o aviso" marca a
atividade como vista sem o dono ter visto, e chamar `core_user_view_user_profile` registra que
aquela conta olhou o perfil de alguém.

Nenhuma delas precisa existir num MCP de leitura. **Recomendação: negar o padrão `*_view_*`
inteiro** — é a única regra por padrão que eu recomendaria, porque o conjunto é homogêneo e o
benefício é zero. Nomes: `core_blog_view_entries`, `core_course_view_course`, `core_my_view_page`,
`core_notes_view_notes`, `core_search_view_results`, `core_user_view_user_list`,
`core_user_view_user_profile`, `gradereport_overview_view_grade_report`,
`gradereport_user_view_grade_report`, `mod_assign_view_assign`, `mod_assign_view_grading_table`,
`mod_assign_view_submission_status`, `mod_bigbluebuttonbn_view_bigbluebuttonbn`,
`mod_book_view_book`, `mod_choice_view_choice`, `mod_choicegroup_view_choicegroup`,
`mod_data_view_database`, `mod_diary_view_diary`, `mod_feedback_view_feedback`,
`mod_folder_view_folder`, `mod_forum_view_forum`, `mod_forum_view_forum_discussion`,
`mod_glossary_view_entry`, `mod_glossary_view_glossary`, `mod_h5pactivity_view_h5pactivity`,
`mod_h5pactivity_log_report_viewed`, `mod_imscp_view_imscp`, `mod_journal_view_journal`,
`mod_lesson_view_lesson`, `mod_lti_view_lti` (declara `read`), `mod_page_view_page`,
`mod_quiz_view_attempt`, `mod_quiz_view_attempt_review`, `mod_quiz_view_attempt_summary`,
`mod_quiz_view_quiz`, `mod_resource_view_resource`, `mod_scorm_view_scorm`,
`mod_subcourse_view_subcourse`, `mod_url_view_url`, `mod_wiki_view_page`, `mod_wiki_view_wiki`,
`mod_workshop_view_submission`, `mod_workshop_view_workshop`,
mais os cinco `core_competency_*_viewed`.

### 6.8 Perfil, arquivos e dispositivo do próprio dono

Dano menor, mas nenhuma responde pergunta nenhuma do §5.

`core_user_update_picture`, `core_user_set_user_preferences` (declara capability
**`moodle/site:config`** **[fonte]** — a versão que aceita `userid` de terceiro),
`core_user_update_user_preferences`, `core_user_add_user_private_files`,
`core_user_update_private_files`, `core_user_prepare_private_files_for_edition`,
`core_user_add_user_device`, `core_user_remove_user_device`,
`core_user_update_user_device_public_key`, `message_airnotifier_enable_device`,
`core_files_delete_draft_files`, `core_course_set_favourite_courses` (declara `read`),
`core_message_message_processor_config_form`.

### 6.9 Custo institucional e requisição externa

| função | por quê |
|---|---|
| **`aiplacement_courseassist_explain_text`**, **`aiplacement_courseassist_summarise_text`**, **`aiplacement_editor_generate_text`**, **`aiplacement_editor_generate_image`** | mandam conteúdo do curso para o provedor de IA contratado pela USP e consomem cota institucional. Um MCP que já é um modelo chamando outro modelo pela conta da universidade é gasto que ninguém autorizou. Também é exfiltração de conteúdo de curso para fora |
| **`tool_moodlenet_search_courses`**, **`tool_moodlenet_verify_webfinger`** | declaradas `read`, mas fazem o **servidor da USP** buscar uma URL externa a partir de parâmetro nosso. **[inferência]** sobre alcance — não li o corpo. É o formato de um SSRF e merece leitura antes de liberar |
| **`qtype_stack_library_import`** | declara `read`, descrição é *"Import a given file from the library"* **[fonte]**. Importa, não lê |
| **`tool_mobile_get_content`** | despachante genérico `component`+`method`+`args` (ver §3.10) |

### 6.10 Leitura que não é escrita mas também não é inócua

Não pedem bloqueio permanente; pedem que **não entrem na allowlist** e que, se algum dia
entrarem, seja com justificativa escrita. Todas expõem dados de terceiros identificáveis:

`core_enrol_get_enrolled_users` e `core_enrol_search_users` (turma inteira com e-mail),
`core_user_get_users_by_field` (busca por e-mail ou nº USP), `core_user_get_course_user_profiles`,
`gradereport_grader_get_users_in_report`, `core_grades_get_gradable_users`,
`core_grades_get_enrolled_users_for_selector`, `mod_assign_list_participants`,
`mod_assign_get_submissions`, `mod_assign_get_grades`, `mod_assign_get_participant`,
`mod_workshop_get_submissions` e `mod_workshop_get_submission_assessments`,
`mod_feedback_get_non_respondents` (quem **não** respondeu), `mod_feedback_get_responses_analysis`,
`mod_choice_get_choice_results`, `mod_lesson_get_attempts_overview`,
`mod_h5pactivity_get_user_attempts`, `mod_glossary_get_entries_by_author*`, e o bloco inteiro
de leitura de `core_message_*` (conversa privada é o dado mais sensível que este token alcança).

E uma leitura do próprio usuário que ainda assim é sensível: **`mod_quiz_get_attempt_data`**,
que devolve o enunciado das questões de uma tentativa em andamento. Não escreve nada, e ainda
assim é a última coisa que se quer dentro do contexto de um modelo durante uma prova.

### 6.11 Resumo do delta

| categoria | nomes no §2.2 hoje | nomes que faltam (contagem) |
|---|---:|---:|
| bypass do bloqueio | 0 | **1** |
| credencial | 2 | **4** |
| entrega / tentativa avaliada | 4 (3 existentes) | **~22** |
| fala com terceiros | 3 padrões (5 funções) | **~30** |
| consentimento | 0 | **5** |
| nota de terceiro | 0 | **17** |
| `*_view_*` | 0 | **~45** |
| perfil / arquivo / dispositivo | 0 | **13** |
| custo institucional / requisição externa | 0 | **7** |

**178 funções mudam estado; o §2.2 alcança 10; 168 ficam de fora.** As contagens por categoria
acima se sobrepõem em alguns casos (uma função de nota de terceiro que também é `*_view_*`, por
exemplo) e servem de ordem de grandeza, não de soma exata. Daí a recomendação de allowlist no
lugar de denylist, com o §2.2 como camada de baixo.

---

## Apêndice A — as 447, completas

Tabela gerada por script cruzando `fixtures/moodle/raw/site_info.json` **[fixture]** com o
`db/services.php` de cada plugin no `MOODLE_500_STABLE` **[fonte]**. A coluna **tipo declarado**
é o campo `type` do Moodle — que, como mostra o §2.1, **não é uma fronteira de segurança**. A
coluna **risco** é a classificação deste catálogo. `?` e `sem-fonte` significam que o
`db/services.php` do plugin não foi localizado publicamente: para essas 10, nada foi verificado.

Grupos ordenados por tamanho.

#### `core_message_*` — 41 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_message_block_user` | write | escrita | Blocks a user |
| `core_message_confirm_contact_request` | write | escrita | Confirms a contact request |
| `core_message_create_contact_request` | write | escrita | Creates a contact request |
| `core_message_data_for_messagearea_search_messages` | read | cuidado | Retrieve the template data for searching for messages |
| `core_message_decline_contact_request` | write | escrita | Declines a contact request |
| `core_message_delete_contacts` | write | escrita | Remove contacts from the contact list |
| `core_message_delete_conversations_by_id` | write | escrita | Deletes a list of conversations. |
| `core_message_delete_message` | write | escrita | Deletes a message. |
| `core_message_delete_message_for_all_users` | write | escrita | Deletes a message for all users. |
| `core_message_get_blocked_users` | read | cuidado | Retrieve a list of users blocked |
| `core_message_get_contact_requests` | read | cuidado | Returns contact requests for a user |
| `core_message_get_conversation` | read | cuidado | Retrieve a conversation for a user |
| `core_message_get_conversation_between_users` | read | cuidado | Retrieve a conversation for a user between another user |
| `core_message_get_conversation_counts` | read | livre | Retrieve a list of conversation counts, indexed by type. |
| `core_message_get_conversation_members` | read | cuidado | Retrieve a list of members in a conversation |
| `core_message_get_conversation_messages` | read | cuidado | Retrieve the conversation messages and relevant member information |
| `core_message_get_conversations` | read | cuidado | Retrieve a list of conversations for a user |
| `core_message_get_member_info` | read | cuidado | Retrieve a user message profiles |
| `core_message_get_messages` | read | cuidado | Retrieve a list of messages sent and received by a user (conversations, notifications or both) |
| `core_message_get_received_contact_requests_count` | read | livre | Gets the number of received contact requests |
| `core_message_get_self_conversation` | read | cuidado | Retrieve a self-conversation for a user |
| `core_message_get_unread_conversation_counts` | read | livre | Retrieve a list of unread conversation counts, indexed by type. |
| `core_message_get_unread_conversations_count` | read | livre | Retrieve the count of unread conversations for a given user |
| `core_message_get_unread_notification_count` | read | livre | Get number of unread notifications. |
| `core_message_get_user_contacts` | read | cuidado | Retrieve the contact list |
| `core_message_get_user_message_preferences` | read | cuidado | Get the message preferences for a given user. |
| `core_message_get_user_notification_preferences` | read | cuidado | Get the notification preferences for a given user. |
| `core_message_mark_all_conversation_messages_as_read` | write | escrita | Mark all conversation messages as read for a given user |
| `core_message_mark_all_notifications_as_read` | write | escrita | Mark all notifications as read for a given user |
| `core_message_mark_message_read` | write | escrita | Mark a single message as read, trigger message_viewed event. |
| `core_message_mark_notification_read` | write | escrita | Mark a single notification as read, trigger notification_viewed event. |
| `core_message_message_processor_config_form` | write | escrita | Process the message processor config form |
| `core_message_message_search_users` | read | cuidado | Retrieve the data for searching for people |
| `core_message_mute_conversations` | write | escrita | Mutes a list of conversations |
| `core_message_search_contacts` | read | cuidado | Search for contacts |
| `core_message_send_instant_messages` | write | bloqueada-§2.2 | Send instant messages |
| `core_message_send_messages_to_conversation` | write | escrita | Send messages to an existing conversation between users |
| `core_message_set_favourite_conversations` | write | escrita | Mark a conversation or group of conversations as favourites/starred conversations. |
| `core_message_unblock_user` | write | escrita | Unblocks a user |
| `core_message_unmute_conversations` | write | escrita | Unmutes a list of conversations |
| `core_message_unset_favourite_conversations` | write | escrita | Unset a conversation or group of conversations as favourites/starred conversations. |

#### `mod_assign_*` — 24 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_assign_get_assignments` | read | livre | Returns the courses and assignments for the users capability |
| `mod_assign_get_grades` | read | cuidado | Returns grades from the assignment |
| `mod_assign_get_participant` | read | cuidado | Get a participant for an assignment, with some summary info about their submissions. |
| `mod_assign_get_submission_status` | read | cuidado | Returns information about an assignment submission status for a given user. |
| `mod_assign_get_submissions` | read | cuidado | Returns the submissions for assignments |
| `mod_assign_get_user_flags` | read | cuidado | Returns the user flags for assignments |
| `mod_assign_get_user_mappings` | read | cuidado | Returns the blind marking mappings for assignments |
| `mod_assign_list_participants` | read | cuidado | List the participants for a single assignment, with some summary info about their submissions. |
| `mod_assign_lock_submissions` | write | escrita | Prevent students from making changes to a list of submissions |
| `mod_assign_remove_submission` | write | escrita | Remove submission. |
| `mod_assign_reveal_identities` | write | escrita | Reveal the identities for a blind marking assignment |
| `mod_assign_revert_submissions_to_draft` | write | escrita | Reverts the list of submissions to draft status |
| `mod_assign_save_grade` | write | escrita | Save a grade update for a single student. |
| `mod_assign_save_grades` | write | escrita | Save multiple grade updates for an assignment. |
| `mod_assign_save_submission` | write | bloqueada-§2.2 | Update the current students submission |
| `mod_assign_save_user_extensions` | write | escrita | Save a list of assignment extensions |
| `mod_assign_set_user_flags` | write | escrita | Creates or updates user flags |
| `mod_assign_start_submission` | write | escrita | Start a submission for user if assignment has a time limit. |
| `mod_assign_submit_for_grading` | write | bloqueada-§2.2 | Submit the current students assignment for grading |
| `mod_assign_submit_grading_form` | write | escrita | Submit the grading form data via ajax |
| `mod_assign_unlock_submissions` | write | escrita | Allow students to make changes to a list of submissions |
| `mod_assign_view_assign` | write | escrita | Update the module completion status. |
| `mod_assign_view_grading_table` | write | escrita | Trigger the grading_table_viewed event. |
| `mod_assign_view_submission_status` | write | escrita | Trigger the submission status viewed event. |

#### `mod_quiz_*` — 19 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_quiz_get_attempt_access_information` | read | livre | Return access information for a given attempt in a quiz. |
| `mod_quiz_get_attempt_data` | read | cuidado | Returns information for the given attempt page for a quiz attempt in progress. |
| `mod_quiz_get_attempt_review` | read | cuidado | Returns review information for the given finished attempt, can be used by users or teachers. |
| `mod_quiz_get_attempt_summary` | read | cuidado | Returns a summary of a quiz attempt before it is submitted. |
| `mod_quiz_get_combined_review_options` | read | cuidado | Combines the review options from a number of different quiz attempts. |
| `mod_quiz_get_quiz_access_information` | read | livre | Return access information for a given quiz. |
| `mod_quiz_get_quiz_feedback_for_grade` | read | cuidado | Get the feedback text that should be show to a student who got the given grade in the given quiz. |
| `mod_quiz_get_quiz_required_qtypes` | read | livre | Return the potential question types that would be required for a given quiz. |
| `mod_quiz_get_quizzes_by_courses` | read | livre | Returns a list of quizzes in a provided list of courses |
| `mod_quiz_get_user_attempts` | read | cuidado | Return a list of attempts for the given quiz and user. |
| `mod_quiz_get_user_best_grade` | read | cuidado | Get the best current grade for the given user on a quiz. |
| `mod_quiz_get_user_quiz_attempts` | read | cuidado | Return a list of attempts for the given quiz and user. |
| `mod_quiz_process_attempt` | write | bloqueada-§2.2 | Process responses during an attempt at a quiz and also deals with attempts finishing. |
| `mod_quiz_save_attempt` | write | bloqueada-§2.2 | Processes save requests during the quiz. |
| `mod_quiz_start_attempt` | write | bloqueada-§2.2 | Starts a new attempt at a quiz. |
| `mod_quiz_view_attempt` | write | escrita | Trigger the attempt viewed event. |
| `mod_quiz_view_attempt_review` | write | escrita | Trigger the attempt reviewed event. |
| `mod_quiz_view_attempt_summary` | write | escrita | Trigger the attempt summary viewed event. |
| `mod_quiz_view_quiz` | write | escrita | Trigger the course module viewed event and update the module completion status. |

#### `mod_workshop_*` — 19 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_workshop_add_submission` | write | escrita | Add a new submission to a given workshop. |
| `mod_workshop_delete_submission` | write | escrita | Deletes the given submission. |
| `mod_workshop_evaluate_assessment` | write | escrita | Evaluates an assessment (used by teachers for provide feedback to the reviewer). |
| `mod_workshop_evaluate_submission` | write | escrita | Evaluates a submission (used by teachers for provide feedback or override the submission grade). |
| `mod_workshop_get_assessment` | read | cuidado | Retrieves the given assessment. |
| `mod_workshop_get_assessment_form_definition` | read | livre | Retrieves the assessment form definition. |
| `mod_workshop_get_grades` | read | cuidado | Returns the assessment and submission grade for the given user. |
| `mod_workshop_get_grades_report` | read | cuidado | Retrieves the assessment grades report. |
| `mod_workshop_get_reviewer_assessments` | read | cuidado | Retrieves all the assessments reviewed by the given user. |
| `mod_workshop_get_submission` | read | cuidado | Retrieves the given submission. |
| `mod_workshop_get_submission_assessments` | read | cuidado | Retrieves all the assessments of the given submission. |
| `mod_workshop_get_submissions` | read | cuidado | Retrieves all the workshop submissions or the one done by the given user (except example submissions). |
| `mod_workshop_get_user_plan` | read | cuidado | Return the planner information for the given user. |
| `mod_workshop_get_workshop_access_information` | read | livre | Return access information for a given workshop. |
| `mod_workshop_get_workshops_by_courses` | read | livre | Returns a list of workshops in a provided list of courses, if no list is provided all workshops that |
| `mod_workshop_update_assessment` | write | escrita | Add information to an allocated assessment. |
| `mod_workshop_update_submission` | write | escrita | Update the given submission. |
| `mod_workshop_view_submission` | write | escrita | Trigger the submission viewed event. |
| `mod_workshop_view_workshop` | write | escrita | Trigger the course module viewed event and update the module completion status. |

#### `mod_forum_*` — 18 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_forum_add_discussion` | write | bloqueada-§2.2 | Add a new discussion into an existing forum. |
| `mod_forum_add_discussion_post` | write | bloqueada-§2.2 | Create new posts into an existing discussion. |
| `mod_forum_can_add_discussion` | read | livre | Check if the current user can add discussions in the given forum (and optionally for the given group). |
| `mod_forum_delete_post` | write | escrita | Deletes a post or a discussion completely when the post is the discussion topic. |
| `mod_forum_get_discussion_post` | read | cuidado | Get a particular discussion post. |
| `mod_forum_get_discussion_posts` | read | cuidado | Returns a list of forum posts for a discussion. |
| `mod_forum_get_forum_access_information` | read | livre | Return capabilities information for a given forum. |
| `mod_forum_get_forum_discussions` | read | cuidado | Returns a list of forum discussions optionally sorted and paginated. |
| `mod_forum_get_forums_by_courses` | read | livre | Returns a list of forum instances in a provided set of courses, if |
| `mod_forum_mark_posts_read` | write | escrita | Mark forum posts as read. |
| `mod_forum_prepare_draft_area_for_post` | write | escrita | Prepares a draft area for editing a post. |
| `mod_forum_set_lock_state` | write | escrita | Set the lock state for the discussion |
| `mod_forum_set_pin_state` | write | escrita | Set the pin state |
| `mod_forum_set_subscription_state` | write | escrita | Set the subscription state |
| `mod_forum_toggle_favourite_state` | write | escrita | Toggle the favourite state |
| `mod_forum_update_discussion_post` | write | escrita | Updates a post or a discussion topic post. |
| `mod_forum_view_forum` | write | escrita | Trigger the course module viewed event and update the module completion status. |
| `mod_forum_view_forum_discussion` | write | escrita | Trigger the forum discussion viewed event. |

#### `mod_glossary_*` — 18 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_glossary_add_entry` | write | escrita | Add a new entry to a given glossary |
| `mod_glossary_delete_entry` | write | escrita | Delete the given entry from the glossary. |
| `mod_glossary_get_authors` | read | cuidado | Get the authors. |
| `mod_glossary_get_categories` | read | livre | Get the categories. |
| `mod_glossary_get_entries_by_author` | read | cuidado | Browse entries by author. |
| `mod_glossary_get_entries_by_author_id` | read | cuidado | Browse entries by author ID. |
| `mod_glossary_get_entries_by_category` | read | livre | Browse entries by category. |
| `mod_glossary_get_entries_by_date` | read | livre | Browse entries by date. |
| `mod_glossary_get_entries_by_letter` | read | livre | Browse entries by letter. |
| `mod_glossary_get_entries_by_search` | read | livre | Browse entries by search query. |
| `mod_glossary_get_entries_by_term` | read | livre | Browse entries by term (concept or alias). |
| `mod_glossary_get_entries_to_approve` | read | cuidado | Browse entries to be approved. |
| `mod_glossary_get_entry_by_id` | read | livre | Get an entry by ID |
| `mod_glossary_get_glossaries_by_courses` | read | livre | Retrieve a list of glossaries from several courses. |
| `mod_glossary_prepare_entry_for_edition` | read | escrita | Prepares the given entry for edition returning draft item areas and file areas information. |
| `mod_glossary_update_entry` | write | escrita | Updates the given glossary entry. |
| `mod_glossary_view_entry` | write | escrita | Notify a glossary entry as being viewed. |
| `mod_glossary_view_glossary` | write | escrita | Notify the glossary as being viewed. |

#### `mod_lesson_*` — 17 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_lesson_finish_attempt` | write | escrita | Finishes the current attempt. |
| `mod_lesson_get_attempts_overview` | read | cuidado | Get a list of all the attempts made by users in a lesson. |
| `mod_lesson_get_content_pages_viewed` | read | cuidado | Return the list of content pages viewed by a user during a lesson attempt. |
| `mod_lesson_get_lesson` | read | livre | Return information of a given lesson. |
| `mod_lesson_get_lesson_access_information` | read | livre | Return access information for a given lesson. |
| `mod_lesson_get_lessons_by_courses` | read | livre | Returns a list of lessons in a provided list of courses |
| `mod_lesson_get_page_data` | read | livre | Return information of a given page, including its contents. |
| `mod_lesson_get_pages` | read | livre | Return the list of pages in a lesson (based on the user permissions). |
| `mod_lesson_get_pages_possible_jumps` | read | livre | Return all the possible jumps for the pages in a given lesson. |
| `mod_lesson_get_questions_attempts` | read | cuidado | Return the list of questions attempts in a given lesson. |
| `mod_lesson_get_user_attempt` | read | cuidado | Return information about the given user attempt (including answers). |
| `mod_lesson_get_user_attempt_grade` | read | cuidado | Return grade information in the attempt for a given user. |
| `mod_lesson_get_user_grade` | read | cuidado | Return the final grade in the lesson for the given user. |
| `mod_lesson_get_user_timers` | read | cuidado | Return the timers in the current lesson for the given user. |
| `mod_lesson_launch_attempt` | write | escrita | Starts a new attempt or continues an existing one. |
| `mod_lesson_process_page` | write | escrita | Processes page responses. |
| `mod_lesson_view_lesson` | write | escrita | Trigger the course module viewed event and update the module completion status. |

#### `core_course_*` — 16 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_course_check_updates` | read | cuidado | Check if there is updates affecting the user for the given course and contexts. |
| `core_course_get_categories` | read | livre | Return category details |
| `core_course_get_contents` | read | cuidado | Get course contents |
| `core_course_get_course_module` | read | livre | Return information about a course module |
| `core_course_get_course_module_by_instance` | read | livre | Return information about a given module name and instance id |
| `core_course_get_courses` | read | livre | Return course details |
| `core_course_get_courses_by_field` | read | livre | Get courses matching a specific field (id/s, shortname, idnumber, category) |
| `core_course_get_enrolled_courses_by_timeline_classification` | read | cuidado | List of enrolled courses for the given timeline classification (past, inprogress, or future). |
| `core_course_get_enrolled_courses_with_action_events_by_timeline_classification` | read | cuidado | List of enrolled courses with action events in a given timeframe, for the given timeline classification. |
| `core_course_get_recent_courses` | read | cuidado | List of courses a user has accessed most recently. |
| `core_course_get_updates_since` | read | cuidado | Check if there are updates affecting the user for the given course since the given time stamp. |
| `core_course_get_user_administration_options` | read | livre | Return a list of administration options in a set of courses that are avaialable or not for the current |
| `core_course_get_user_navigation_options` | read | livre | Return a list of navigation options in a set of courses that are avaialable or not for the current user. |
| `core_course_search_courses` | read | livre | Search courses by (name, module, block, tag) |
| `core_course_set_favourite_courses` | read | escrita | Add a list of courses to the list of favourite courses. |
| `core_course_view_course` | write | escrita | Log that the course was viewed |

#### `core_user_*` — 16 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_user_add_user_device` | write | escrita | Store mobile user devices information for PUSH Notifications. |
| `core_user_add_user_private_files` | write | escrita | Copy files from a draft area to users private files area. |
| `core_user_agree_site_policy` | write | escrita | Agree the site policy for the current user. |
| `core_user_get_course_user_profiles` | read | cuidado | Get course user profiles (each of the profils matching a course id and a user id),. |
| `core_user_get_private_files_info` | read | cuidado | Returns general information about files in the user private files area. |
| `core_user_get_user_preferences` | read | cuidado | Return user preferences. |
| `core_user_get_users_by_field` | read | cuidado | Retrieve users' information for a specified unique field - If you want to do a user search, use |
| `core_user_prepare_private_files_for_edition` | write | escrita | Prepares the draft area for user private files. |
| `core_user_remove_user_device` | write | escrita | Remove a user device from the Moodle database. |
| `core_user_set_user_preferences` | write | escrita | Set user preferences. |
| `core_user_update_picture` | write | escrita | Update or delete the user picture in the site |
| `core_user_update_private_files` | write | escrita | Copy files from a draft area to users private files area. |
| `core_user_update_user_device_public_key` | write | escrita | Store mobile user public key. |
| `core_user_update_user_preferences` | write | escrita | Update a user's preferences |
| `core_user_view_user_list` | write | escrita | Simulates the web-interface view of user/index.php (triggering events),. |
| `core_user_view_user_profile` | write | escrita | Simulates the web-interface view of user/view.php and user/profile.php (triggering events),. |

#### `core_calendar_*` — 15 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_calendar_create_calendar_events` | write | escrita | Create calendar events |
| `core_calendar_delete_calendar_events` | write | escrita | Delete calendar events |
| `core_calendar_get_action_events_by_course` | read | cuidado | Get calendar action events by course |
| `core_calendar_get_action_events_by_courses` | read | cuidado | Get calendar action events by courses |
| `core_calendar_get_action_events_by_timesort` | read | cuidado | Get calendar action events by tiemsort |
| `core_calendar_get_allowed_event_types` | read | livre | Get the type of events a user can create in the given course. |
| `core_calendar_get_calendar_access_information` | read | livre | Convenience function to retrieve some permissions/access information for the given course calendar. |
| `core_calendar_get_calendar_day_view` | read | cuidado | Fetch the day view data for a calendar |
| `core_calendar_get_calendar_event_by_id` | read | cuidado | Get calendar event by id |
| `core_calendar_get_calendar_events` | read | cuidado | Get calendar events |
| `core_calendar_get_calendar_export_token` | read | cuidado | Return the auth token required for exporting a calendar. |
| `core_calendar_get_calendar_monthly_view` | read | cuidado | Fetch the monthly view data for a calendar |
| `core_calendar_get_calendar_upcoming_view` | read | cuidado | Fetch the upcoming view data for a calendar |
| `core_calendar_submit_create_update_form` | write | escrita | Submit form data for event form |
| `core_calendar_update_event_start_day` | write | escrita | Update the start day (but not time) for an event. |

#### `mod_feedback_*` — 14 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_feedback_get_analysis` | read | cuidado | Retrieves the feedback analysis. |
| `mod_feedback_get_current_completed_tmp` | read | cuidado | Returns the temporary completion record for the current user. |
| `mod_feedback_get_feedback_access_information` | read | livre | Return access information for a given feedback. |
| `mod_feedback_get_feedbacks_by_courses` | read | livre | Returns a list of feedbacks in a provided list of courses, if no list is provided all feedbacks that |
| `mod_feedback_get_finished_responses` | read | cuidado | Retrieves responses from the last finished attempt. |
| `mod_feedback_get_items` | read | livre | Returns the items (questions) in the given feedback. |
| `mod_feedback_get_last_completed` | read | cuidado | Retrieves the last completion record for the current user. |
| `mod_feedback_get_non_respondents` | read | cuidado | Retrieves a list of students who didn't submit the feedback. |
| `mod_feedback_get_page_items` | read | livre | Get a single feedback page items. |
| `mod_feedback_get_responses_analysis` | read | cuidado | Return the feedback user responses analysis. |
| `mod_feedback_get_unfinished_responses` | read | cuidado | Retrieves responses from the current unfinished attempt. |
| `mod_feedback_launch_feedback` | write | escrita | Starts or continues a feedback submission. |
| `mod_feedback_process_page` | write | escrita | Process a jump between pages. |
| `mod_feedback_view_feedback` | write | escrita | Trigger the course module viewed event and update the module completion status. |

#### `mod_data_*` — 11 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_data_add_entry` | write | escrita | Adds a new entry. |
| `mod_data_approve_entry` | write | escrita | Approves or unapproves an entry. |
| `mod_data_delete_entry` | write | escrita | Deletes an entry. |
| `mod_data_get_data_access_information` | read | livre | Return access information for a given database. |
| `mod_data_get_databases_by_courses` | read | livre | Returns a list of database instances in a provided set of courses, if |
| `mod_data_get_entries` | read | cuidado | Return the complete list of entries of the given database. |
| `mod_data_get_entry` | read | cuidado | Return one entry record from the database, including contents optionally. |
| `mod_data_get_fields` | read | livre | Return the list of configured fields for the given database. |
| `mod_data_search_entries` | read | cuidado | Search for entries in the given database. |
| `mod_data_update_entry` | write | escrita | Updates an existing entry. |
| `mod_data_view_database` | write | escrita | Simulate the view.php web interface data: trigger events, completion, etc... |

#### `mod_bigbluebuttonbn_*` — 10 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_bigbluebuttonbn_can_join` | read | cuidado | Returns information if the current user can join or not. |
| `mod_bigbluebuttonbn_completion_validate` | write | escrita | Validate completion |
| `mod_bigbluebuttonbn_end_meeting` | write | escrita | End a meeting |
| `mod_bigbluebuttonbn_get_bigbluebuttonbns_by_courses` | read | livre | Returns a list of bigbluebuttonbns in a provided list of courses, if no list is provided |
| `mod_bigbluebuttonbn_get_join_url` | write | escrita | Get the join URL for the meeting and create if it does not exist. |
| `mod_bigbluebuttonbn_get_recordings` | read | cuidado | Returns a list of recordings ready to be processed by a datatable. |
| `mod_bigbluebuttonbn_get_recordings_to_import` | read | cuidado | Returns a list of recordings ready to import to be processed by a datatable. |
| `mod_bigbluebuttonbn_meeting_info` | read | cuidado | Get displayable information on the meeting |
| `mod_bigbluebuttonbn_update_recording` | write | escrita | Update a single recording |
| `mod_bigbluebuttonbn_view_bigbluebuttonbn` | write | escrita | Trigger the course module viewed event and update the module completion status. |

#### `mod_wiki_*` — 10 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_wiki_edit_page` | write | escrita | Save the contents of a page. |
| `mod_wiki_get_page_contents` | read | cuidado | Returns the contents of a page. |
| `mod_wiki_get_page_for_editing` | write | escrita | Locks and retrieves info of page-section to be edited. |
| `mod_wiki_get_subwiki_files` | read | cuidado | Returns the list of files for a specific subwiki. |
| `mod_wiki_get_subwiki_pages` | read | cuidado | Returns the list of pages for a specific subwiki. |
| `mod_wiki_get_subwikis` | read | cuidado | Returns the list of subwikis the user can see in a specific wiki. |
| `mod_wiki_get_wikis_by_courses` | read | livre | Returns a list of wiki instances in a provided set of courses, if |
| `mod_wiki_new_page` | write | escrita | Create a new page in a subwiki. |
| `mod_wiki_view_page` | write | escrita | Trigger the page viewed event and update the module completion status. |
| `mod_wiki_view_wiki` | write | escrita | Trigger the course module viewed event and update the module completion status. |

#### `core_competency_*` — 9 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_competency_competency_viewed` | read | livre | Log event competency viewed |
| `core_competency_delete_evidence` | write | escrita | Delete an evidence |
| `core_competency_get_scale_values` | read | livre | Fetch the values for a specific scale |
| `core_competency_grade_competency_in_course` | write | escrita | Grade a competency from the course page. |
| `core_competency_list_course_competencies` | read | livre | List the competencies in a course |
| `core_competency_user_competency_plan_viewed` | read | livre | Log the user competency plan viewed event. |
| `core_competency_user_competency_viewed` | read | livre | Log the user competency viewed event. |
| `core_competency_user_competency_viewed_in_course` | read | livre | Log the user competency viewed in course event |
| `core_competency_user_competency_viewed_in_plan` | read | livre | Log the user competency viewed in plan event. |

#### `mod_scorm_*` — 9 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_scorm_get_scorm_access_information` | read | livre | Return capabilities information for a given scorm. |
| `mod_scorm_get_scorm_attempt_count` | read | cuidado | Return the number of attempts done by a user in the given SCORM. |
| `mod_scorm_get_scorm_sco_tracks` | read | cuidado | Retrieves SCO tracking data for the given user id and attempt number |
| `mod_scorm_get_scorm_scoes` | read | livre | Returns a list containing all the scoes data related to the given scorm id |
| `mod_scorm_get_scorm_user_data` | read | cuidado | Retrieves user tracking and SCO data and default SCORM values |
| `mod_scorm_get_scorms_by_courses` | read | livre | Returns a list of scorm instances in a provided set of courses, if |
| `mod_scorm_insert_scorm_tracks` | write | escrita | Saves a scorm tracking record. |
| `mod_scorm_launch_sco` | write | escrita | Trigger the SCO launched event. |
| `mod_scorm_view_scorm` | write | escrita | Trigger the course module viewed event. |

#### `core_grades_*` — 8 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_grades_get_enrolled_users_for_selector` | read | cuidado | Returns the enrolled users within and map some fields to the returned array of user objects. |
| `core_grades_get_gradable_users` | read | cuidado | Returns the gradable users in a course |
| `core_grades_get_gradeitems` | read | cuidado | Get the gradeitems for a course |
| `core_grades_get_groups_for_selector` | read | cuidado | ** DEPRECATED ** Please do not call this function any more. |
| `core_grades_grader_gradingpanel_point_fetch` | write | escrita | Fetch the data required to display the grader grading panel for simple grading, |
| `core_grades_grader_gradingpanel_point_store` | write | escrita | Store the data required to display the grader grading panel for simple grading |
| `core_grades_grader_gradingpanel_scale_fetch` | write | escrita | Fetch the data required to display the grader grading panel for scale-based grading, |
| `core_grades_grader_gradingpanel_scale_store` | write | escrita | Store the data required to display the grader grading panel for scale-based grading |

#### `tool_lp_*` — 8 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `tool_lp_data_for_course_competencies_page` | read | cuidado | Load the data for the course competencies page template. |
| `tool_lp_data_for_plan_page` | read | cuidado | Load the data for the plan page template. |
| `tool_lp_data_for_plans_page` | read | cuidado | Load the data for the plans page template |
| `tool_lp_data_for_user_competency_summary` | read | cuidado | Load a summary of a user competency. |
| `tool_lp_data_for_user_competency_summary_in_course` | read | cuidado | Load a summary of a user competency. |
| `tool_lp_data_for_user_competency_summary_in_plan` | read | cuidado | Load a summary of a user competency. |
| `tool_lp_data_for_user_evidence_list_page` | read | cuidado | Load the data for the user evidence list page template |
| `tool_lp_data_for_user_evidence_page` | read | cuidado | Load the data for the user evidence page template |

#### `tool_mobile_*` — 8 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `tool_mobile_call_external_functions` | write | escrita | Call multiple external functions and return all responses. |
| `tool_mobile_get_autologin_key` | write | bloqueada-§2.2 | Creates an auto-login key for the current user. |
| `tool_mobile_get_config` | read | livre | Returns a list of the site configurations, filtering by section. |
| `tool_mobile_get_content` | read | livre | Returns a piece of content to be displayed in the Mobile app. |
| `tool_mobile_get_plugins_supporting_mobile` | read | livre | Returns a list of Moodle plugins supporting the mobile app. |
| `tool_mobile_get_public_config` | read | livre | Returns a list of the site public settings, those not requiring authentication. |
| `tool_mobile_get_tokens_for_qr_login` | read | bloqueada-§2.2 | Returns a WebService token (and private token) for QR login. |
| `tool_mobile_validate_subscription_key` | write | escrita | Check if the given site subscription key is valid. |

#### `core_blog_*` — 7 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_blog_add_entry` | write | escrita | Creates a new blog post entry. |
| `core_blog_delete_entry` | write | escrita | Deletes a blog post entry. |
| `core_blog_get_access_information` | read | livre | Retrieves permission information for the current user. |
| `core_blog_get_entries` | read | cuidado | Returns blog entries. |
| `core_blog_prepare_entry_for_edition` | write | escrita | Prepare a draft area for editing a blog entry.. |
| `core_blog_update_entry` | write | escrita | Updates a blog entry. |
| `core_blog_view_entries` | read | livre | Trigger the blog_entries_viewed event. |

#### `mod_h5pactivity_*` — 7 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_h5pactivity_get_attempts` | read | cuidado | Return the information needed to list a user attempts. |
| `mod_h5pactivity_get_h5pactivities_by_courses` | read | livre | Returns a list of h5p activities in a list of |
| `mod_h5pactivity_get_h5pactivity_access_information` | read | livre | Return access information for a given h5p activity. |
| `mod_h5pactivity_get_results` | read | cuidado | Return the information needed to list a user attempt results. |
| `mod_h5pactivity_get_user_attempts` | read | cuidado | Return the information needed to list all enrolled user attempts. |
| `mod_h5pactivity_log_report_viewed` | write | escrita | Log that the h5pactivity was viewed. |
| `mod_h5pactivity_view_h5pactivity` | write | escrita | Trigger the course module viewed event and update the module completion status. |

#### `core_group_*` — 6 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_group_get_activity_allowed_groups` | read | cuidado | Gets a list of groups that the user is allowed to access within the specified activity. |
| `core_group_get_activity_groupmode` | read | livre | Returns effective groupmode used in a given activity. |
| `core_group_get_course_groupings` | read | cuidado | Returns all groupings in specified course. |
| `core_group_get_course_groups` | read | cuidado | Returns all groups in specified course. |
| `core_group_get_course_user_groups` | read | cuidado | Returns all groups in specified course for the specified user. |
| `core_group_get_groups_for_selector` | read | cuidado | Get the group/(s) for a course |

#### `core_xapi_*` — 6 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_xapi_delete_state` | write | escrita | Delete an xAPI state data from an activityId. |
| `core_xapi_delete_states` | write | escrita | Delete all xAPI state data from an activityId. |
| `core_xapi_get_state` | read | livre | Get an xAPI state data from an activityId. |
| `core_xapi_get_states` | read | livre | Get all state ID from an activityId. |
| `core_xapi_post_state` | write | escrita | Post an xAPI state into an activityId. |
| `core_xapi_statement_post` | write | escrita | Post an xAPI statement. |

#### `mod_choice_*` — 6 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_choice_delete_choice_responses` | write | escrita | Delete the given submitted responses in a choice |
| `mod_choice_get_choice_options` | read | livre | Retrieve options for a specific choice. |
| `mod_choice_get_choice_results` | read | cuidado | Retrieve users results for a given choice. |
| `mod_choice_get_choices_by_courses` | read | livre | Returns a list of choice instances in a provided set of courses |
| `mod_choice_submit_choice_response` | write | escrita | Submit responses to a specific choice item. |
| `mod_choice_view_choice` | write | escrita | Trigger the course module viewed event and update the module completion status. |

#### `core_reportbuilder_*` — 5 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_reportbuilder_can_view_system_report` | read | livre | Determine access to a system report |
| `core_reportbuilder_list_reports` | read | cuidado | List custom reports for current user |
| `core_reportbuilder_retrieve_report` | read | cuidado | Retrieve custom report content |
| `core_reportbuilder_retrieve_system_report` | read | cuidado | Retrieve system report content |
| `core_reportbuilder_view_report` | write | escrita | Trigger custom report viewed |

#### `core_tag_*` — 5 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_tag_get_tag_areas` | read | livre | Retrieves existing tag areas. |
| `core_tag_get_tag_cloud` | read | livre | Retrieves a tag cloud for the given collection and/or query search. |
| `core_tag_get_tag_collections` | read | livre | Retrieves existing tag collections. |
| `core_tag_get_tagindex` | read | livre | Gets tag index page for one tag and one tag area |
| `core_tag_get_tagindex_per_area` | read | livre | Gets tag index page per different areas. |

#### `tool_dataprivacy_*` — 5 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `tool_dataprivacy_cancel_data_request` | write | escrita | Cancel the data request made by the user |
| `tool_dataprivacy_contact_dpo` | write | escrita | Contact the site Data Protection Officer(s) |
| `tool_dataprivacy_create_data_request` | write | escrita | Creates a data request. |
| `tool_dataprivacy_get_access_information` | read | cuidado | Retrieving privacy API access (permissions) information for the current user. |
| `tool_dataprivacy_get_data_requests` | read | cuidado | Gets data request. |

#### `core_completion_*` — 4 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_completion_get_activities_completion_status` | read | cuidado | Return the activities completion status for a user in a course. |
| `core_completion_get_course_completion_status` | read | cuidado | Returns course completion status. |
| `core_completion_mark_course_self_completed` | write | escrita | Update the course completion status for the current user (if course self-completion is enabled). |
| `core_completion_update_activity_completion_status_manually` | write | escrita | Update completion status for the current user in an activity, only for activities with manual tracking. |

#### `core_enrol_*` — 4 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_enrol_get_course_enrolment_methods` | read | livre | Get the list of course enrolment methods |
| `core_enrol_get_enrolled_users` | read | cuidado | Get enrolled users by course id. |
| `core_enrol_get_users_courses` | read | cuidado | Get the list of courses where a user is enrolled in |
| `core_enrol_search_users` | read | cuidado | Search within the list of course participants |

#### `core_notes_*` — 4 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_notes_create_notes` | write | escrita | Create notes |
| `core_notes_delete_notes` | write | escrita | Delete notes |
| `core_notes_get_course_notes` | read | cuidado | Returns all notes in specified course (or site), for the specified user. |
| `core_notes_view_notes` | write | escrita | Simulates the web interface view of notes/index.php: trigger events. |

#### `core_search_*` — 4 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_search_get_results` | read | cuidado | Get search results. |
| `core_search_get_search_areas_list` | read | livre | Get search areas. |
| `core_search_get_top_results` | read | cuidado | Get top search results. |
| `core_search_view_results` | write | escrita | Trigger view search results event. |

#### `gradereport_user_*` — 4 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `gradereport_user_get_access_information` | read | livre | Returns user access information for the user grade report. |
| `gradereport_user_get_grade_items` | read | cuidado | Returns the complete list of grade items for users in a course |
| `gradereport_user_get_grades_table` | read | cuidado | Get the user/s report grades table for a course |
| `gradereport_user_view_grade_report` | write | escrita | Trigger the report view event |

#### `message_airnotifier_*` — 4 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `message_airnotifier_are_notification_preferences_configured` | read | livre | Check if the users have notification preferences configured yet |
| `message_airnotifier_enable_device` | write | escrita | Enables or disables a registered user device so it can receive Push notifications |
| `message_airnotifier_get_user_devices` | read | cuidado | Return the list of mobile devices that are registered in Moodle for the given user |
| `message_airnotifier_is_system_configured` | read | livre | Check whether the airnotifier settings have been configured |

#### `mod_choicegroup_*` — 4 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_choicegroup_delete_choicegroup_responses` | write | escrita | Delete the given submitted responses in a choice group |
| `mod_choicegroup_get_choicegroup_options` | read | cuidado | Retrieve options for a specific choicegroup. |
| `mod_choicegroup_submit_choicegroup_response` | write | escrita | Submit responses to a specific choicegroup item. |
| `mod_choicegroup_view_choicegroup` | write | escrita | Trigger the course module viewed event and update the module completion status. |

#### `mod_journal_*` — 4 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_journal_get_entry` | ? | sem-fonte | ? |
| `mod_journal_save_feedback` | ? | sem-fonte | ? |
| `mod_journal_set_text` | ? | sem-fonte | ? |
| `mod_journal_view_journal` | ? | sem-fonte | ? |

#### `core_badges_*` — 3 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_badges_get_badge` | read | cuidado | Retrieves a badge by id. |
| `core_badges_get_user_badge_by_hash` | read | cuidado | Returns the badge awarded to a user by hash. |
| `core_badges_get_user_badges` | read | cuidado | Returns the list of badges awarded to a user. |

#### `core_block_*` — 3 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_block_fetch_addable_blocks` | read | livre | Returns all addable blocks in a given page. |
| `core_block_get_course_blocks` | read | livre | Returns blocks information for a course. |
| `core_block_get_dashboard_blocks` | read | livre | Returns blocks information for the given user dashboard. |

#### `core_comment_*` — 3 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_comment_add_comments` | write | escrita | Adds a comment or comments. |
| `core_comment_delete_comments` | write | escrita | Deletes a comment or comments. |
| `core_comment_get_comments` | read | cuidado | Returns comments. |

#### `core_files_*` — 3 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_files_delete_draft_files` | write | escrita | Delete the indicated files (or directories) from a user draft file area. |
| `core_files_get_files` | read | cuidado | browse moodle files |
| `core_files_get_unused_draft_itemid` | write | escrita | Generate a new draft itemid for the current user. |

#### `mod_diary_*` — 3 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_diary_save_feedback` | ? | sem-fonte | ? |
| `mod_diary_set_text` | ? | sem-fonte | ? |
| `mod_diary_view_diary` | ? | sem-fonte | ? |

#### `mod_lti_*` — 3 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_lti_get_ltis_by_courses` | read | livre | Returns a list of external tool instances in a provided set of courses, if |
| `mod_lti_get_tool_launch_data` | read | cuidado | Return the launch data for a given external tool. |
| `mod_lti_view_lti` | read | escrita | Trigger the course module viewed event and update the module completion status. |

#### `qtype_stack_*` — 3 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `qtype_stack_library_import` | read | escrita | Import a given file from the library |
| `qtype_stack_library_render` | read | livre | Returns details of a question in a given file |
| `qtype_stack_validate_input` | read | livre | Validates STACK question type input data |

#### `aiplacement_courseassist_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `aiplacement_courseassist_explain_text` | write | escrita | Explain text for the Course Assistance Placement |
| `aiplacement_courseassist_summarise_text` | write | escrita | Summarise text for the Course Assistance Placement |

#### `aiplacement_editor_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `aiplacement_editor_generate_image` | write | escrita | Generate image for the HTML Text editor AI Placement |
| `aiplacement_editor_generate_text` | write | escrita | Generate text for the HTML Text editor AI Placement |

#### `core_ai_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_ai_get_policy_status` | read | cuidado | Get a users AI policy acceptance |
| `core_ai_set_policy_status` | write | escrita | Set a users AI policy acceptance |

#### `core_filters_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_filters_get_all_states` | read | livre | Retrieve all the filters and their states (including overridden ones in any context). |
| `core_filters_get_available_in_context` | read | livre | Returns the filters available in the given contexts. |

#### `core_rating_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_rating_add_rating` | write | escrita | Rates an item. |
| `core_rating_get_item_ratings` | read | cuidado | Retrieve all the ratings for an item. |

#### `enrol_guest_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `enrol_guest_get_instance_info` | read | livre | Return guest enrolment instance information. |
| `enrol_guest_validate_password` | write | escrita | Perform password validation. |

#### `enrol_self_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `enrol_self_enrol_user` | write | bloqueada-§2.2 | Self enrol the current user in the given course. |
| `enrol_self_get_instance_info` | read | livre | self enrolment instance information. |

#### `gradereport_overview_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `gradereport_overview_get_course_grades` | read | cuidado | Get the given user courses final grades |
| `gradereport_overview_view_grade_report` | write | escrita | Trigger the report view event |

#### `message_popup_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `message_popup_get_popup_notifications` | read | cuidado | Retrieve a list of popup notifications for a user |
| `message_popup_get_unread_popup_notification_count` | read | livre | Retrieve the count of unread popup notifications for a given user |

#### `mod_book_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_book_get_books_by_courses` | read | livre | Returns a list of book instances in a provided set of courses |
| `mod_book_view_book` | write | escrita | Simulate the view.php web interface book: trigger events, completion, etc... |

#### `mod_folder_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_folder_get_folders_by_courses` | read | livre | Returns a list of folders in a provided list of courses, if no list is provided all folders that |
| `mod_folder_view_folder` | write | escrita | Simulate the view.php web interface folder: trigger events, completion, etc... |

#### `mod_imscp_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_imscp_get_imscps_by_courses` | read | livre | Returns a list of IMSCP instances in a provided set of courses |
| `mod_imscp_view_imscp` | write | escrita | Simulate the view.php web interface imscp: trigger events, completion, etc... |

#### `mod_page_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_page_get_pages_by_courses` | read | livre | Returns a list of pages in a provided list of courses, if no list is provided all pages that the user |
| `mod_page_view_page` | write | escrita | Simulate the view.php web interface page: trigger events, completion, etc... |

#### `mod_resource_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_resource_get_resources_by_courses` | read | livre | Returns a list of files in a provided list of courses, if no list is provided all files that |
| `mod_resource_view_resource` | write | escrita | Simulate the view.php web interface resource: trigger events, completion, etc... |

#### `mod_url_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_url_get_urls_by_courses` | read | livre | Returns a list of urls in a provided list of courses, if no list is provided all urls that the user |
| `mod_url_view_url` | write | escrita | Trigger the course module viewed event and update the module completion status. |

#### `mod_zoom_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_zoom_get_state` | read | cuidado | Determine if a zoom meeting is available, meeting |
| `mod_zoom_grade_item_update` | write | escrita | Creates or updates grade item for the given zoom instance and returns join url. |

#### `tool_moodlenet_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `tool_moodlenet_search_courses` | read | livre | For some given input search for a course that matches |
| `tool_moodlenet_verify_webfinger` | read | livre | Verify if the passed information resolves into a WebFinger profile URL |

#### `tool_policy_*` — 2 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `tool_policy_get_user_acceptances` | read | cuidado | Get user policies acceptances. |
| `tool_policy_set_acceptances_status` | write | escrita | Set the acceptance status (accept or decline only) for the indicated policies for the given user. |

#### `block_recentlyaccesseditems_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `block_recentlyaccesseditems_get_recent_items` | read | cuidado | List of items a user has accessed most recently. |

#### `block_starredcourses_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `block_starredcourses_get_starred_courses` | read | cuidado | Get users starred courses. |

#### `core_get_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_get_component_strings` | read | livre | Return all raw strings (with {$a->xxx}), for a specific component |

#### `core_h5p_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_h5p_get_trusted_h5p_file` | read | livre | Get the H5P file cleaned for Mobile App. |

#### `core_my_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_my_view_page` | write | escrita | Trigger the My or Dashboard viewed event. |

#### `core_question_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_question_update_flag` | write | escrita | Update the flag state of a question attempt. |

#### `core_table_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_table_get_dynamic_table_content` | read | cuidado | Get the dynamic table content raw html |

#### `core_webservice_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `core_webservice_get_site_info` | read | livre | Return some site info / user info / list web service functions |

#### `editor_tiny_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `editor_tiny_get_configuration` | read | livre | Returns the TinyMCE configuration for a context. |

#### `gradereport_grader_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `gradereport_grader_get_users_in_report` | read | cuidado | Returns the dataset of users within the report |

#### `gradereport_singleview_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `gradereport_singleview_get_grade_items_for_search_widget` | read | cuidado | Get the gradeitem/(s) for a course |

#### `mod_checklist_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_checklist_update_item_state` | write | escrita | ? |

#### `mod_dialogue_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_dialogue_search_users` | ? | sem-fonte | ? |

#### `mod_label_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_label_get_labels_by_courses` | read | livre | Returns a list of labels in a provided list of courses, if no list is provided all labels that the user |

#### `mod_questionnaire_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_questionnaire_submit_questionnaire_response` | write | escrita | Questionnaire submit |

#### `mod_simplecertificate_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_simplecertificate_create_issue` | write | escrita | Create a new certificate issue for a user |

#### `mod_subcourse_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `mod_subcourse_view_subcourse` | ? | sem-fonte | ? |

#### `report_insights_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `report_insights_action_executed` | write | escrita | Stores an action executed over a group of predictions. |

#### `tiny_premium_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `tiny_premium_get_api_key` | read | cuidado | Get the Tiny Premium API key from Moodle |

#### `tool_analytics_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `tool_analytics_potential_contexts` | read | livre | Retrieve the list of potential contexts for a model. |

#### `tool_certificate_*` — 1 funções

| função | tipo declarado | risco | descrição (Moodle 5.0 `db/services.php`) |
|---|---|---|---|
| `tool_certificate_revoke_issue` | ? | sem-fonte | ? |

---

## Apêndice B — o que este catálogo deixou aberto

Coisas que só fecham com uma chamada, e que por isso **não foram fechadas**. Registradas aqui
em vez de resolvidas em silêncio, como pede o §0 do SPEC.

1. **`core_course_get_enrolled_courses_by_timeline_classification` com `classification=inprogress`
   bate com as 10 disciplinas do filtro `startdate`/`enddate`?** Se bater, a regra de negócio da
   Fase 1 sai de graça da própria API. Uma chamada, allowlist explícita.
2. **`core_completion_get_activities_completion_status` é barata e os professores da USP usam
   conclusão de atividade?** Poderia ser o caminho leve para "o que falta".
3. **`core_search_get_results` está habilitada neste site?** Se estiver, "onde está o PDF"
   pode virar uma chamada em vez de ~14,5k tokens de `get_contents`.
4. **`gradereport_user_get_grade_items` com `courseid=0`** — o default é 0 e não sei o que ele
   faz. Pode ser erro, pode ser "todos os cursos" e uma resposta gigante.
5. **O corpo de `tool_mobile_get_content` e de `tool_moodlenet_*`** — li a assinatura, não a
   implementação. Ambos aceitam entrada que vira comportamento do servidor.
6. **As 10 funções `sem-fonte`** (`mod_journal_*`, `mod_diary_*`, `mod_dialogue_search_users`,
   `mod_subcourse_view_subcourse`, `tool_certificate_revoke_issue`). Plugins de contribuição
   instalados pela USP; o código não está nos repositórios que localizei. Tudo o que este
   catálogo diz delas é inferência a partir do nome.
7. **Se o token do Caio tem capability de correção em alguma disciplina** (monitoria, PAE). Isso
   muda §6.6 de "falharia por permissão" para "funcionaria". `core_enrol_get_users_courses`
   devolve `roles` por curso e responderia — mas é uma chamada, e não foi feita aqui.
8. **A rotação do `authtoken` do iCal numa conta de SSO.** A derivação está verificada
   (`sha1(id + hash_da_senha + salt)`); o comportamento do campo `password` numa conta sem
   senha local, não.
