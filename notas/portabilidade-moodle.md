# O servidor do Moodle funciona fora da USP? (medição de 13/09/2026)

Pergunta do dono: o que montamos serve só para o e-Disciplinas, ou serve para o
Moodle da Unicamp, das federais, de universidade fora do Brasil?

**Nenhuma chamada autenticada foi feita, em lugar nenhum.** As duas fontes desta
nota são (a) o código-fonte do Moodle no GitHub `moodle/moodle` e (b) **uma**
requisição *não autenticada* por site a
`/lib/ajax/service-nologin.php?info=tool_mobile_get_public_config` — a mesma que
o app oficial do Moodle faz antes de qualquer login, declarada
`loginrequired => false` no core. Sem token, sem credencial, um request por
host. A Regra de Ouro do §3.1 continua de pé.

---

## 1. Resposta curta

O **Moodle** é portável quase inteiro; o **RUCard** e o **Jupiter** não são
portáveis em nada.

| servidor | fora da USP |
|---|---|
| `usp_mcp/moodle` | o protocolo e as 5 funções são core upstream; o que trava são 4 pontos localizados, todos no nosso código |
| `usp_mcp/rucard` | **zero** — `uspdigital.usp.br/rucard`, bandejão da USP |
| `usp_mcp/jupiter` | **zero** — `uspdigital.usp.br/jupiterweb`, endpoint DWR proprietário |

---

## 2. A superfície que usamos é 100% core do Moodle **[fonte]**

As 5 funções da `politica.ALLOWLIST` estão declaradas no core, com
`'services' => array(MOODLE_OFFICIAL_MOBILE_SERVICE)` — isto é, **entram
automaticamente** em qualquer site que habilite o serviço mobile. Não há
configuração por função, nem plugin da USP envolvido.

| função | arquivo no core (`MOODLE_500_STABLE`) | existe desde |
|---|---|---|
| `core_webservice_get_site_info` | `lib/db/services.php:2810` | ≤ 2.9 |
| `core_enrol_get_users_courses` | `lib/db/services.php:870` | ≤ 2.9 |
| `core_course_get_contents` | `lib/db/services.php:548` | ≤ 2.9 |
| `core_calendar_get_action_events_by_timesort` | `lib/db/services.php:270` | **3.3** |
| `mod_assign_get_assignments` | `mod/assign/db/services.php:46` | ≤ 2.9 |

Verificado branch a branch (2.9, 3.3, 3.5, 3.9, 3.11, 4.1, 4.5, 5.0): as quatro
primeiras existem em todas; a do calendário **não existe em 2.9 e existe a
partir de 3.3**. **Piso do projeto: Moodle 3.3 (2017).**

O resto do transporte também é core, e não convenção da USP:

- `/webservice/rest/server.php` com `wstoken`+`wsfunction`+`moodlewsrestformat`;
- `/webservice/pluginfile.php` lendo o token com
  `required_param('token', PARAM_ALPHANUM)` (`webservice/pluginfile.php:47`) —
  `required_param` lê GET **e** POST, então o "token no corpo" medido em 01/09
  vale em qualquer Moodle, não é peculiaridade do e-Disciplinas;
- o teto `limitnum` entre 1 e 50 de `o_que_vence` é validação do core
  (`calendar/classes/local/api.php:146`), com default 20 — a medição de 31/08
  contra a USP bate com o upstream;
- o fluxo de token do `scripts/token.sh` é `admin/tool/mobile/launch.php`, do
  plugin core `tool_mobile`, com os mesmos parâmetros (`passport`, `urlscheme`,
  `confirmed`, `forcedurlscheme`) em 3.11, 4.1, 4.5 e 5.0.

Consequência: `usp_mcp/moodle/politica.py` inteiro — allowlist e bloqueio
permanente do §2.2 — é uma lista de nomes **do core**. Ela vale igual em
qualquer instituição. Um plugin de terceiro de outra universidade simplesmente
não está na allowlist, e o default é negar: erra para o lado seguro.

---

## 3. O serviço está ligado nessas instituições? **[medido 13/09/2026]**

Uma requisição não autenticada por site. `mobile` é
`enablemobilewebservice`, `login` é `typeoflogin`
(1 = formulário no app, 3 = navegador embutido/SSO).

| instituição | host | ws | mobile | login |
|---|---|---:|---:|---:|
| USP — e-Disciplinas | `edisciplinas.usp.br` | 1 | **1** | 3 |
| Unicamp | `moodle.ggte.unicamp.br` | 1 | **1** | 1 |
| UFRGS | `moodle.ufrgs.br` | 1 | **1** | 1 |
| UnB — Aprender 3 | `aprender3.unb.br` | 1 | **1** | 1 |
| UFPR Virtual | `ufprvirtual.ufpr.br` | 1 | **1** | 1 |
| UFC | `moodle2.quixada.ufc.br` | 1 | **1** | 1 |
| IFRS | `moodle.ifrs.edu.br` | 1 | **1** | 1 |
| Open University (UK) | `learn2.open.ac.uk` | 1 | **1** | 3 |
| Humboldt (Berlim) | `moodle.hu-berlin.de` | 1 | **1** | 3 |
| UNESP | `moodle.unesp.br` | 1 | **1** | 1 |
| UFABC | `moodle.ufabc.edu.br` | 1 | **1** | 1 |
| UFES | `ava.ufes.br` | 1 | **1** | 1 |
| UTFPR | `moodle.utfpr.edu.br` | 1 | **1** | 1 |
| UFJF | `ead.ufjf.br` | 1 | **1** | **2** |
| Moodle demo | `school.moodledemo.net` | 1 | **1** | 1 |
| **Monash (Austrália)** | `learning.monash.edu` | 1 | **0** | 1 |
| moodle.org | `moodle.org` | 1 | **1** | 1 |

