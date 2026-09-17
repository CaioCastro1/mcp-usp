# Questionário como objeto: "já fiz?", "ainda dá?", "perdi algum?" — design

> 17/09/2026. Trilha de **leitura**. Nenhuma das três funções de tentativa que
> o §2.2 recusa (`mod_quiz_start_attempt`, `mod_quiz_save_attempt`,
> `mod_quiz_process_attempt`) sai do bloqueio permanente, muda de lugar ou é
> discutida aqui como candidata a sair. O que este spec faz é o contrário:
> ele fecha a fronteira em volta delas com regra verificável, e abre ao lado
> duas funções de leitura.
>
> O defeito veio de uso real. No Moodle, **atividade** (`mod_assign`) e
> **questionário** (`mod_quiz`) são objetos diferentes, e o projeto tratava só
> o primeiro. O dono perguntou sobre uma avaliação que é questionário e
> recebeu, de `ja_entreguei`, um "questionário não passa por aqui, use
> `o_que_vence`"; `o_que_vence` disse a data e mais nada. Metade dos
> vencimentos reais dele é questionário: 3 dos 4 itens de uma janela de 14 dias
> **[roadmap D1]**, e o calendário vê quiz em 6 disciplinas contra 4 com
> `assign` **[notas/fase1-moodle.md]**.
>
> O spec vizinho, `2026-09-15-notas-de-questionario-design.md`, está mergeado
> e **não implementado**. Ele desenhou a ferramenta `questionarios` para a
> pergunta do orçamento de tentativa, e deixou cinco medições pendentes, duas
> delas capazes de derrubar o desenho. Este spec implementa o miolo daquele,
> herda a fronteira dele por escrito, e **diverge em três pontos com razão
> escrita** (ver *Relação com o spec de 15/09*). E, como aquele, não tem número
> de bytes: este worktree não tem token nem rede, e inventar já custou caro
> (`tests/moodle/test_forma_real.py`, cabeçalho). A diferença é que aqui a
> primeira linha de código vem **antes** da captura, então o código tem de
> **degradar com honestidade** se o campo não vier — e isso vira teste, não
> promessa.

## O que está decidido hoje, e continua

`usp_mcp/moodle/politica.py` lista 40 nomes no `BLOQUEIO_PERMANENTE`
**[código]**; três são as escritas da família quiz, e `decidir` as recusa
antes de olhar a allowlist, inclusive com `permitir_escrita=True` e com
`confirmada=True` (T1, T2, T3b, E4). O spec de entrega de 15/09 tirou duas
funções de `mod_assign` dessa lista e **deixou as três de quiz**, com a razão
escrita em `politica.py`: para tentativa não existe rascunho, e abrir uma já é
irreversível. Este spec assume aquela decisão como dada e não a reabre.

O que existe hoje sobre questionário, ferramenta a ferramenta:

| ferramenta | o que diz sobre questionário | o que não diz |
|---|---|---|
| `o_que_vence` | que fecha, e quando **[código, `o_que_vence.py`]** | se já foi feito |
| `notas <disciplina>` | a nota de cada um, quando lançada: 13 itens `quiz` em PTC3314 **[fixture `grade_items_ptc3314.json`]** | `"-"` é a mesma string para "não fiz" e "fiz e está oculta" **[código, `notas.py`]**; 9 dos 13 itens da captura vêm com `gradeishidden: true` |
| `ja_entreguei` | **recusa por escrito** **[código, `COBERTURA`]**, com teste exigindo a frase (J16) | tudo |
| `atrasadas` | idem, pela mesma constante (AT14) | tudo |

## As perguntas que ficam sem resposta, e qual vale ferramenta

Quem tem um questionário na semana pergunta, nesta ordem de frequência:

1. **"Já fiz o Teste 12?"** — o `ja_entreguei` do questionário. Hoje recusada.
2. **"Ainda dá para fazer? Quantas tentativas sobram?"** — a pergunta do D1.
   Hoje sem resposta em lugar nenhum.
3. **"Perdi algum questionário? Fechou e eu não fiz?"** — o `atrasadas` do
   questionário. Hoje sem resposta: `notas` mostra `"-"`, que não distingue
   "não fiz" de "está oculta", e a captura de PTC3314 tem 9 itens ocultos.
4. **"Quanto tirei?"** — `notas` já responde, item a item. Não entra aqui.
5. **"O que eu errei?"** — recusada com dado em 15/09 (R3 do spec vizinho:
   é `mod_quiz_get_attempt_review`, exige `attemptid` e devolve enunciado).
   Não entra aqui, e a condição de entrada está escrita lá.

