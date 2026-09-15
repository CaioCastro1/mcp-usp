# Questionário: o que eu já fiz, e o que ainda posso fazer — design

> 15/09/2026. Spec do item **D1** do `docs/decisions/ROADMAP-proximos-passos.md`.
> Este documento **não reabre o §2.2** — faz o contrário: propõe duas funções
> novas *para dentro* do bloqueio permanente, e as duas são de **leitura**.
>
> O item D1 existe porque metade dos vencimentos reais é questionário: numa
> amostra de 14 dias, 3 dos 4 itens de `o_que_vence` eram `questionário`
> **[roadmap D1]**, e o calendário vê quiz em 6 disciplinas contra 4 que têm
> `assign` **[notas/fase1-moodle.md]**. Hoje o projeto responde prazo para essa
> metade e não responde mais nada sobre ela.
>
> O trabalho difícil aqui não é a ferramenta. É desenhar **onde fica a
> fronteira** com `mod_quiz_start_attempt`, `mod_quiz_save_attempt` e
> `mod_quiz_process_attempt` — que continuam bloqueadas — e sustentar essa
> fronteira com teste, não com boa intenção.

## O que está decidido hoje, e continua

`usp_mcp/moodle/politica.py:103` lista 40 nomes no `BLOQUEIO_PERMANENTE`
**[código]**. Três são da família quiz, e nenhuma sai desta trilha:

| função | por que está lá |
|---|---|
| `mod_quiz_start_attempt` | abre tentativa; queima uma tentativa de prova real |
| `mod_quiz_save_attempt` | escreve resposta dentro da tentativa aberta |
| `mod_quiz_process_attempt` | finaliza (`finishattempt=true`); é o `finish` deste Moodle |

`decidir` recusa as três antes de olhar a allowlist, e recusa **mesmo com
`permitir_escrita=True`** **[código, `politica.py:190`]**.

O spec irmão de hoje (`2026-09-15-entrega-com-confirmacao-design.md`) tirou duas
funções de `mod_assign` dessa lista, sob condição, e **deixou as três de quiz
onde estavam**, com a razão escrita: para entrega existe estado anterior legível
e rascunho que se sobrescreve, para tentativa não existe rascunho e
`start_attempt` já é irreversível. Este spec assume aquela decisão como dada.

## A pergunta que hoje fica sem resposta

*"Ainda dá pra refazer o Teste semanal 12? Quantas tentativas eu já usei?"*

Percorrendo o que existe, uma a uma:

- `o_que_vence` diz que o questionário vence e quando — e nada sobre o que já
  foi feito. Ela traduz `quiz` como "questionário" e para por aí **[código,
  `o_que_vence.py:37`]**.
- `ja_entreguei` **recusa a pergunta por escrito**: *"questionário (`quiz`) não
  passa por `mod_assign_*`"* **[código, `ja_entreguei.py:41`]**, e há teste que
  exige que ela diga isso em voz alta **[`tests/moodle/test_ja_entreguei.py:400`]**.
- `atrasadas` tem a mesma lacuna e o mesmo teste **[`test_atrasadas.py:428`]**.
- `notas PTC3314` chega mais perto do que o roadmap supõe, e é o ponto que este
  spec precisa resolver antes de propor qualquer coisa: a captura real de 15/09
  traz **13 itens de nota com `itemmodule: "quiz"`**, com nome e nota, dos 20
  itens da disciplina **[fixture `grade_items_ptc3314.json`]**. Ou seja: **a nota
  do questionário já sai hoje**, item a item. O D1 diz que a ferramenta de notas
  "cobre a nota final do curso" e que esta cobriria o item — isso está errado, e
  a fixture desmente.

O que `notas` **não** responde, e nenhuma outra ferramenta responde:

1. **quantas tentativas eu usei, e quantas ainda tenho.** Não existe esse número
   em lugar nenhum do projeto.
2. **"não fiz" contra "fiz e não corrigiu".** Item sem nota é a mesma string
   (`"-"`) nos dois casos **[código, `notas.py:70`]**. Em prova isso é
   ambíguo; em questionário é pior, porque questionário costuma corrigir na hora
   — então item vazio é *quase sempre* "não fiz", e "quase sempre" não é resposta
   que se dá a quem pergunta na véspera.