**Placar: 17 sites Moodle alcançados, 16 com o serviço ligado, 1 sem.**
Ampliado em 14/09/2026 com mais 20 hosts brasileiros tentados (5 responderam, e
todos os 5 com o serviço ligado). A UFJF trouxe `typeoflogin=2` — os três modos
que o core define aparecem todos na amostra.

**Monash é o contraexemplo, e ele é o dado importante:** o serviço mobile é uma
decisão do administrador do site, não do Moodle. Onde ele está desligado, nada
do nosso servidor funciona e não há o que consertar no nosso lado. Não afirme
"funciona em qualquer Moodle" — afirme "funciona onde `enablemobilewebservice`
está ligado", e **isso é medível em uma requisição sem credencial**, com a
chamada do topo desta nota.

Quatro hosts brasileiros não responderam ao probe (UFSC, UFSCar, PUC-Rio,
UFRN). Isso é **URL provavelmente errada da minha parte**, não evidência de
serviço desligado — UFRN usa SIGAA, que nem é Moodle. Não conte como negativo.

Achado lateral do `typeoflogin`: nas instituições com `login=1` (Unicamp,
UFRGS, UnB, UFPR, UFC, IFRS) existe o caminho de `/login/token.php`, um POST
único com usuário e senha — **mais simples que o da USP**, que é `login=3`
(SSO) e por isso exige o `launch.php` com navegador logado que o
`scripts/token.sh` implementa. Ou seja: o caso da USP é o mais difícil dos
dois, e o `token.sh` resolve o difícil.

---

## 4. O que no NOSSO código é da USP e trava fora dela

Quatro pontos. Nenhum é do protocolo; todos são nossos.

### 4.1 `shortname` "SIGLA-ano" é convenção do e-Disciplinas — e a busca não cobre a falta

`disciplinas.py` deriva a sigla de `rotulo.split("-")[0]` ("PSI3323-2026" →
"PSI3323"). Fora da USP o `shortname` é o que a instituição quiser
("BIO101", "2026S2-BIO-101", "Intro to Biology").

O agravante está em `resolver`: o match parcial olha `d.sigla` e `d.nome`
(`fullname`) e **nunca olha `d.rotulo`**. Num site com shortname
"2026S2-BIO-101", a sigla vira "2026S2" e procurar por "BIO101" não acha nada —
mesmo com a string literalmente presente no shortname. Na USP isso nunca
aparece porque sigla é, por construção, o primeiro segmento do rótulo.

Degrada bem para busca por nome ("biology" casa com o `fullname`), e o
Invariante 6 segura o resto: a mensagem de "não achei" lista as siglas
existentes. Mas é a diferença entre portável e quase-portável.

**Corrigido em 15/09/2026 — e o 4.1 estava subestimado.** Ao medir as duas
capturas desta conta para escrever a correção, os dois lados apareceram maiores
do que esta seção dizia, e nenhum deles é de fora da USP:

- **O rótulo fora da busca custava em casa.** Digitar o rótulo inteiro — que é
  exatamente o que a ferramenta `disciplinas` imprime na tela — não achava nada
  em **69 das 74** matrículas de `users_courses.json` (44 de 47 na captura de
  15/09). Copiar da resposta e colar na pergunta seguinte devolvia "não
  encontrei".
- **O `split("-")` não era convenção da USP, era suposição sobre ela.** O
  separador do `shortname` nesta conta é `-` (69), `_` (2), espaço (1), `.` (1)
  e nenhum (1). E o estrago não foi "não acha": a conta tem
  `PEA3301_2026_1sem` (cursando) e `PEA3301-2021`, a primeira recebia a sigla
  `PEA330120261SEM` e a segunda ficava com `PEA3301` sozinha — então perguntar
  por "PEA3301" tinha uma candidata só, e `material` ao vivo em 15/09 respondeu
  com 177 itens sobre a de 2021. **Escolha calada, dentro da USP, em disciplina
  do semestre corrente.**

A sigla passou a ser o primeiro pedaço alfanumérico do rótulo (`PTC3314-2026`
continua dando `PTC3314`), e o rótulo entrou na busca com exato antes de
parcial nos dois níveis. O caso `2026S2-BIO-101` procurado como "BIO101"
resolve — não porque a sigla ficou certa (ela ainda sai `2026S2`, e nenhum corte
conserta isso), mas porque a busca passou a olhar o rótulo. Os outros três
pontos do §4 continuam abertos.