As perguntas 1, 2 e 3 são **a mesma consulta aos mesmos dados**: para cada
questionário, a lista de tentativas finalizadas do aluno. "Já fiz" é contagem
maior que zero; "quantas sobram" é o permitido menos essa contagem; "perdi" é
contagem zero num questionário que já fechou. Uma pergunta em três tempos
verbais, e o §5 pede que ela se resolva numa chamada de ferramenta do ponto de
vista do modelo. É **uma** ferramenta, e o objeto dela é o questionário com
quatro estados:

|  | aberto | fechado |
|---|---|---|
| **com tentativa finalizada** | FEITO, ainda dá para refazer se sobrar tentativa | FEITO |
| **sem tentativa finalizada** | ainda no prazo | **perdido** — a linha que ninguém dava |

O quadrante inferior direito é a razão de este spec não ser só a implementação
do vizinho: aquele recorta por padrão "só o que está aberto" e manda o fechado
para `notas`, e `notas` não sabe dizer "não fiz". Ver *Relação com o spec de
15/09*, ponto 2.

## Decisão 1 — uma ferramenta, `questionarios`, e o que ela NÃO absorve

**Uma ferramenta nova**, `questionarios`, com `disciplina` obrigatória e
`questionario` opcional (pedaço do nome). O nome, a assinatura e o motivo do
nome são os do spec vizinho, e valem: "questionário" é a palavra que
`o_que_vence` já imprime, e `ja_fiz` ficaria a uma palavra de `ja_entreguei`
na cabeça de quem gera a chamada.

**Por que não é `ja_entreguei` aprendendo a ver quiz**, embora seja exatamente
onde o dono bateu: `ja_entreguei` responde com um vocabulário de estados de
entrega (ENTREGUE, RASCUNHO NÃO ENVIADO, REABERTA) sobre `mod_assign_*`, e
nenhum desses estados existe para questionário — não há rascunho, há
orçamento de tentativa. Somar quiz lá dentro obrigaria a mesma resposta a
falar duas línguas, e dobraria a contagem de chamadas de uma ferramenta que já
tem teto de 10. O precedente é `atrasadas`: outra pergunta, ferramenta própria,
mesmo que sobre objetos vizinhos. A cura para o que aconteceu com o dono não é
`ja_entreguei` responder — é (a) a recusa dela **apontar para uma ferramenta
que responde**, e (b) a recusa aparecer **também no ramo em que ele caiu**,
que hoje não a imprime (ver Decisão 5).

**Por que `atrasadas` não ganha uma seção de questionário nesta trilha.**
"Perdi algum prazo?" sem disciplina é a pergunta em que quiz mais falta, e
mesmo assim fica de fora, por custo: saber se um questionário fechado foi feito
custa **uma chamada por questionário**, e questionário fechado acumula o
semestre inteiro — PTC3314 tem 13 **[fixture]**, e o calendário vê quiz em 6
disciplinas. Dez disciplinas em andamento com esse perfil dão dezenas de
chamadas para uma resposta que o teto cortaria em 10 e diria "conferi 10 de
60", que é pior do que apontar para a ferramenta por disciplina. O caminho
barato existe **como hipótese**, e está escrito na *Medição pendente* (ponto
4): se o sinal do boletim se confirmar, `atrasadas` ganha quiz a uma chamada
por disciplina, sem função nova. Até lá, ela diz por escrito que não cobre e
diz para onde ir.

## Decisão 2 — duas funções, e não três

Entram na `ALLOWLIST` **duas** funções, que vai de 11 para 13 **[código]**:

| função | o que ela dá que ninguém mais dá | risco no catálogo |
|---|---|---|
| `mod_quiz_get_quizzes_by_courses` | o questionário existe, o nome, quando abre e fecha, quantas tentativas permite (`0` = ilimitadas), e o `quizid` | livre **[catálogo §3.8]** |
| `mod_quiz_get_user_attempts` | quantas tentativas eu **finalizei**, e quando | cuidado **[catálogo §3.8]** |

**`mod_quiz_get_user_best_grade` fica de fora**, e essa é a primeira
divergência do spec vizinho. A razão de lá para incluí-la era boa — derivar a
nota de `sumgrades` seria inferência apresentada como dado — e a conclusão
aqui é outra: **não derivar e não mostrar**. A nota do questionário já sai em
`notas <disciplina>`, item a item, na escala do boletim, e é a captura real
de 15/09 que diz isso (13 itens `quiz`). Uma segunda ferramenta dando "a nota
do Teste 5" por outro caminho é o problema que a Decisão 4 do spec vizinho
precisou resolver (dois números certos e diferentes quando `grademethod` não
é "maior nota"). Sem a função, o problema não existe: um número, um lugar.
Custa também uma chamada a menos por questionário, e retira do desenho a
hipótese sobre `grade` na resposta para conta de aluno — o que sobra de
hipótese está na *Medição pendente*, e é menos.