3. **de quanto era.** `notas` documenta, com medição, que `grademax` não vem na
   resposta de `gradereport_user_get_grade_items` e que derivar seria inferência
   apresentada como dado **[`notas.py`, cabeçalho]**. Para questionário o máximo
   existe em outra função, como campo próprio — se a conta de aluno o receber
   (ver *Medição pendente*, ponto 2).

É a interseção de "vence" com "já fiz", para a metade dos vencimentos que
`ja_entreguei` recusa. Isso é uma pergunta, não uma função sobrando na API.

## Decisão 1 — uma ferramenta nova, e nem `notas` ganha parâmetro

**Uma.** Chamada `questionarios`, com `disciplina` obrigatória e `questionario`
opcional.

**Por que não é parâmetro da `notas`.** O precedente de 14/09 diz que "como estou
de nota?" e "como estou de nota em PTC3314?" são a mesma pergunta com e sem
escopo, e por isso são uma ferramenta com parâmetro **[§9, 14/09]**. O critério
ali é a pergunta, e é o mesmo critério que separa aqui: `notas` responde *quanto
tirei*, e esta responde *o que ainda posso fazer*. Verbo diferente, tempo verbal
diferente, e — o que decide — a resposta desta muda quando ninguém tirou nota
nenhuma, que é exatamente o caso em que `notas` não tem o que dizer. Enfiar isso
num parâmetro faria uma ferramenta chamada `notas` responder sobre prazo e
orçamento de tentativa, e obrigaria o modelo a descobrir uma combinação de
parâmetros para chegar a uma resposta que o nome da ferramenta não promete.

**Por que não duas ou três.** O Anexo A (§7) avisa contra derivar ferramenta da
lista de funções, e três funções novas convidam a exatamente isso: uma para
`best_grade`, uma para `user_attempts`, uma para `attempt_review`. As três
responderiam pedaços de uma pergunta só, e o §5 exige que uma pergunta se resolva
em **uma chamada de ferramenta** do ponto de vista do modelo. Uma delas — a de
nota — seria ainda pior que redundante: duplicaria um número que `notas` já dá,
por outro caminho, com risco de os dois discordarem (ver Decisão 4).

**Por que ferramenta separada e não uma linha dentro de `ja_entreguei`.** O
precedente é `atrasadas`, que existe como ferramenta própria usando **o mesmo
par de funções** de `ja_entreguei`, porque é outra pergunta sobre os mesmos
objetos **[código, `diagnostico.py:69`]**. Aqui nem as funções são as mesmas:
questionário não tem rascunho, tem orçamento de tentativa, e o vocabulário de
saída de `ja_entreguei` (ENTREGUE / RASCUNHO NÃO ENVIADO) não descreve nada
disso. Somar quiz lá dentro também dobraria a contagem de chamadas de uma
ferramenta que já tem teto de 10 **[código, `ja_entreguei.py:TETO_CONSULTAS`]**.

As duas se apontam, que é o padrão que `o_que_mudou` já usa. Isso **muda o texto
que `ja_entreguei` imprime hoje**, e esse texto tem teste que o exige
(`test_ja_entreguei.py:400`): a frase deixa de ser só "questionário não passa por
aqui" e passa a dizer para onde ir. O teste muda junto, no mesmo commit.

**Por que o nome.** "Questionário" é a palavra que o e-Disciplinas imprime e que
`o_que_vence` já devolve em português **[código]** — o modelo que acabou de ler
`o_que_vence` tem a palavra na mão. O nome-pergunta (`ja_fiz`) foi considerado e
descartado: `ja_entreguei` e `ja_fiz` ficam a uma palavra de distância na cabeça
de quem gera a chamada, que é o risco medido no spec de entrega de hoje para
`salvar` e `entregar`.

### Forma da resposta

```
PTC3314 — questionários em aberto (2 de 13)

  Teste semanal - 12 — reflexões em vários dielétricos
    fecha 18/09 23:59 (faltam 3 dias)
    tentativas: 1 de 3 usadas — ainda dá para refazer 2 vezes
    melhor até agora: 6,00 de 10,00 (tentativa 1, 12/09 21:04)

  Teste semanal - 13 — incidência oblíqua
    fecha 25/09 23:59
    tentativas: nenhuma finalizada, 3 disponíveis

⚠ Esta ferramenta lê e só. Ela não abre, não responde e não finaliza
  questionário, e não há configuração que a faça abrir.
⚠ Tentativa EM ANDAMENTO não é contada aqui (ver Decisão 3): se você tem uma
  aberta agora, o número de tentativas restantes acima está otimista por uma.
⚠ 11 questionários já fechados não aparecem acima. A nota deles sai em
  `notas PTC3314`.
```