### 4.2 Fuso fixo em −3

`projecao.FUSO_SAO_PAULO = timezone(timedelta(hours=-3))`, com justificativa
boa **para o Brasil** na docstring. Em Berlim ou na Open University todo horário
de entrega sai deslocado — e deslocado em silêncio, que é o modo de falhar que
o Invariante 6 proíbe. **E este é o único dos quatro que não dá para derivar do token.** Conferido em
14/09/2026 no core (`webservice/externallib.php`): `core_webservice_get_site_info`
devolve `lang`, `sitecalendartype` e `usercalendartype`, e **nenhum campo de
fuso** — o mesmo vale para `get_public_config`. Ou seja, a regra do §2 do
`CONVENTIONS.md` ("derive, não configure", que fechou a questão do `userid`) não
tem como valer aqui: a cura é env var ou o fuso local da máquina, e a diferença
entre as duas é uma decisão, não uma medição.

### 4.3 `slasharguments` desligado quebra `baixar_arquivo` — em silêncio

`url.set_slashargument` (`lib/classes/url.php:632`): quando
`$CFG->slasharguments` está vazio, a `fileurl` sai como
`…/webservice/pluginfile.php?file=/…` em vez de `…/webservice/pluginfile.php/…`.
Nosso código assume a segunda forma em dois lugares que exigem a barra:
`cliente._PREFIXO_ARQUIVO` e `material._fileid`.

O desfecho é o pior possível: `_fileid` devolve `None`, `_entregar`
(`arquivo.py:222`) classifica o arquivo como **link externo**, e `_url_publica`
já tinha devolvido `None` porque `_MARCAS_INTERNAS` (que casa sem a barra)
reconheceu o host interno. O usuário recebe o arquivo listado como link com
**URL vazia**. Nada de erro, nada de aviso.

Não sei se algum site real roda com `slasharguments` desligado — é default
ligado há muitas versões. Mas o modo de falha é mudo, e é isso que o torna caro.

### 4.4 Língua e nome no que o modelo lê

`_DIAS_SEMANA` e `_TIPOS_PT` em português, e as três `description` de
`server.py` dizem "e-Disciplinas (Moodle da USP)" e dão exemplos com siglas da
Poli. É o que faz o modelo escolher a ferramenta certa em português — e é
exatamente o que atrapalharia um usuário da Open University. Não é bug; é
escopo declarado.

Fora desses quatro: `MOODLE_URL` já é env var com a USP só como default
(`server._URL_PADRAO`), e a concatenação `{url}/webservice/...` funciona
inclusive com Moodle instalado em subdiretório. Um `MOODLE_URL` com barra no
fim, porém, monta `//webservice/pluginfile.php/` e faz a checagem de origem do
`baixar` recusar tudo — vale normalizar.

---

## 5. Como extrapolar para uma faculdade qualquer

O probe do §3 virou `scripts/compatibilidade.sh` em 14/09/2026, porque ele é a
única metade desta pergunta que se responde **sem credencial**:

```
./scripts/compatibilidade.sh https://moodle.ggte.unicamp.br
```

Uma requisição, sem token, e três desfechos distintos em vez de um "deu erro":
transporte funciona (sai 0), serviço desligado no site (sai 1, e não há o que
consertar do nosso lado), URL que não é raiz de Moodle (sai 2). Ele também diz
qual caminho de token usar, derivado do `typeoflogin` — e **não** imprime esse
passo a passo quando o serviço está desligado, porque mandar alguém buscar token
numa porta que o próprio script acabou de medir como fechada seria o oposto do
Invariante 6.

O que ele deliberadamente **não** promete: verde ali é "o transporte existe e
está ligado", nunca "as três ferramentas vão responder bem". Os quatro pontos do
§4 continuam de pé, e três deles só aparecem com token na mão. Essa distinção é
metade do valor do script.

## 6. O que NÃO foi verificado

- **Nenhuma execução real contra um Moodle não-USP.** Obter token exige
  autenticar, e isso é decisão e credencial do dono (Invariante 4). O que dá
  para fazer em um passo, no site de demonstração do próprio Moodle:

  ```
  curl -sS -d "username=student" -d "password=moodle" \
       -d "service=moodle_mobile_app" \
       https://school.moodledemo.net/login/token.php
  ```

  e depois `MOODLE_URL=https://school.moodledemo.net MOODLE_TOKEN=<token>
  ./scripts/ws.sh core_webservice_get_site_info`. É a medição que fecharia esta
  nota de verdade — e provavelmente exporia o 4.1 na primeira pergunta, porque
  o Mount Orange usa shortname que não é sigla.
- Se algum site real roda `slasharguments=0` (§4.3).
- Se as instituições com `login=1` de fato aceitam `/login/token.php` — o
  `typeoflogin` diz o que o app deve fazer, não garante o endpoint.
- Os 4 hosts que não responderam ao probe (§3).