A gêmea `mod_quiz_get_user_quiz_attempts` não entra (descrição idêntica no
site; uma pergunta, uma função escolhida à mão), e
`mod_quiz_get_attempt_review` não entra (R3 herdada).

**Custo em chamadas, e o teto.** `get_quizzes_by_courses` é uma por
disciplina; `get_user_attempts` é uma por questionário consultado. O teto é
`TETO_CONSULTAS` de `ja_entreguei`, **importado e não recopiado** (o
precedente é `atrasadas`): é a mesma natureza de custo — latência e log da
conta, não contexto — e o mesmo número, 10. Sem `questionario`, o pior caso
é **1 + 10 = 11 chamadas**; com `questionario` dito, **2**. Quem é consultado
sob o teto segue uma ordem que é decisão: **abertos primeiro**, do que fecha
antes para o que fecha depois, porque é onde ainda dá para agir; depois os
**fechados, do mais recente para o mais antigo**, porque "perdi o de semana
passada" é pergunta e "perdi o de março" não é. Questionário que **ainda não
abriu** não gasta chamada — não pode ter tentativa —, como `nosubmissions`
não gasta em `ja_entreguei`.

**Não consultar não é sumir.** A existência, o nome e o prazo de **todos** os
questionários saem da primeira chamada, que já foi paga. Os que ficarem fora
do teto aparecem na lista com "não consultado" no lugar do estado, e o aviso
diz quantos e qual parâmetro evita o corte. É o corte de detalhe e não de
existência que `disciplinas` já pratica.

**Parâmetros enviados, e nenhum deles é default.** `courseids[0]` explícito
(sem ele a função devolve todos os cursos **[catálogo §3.8]**, e ninguém
verificou o que "todos" custa em 74 matrículas). `userid` derivado do token
por `disciplinas.userid_do_token`, cache quente, zero chamada nova.
`status="finished"`, literal (R2 herdada). `includepreviews=0`, literal: o
default documentado é falso e é o que se quer, e este projeto não confia em
default não verificado — mandar custa nada e a asserção é sobre o parâmetro
enviado.

### O que muda em `FUNCOES_POR_FERRAMENTA`

`diagnostico.py` ganha **uma linha** e as dez existentes não mudam:

```python
    "questionarios": (
        "core_webservice_get_site_info",
        "core_enrol_get_users_courses",
        "mod_quiz_get_quizzes_by_courses",
        "mod_quiz_get_user_attempts",
    ),
```

As duas de quiz **juntas**, como `avisos` exige as duas de fórum:
`get_user_attempts` pede um `quizid`, e o único lugar de onde ele sai é
`get_quizzes_by_courses`. D4 exige que a união da tabela seja **igual** à
allowlist, então os dois nomes só entram na allowlist se esta linha entrar, e
vice-versa; é o drift que D4 existe para impedir. D1 itera a tabela e cobra
`OK` no site completo: a linha entra no laço sozinha. D2 não muda: a lista de
reprovadas dele é sobre `mod_assign_get_assignments`, de que `questionarios`
não depende.

## Decisão 3 — a fronteira, herdada e verificável

O spec vizinho resolveu a fronteira com uma regra: **nenhum identificador de
tentativa entra ou sai do projeto**. Ela é herdada aqui na íntegra, e a razão
de herdar em vez de reescrever é que a regra é operacional e não estética. O
caminho natural para descobrir um `attemptid` é chamar a função que fabrica
um, e essa função é a primeira das três bloqueadas. Enquanto nenhum
`attemptid` cruzar a fronteira MCP, não existe pergunta cujo próximo passo
útil seja "me arruma um attemptid" — e é só essa pergunta que encosta no
bloqueio. Uma fronteira que depende de o modelo não querer é frágil; uma que
depende de o identificador não existir no vocabulário da ferramenta é
verificável por leitura do descritor e da saída.

### R1. Nenhum identificador de tentativa entra ou sai

Nenhuma ferramenta do Moodle aceita `attemptid`, `quizid`, `cmid` ou `id`
como propriedade do `inputSchema` — com e sem `USP_MCP_ENTREGA`. O `quizid`
nasce dentro da invocação, em `get_quizzes_by_courses`, viaja para
`get_user_attempts` e morre ali: não aparece na saída, não volta em parâmetro.
O `attemptid` chega dentro da resposta de `get_user_attempts` e **não é
projetado**: a projeção lê `state` e `timefinish`, e nada mais. `sumgrades`
também não é lido — é a nota bruta, e nota é assunto de `notas`.