O recorte padrão — **só o que ainda está aberto** — não é economia, é a divisão
de trabalho com `notas`: questionário fechado é pergunta de nota, e `notas` já
responde; questionário aberto é pergunta de tentativa, e é esta. `questionario`
dito por nome passa por cima do recorte, inclusive para um já fechado.

## Decisão 2 — as funções, e o teto de chamadas

Entram na `ALLOWLIST` **três** nomes, que vão de 11 para 14 **[código]**:

| função | o que ela dá que ninguém mais dá | risco no catálogo |
|---|---|---|
| `mod_quiz_get_quizzes_by_courses` | o questionário existe, o prazo, quantas tentativas são permitidas (`0` = ilimitadas), a nota máxima, e o `quizid` | livre **[catálogo §3.8]** |
| `mod_quiz_get_user_attempts` | quantas tentativas eu finalizei, e quando | cuidado **[catálogo §3.8]** |
| `mod_quiz_get_user_best_grade` | a melhor nota, **na escala do questionário** | cuidado **[catálogo §3.8]** |

`get_user_best_grade` parece derivável de `get_user_attempts` — cada tentativa
traz `sumgrades` — e não é: `sumgrades` está na escala bruta da soma das
questões, e converter para a escala do questionário exige multiplicar por
`grade/sumgrades` do quiz. Isso é aritmética sobre dois campos, apresentada como
nota. É o mesmo erro que `notas` já cometeu e reverteu com o `grademax`
derivado, e o §9 de 15/09 registra a regra: inferência apresentada como dado é
o que o Invariante 6 proíbe. Uma chamada a mais custa menos que um número errado.

A gêmea `mod_quiz_get_user_quiz_attempts` — descrição idêntica no site
**[catálogo §3.8]** — **não entra**. Uma pergunta, uma função escolhida à mão.

**Custo em chamadas, e o teto.** `get_quizzes_by_courses` é uma por disciplina;
as outras duas são **por questionário**. PTC3314 tem 13 **[fixture
`grade_items_ptc3314.json`]**, então a versão ingênua custaria 1 + 2×13 = **27
idas ao Moodle numa invocação**, cada uma no log da conta do dono (Invariante 5).
Vale o precedente de `ja_entreguei`: teto declarado, com o nome do parâmetro que
o evita. `TETO_QUESTIONARIOS = 5` → no máximo **11 chamadas** sem escopo, e
exatamente **3** quando `questionario` é dito — que é o caso principal.

`courseids` vai **sempre explícito**, nunca a lista vazia que o site aceita como
"todos os cursos" **[catálogo §3.8]**: são 74 matrículas **[§9, 14/09]**, e o
catálogo registra que ninguém verificou o que o default faz. Mesma regra dos dois
parâmetros que `notas` manda e a API não exige **[`notas.py`, cabeçalho]**.

`userid` vai derivado do token, nunca configurado, com cache quente de
`disciplinas.carregar` **[código, `notas.py:224`]**.

### O que muda em `FUNCOES_POR_FERRAMENTA`

`usp_mcp/moodle/diagnostico.py:37` ganha **uma linha**, e as nove existentes não
mudam:

```python
    # `questionarios` (15/09) exige as três de quiz JUNTAS, e não uma ou outra
    # como `notas`: `get_user_attempts` e `get_user_best_grade` pedem um
    # `quizid`, e o único lugar de onde ele sai é `get_quizzes_by_courses`. Um
    # site com só as duas últimas não responde meia pergunta — não responde
    # nenhuma. É o mesmo formato de dependência que `avisos` tem com o fórum.
    "questionarios": (
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
        "mod_quiz_get_quizzes_by_courses",
        "mod_quiz_get_user_attempts",
        "mod_quiz_get_user_best_grade",
    ),
```

As duas primeiras são a resolução de sigla, que toda ferramenta com escopo de
disciplina já exige **[código, `diagnostico.py:64`]**.

**D4 é o teste que torna essa linha obrigatória.** Ele afirma que a união da
tabela é **igual** ao conjunto da allowlist **[`tests/moodle/test_diagnostico.py:105`]**
— não "contida", igual. Então acrescentar os três nomes à allowlist sem
acrescentar esta linha reprova D4, e acrescentar a linha sem os nomes reprova
igual. É exatamente o drift que D4 existe para impedir, e é o motivo de esta
seção existir no spec em vez de ser detalhe de implementação: um site que não
tenha `mod_quiz_*` precisa ver `questionarios NÃO — faltam: ...` em vez de um OK
que quebra na primeira pergunta.

D1 (o teste homônimo do diagnóstico, sem relação com o item D1 do roadmap) itera
sobre a tabela e exige `OK` para cada ferramenta no site completo: a linha nova
entra no laço sozinha, sem mudança no teste.

## Decisão 3 — a fronteira, e é aqui que este spec se paga

`mod_quiz_get_attempt_review` pede um `attemptid`. O caminho natural para
descobrir um `attemptid` é chamar a função que **fabrica** um, e essa função é
`mod_quiz_start_attempt`. É a única vizinhança do projeto em que um identificador
que a leitura precisa nasce de uma escrita bloqueada — por isso o desenho é uma
regra, e não um cuidado.

### R1. Nenhum identificador de tentativa entra ou sai deste projeto

Nenhuma ferramenta aceita `attemptid`, `quizid` ou `cmid`. Os parâmetros são
`disciplina` (sigla) e `questionario` (nome ou pedaço), como em todas as outras.
O `quizid` nasce dentro da invocação, em `get_quizzes_by_courses`, e morre nela.
O `attemptid` chega dentro da resposta de `get_user_attempts` e **não é
projetado**: não aparece na saída, não volta em parâmetro nenhum, não é
mencionado em aviso.

A razão é operacional, não estética: enquanto nenhum `attemptid` entrar nem sair,
não existe pergunta cujo próximo passo útil seja *"me arruma um attemptid"* — e é
essa pergunta, e só ela, que encosta na função bloqueada. Uma fronteira que
depende de o modelo não querer é frágil; uma que depende de o identificador não
existir no vocabulário da ferramenta é verificável (Q7, Q10).

### R2. `status` é literalmente `"finished"`, sempre

`get_user_attempts` tem `status [opt='finished']` **[catálogo §3.8]**, e este
projeto não confia em default não verificado. Mais importante: `unfinished` e
`all` devolvem **tentativa em andamento**, e "você tem uma tentativa aberta
agora" é a deixa perfeita para "então termina pra mim" — com as duas funções que
terminariam a um nome de distância.

O preço está declarado na saída: a contagem de tentativas restantes ignora a que
estiver em curso, e pode estar otimista por uma. Uma linha de aviso (Invariante
7) é mais barata que ensinar ao modelo que existe uma tentativa aberta.

A asserção é sobre o parâmetro **enviado**, não sobre a saída — o dublê devolve o
que o teste mandou (item 11 do `CLAUDE.md`), e `ClienteFalso.params_de` existe
para isso **[`tests/moodle/conftest.py:215`]**.

### R3. `mod_quiz_get_attempt_review` fica fora desta fase

Três razões, em ordem de peso:

1. **A pergunta dela já foi recusada com dado.** "O que eu errei" é outra
   pergunta — é o que `notas` diz ao descartar o `feedback` do professor,
   contando quantos itens têm comentário e mandando para a página da disciplina
   **[código, `notas.py:312`]**. Reabrir isso precisa de dado novo, não de uma
   função disponível.
2. **O que ela devolve é o enunciado renderizado.** Ou a projeção joga o `html`
   fora — e sobra "você errou as questões 4 e 7", que cabe num clique no site —,
   ou o `html` entra, e aí conteúdo de prova entra no contexto de um modelo. O
   catálogo já classificou essa família: expor conteúdo de prova a um modelo é o
   cenário que motiva o §2.2 **[catálogo §3.8, §6.10]**.
3. **É a única das três que exige `attemptid`.** Sem ela, R1 é uma regra de uma
   linha, e regra de uma linha é a que o teste trava.