### R2. `status` é literalmente `"finished"`, e a projeção conta só `finished`

`unfinished` e `all` devolvem tentativa em andamento, e "você tem uma
tentativa aberta agora" é a deixa para "então termina para mim", com as duas
funções que terminariam a um nome de distância. O parâmetro é literal e
asserido no que foi **enviado**. E a projeção **conta só itens com
`state == "finished"`** mesmo assim: um site que ignore o parâmetro não pode
fazer esta ferramenta contar uma tentativa em curso como feita. O preço vai
na saída: a contagem ignora a tentativa que estiver em curso, e o aviso diz.

### R3. `mod_quiz_get_attempt_review` fica fora

Herdada com as três razões do spec vizinho (a pergunta dela já foi recusada
com dado; o que ela devolve é enunciado renderizado; é a única das leituras
úteis que exige `attemptid`). A condição de entrada também está lá escrita, e
não se repete aqui.

### R4. Duas leituras entram no bloqueio permanente

`mod_quiz_get_attempt_data` e `mod_quiz_get_attempt_summary` entram no
`BLOQUEIO_PERMANENTE`, que vai de 40 para 42. São as **primeiras funções de
leitura** da lista, e a mudança de caráter fica escrita ao lado delas: o §2.2
dizia "não escreve em nome do aluno" e passa a dizer também "não lê o que não
pode estar no contexto de um modelo". O catálogo já as classificou —
`get_attempt_data` devolve o enunciado das questões de uma tentativa **em
andamento**, e `get_attempt_summary` é a mesma tentativa, por questão, antes
do envio **[catálogo §3.8, §6.10]**. A allowlist já as nega por omissão; esta é
a segunda linha, para o dia em que alguém acrescentar algo à allowlist por
engano — e R5 é o que torna esse dia plausível.

Nenhum teste trava a **cardinalidade** da lista, só pertencimento: o spec de
entrega propõe 40 → 38 e este 40 → 42 sobre nomes distintos, e a contagem
depende da ordem de merge.

### R5. O prefixo novo é teto, e o teto cobre coisa que recusamos

P5 ganha `mod_quiz_get_`. Ele não casa com as três de escrita nem com as
quatro `mod_quiz_view_*` (escrita: disparam evento no relatório do professor
**[catálogo §3.8]**). Casa com `get_attempt_data`, `get_attempt_summary`,
`get_attempt_review`, `get_user_best_grade` e `get_user_quiz_attempts` — todas
recusadas por omissão, duas delas agora recusadas duas vezes. É a primeira vez
que o teto de P5 cobre função que o projeto recusa por escrito, e é por isso
que R4 existe: prefixo nunca foi autorização (T6), a autorização é igualdade
exata de nome, e as duas camadas passam a se apoiar.

### R6. O módulo que toca a família não tem os nomes de escrita ao alcance

Regra nova, e verificável como P2 é para a camada live: **o fonte de
`usp_mcp/moodle/questionarios.py` não contém, em lugar nenhum — nem em
docstring —, nenhum nome do `BLOQUEIO_PERMANENTE` nem do
`ESCRITA_CONFIRMADA`.** É o módulo que abre a família `mod_quiz_` para
leitura, e um nome de escrita escrito nele está a uma linha de ser chamado. A
fronteira do spec vizinho era sobre identificadores; esta é sobre vocabulário,
e as duas se completam.

## Decisão 4 — degradar com honestidade quando o campo não vier

Esta é a metade da trilha que o spec vizinho não podia fazer e esta faz: o
código nasce antes da captura, então **cada campo cuja presença é hipótese tem
um comportamento declarado para a ausência**, e esse comportamento é testado
com dublê que omite a chave. A lição é a de `notas.py` com `grademax`: `.get`
de chave ausente devolve `None`, o renderizador degrada sozinho e a saída
nunca mente — e é exatamente por isso que ninguém vê. Aqui a ausência **fala**.

| campo | de onde | se vier | se **não** vier (hipótese) |
|---|---|---|---|
| `attempts` | `get_quizzes_by_courses` | `0` → "tentativas ilimitadas"; `n` → "k de n usadas" | a linha não fala de orçamento, e **um aviso** diz que o e-Disciplinas não informou quantas tentativas cada questionário permite para esta conta — "já fiz" continua respondido |
| `timeclose` | idem | `0` → "sem fechamento"; epoch → o estado aberto/fechado | a linha sai com "prazo não informado" e um aviso conta quantos ficaram sem estado |
| `timeopen` | idem | epoch no futuro → "AINDA NÃO ABRIU", sem gastar chamada | tratado como já aberto (o pior caso é uma chamada a mais, nunca uma afirmação a mais) |
| `attempts[]` vazio | `get_user_attempts` | "sem tentativa finalizada" **deste** questionário | — a existência do questionário veio da outra chamada, então lista vazia aqui nunca vira "você não tem questionário" |
| erro do cliente | qualquer | — | sobe; credencial recusada não vira "não fez nenhum" |

O que a projeção **lê** é um conjunto declarado no módulo
(`CAMPOS_LIDOS_DO_QUESTIONARIO`, `CAMPOS_LIDOS_DA_TENTATIVA`), e há teste que
lê o fonte por AST e exige que os `.get` sejam **exatamente** esse conjunto —
nem uma chave a mais que não passou por esta tabela, nem uma declarada que o
código não lê. No dia da captura, o mesmo teste confronta o conjunto com a
resposta real e vira o F8 desta família.

## Decisão 5 — o que muda em `ja_entreguei` e `atrasadas`

**A recusa continua fazendo sentido, e continua escrita.** Objeto diferente,
funções diferentes, vocabulário de estado diferente, e um teto de chamadas
que não comporta os dois. O que muda é o **destino** da recusa e **onde** ela
aparece:

1. `COBERTURA` deixa de mandar para `o_que_vence` (que só sabe a data) e passa
   a mandar para `questionarios` (que sabe se foi feito, se ainda dá e quantas
   tentativas). `o_que_vence` continua citada para "o que tem prazo". A
   constante é uma e importada por `atrasadas`, então as duas mudam juntas.
2. **O ramo em que o dono caiu passa a imprimir a cobertura.** Hoje
   `ja_entreguei("PTC3314", entrega="Teste 12")` responde "Nenhuma entrega com
   'Teste 12' no nome. A disciplina tem 4 entregas: …" e **para aí** — o ramo
   `busca_sem_resultado` não anexa `COBERTURA`. É o ramo exato de quem pergunta
   por um questionário pelo nome, e ele saía mudo sobre questionário. Passa a
   dizer que, se o nome for de questionário, a resposta está em
   `questionarios`.
3. As descrições no `tools/list` de `ja_entreguei`, `atrasadas` e `o_que_vence`
   apontam para `questionarios`, para que o modelo vá direto na primeira vez —
   que é o que faz a pergunta se resolver em uma chamada do ponto de vista dele.
4. J16 e AT14 continuam exigindo a palavra "questionário" e passam a exigir o
   destino: `questionarios`. Um teste novo cobre o ramo do item 2.

## Forma da resposta

```
PTC3314 (PTC3314-2026) — questionários (13)

sex 18/09 23:59  Teste semanal - 12 - reflexões em vários dielétricos: SEM TENTATIVA FINALIZADA — ainda no prazo; 3 tentativas disponíveis
sex 25/09 23:59  Teste semanal - 13 - incidência oblíqua: SEM TENTATIVA FINALIZADA — ainda no prazo; 3 tentativas disponíveis
qui 10/09 23:59  Teste semanal - 11 - propagação de ondas em condutores: FEITO — 1 tentativa finalizada, a última em qua 09/09 21:04; 1 de 3 tentativas usadas (fechado)
qui 03/09 23:59  Teste semanal - 10 - polarização de ondas: SEM TENTATIVA FINALIZADA — PRAZO VENCIDO
…
qui 06/08 23:59  Teste semanal - 1 - parâmetros de LT e propagação: não consultado
abre seg 21/09 00:00  Teste semanal - 14: AINDA NÃO ABRIU

⚠ Esta consulta custa uma ida ao e-Disciplinas por questionário, e para em 10: 3 questionário(s) fechados há mais tempo aparecem acima sem estado. Use o parâmetro `questionario` para perguntar por um deles pelo nome.
⚠ Tentativa EM ANDAMENTO não conta: só a finalizada conta como feita. Se você tem uma aberta agora, ela não aparece aqui e o número de tentativas usadas está uma abaixo.
⚠ Esta ferramenta só lê. Ela não abre, não responde e não finaliza questionário, e não há configuração que a faça fazer isso — para responder, use a página do e-Disciplinas.
⚠ Esta resposta cobre só QUESTIONÁRIO. Tarefa de entrega é `ja_entreguei`; a nota de cada questionário, quando lançada, sai em `notas`.
```

A grafia da data é `texto.formatar_data`, a mesma de `o_que_vence` e
`ja_entreguei` (J18): quem lê as três respostas na mesma noite reconhece o
mesmo prazo. O rótulo é `FEITO` / `SEM TENTATIVA FINALIZADA`, e não
`NÃO FEITO`: a lição de `atrasadas` é que a frase é sobre o que o sistema
registra, e a tentativa em curso (R2) é o caso em que "não fez" seria falso.