**O que ela precisaria para entrar depois**, escrito agora para a próxima sessão
não redescobrir: `attemptid` continua não cruzando a fronteira MCP; só tentativa
com `state == "finished"` lida na mesma invocação; `questions[].html` nunca
projetado; e a medição de bytes feita antes, porque é a resposta mais gorda das
quatro e ninguém mediu.

### R4. Duas leituras entram no bloqueio permanente

`mod_quiz_get_attempt_data` e `mod_quiz_get_attempt_summary` passam a estar no
`BLOQUEIO_PERMANENTE`. São as **primeiras funções de leitura da lista**, e isso é
mudança de caráter que merece ficar escrita: até hoje o §2.2 dizia "não escreve
em nome do aluno", e passa a dizer também "não lê o que não pode estar no
contexto de um modelo".

O motivo é o do catálogo, que já o registrou e nunca virou linha de código:
`get_attempt_data` devolve o enunciado das questões de uma tentativa **em
andamento**; não escreve nada, e ainda assim é a última coisa que se quer dentro
do contexto de um modelo durante uma prova **[catálogo §6.10]**.
`get_attempt_summary` é a mesma tentativa em curso, por questão, antes do envio.

Isto **não** é o único jeito de barrá-las — a allowlist já as nega por omissão,
que é a primeira linha. É a segunda linha, pelo motivo que o próprio arquivo dá:
o dia em que alguém acrescentar algo à allowlist por engano **[código,
`politica.py:9`]**. E é justamente esta família que torna esse dia plausível, por
causa de R5.

O número da lista sai de 40 e vai para 42 **se** esta trilha entrar sozinha. O
spec de entrega de hoje propõe 40 → 38 na mesma lista; as duas mudanças não se
tocam em nome nenhum, mas **qualquer teste que trave a contagem quebra na ordem
de merge**. Por isso Q2 afirma pertencimento, nunca cardinalidade.

### R5. O prefixo novo é teto, e o teto cobre coisa que recusamos

P5 exige que toda função da allowlist case com um prefixo de leitura conhecido
**[`tests/moodle/test_politica.py`]**. Entra `mod_quiz_get_`, e ele **não** casa
com as três de escrita bloqueadas (`start_attempt`, `save_attempt`,
`process_attempt`) nem com as quatro `mod_quiz_view_*`, que são escrita e
disparam evento no relatório do professor **[catálogo §3.8]**.

Ele casa, porém, com `mod_quiz_get_attempt_data`, `mod_quiz_get_attempt_summary`,
`mod_quiz_get_attempt_review` e `mod_quiz_get_user_quiz_attempts`. Isso é o
esperado e é o ponto: **prefixo nunca foi autorização** (T6 — glob não é
blindagem). A autorização é igualdade exata de nome; o prefixo é teto sobre o que
pode entrar sem passar pelo §9. Esta é a primeira vez em que o teto cobre uma
função que o projeto recusa por escrito, e é por isso que R4 existe: as duas
camadas passam a se apoiar em vez de se repetir.

**Achado colateral, que não vira trabalho aqui:** as quatro `mod_quiz_view_*` são
escrita, existem no site e o §2.2 não as nomeia **[catálogo §3.8]**. Não abro
linha nova no `BACKLOG-correcoes.md` porque o item **A2** do roadmap já registra a
revisão da lista inteira contra as 447, e duplicar registro é como uma dívida
some de vista.

## Decisão 4 — os dois números que podem discordar

`get_user_best_grade` devolve a **melhor** nota. O boletim pode contar outra:
`get_quizzes_by_courses` traz `grademethod`, e o Moodle tem quatro (maior nota,
média, primeira, última) **[catálogo §3.8]**. Se o método não for "maior nota", o
número desta ferramenta e o número que `notas PTC3314` mostra para o mesmo item
**são diferentes e os dois estão certos**.

Duas ferramentas do mesmo servidor dando números diferentes para "a nota do Teste
5", sem dizer por quê, é a pior saída possível — pior que não responder. Então:
o número sai sempre rotulado como *melhor tentativa*, e quando `grademethod` não
for "maior nota" a saída diz qual regra a disciplina usa e manda para `notas`
buscar a que conta.

## Medição pendente — pré-requisito, não acabamento