## Relação com o spec de 15/09

Herdado na íntegra: nome e assinatura da ferramenta; R1, R2, R3, R4, R5;
`courseids` explícito; `userid` derivado; o não-uso de `get_user_quiz_attempts`.

Divergências, com a razão:

1. **Duas funções e não três.** `get_user_best_grade` fica de fora porque a
   nota já sai em `notas` e um segundo número por outro caminho é o problema,
   não a solução (Decisão 2). Some junto a Decisão 4 daquele spec.
2. **O recorte padrão inclui os fechados.** Lá, o padrão era "só aberto" e o
   fechado ia para `notas`; mas `notas` não distingue "não fiz" de "oculta"
   (o próprio spec diz isso no ponto 2 de "o que `notas` não responde"), e a
   captura tem 9 de 13 itens ocultos. O quadrante fechado × sem tentativa é a
   pergunta 3, e só esta ferramenta pode respondê-la. O teto ordena abertos
   primeiro, então o custo do caso principal não muda.
3. **Q15 não pode ser "fixture ausente é vermelho" nesta trilha**, porque a
   captura não existe e este worktree não pode fazê-la. O teste de forma real
   existe, e **declara a pendência** com o comando exato quando a fixture não
   está lá; no dia em que ela chegar, ele passa a conferir. É a única
   exceção do projeto à regra "skip é verde que não testou nada", e ela está
   escrita como exceção, com prazo: fecha quando a captura entrar.

## Medição pendente — o que só o dono, com token, fecha

Nada abaixo foi medido. Os comandos não varrem lista de funções (§3.1) e
`capture.sh` imprime medida, nunca payload.

```bash
./scripts/userid.sh
./scripts/ws.sh core_enrol_get_users_courses "userid=<o de cima>"      # courseid de PTC3314

./scripts/capture.sh quizzes_ptc3314 \
    mod_quiz_get_quizzes_by_courses "courseids[0]=<courseid>"
./scripts/capture.sh quiz_attempts_t12 \
    mod_quiz_get_user_attempts "quizid=<id de um quiz>" "userid=<...>" status=finished includepreviews=0

python3 scripts/higienizar.py   # antes de versionar (§3.3): a resposta traz userid
python3 scripts/reduzir.py      # razão projetado/cru, com as duas linhas novas
```

1. **A conta de ALUNO recebe `attempts`, `timeopen` e `timeclose` em
   `get_quizzes_by_courses`?** É a hipótese principal do spec vizinho, e a
   deste. O Moodle reduz retorno por capacidade em várias funções. O código
   degrada como a Decisão 4 descreve; a captura decide se a degradação é o
   caminho normal ou a exceção. Se `attempts` não vier, a pergunta 2 fica sem
   resposta **e a ferramenta diz isso**, mas as perguntas 1 e 3 continuam
   respondidas — o desenho sobrevive, menor.
2. **O que `get_user_attempts` com `status=finished` devolve sem tentativa
   nenhuma** — `{attempts: [], warnings: []}` ou erro. O código trata lista
   vazia como "sem tentativa finalizada deste questionário"; se o site
   responder com erro, ele sobe como está, e a captura diz se há um
   `errorcode` a traduzir.
3. **Quantos bytes cada uma custa, crua, e a razão projetado/cru.** `intro`
   (HTML) é o campo gordo da primeira, e é descartado.
4. **Se `gradedatesubmitted` no boletim marca tentativa finalizada.** Na
   captura real de `grade_items_ptc3314.json`, os 3 itens `quiz` com nota
   trazem `gradedatesubmitted` preenchido e os 10 sem nota trazem `null` — o
   padrão bate com a hipótese, mas 9 desses 10 estão com `gradeishidden: true`
   e não se sabe se o dono os fez. Se o campo vier preenchido para item
   oculto com tentativa, `atrasadas` ganha questionário **a uma chamada por
   disciplina, sem função nova**, e a Decisão 1 é revista. Medir: um
   questionário feito com nota ainda oculta, e ler `gradedatesubmitted` dele
   no boletim. **[inferência do fonte do Moodle, não medida]**
5. **Se `o_que_vence` já omite questionário com tentativa finalizada.** O
   calendário de ações do Moodle esconde, no fonte, eventos cuja ação o módulo
   declara vazia, e o módulo de quiz declara vazia quando há tentativa
   finalizada **[inferência do fonte, não medida]**. Se for assim,
   `o_que_vence` já está respondendo metade da pergunta 1 **em silêncio**, o
   que é o Invariante 7 quebrado numa ferramenta que existe desde 28/08 — e a
   cura seria uma linha de cobertura, não código. Medir: comparar
   `o_que_vence` com `questionarios` na mesma semana.
6. **Quantos questionários tem uma disciplina típica.** 13 em PTC3314, uma
   amostra. O teto de 10 sai daí e deve ser reconferido.

O resultado vai para `notas/` com a origem rotulada na mesma linha, e a
decisão para o §9 — nunca só na janela da conversa.

## Bateria de testes

Camada `politica`, offline (`tests/moodle/test_politica_questionario.py`, e
duas mudanças em `test_politica.py`):

- **QO1** as três de escrita da família quiz seguem recusadas, com
  `permitir_escrita=True`, com `confirmada=True` e com as duas. Regressão do
  §2.2 numa trilha que mexe nas vizinhas.
- **QO2** `mod_quiz_get_attempt_data` e `mod_quiz_get_attempt_summary` estão no
  `BLOQUEIO_PERMANENTE` e são recusadas; nenhum nome `mod_quiz_` está nas duas
  listas ao mesmo tempo. Pertencimento, nunca cardinalidade.
- **QO3** as duas novas estão na `ALLOWLIST` e são permitidas;
  `get_user_best_grade`, `get_user_quiz_attempts` e `get_attempt_review` são
  recusadas por omissão, com o motivo da omissão e não do bloqueio.
- **QO4** as duas novas casam com `mod_quiz_get_`; nenhuma das três de
  escrita nem das quatro `mod_quiz_view_*` casa; `get_attempt_data` casa e é
  recusada mesmo assim — teto não é autorização.
- **QO5** com `get_attempt_data` posta na `ALLOWLIST` por monkeypatch, ela
  segue recusada e o motivo cita o bloqueio permanente (a segunda camada
  exercitada de verdade, como T3b).
- **QO6** nenhum `inputSchema` das ferramentas do Moodle tem propriedade
  `attemptid`, `quizid`, `cmid` ou `id` — com `USP_MCP_ENTREGA` ligada e
  desligada. R1 por leitura do descritor.
- **QO7** o fonte de `questionarios.py` não contém nenhum nome do
  `BLOQUEIO_PERMANENTE` nem do `ESCRITA_CONFIRMADA`, nem em docstring (R6).
- **T7** a `ALLOWLIST` é exatamente o conjunto de 13 nomes; **P5** ganha
  `mod_quiz_get_` com o motivo ao lado.

Camada `contrato`, offline (`tests/moodle/test_questionarios.py`, com os
construtores novos do `conftest`, rotulados **escrita à mão** como os de
fórum):

- **QO8** `questionarios("PTC3314")` envia `courseids[0]` explícito com o id
  da disciplina, uma vez só; nunca lista vazia.
- **QO9** toda chamada a `get_user_attempts` envia `status="finished"` e
  `includepreviews=0` literais, `userid` igual ao derivado do token, e
  `quizid` igual ao que veio da primeira resposta. Sobre o parâmetro enviado.
- **QO10** sigla que não resolve levanta erro legível sem gastar nenhuma
  chamada de quiz.
- **QO11** os quatro estados saem certos e com a grafia de data de J18:
  aberto sem tentativa ("ainda no prazo"), aberto com tentativa (FEITO),
  fechado com tentativa (FEITO, "fechado"), fechado sem tentativa (PRAZO
  VENCIDO).
- **QO12** `attempts` **ausente** na resposta: nenhuma linha fala de
  orçamento, o aviso diz que o site não informou, e FEITO/SEM TENTATIVA
  continuam saindo. A hipótese principal, derrubada no dublê.
- **QO13** `attempts == 0` sai como ilimitadas; `attempts == 3` com uma
  finalizada sai como "1 de 3".
- **QO14** `timeclose` **ausente** sai como "prazo não informado" com aviso;
  `timeclose == 0` sai como "sem fechamento"; nenhum dos dois vira 01/01/1970.
- **QO15** questionário que ainda não abriu não gasta chamada e sai rotulado.
- **QO16** 13 questionários gastam no máximo 1 + `TETO_CONSULTAS` chamadas;
  os abertos são consultados antes dos fechados e os fechados do mais recente
  para o mais antigo; os não consultados **aparecem** na lista com nome e
  prazo; o aviso declara o corte com o nome do parâmetro que o evita.
- **QO17** `questionario` que casa consulta só os que casam; que não casa não
  gasta chamada, lista os nomes existentes e diz que tarefa é `ja_entreguei`.
- **QO18** disciplina sem questionário: `vazio_por` rotulado, texto diz que
  não há, e a cobertura aponta para `ja_entreguei`.