**Não há número de bytes neste spec, e é de propósito.** Este worktree não tem
token nem rede, e o projeto tem caso registrado do custo de inventar: a razão de
projeção de `notas` foi escrita contra um dicionário imaginado e **saiu errada
por mais do que o dobro** **[`tests/moodle/test_forma_real.py`, cabeçalho, 14/09]**.
A primeira linha de código desta trilha vem **depois** da captura.

O que a captura precisa responder:

1. **Quantos bytes cada uma das três custa, crua**, e qual a razão
   projetado/cru. Nada disso é estimável daqui.
2. **Se a conta de ALUNO recebe `grade`, `attempts`, `grademethod` e `timeclose`
   em `get_quizzes_by_courses`.** O Moodle reduz retorno por capacidade em várias
   funções, e a projeção desenhada acima lê os quatro **[inferência — é a hipótese
   a ser derrubada]**. Se `attempts` não vier, a razão de existir da ferramenta
   vai junto e o desenho muda; se `grade` não vier, some o "de 10,00" e a lacuna
   que `notas` declara continua aberta.
3. **O que `get_user_best_grade` devolve para questionário sem tentativa** —
   `hasgrade: false` ou erro. É o caso mais importante da fronteira: é nele que a
   resposta precisa ser terminal.
4. **O que `get_user_attempts` com `status=finished` devolve sem tentativa
   nenhuma** — lista vazia ou erro. Lista vazia não pode virar "você não tem
   questionário".
5. **Quantos questionários tem uma disciplina típica.** 13 em PTC3314
   **[fixture]**, uma amostra. O teto de 5 sai daí e deve ser reconferido.

Os comandos, e nenhum deles varre lista de funções (§3.1):

```bash
./scripts/userid.sh                       # id derivado do token, cacheado
./scripts/ws.sh core_enrol_get_users_courses "userid=<o de cima>"   # courseid da sigla

./scripts/capture.sh quizzes_ptc3314 \
    mod_quiz_get_quizzes_by_courses "courseids[0]=<courseid>"
./scripts/capture.sh quiz_attempts_t13 \
    mod_quiz_get_user_attempts "quizid=<id do quiz>" "userid=<...>" status=finished
./scripts/capture.sh quiz_best_grade_t13 \
    mod_quiz_get_user_best_grade "quizid=<id do quiz>" "userid=<...>"

python3 scripts/reduzir.py                # razão projetado/cru, com as linhas novas
python3 scripts/higienizar.py             # antes de versionar qualquer fixture (§3.3)
```

`capture.sh` imprime medida e nunca payload, que é o que permite medir uma
resposta sem ler uma resposta grande por acidente (item 8 do `CLAUDE.md`).

O resultado vai para `notas/`, com a origem rotulada na mesma linha, e a decisão
para o §9 — nunca só na janela da conversa.

## Bateria de testes

Camada `politica`, offline (nenhuma toca rede nem pede credencial):

- **Q1** as três de escrita da família quiz seguem recusadas, e recusadas também
  com `permitir_escrita=True`. É regressão do §2.2 numa trilha que mexe nas
  vizinhas: afrouxar aqui é o modo de falha desta mudança.
- **Q2** `mod_quiz_get_attempt_data` e `mod_quiz_get_attempt_summary` estão no
  `BLOQUEIO_PERMANENTE` e são recusadas. Pertencimento, **nunca** cardinalidade
  da lista (ver R4).
- **Q3** `ALLOWLIST` é exatamente o conjunto de 14 nomes. O T7 cresce, e é onde a
  decisão do §9 fica visível na próxima sessão.
- **Q4** as três novas casam com `mod_quiz_get_`; nenhuma das três de escrita nem
  das quatro `mod_quiz_view_*` casa; e `mod_quiz_get_attempt_data` casa e mesmo
  assim é negada. Este é o teste que afirma que teto não é autorização.
- **Q5** `mod_quiz_get_user_quiz_attempts` é negada por omissão, embora case com
  o prefixo e seja descrita igual à que entrou.
- **Q6** `ALLOWLIST` e `BLOQUEIO_PERMANENTE` seguem disjuntos, agora com a mesma
  família dos dois lados — que é a situação em que T10 deixa de ser trivial.
- **Q7** nenhum `inputSchema` das ferramentas do Moodle tem propriedade
  `attemptid`, `quizid`, `cmid` ou `id`. R1 travada por leitura do descritor, não
  por convenção.

Camada `contrato`, offline, com dublê e com a captura versionada:

- **Q8** `questionarios("PTC3314")` envia `courseids` explícito com um id — nunca
  lista vazia. Asserção sobre o parâmetro **enviado**.
- **Q9** toda chamada a `get_user_attempts` envia `status="finished"`, literal.
  Também sobre o parâmetro enviado.
- **Q10** nenhum `attemptid` presente na resposta do dublê aparece no texto de
  saída, em nenhum dos caminhos (com tentativa, sem tentativa, com teto batido).
- **Q11** disciplina com 13 questionários em aberto gasta no máximo 1 + 2×`TETO`
  chamadas, e a saída declara o corte com o nome do parâmetro que o evita.
- **Q12** zero tentativas finalizadas: a saída diz que a ferramenta não abre
  questionário e que nenhuma configuração a faz abrir, **e não nomeia nenhuma
  função do bloqueio permanente** — mesma regra do D5 do diagnóstico, pelo mesmo
  motivo (não dar ao modelo o vocabulário que a política existe para negar).
- **Q13** `grademethod` diferente de "maior nota": a saída rotula o número como
  melhor tentativa e manda para `notas <disciplina>` buscar a que conta.
- **Q14** questionário já fechado fora do recorte padrão: a saída diz **quantos**
  ficaram de fora e onde a nota deles está (Invariante 7).
- **Q15** forma real, contra a captura higienizada: todo campo que a projeção lê
  existe nas três respostas reais, e todo campo que o construtor do `conftest`
  produz existe nelas. Fixture ausente é **vermelho, não skip** — é a regra que
  F8/F9 já aplicam.
- **Q16** erro do cliente sobe sem ser capturado: credencial recusada não vira
  "você não fez nenhum questionário".
- **Q17** `ja_entreguei` e `atrasadas` continuam dizendo que não cobrem
  questionário, e agora dizem para onde ir. Os dois testes que hoje exigem a
  frase antiga mudam junto, no mesmo commit.

Camada `live`, atrás de `USP_MCP_LIVE=1`:

- **Q18** as três funções respondem para uma disciplina real, uma função por
  invocação, nome literal no fonte — P1-P3 seguem valendo, e P2 passa a proibir
  que `mod_quiz_get_attempt_data` seja **escrita** no fonte da camada live.
- **Q19** a contagem de tentativas ao vivo bate com o que a página do
  e-Disciplinas mostra para o mesmo questionário. Conferência humana, uma vez,
  registrada no §9 — é o único jeito de saber que `finished` conta o que se
  pensa que conta.

Handshake, offline:

- **Q20** `questionarios` aparece no `tools/list` com `readOnlyHint` verdadeiro,
  e a contagem de ferramentas do Moodle vai de 10 para 11.

## Critério de parada

As vinte passam; a suíte inteira fica verde (hoje `759 passed, 10 skipped`, sem
skip novo); `./scripts/gate.sh` passa 4/4; a medição dos cinco pontos está
escrita em `notas/` com a origem rotulada na mesma linha; e a decisão está no §9.

E uma condição que não é teste: **nenhuma linha de `usp_mcp/` aceita um
identificador de tentativa vindo de fora.** Se essa frase deixar de ser verdade,
a fronteira deste spec deixou de existir, mesmo com tudo verde.

## O que precisa ir para o §9

1. Que o D1 foi desenhado e que a premissa dele estava **parcialmente errada**: a
   nota do questionário já sai em `notas <disciplina>`, com 13 itens `quiz` na
   captura de 15/09. O que faltava era o orçamento de tentativa, não a nota.
2. Que a allowlist vai de 11 para 14, com as três de quiz e o prefixo
   `mod_quiz_get_` em P5 — e que esse prefixo cobre funções que o projeto recusa,
   o que é por onde a segunda camada passa a ser necessária.
3. Que o `BLOQUEIO_PERMANENTE` ganha **leitura** pela primeira vez, e por quê.
4. Que `mod_quiz_get_attempt_review` foi olhada e deixada de fora, com as três
   razões e com a condição de entrada — para a próxima sessão não reabrir a mesma
   pergunta por achar a função disponível.
5. Que os números de bytes **não existiam** quando este spec foi escrito, quais
   comandos os produzem, e que o desenho tem duas hipóteses (pontos 2 e 3 da
   medição) capazes de mudá-lo.