- **QO19** nenhum `attemptid`, `quizid` nem `sumgrades` presente na resposta
  do dublê aparece no texto, em nenhum caminho (com tentativa, sem, com teto).
- **QO20** a saída diz que a ferramenta não abre nem finaliza questionário e
  que nenhuma configuração a faz, e **não nomeia nenhuma função do bloqueio
  permanente** — mesma regra de D5.
- **QO21** tentativa com `state == "inprogress"` na resposta **não** é
  contada, e o aviso de tentativa em andamento está presente (R2 do lado da
  projeção).
- **QO22** `warnings` das duas chamadas viram avisos com contagem, separados
  (o da lista e o do estado), como J21-J23.
- **QO23** erro do cliente sobe sem ser capturado — credencial recusada não
  vira "você não fez nenhum".
- **QO24** as chaves que a projeção lê, por AST, são **exatamente**
  `CAMPOS_LIDOS_DO_QUESTIONARIO` e `CAMPOS_LIDOS_DA_TENTATIVA`. Sempre roda.
- **QO25** forma real: se `fixtures/moodle/quizzes_ptc3314.json` e
  `quiz_attempts_t12.json` existem, todo campo que os construtores montam
  existe nelas e toda chave lida existe nelas (F1-F6 e F8 desta família); se
  não existem, **skip com o comando de captura na razão** — a exceção
  declarada do ponto 3 da *Relação*.
- **QO26** `ja_entreguei` sem entrega, e `ja_entreguei` com `entrega` que não
  casa, dizem "questionário" e dizem `questionarios`; `atrasadas` sem atraso
  idem. J16 e AT14 mudam junto, no mesmo commit.
- **QO27** o descritor de `questionarios` está no `tools/list` com
  `SO_LEITURA`, propriedades exatamente `{disciplina, questionario}`,
  `required == ["disciplina"]`, descrição sem nome de função do Moodle; e
  `chamar_ferramenta` roteia com cliente injetado.

Camada `handshake`, offline:

- **E14/E14b** a contagem no fio vai de 10 para **11** sem a flag e de 12
  para **13** com ela; A1-A8 descobrem a ferramenta nova sozinhos e cobram a
  anotação.

Camada `live`, atrás de `USP_MCP_LIVE=1`:

- **QO28** `mod_quiz_get_quizzes_by_courses` responde para PTC3314 com
  `courseids[0]` explícito, nome literal no fonte, e — se houver questionário
  — as chaves de `CAMPOS_LIDOS_DO_QUESTIONARIO` existem no primeiro item. É o
  ponto 1 da medição pendente virado canário: o dia em que rodar verde é o dia
  em que a hipótese principal deixa de ser hipótese. P1-P3 seguem valendo, e
  P2 proíbe que qualquer nome do bloqueio apareça neste fonte.
- **QO29** (conferência humana, uma vez, registrada no §9) a contagem de
  tentativas finalizadas ao vivo bate com a página do e-Disciplinas para o
  mesmo questionário. Sem isso não se sabe que `finished` conta o que se pensa.

## Critério de parada

Nenhum vermelho novo na suíte (a baseline traz um, `T58`, anterior a esta
trilha e em outra frente); `./scripts/gate.sh` sem regressão; um skip novo e
declarado (QO25, com o comando na razão), mais o live de sempre. E a condição
que não é teste: **nenhuma linha de `usp_mcp/` aceita identificador de
tentativa vindo de fora, e nenhuma linha de `questionarios.py` contém nome de
função de escrita.** Se uma das duas frases deixar de ser verdade, a fronteira
deste spec deixou de existir, mesmo com tudo verde.

## O que precisa ir para o §9

Este spec não edita o `SPEC1.md`; quem mergear registra:

1. Que a allowlist vai de 11 para 13 com **duas** funções de quiz, e por que
   `get_user_best_grade` ficou de fora (um número, um lugar).
2. Que o `BLOQUEIO_PERMANENTE` ganha **leitura** pela primeira vez, e o que
   isso muda no caráter do §2.2.
3. Que `mod_quiz_get_` entrou em P5 e cobre cinco funções recusadas — por onde
   a segunda camada passa a ser necessária.
4. Que `ja_entreguei` e `atrasadas` continuam recusando questionário, que o
   destino da recusa mudou, e que o ramo `busca_sem_resultado` recusava em
   silêncio até 17/09.
5. Que os números de bytes **não existiam** quando este spec foi escrito, que
   o código degrada declaradamente para `attempts` e `timeclose` ausentes, e
   que os seis pontos da medição pendente — em especial o 4 e o 5, que podem
   mudar `atrasadas` e `o_que_vence` — estão abertos.
