# Abrir tentativa de questionário atrás de duas variáveis: ilimitadas e limitadas. Design

> 18/09/2026. Este spec **reabre o §2.2 pela terceira vez**. A primeira foi a
> entrega de atividade (15/09, aceita em parte); a segunda foi mensagem pelo
> Moodle (17/09, recusada). Agora é a tentativa de questionário, e a decisão
> de partida já foi tomada pelo dono e não se rediscute aqui: **duas
> variáveis de ambiente**, uma para questionário com **tentativas
> ilimitadas** e outra para questionário com **tentativas limitadas**, as
> duas desligadas por padrão, como a de entrega. O trabalho deste documento é
> desenhar isso de um jeito que caiba no que o projeto já tem, dizer o que
> cada variável destrava, dizer onde o desenho depende de um dado que ninguém
> mediu, e entregar ao dono, bem postas, as quatro decisões que ele pediu para
> não serem tomadas sem ele.
>
> **Zero linhas de código nesta trilha.** Nenhuma chamada ao e-Disciplinas
> foi feita para escrever isto (Regra de Ouro, §3.1). Tudo abaixo saiu do
> código do repositório, do `SPEC1.md`, de `notas/moodle-catalogo.md`, dos
> dois specs vizinhos e da leitura do fonte do Moodle, com a origem rotulada
> na linha. O que está rotulado **[inferência do fonte do Moodle, não
> medida]** é hipótese até a captura dizer o contrário.
>
> Este spec não contém travessão. O README também não, e o texto proposto
> para ele no fim segue a mesma regra.

## O que está decidido hoje, conferido no código

`usp_mcp/moodle/politica.py` tem três conjuntos **[código]**:

| conjunto | tamanho | o que é |
|---|---:|---|
| `ALLOWLIST` | 13 | superfície de leitura; igualdade exata de nome, sem outra condição |
| `BLOQUEIO_PERMANENTE` | 40 | negado antes de qualquer outra checagem; nenhuma flag libera |
| `ESCRITA_CONFIRMADA` | 2 | as duas de `mod_assign` que saíram do bloqueio em 15/09; exigem `USP_MCP_ENTREGA=1` **e** confirmação declarada por chamada |

Cinco nomes da família `mod_quiz` estão no bloqueio permanente, e são o
assunto:

| função | desde | razão escrita | o que faz na API **[catálogo §3.8]** |
|---|---|---|---|
| `mod_quiz_start_attempt` | 31/08 | "queima tentativa de prova real" | abre tentativa; `quizid`, `preflightdata`, `forcenew` |
| `mod_quiz_save_attempt` | 31/08 | idem | grava respostas na tentativa aberta; `attemptid`, `data[]` |
| `mod_quiz_process_attempt` | 31/08 | idem; é o `finish` deste Moodle | grava e, com `finishattempt=true`, **finaliza**; `attemptid`, `data[]`, `finishattempt`, `timeup` |
| `mod_quiz_get_attempt_data` | 17/09 | "não lê o que não pode estar no contexto de um modelo" | enunciado das questões de uma tentativa **em andamento**; `attemptid`, `page` |
| `mod_quiz_get_attempt_summary` | 17/09 | idem | a mesma tentativa, por questão, antes do envio; `attemptid` |

Duas leituras da família estão na `ALLOWLIST` desde 17/09, chamadas pela
ferramenta `questionarios`: `mod_quiz_get_quizzes_by_courses` e
`mod_quiz_get_user_attempts`. O spec daquela trilha herdou e travou por teste
três regras que este documento precisa respeitar ou reabrir com razão escrita:
R1 (nenhum identificador de tentativa entra por parâmetro nem sai na
resposta, QO6 e QO19), R2 (`status` vai literal como `finished`, QO9 e QO21) e
R6 (o fonte de `questionarios.py` não contém nome de escrita da família, QO7).

E o texto que o servidor diz hoje sobre isso, em quatro lugares, é que **não
há flag que libere questionário**: `.env.example` ("As três de questionário
seguem no bloqueio permanente, e não há flag que as libere"), `CLAUDE.md` item
3 ("A exceção, e é uma só"), a docstring de `politica.py` e o aviso fixo de
`questionarios.py` ("não há configuração que a faça fazer isso", travado por
QO20). Este spec torna as quatro frases falsas, e a seção *Onde a informação
vive* lista o que muda em cada uma.

## A correção ao spec de 15/09

O spec `2026-09-15-entrega-com-confirmacao-design.md` justificou deixar as
três de questionário no bloqueio assim:

> para tentativa de questionário não existe rascunho, `start_attempt` já é
> irreversível, e o plano honesto seria "vou abrir uma tentativa e não sei
> dizer o que acontece depois".

**Isso está errado, e foi escrito por quem escreve este spec.** A API sabe
dizer o que acontece depois. `mod_quiz_get_quizzes_by_courses` traz o total de
tentativas permitidas (`attempts`, com `0` para ilimitadas) e o tempo limite
(`timelimit`, em segundos, `0` para sem limite) **[catálogo §3.8; campos do
fonte do Moodle]**. `mod_quiz_get_user_attempts` traz quantas já foram usadas
**[código, `questionarios.py`]**. Um plano fiel é construível:

> Vou abrir a tentativa 1 de 1 de "Exercícios 6", em PTC3360. Depois de
> aberta, não dá para desfazer. O relógio de N minutos começa. Restarão 0
> tentativas.

O que continua verdade é outra coisa, e é de **custo**, não de capacidade: com
tentativas ilimitadas o engano custa zero; com limitadas, um clique errado
queima uma chance que não volta. É essa diferença de custo, e não uma
suposta cegueira da API, que justifica as duas variáveis que o dono pediu.

A mesma frase errada vive na docstring de `politica.py` ("para tentativa de
questionário não existe rascunho e `start_attempt` já é irreversível" como
razão de ficar) e no §9 de 15/09. A implementação corrige a docstring; o §9
não se reescreve, ganha entrada nova dizendo que a de 15/09 errou neste ponto.

## O que foi lido para este spec

**1. Os campos de que o plano precisa existem na API, e a maioria está atrás
de uma capacidade que aluno tem.** No fonte de `mod_quiz_get_quizzes_by_courses`
os campos se dividem em três blocos: os que qualquer pessoa vê (`id`,
`coursemodule`, `course`, `name`); os que exigem `mod/quiz:view` (`timeopen`,
`timeclose`, `attempts`, `timelimit`, `grademethod`, `sumgrades`, `grade`,
`preferredbehaviour`, entre outros); e os que só vêm quando o gestor de acesso
do questionário **não impede** o acesso da pessoa (`overduehandling`,
`graceperiod`, `navmethod`, `questionsperpage`, entre outros). `mod/quiz:view`
é a capacidade de aluno matriculado **[inferência do fonte do Moodle, não
medida]**. Ou seja: pela leitura do fonte, `attempts` e `timelimit` **devem**
chegar à conta de aluno, e `overduehandling` **só chega** para questionário a
que a pessoa tem acesso agora. Nada disso foi medido neste site, e o spec de
17/09 já registrou o que acontece quando se confia em dicionário imaginado
(`tests/moodle/test_forma_real.py`, cabeçalho). Ver *Pré-requisito*.

**2. `start_attempt` sem `forcenew`, havendo tentativa em andamento, devolve
a tentativa em andamento em vez de criar outra; com `forcenew=true`, dá erro
`attemptstillinprogress`** **[inferência do fonte do Moodle, não medida]**.
Isto importa em dois lugares: `forcenew` nunca é enviado por este projeto, e a
existência de uma tentativa em andamento é um dos itens do plano.

**3. Questionário cronometrado tem um comportamento declarado para quando o
tempo acaba com a tentativa aberta, e ele é configuração do professor.** O
campo é `overduehandling`, com três valores: `autosubmit` (o Moodle envia o
que estava respondido), `graceperiod` (a pessoa ganha `graceperiod` segundos
só para enviar, sem responder mais nada) e `autoabandon` (a tentativa vira
`abandoned` e **não conta como nota**, mas **conta como tentativa usada**)
**[inferência do fonte do Moodle, não medida]**. É o dado da decisão pendente
4, e ele só chega quando o acesso não está impedido (item 1).

**4. Existem duas leituras de acesso na família, ambas `livre` no catálogo e
nenhuma das duas na allowlist.** `mod_quiz_get_quiz_access_information(quizid)`
devolve `canattempt`, `preventaccessreasons[]` e `activerulenames[]`;
`mod_quiz_get_attempt_access_information(quizid, attemptid)` devolve `endtime`,
`isfinished` e `preventnewattemptreasons[]`, e `attemptid` é opcional com
padrão `0`, que significa "uma tentativa nova" **[catálogo §3.8; opcionalidade
do `attemptid` por inferência do fonte, não medida]**. São as duas funções que
dizem, na voz do site, "você pode abrir" ou "não pode, e por isto". Entrar
com elas é decisão de §9 e depende de medição; ver Camada 5.

**5. O mecanismo de contexto já existe e tem teste.** `capacidades.py` monta
o campo `instructions` do `initialize` e o eco no fim de `diagnostico`, com um
texto por estado da flag, sem nome de função do Moodle e sem palavra de
convite (C1 a C8, G1 a G4, D7 a D7c) **[código]**. É a ele que este spec pede
para crescer, e não a um item novo no `tools/list`.

**6. O plano com código existe e tem uma lição registrada.** `codigo_do_plano`
em `entrega.py` mistura cinco coisas, e a quinta (o verbo) entrou em 16/09
porque sem ela o código do rascunho confirmava a entrega **[código]**. O
código não é prova de humano; é prova de que o plano não mudou entre a
leitura e a escrita.

## O modelo de ameaça, herdado e com um termo a mais

O que o desenho de 15/09 protege contra continua: **acidente e
ambiguidade**. O que ele não protege contra também continua: um modelo com
shell alcança o `.env`. Nada abaixo muda isso, e nada abaixo finge mudar.

O termo a mais é este: **o acidente aqui tem dois preços, e o preço é do
questionário, não da pessoa.** Um "abre aí o Exercícios 6" que abre o
questionário errado custa zero quando o errado tem tentativas ilimitadas, e
custa uma chance que não volta quando o errado tem três. As duas variáveis
existem para que quem liga escolha qual preço aceita pagar por engano, e para
que a pessoa que ligou só a primeira nunca pague o segundo.

Há ainda um terceiro custo, que nenhuma variável cobre e que a decisão
pendente 4 trata: um questionário **cronometrado** aberto e abandonado tem
consequência decidida pelo professor, não por quem abriu.

## Pré-requisito: medir se a conta de aluno recebe `attempts`

**Se `attempts` não vier na resposta de `mod_quiz_get_quizzes_by_courses` para
a conta de aluno, a distinção inteira entre as duas variáveis cai**, porque o
servidor não tem como saber a classe do questionário. Isto não é acabamento,
é pré-requisito: a primeira linha de código desta trilha vem depois desta
captura, e o desenho abaixo declara o que faz na ausência do campo (recusa,
nunca adivinha). O spec de 17/09 pediu a mesma medição e ela ainda não
aconteceu; `fixtures/moodle/` não tem nenhuma captura da família `mod_quiz`
**[disco]**.

Os comandos, nenhum deles varre lista de funções e nenhum escreve:

```bash
./scripts/userid.sh
./scripts/ws.sh core_enrol_get_users_courses "userid=<o de cima>"       # courseid da sigla

# a lista de questionários de uma disciplina: mede e grava o cru em fixtures/moodle/raw/
./scripts/capture.sh quizzes_ptc3360 \
    mod_quiz_get_quizzes_by_courses "courseids[0]=<courseid>"

# SÓ OS NOMES DAS CHAVES do primeiro questionário, sem valor nenhum (item 8 do CLAUDE.md)
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(sorted(d["quizzes"][0].keys()))' \
    fixtures/moodle/raw/quizzes_ptc3360.json

# tentativas do aluno num questionário, com TODOS os estados (o plano precisa saber da em andamento)
./scripts/capture.sh quiz_attempts_all_ex6 \
    mod_quiz_get_user_attempts "quizid=<id>" "userid=<...>" status=all includepreviews=0

# as duas leituras de acesso, uma chamada cada, para decidir se entram (Camada 5)
./scripts/capture.sh quiz_access_ex6 mod_quiz_get_quiz_access_information "quizid=<id>"
./scripts/capture.sh quiz_attempt_access_ex6 mod_quiz_get_attempt_access_information "quizid=<id>" attemptid=0

python3 scripts/higienizar.py    # antes de versionar (§3.3): as respostas trazem userid
python3 scripts/reduzir.py
```

O que a captura precisa responder, em ordem de peso:

1. **`attempts` vem?** Sem ele não há classe, e sem classe não há variável que
   se aplique. É a hipótese que derruba o spec.
2. **`timelimit` vem?** Sem ele o plano não sabe dizer "o relógio de N
   minutos começa", e a decisão pendente 4 fica sem dado.
3. **`overduehandling` e `graceperiod` vêm, e para quais questionários?** Pela
   leitura do fonte, só para os de acesso não impedido. Se vier, o plano diz o
   que acontece se a pessoa sumir; se não vier, o plano diz que não sabe.
4. **`grade` vem?** É o dado da decisão pendente 3 (questionário que vale nota).
5. **`get_user_attempts` com `status=all` devolve o `state` de cada tentativa
   (`inprogress`, `overdue`, `finished`, `abandoned`)?** O plano precisa
   distinguir "há uma aberta" de "todas terminaram".
6. **As duas leituras de acesso respondem para aluno, e o que
   `preventnewattemptreasons` diz quando restam zero tentativas?** Decide a
   Camada 5.
7. **Quantos bytes cada resposta custa** e a razão projetado/cru. Nada disto é
   estimável daqui.

O que **não** se mede antes de implementar, de propósito: o comportamento de
`mod_quiz_start_attempt` em si. Medir é chamar, chamar é abrir uma tentativa
de verdade na conta do dono, e este spec existe para que isso só aconteça com
plano, código e variável. A primeira abertura real sob a variável de
ilimitadas, num questionário sem nota, é a medição, e ela vai para o §9 com
o que devolveu.

O resultado inteiro vai para `notas/`, com a origem rotulada na mesma linha,
e a decisão para o §9.

## Desenho

### Camada 1. Duas variáveis, uma classe por questionário

```
USP_MCP_QUESTIONARIO_ILIMITADO=0
USP_MCP_QUESTIONARIO_LIMITADO=0
```

As duas só no Moodle, as duas lidas do ambiente a cada chamada (como
`entrega_habilitada`), as duas ligadas só por igualdade exata com `"1"`. O
nome carrega a palavra que a pessoa vai ler no `.env`, e não uma abreviação
(`QUIZ`), porque o público do README não sabe o que é quiz e sabe o que é
questionário; e o sufixo diz a classe pelo nome, para que ninguém ligue a
errada por parecer a genérica. `NOME_DA_FLAG` vira um par de constantes no
mesmo lugar, pelo mesmo motivo que a primeira é constante: o nome aparece na
leitura do ambiente, no motivo de recusa e nas instruções, e os três precisam
concordar.

A **classe** de um questionário sai de um campo só, `attempts` de
`mod_quiz_get_quizzes_by_courses`:

| `attempts` | classe | variável que governa |
|---|---|---|
| `0` | ilimitadas | `USP_MCP_QUESTIONARIO_ILIMITADO` |
| `n > 0` | limitadas | `USP_MCP_QUESTIONARIO_LIMITADO` |
| ausente ou inválido | **desconhecida** | **nenhuma**: recusa, e a recusa diz que o site não informou o total de tentativas e que por isso nenhuma das duas variáveis se aplica |

A terceira linha é a que segura o desenho se o pré-requisito falhar. Ela
nunca adivinha para o lado de ilimitadas ("já que não sei, custa zero"), pelo
mesmo motivo de `_orcamento` em `questionarios.py` ficar em silêncio quando
`attempts` não vem: afirmar a mais é o erro caro.

Uma nota sobre o que "ilimitadas" não garante: `attempts == 0` diz que o
Moodle não conta tentativas, e não diz que refazer é indolor. Um questionário
ilimitado com `grademethod` "primeira tentativa" torna a primeira a que vale
**[catálogo §3.8]**. É por isso que a decisão pendente 3 existe, e por isso o
plano imprime `grademethod` quando ele vier.

### Camada 2. O que sai de onde, para onde, sob qual variável

| função | hoje | nesta fase | variável |
|---|---|---|---|
| `mod_quiz_start_attempt` | `BLOQUEIO_PERMANENTE` | sai para um conjunto novo, `TENTATIVA_CONFIRMADA` | a da **classe do questionário** (Camada 1), **e** confirmação declarada por chamada |
| `mod_quiz_process_attempt` | `BLOQUEIO_PERMANENTE` | **fica**, pendente da decisão 1 | a decidir |
| `mod_quiz_save_attempt` | `BLOQUEIO_PERMANENTE` | **fica**; é assunto da fase de responder | a decidir naquela fase |
| `mod_quiz_get_attempt_data` | `BLOQUEIO_PERMANENTE` | **fica**, pendente da decisão 2 | a decidir |
| `mod_quiz_get_attempt_summary` | `BLOQUEIO_PERMANENTE` | **fica**; anda junto com a de cima | a decidir |
| `mod_quiz_get_quizzes_by_courses` | `ALLOWLIST` | fica; o plano a lê | nenhuma (leitura) |
| `mod_quiz_get_user_attempts` | `ALLOWLIST` | fica; o plano a lê com `status=all` (Camada 4) | nenhuma (leitura) |
| `mod_quiz_get_quiz_access_information` | fora | **candidata** à `ALLOWLIST`, se a medição 6 confirmar | nenhuma (leitura) |
| `mod_quiz_get_attempt_access_information` | fora | idem | nenhuma (leitura) |

`BLOQUEIO_PERMANENTE` vai de **40 para 39**. E5 (`test_e5_o_bloqueio_permanente_tem_40_nomes`)
muda junto, e é o único teste do projeto que trava cardinalidade dessa lista;
os de 17/09 travam pertencimento de propósito. `ESCRITA_CONFIRMADA` não muda:
misturar `start_attempt` com as duas de `mod_assign` faria `USP_MCP_ENTREGA`
abrir questionário por tabela, que é exatamente a mudança silenciosa de
significado que o spec de 15/09 recusou para `USP_MCP_ALLOW_WRITES`.

`decidir` ganha um quarto caminho, entre o de escrita confirmada e a
allowlist, e um parâmetro nomeado a mais:

```python
def decidir(funcao, permitir_escrita=False, *, confirmada=False, classe=None) -> Decisao
```

Ordem: bloqueio permanente; escrita confirmada (`mod_assign`, governada por
`USP_MCP_ENTREGA`); **tentativa confirmada** (`mod_quiz`, governada pela
variável da `classe`, que é `"ilimitadas"`, `"limitadas"` ou `None`); allowlist.
Um call site que passe `classe=None` para `start_attempt` recebe a recusa da
terceira linha da tabela da Camada 1, com as duas flags ligadas. A regra que
vale para `confirmada` vale para `classe`: sozinha não abre nada, e chamar
`decidir("mod_quiz_start_attempt", classe="ilimitadas")` com a variável
desligada recebe a mesma recusa de quem não passou classe nenhuma.

`USP_MCP_ALLOW_WRITES` continua não abrindo nada, e o teste que afirma isso
nos três servidores não muda.

### Camada 3. Uma ferramenta, e por que uma

Entra `abrir_questionario`, com `disciplina` obrigatória, `questionario`
obrigatório (pedaço do nome; casar com mais de um lista os candidatos em vez
de escolher) e `confirmacao` opcional. Ela **só aparece no `tools/list` se ao
menos uma das duas variáveis estiver ligada**, pelo mesmo mecanismo de
`_ferramentas_de_entrega`, e a descrição dela é montada com o estado das
flags: diz qual classe este servidor abre. A contagem de ferramentas do
Moodle vai de 11 para 12 com uma das variáveis ou as duas, e para 14 com
`USP_MCP_ENTREGA` junto.

Por que **uma** ferramenta para duas variáveis, e não `abrir_questionario` e
`abrir_questionario_limitado`: o precedente de 15/09 separa **verbos** (salvar
e entregar são ações diferentes que a pessoa pede com palavras diferentes). Aqui
o verbo é um só, abrir, e a classe não é escolha da pessoa, é dado do
questionário. Duas ferramentas com o mesmo verbo obrigariam o modelo a
adivinhar a classe antes de chamar, e um chute errado gastaria uma chamada
para receber "não é esse, use o outro", que é o laço que ensina a insistir.
Com uma ferramenta a classe é lida do site dentro da invocação e a variável
certa é consultada pelo código.

O preço dessa escolha, dito em voz alta: com **só uma** das variáveis ligada,
`abrir_questionario` está na lista e recusa questionário da outra classe. É
uma ferramenta visível que recusa **às vezes**, por dado do site, na mesma
natureza da recusa por `teamsubmission` em `entregar`; não é uma que recusa
**sempre**, que é o caso que E14 proíbe. A descrição diz a classe que este
processo abre, e a recusa diz a variável que governa a outra classe e de quem
é a decisão de ligá-la, com as mesmas palavras que a política já usa para
`USP_MCP_ENTREGA`. Se o uso real mostrar o modelo insistindo nessa recusa, a
alternativa registrada é a de duas ferramentas, e a troca é de nome, não de
desenho.

### Camada 4. O plano em duas etapas transporta, com outro material

O precedente usa um hash do estado anterior da entrega. Questionário não tem
"estado anterior" no mesmo sentido: abrir não altera um objeto que já existe,
**cria** um. O mecanismo transporta mesmo assim, porque o que o hash prova não
é "o objeto não mudou", é "**o plano que eu mostrei ainda é o plano real**", e
isso tem material aqui:

```python
material = [verbo, quizid, tentativas_permitidas, finalizadas, em_andamento,
            timeclose, timelimit]
```

Sete coisas, e cada uma muda o significado de confirmar: alguém abriu ou
terminou uma tentativa pelo site entre o plano e a confirmação (`finalizadas`
ou `em_andamento` mudam); o professor prorrogou ou deu tentativa extra
(`timeclose`, `tentativas_permitidas`); mudou o tempo (`timelimit`). O verbo
entra desde o início pela lição de 16/09.

Uma propriedade que a entrega não tem e esta tem: **depois de uma abertura
bem sucedida, repetir a confirmação é recusado sozinho**, porque a contagem de
tentativas mudou e o código não casa mais. O plano em duas etapas protege
contra abrir duas vezes sem nenhuma linha a mais.

O plano lê duas funções que já estão na allowlist, com uma exceção declarada
a R2. `mod_quiz_get_user_attempts` vai com `status=all` **neste módulo**,
porque um plano que não sabe se há tentativa em andamento não é fiel, e "você
já tem uma tentativa aberta desde ontem" é a linha mais importante que ele
pode imprimir. R2 continua valendo, na íntegra, para `questionarios.py`: lá a
pergunta é "já fiz", e a tentativa em curso não responde a ela. R1 continua
valendo para os dois módulos: o `attemptid` da tentativa em andamento chega
na resposta, entra no plano como **contagem** (`em_andamento = 1`) e não é
projetado nem devolvido. E o medo escrito em R2 ("você tem uma tentativa
aberta agora" como deixa para "então termina para mim") é exatamente o que a
decisão pendente 1 decide: enquanto `process_attempt` estiver no bloqueio,
não há para onde a deixa levar.

O plano, com os dados que o pré-requisito confirmar:

```
Plano: abrir tentativa. PTC3360, "Exercícios 6"
  tentativas: 0 de 1 usadas; esta será a 1 de 1. Depois dela restarão 0.
  tempo: 40 minutos a partir da abertura. O relógio não para nem volta.
  fecha: qui 24/09 23:59 (faltam 6 dias)
  se o tempo acabar com a tentativa aberta: o e-Disciplinas envia o que estiver respondido
  vale nota: sim, até 10,00; conta a maior nota entre as tentativas
  isto NÃO tem desfazer pela API nem pelo site.
  este servidor não responde nem finaliza: depois de aberta, a tentativa continua na página do e-Disciplinas.

Para confirmar, chame de novo com confirmacao="7b2e91"
```

Cada linha que depende de campo hipotético tem a versão para a ausência:
"tempo: o e-Disciplinas não informou se há limite"; "se o tempo acabar: o
e-Disciplinas não informou o que faz"; "vale nota: não informado". A regra é a
da Decisão 4 do spec de 17/09: a ausência **fala**.

A elicitação (`Context.elicit`) entra entre o plano e a escrita, como
apresentação e não como garantia, com os três resultados distintos na saída
(aceitou, recusou, não pude perguntar). É o adaptador que `entrega.py` já tem,
reaproveitado e não recopiado.

### Camada 5. Recusas que as variáveis não abrem

Mesmo com a classe certa ligada e o código conferindo, `abrir_questionario`
recusa e diz por quê:

- `attempts` ausente (classe desconhecida): recusa da Camada 1.
- **restam 0 tentativas** (`finalizadas >= tentativas_permitidas` em
  questionário limitado): "não há tentativa para abrir".
- **já existe tentativa em andamento**: "você já tem uma aberta; abrir de novo
  não cria outra, e continuar é pela página do e-Disciplinas". Pela leitura do
  fonte o site devolveria a mesma tentativa, mas o projeto não paga uma
  escrita para descobrir o que já sabe.
- questionário **fechado** (`timeclose` passado) ou **ainda não aberto**
  (`timeopen` futuro): o site diria não; o projeto diz antes e não gasta a
  chamada.
- `preventaccessreasons` ou `preventnewattemptreasons` não vazios, **se** as
  duas leituras de acesso entrarem: é o site dizendo não com as próprias
  palavras (senha, faixa de IP, intervalo entre tentativas), e o projeto
  repassa em vez de traduzir.
- `forcenew` **nunca** é enviado. Não é recusa, é regra do módulo, e é teste
  sobre o parâmetro enviado.

Sobre as duas leituras de acesso: elas substituem aritmética nossa por
resposta do site em dois pontos (restam zero; acesso impedido por regra que a
gente não modela). Entram na allowlist (13 para 15) e em
`FUNCOES_POR_FERRAMENTA` só se a medição 6 mostrar que respondem para aluno e
que `preventnewattemptreasons` diz alguma coisa útil. Se não entrarem, o
desenho fica com a aritmética e diz que é aritmética. D4 obriga a tabela do
diagnóstico a acompanhar, e a linha de `abrir_questionario` **não entra** na
tabela, pela mesma razão escrita para `entregar`: a tabela pergunta ao site, e
uma ferramenta que a configuração do processo não expõe não tem o que
perguntar.

### O que este desenho vale sozinho, dito sem enfeite

Abrir sem responder economiza um clique e liga um relógio. O valor de uso
está na fase seguinte, quando o assistente puder ler e responder. Mesmo assim
abrir é a primeira coisa a desenhar, por três razões: é o passo irreversível,
e portão se põe no irreversível; é uma função só, e a política de duas
variáveis fica travada por teste antes de qualquer coisa mais gorda passar por
ela; e é a única das cinco que não exige `attemptid`, então R1 sobrevive
inteira a esta fase.

## Responder é outro problema, e é outra fase

Abrir é **uma chamada** com um parâmetro que já temos (`quizid`). Responder é
outra ordem de trabalho, e este spec dimensiona para que ninguém a tome por
extensão da anterior:

1. **Ler a tentativa.** `mod_quiz_get_attempt_data(attemptid, page)` devolve,
   por questão, `slot`, `type`, `page`, `sequencecheck`, `status` e `html`
   **[catálogo §3.8; forma por inferência do fonte, não medida]**. Está no
   bloqueio permanente desde ontem, e é a decisão pendente 2. Sem ela não há o
   que responder.
2. **Entender os tipos.** Cada tipo de questão do Moodle (`multichoice`,
   `truefalse`, `shortanswer`, `numerical`, `match`, `essay`, `multianswer`,
   arrastar e soltar e os demais) monta os campos de resposta com um esquema
   de nome próprio dentro do `html`, no formato `q<uso>:<slot>_answer`,
   `q<uso>:<slot>_sub0`, e assim por diante, e as alternativas de múltipla
   escolha podem vir embaralhadas por tentativa. Responder exige **um
   interpretador de HTML por tipo**, e cada tipo é um trabalho separado com
   captura separada.
3. **Enviar respeitando a sequência.** `save_attempt` e `process_attempt`
   recebem `data[]` com pares nome/valor e exigem, por questão, o
   `sequencecheck` lido em `get_attempt_data`; um valor velho é recusado pelo
   site. `navmethod` sequencial proíbe voltar de página; `questionsperpage`
   define quantas leituras são.
4. **Finalizar.** `process_attempt` com `finishattempt=true`, decisão pendente
   1, com plano próprio ("vou finalizar com 7 de 10 respondidas").
5. **O custo que não é de código.** Tudo isso põe **o enunciado de uma prova
   em andamento dentro do contexto de um modelo**, que é a frase que justificou
   R4 ontem. Com tentativas ilimitadas e sem nota é exercício; com tentativas
   limitadas e nota, é prova. A fase de responder herda as duas variáveis daqui
   e provavelmente precisa de uma recusa a mais que nenhuma das duas abre. Isso
   é decisão daquele spec, não deste.

Dimensão: cinco funções tocadas contra uma; um interpretador por tipo de
questão contra zero; três fixtures novas no mínimo (dados da tentativa, uma
por tipo de questão presente) contra duas. **Não cabe nesta fase.** Cabe num
spec próprio, que começa pela captura de `get_attempt_data` de uma tentativa
aberta pela fase 1, num questionário ilimitado e sem nota, e que mede antes de
escrever a primeira linha.

## Quatro decisões pendentes, e o dono decide

O dono foi explícito: não decidir sozinho o que bloquear. Cada item abaixo tem
as opções, o custo de cada uma e uma recomendação. **Nenhuma está tomada.**

### Decisão 1. `process_attempt` entra na mesma variável que abrir, ou merece a sua?

`mod_quiz_process_attempt` finaliza a tentativa. É o irreversível de verdade:
abrir queima uma chance, finalizar fixa a nota.

| opção | o que é | custo |
|---|---|---|
| **A** | fica no `BLOQUEIO_PERMANENTE` nesta fase; entra na fase de responder, sob **as mesmas duas variáveis**, como verbo próprio (`finalizar_questionario`) com plano próprio | nesta fase, nenhum; na próxima, o dono que ligou "abrir" ganha "finalizar" junto sem ligar mais nada |
| **B** | fica nesta fase; entra na próxima sob **uma terceira variável** só dela | mais um nome no `.env`, mais um estado nas instruções (de 4 para 8 combinações), mais um teste de simetria; em troca, quem quer abrir e responder sem nunca finalizar pela API tem como dizer isso |
| **C** | entra **agora**, sob as mesmas duas variáveis | finaliza uma tentativa em que este projeto não escreveu nada: o acidente mais silencioso possível é enviar uma prova em branco |

**Recomendação: A.** Finalizar sem ter respondido não tem caso de uso honesto,
então não entra agora. Quando entrar, a variável certa já existe: quem aceitou
o preço de abrir um questionário limitado aceitou o preço da classe, e o que
protege o finalizar não é uma flag a mais, é um verbo separado com plano
separado (a lição do código do plano com verbo). A opção B compra granularidade
que ninguém pediu ao preço de dobrar os estados que o assistente precisa saber.
**Escolha: pendente.**

### Decisão 2. `get_attempt_data` fica atrás de qual variável?

É leitura, mas só existe depois de abrir, e o que ela devolve é enunciado de
prova em curso.

| opção | o que é | custo |
|---|---|---|
| **A** | fica no `BLOQUEIO_PERMANENTE` nesta fase; na fase de responder sai **junto com `save_attempt`**, sob a variável da classe do questionário, nunca sozinha | nesta fase, o assistente abre e não vê; a pessoa responde pela página |
| **B** | sai agora, só sob `USP_MCP_QUESTIONARIO_ILIMITADO` | com tentativas ilimitadas o custo de o modelo ver o enunciado é o de um exercício, não o de uma prova; mas é R4 revogada ontem à noite para hoje de manhã, sem uso real que justifique, e sem nada para fazer com o que se leu |
| **C** | sai agora, sob as duas | é o cenário que motivou R4, liberado sem a fase que o usaria |
| **D** | variável própria, de leitura de prova em curso | mesma conta da opção B da decisão 1: estados a mais para uma distinção que a classe do questionário já faz |

**Recomendação: A.** A razão de R4 (não pôr enunciado de prova no contexto de
um modelo) não muda porque a tentativa foi aberta por aqui. Ler sem responder
não tem uso; ler para responder é a fase seguinte, e lá `get_attempt_data` e
`save_attempt` são metades de uma ação só e saem juntas, sob a variável da
classe. `get_attempt_summary` anda com ela. **Escolha: pendente.**

### Decisão 3. Questionário que vale nota é tratado diferente?

A API diz alguma coisa: `grade` em `mod_quiz_get_quizzes_by_courses` é a nota
máxima do questionário, e **`0` significa que ele não vale nota** (é o que
`quiz_has_grades` testa no fonte) **[inferência do fonte do Moodle, não
medida; presença do campo para aluno é a medição 4]**. O boletim também diz:
questionário sem nota não tem item em `gradereport_user_get_grade_items`, e o
projeto já lê essa função em `notas` **[código]**. E `grademethod` diz **qual**
tentativa conta (maior, média, primeira, última) **[catálogo §3.8]**.

| opção | o que é | custo |
|---|---|---|
| **A** | não distingue; o eixo é só o das tentativas | um questionário ilimitado que vale nota com `grademethod` "primeira tentativa" abre sob a variável barata com o custo da cara |
| **B** | **o plano imprime** "vale nota: sim, até X; conta a Y tentativa" ou "não vale nota", sem recusa nova | a pessoa decide com o dado na frente; o projeto não inventa uma terceira classe |
| **C** | recusa questionário com `grade > 0` sob a variável de ilimitadas, mesmo ligada | a maioria dos exercícios semanais vale nota; a variável barata deixaria de abrir quase tudo |
| **D** | terceira variável, "vale nota" | os estados dobram de novo, e a pergunta "ilimitado com nota é barato ou caro?" não tem resposta única para o projeto responder por decreto |

**Recomendação: B, com uma linha a mais quando `grademethod` for "primeira
tentativa" em questionário ilimitado**: "atenção: nesta disciplina conta a
primeira tentativa, então esta abertura decide a nota". Se `grade` não vier na
captura, a linha diz "vale nota: não informado" e a decisão fica como A por
falta de dado, declarada. **Escolha: pendente.**

### Decisão 4. Questionário cronometrado aberto, e a pessoa some

O que acontece é configuração do professor, campo `overduehandling`:
`autosubmit` envia o que estava respondido; `graceperiod` dá `graceperiod`
segundos só para enviar; `autoabandon` descarta a tentativa **e ela conta como
usada** **[inferência do fonte do Moodle, não medida; o campo só chega para
questionário de acesso não impedido, medição 3]**. Em qualquer dos três, com
tentativas limitadas, sumir custa a tentativa.

| opção | o que é | custo |
|---|---|---|
| **A** | recusa abrir todo questionário com `timelimit > 0`, sob as duas variáveis, no espírito de `_recusa_por_cronometro` da entrega ("este servidor não liga cronômetro em nome de ninguém") | o exemplo que o dono deu tem relógio de N minutos; a opção A o recusa |
| **B** | abre, e **o plano imprime o relógio e a consequência de sumir**, na voz do campo; se o campo não vier, imprime que não sabe | o portão é informação, não recusa; um modelo que confirma sem ler a linha abre um relógio de 40 minutos para uma pessoa que foi almoçar |
| **C** | abre sob ilimitadas com a linha da opção B; **recusa** sob limitadas quando `overduehandling` for `autoabandon` ou não vier | é onde sumir custa a tentativa **e** a nota; a recusa cita o motivo e manda para a página |
| **D** | o servidor "vigia" a tentativa e avisa antes de o tempo acabar | não existe: um servidor MCP stdio não tem como falar com a pessoa fora de uma chamada dela |

**Recomendação: C.** A linha do plano (opção B) é obrigatória em qualquer
caso, porque é o que o dono pediu com "o relógio de N minutos começa". A
recusa da opção C é estreita e cita um dado do site: só no cruzamento em que
o pior resultado (tentativa gasta e sem nota) é o comportamento configurado, ou
em que o projeto não sabe qual é. Fora desse cruzamento, quem ligou a variável
de limitadas aceitou o preço da classe. **Escolha: pendente.**

## Onde a informação vive e como chega ao modelo

O dono pediu que o assistente esteja **sempre contextualizado** sobre essas
variáveis ao chamar as ferramentas, e reclamou que hoje ele está mal
contextualizado sobre como o repositório funciona. São dois problemas com
dois lugares.

### Para o modelo, em tempo de uso: `instructions` e o eco do `diagnostico`

O mecanismo é o de 17/09, e o motivo de não inventar outro está escrito em
`capacidades.py`: o `tools/list` é superfície de **ação**, e um item que
aparece e sempre recusa ensina a insistir; o `instructions` do `initialize` é
superfície de **informação**, chega uma vez por conexão e não tem nada
chamável. A capacidade de questionário entra **lá**, e não como ferramenta a
mais nem como frase na descrição de `questionarios`.

`capacidades.py` passa a falar de **duas capacidades** em vez de uma, e o
texto ganha um parágrafo por capacidade, cada um com a versão curta (para o
diagnóstico) sendo o começo exato da inteira (C3 continua valendo). Para o
questionário há quatro estados, e o texto é montado a partir deles e não
escrito quatro vezes:

| ILIMITADO | LIMITADO | o que o parágrafo diz |
|---|---|---|
| 0 | 0 | existe, está desligada, o que custa em cada classe, quem liga, que não há o que tentar |
| 1 | 0 | ligada **só para questionário com tentativas ilimitadas**; `abrir_questionario` está na conexão e recusa os limitados, dizendo a variável que os governa |
| 0 | 1 | o espelho: ligada só para limitados; e a frase de custo ("um engano aqui gasta uma chance que não volta") vem junto |
| 1 | 1 | ligada para as duas classes, com o custo da segunda repetido |

O texto proposto, com as duas desligadas (o estado de quase todo servidor):

```
Questionário: abrir tentativa está DESLIGADO. Existe neste projeto uma
capacidade de abrir uma tentativa de questionário, em duas variáveis
separadas: uma para questionário com tentativas ilimitadas, em que um engano
custa zero, e outra para questionário com tentativas limitadas, em que um
engano gasta uma chance que não volta. As duas estão desligadas, por isso a
ferramenta delas não está nesta conexão. Quem liga é a pessoa dona do token,
pondo USP_MCP_QUESTIONARIO_ILIMITADO=1 ou USP_MCP_QUESTIONARIO_LIMITADO=1 no
arquivo .env do servidor e subindo o servidor de novo. Abrir uma tentativa
NÃO tem desfazer, e este servidor não responde nem finaliza questionário em
nenhuma configuração desta versão.
```

Ele obedece às cinco regras que já governam o texto da entrega e têm teste:
nenhum nome de função do Moodle; nenhuma palavra de convite (`ligue`,
`habilite`, `recomendo`, `basta`, `é só`); diz de quem é a decisão; diz que
não há o que tentar enquanto a variável não estiver no ambiente; e a versão
curta é o começo exato da inteira. A frase "não responde nem finaliza em
nenhuma configuração **desta versão**" é a que a fase de responder vai trocar,
e por isso ela cita a versão.

**O teto de C7 (1800 caracteres) não cabe mais.** Com dois parágrafos de
capacidade e o de abertura, o pior caso (as três variáveis ligadas, que é o
que mais texto tem) passa. A proposta é subir o teto para **3000** e registrar
no teste o porquê: são duas capacidades, e a regra que segura o crescimento
continua sendo a mesma ("`instructions` carrega só o que o `tools/list` não
tem como carregar"). Se um dia a fase de responder pedir o terceiro parágrafo,
o teto vira decisão de novo, não acomodação.

O `diagnostico` ecoa a versão curta dos dois parágrafos nos dois caminhos de
saída, como hoje faz com um.

E há uma frase que precisa **sair**, porque vira mentira: o aviso fixo
`_SO_LEITURA` de `questionarios.py` diz "não há configuração que a faça fazer
isso". Passa a dizer só "Esta ferramenta só lê. Ela não abre, não responde e
não finaliza questionário; para isso, use a página do e-Disciplinas", sem
afirmar nada sobre configuração, nem para um lado nem para o outro. O estado
das variáveis vive nas `instructions`, e a saída de uma ferramenta de leitura
não é o lugar de anunciar um caminho de escrita (é a mesma razão de 17/09
para não pôr isso na descrição de `ja_entreguei`). QO20 muda junto: continua
exigindo que a saída diga que não abre e que não nomeie função bloqueada, e
deixa de exigir a frase sobre configuração.

As descrições de `abrir_questionario` no `tools/list` são a outra metade do
contexto, e só existem quando a ferramenta existe: dizem que funciona em duas
chamadas, que abrir não tem desfazer, que este servidor não responde, e **qual
classe este processo abre**, montado com o estado das flags. Nenhuma outra
descrição menciona as variáveis.

### Para quem mantém o projeto: os lugares que afirmam "não há flag para questionário"

Isto é o que o dono chamou de "mal contextualizado sobre como o repositório
funciona", e a causa é que a afirmação vive em sete lugares e cada um vai
envelhecer sozinho se a implementação não os tocar no mesmo commit:

| onde | o que diz hoje | o que passa a dizer |
|---|---|---|
| `SPEC1.md` §2.2 | as três de quiz "podem queimar tentativa de prova real", sem flag que libere | `start_attempt` saiu para `TENTATIVA_CONFIRMADA` sob as duas variáveis; as outras quatro ficam, com ponteiro para este spec e para as decisões pendentes |
| `SPEC1.md` §9 | entrada de 15/09 com a frase errada sobre o plano | entrada nova de 18/09 com a correção, palavra por palavra como está na seção acima |
| `CLAUDE.md` item 3 | "A exceção, e é uma só" | "As exceções são duas", com as três variáveis nomeadas e o ponteiro |
| `politica.py`, docstring | "para tentativa de questionário não existe rascunho e `start_attempt` já é irreversível" como razão de ficar | a razão de custo (zero contra uma chance que não volta), e o quarto conjunto |
| `.env.example` | "As três de questionário seguem no bloqueio permanente, e não há flag que as libere" | as duas variáveis, com o texto proposto abaixo |
| `README.md` | "Começar uma prova, responder questionário ou mandar mensagem em seu nome estão bloqueados e continuam bloqueados mesmo se alguém ligar a permissão de escrita" | ver *O README* |
| `questionarios.py`, `_SO_LEITURA` | "não há configuração que a faça fazer isso" | a frase sem a cláusula de configuração |

Um teste segura isso: a versão dos textos que citam variável (C1, D7, o novo
para o parágrafo de questionário) exige o nome da variável pela constante, e
um `grep` de suíte por "não há flag que" e "não há configuração que" em
`usp_mcp/` e `.env.example` reprova enquanto a frase velha existir.

Texto proposto para o `.env.example`, no bloco de escrita, depois de
`USP_MCP_ENTREGA=0`:

```
# Abrir tentativa de questionário, com confirmação em duas etapas. São DUAS
# variáveis porque o engano tem dois preços: com tentativas ilimitadas, abrir
# o questionário errado custa zero; com limitadas, gasta uma chance que não
# volta. A classe vem do próprio questionário (quantas tentativas o professor
# permitiu), e a variável certa é consultada pelo servidor. Questionário cujo
# total de tentativas o e-Disciplinas não informe não abre com nenhuma das
# duas. Abrir não tem desfazer. Este servidor não responde nem finaliza
# questionário em nenhuma configuração desta versão. Leia a seção "Abrindo
# questionário" do README antes de ligar.
USP_MCP_QUESTIONARIO_ILIMITADO=0
USP_MCP_QUESTIONARIO_LIMITADO=0
```

## O README

Público declarado: estudante sem conhecimento técnico. Sem travessão. Quatro
lugares mudam; o texto vai aqui e **não** foi aplicado nesta trilha.

**1. Em *Como funciona*, o parágrafo das cercas.** A frase "Começar uma prova,
responder questionário ou mandar mensagem em seu nome estão bloqueados e
continuam bloqueados mesmo se alguém ligar a permissão de escrita. Entregar
trabalho é a única exceção que pode ser ligada" passa a:

> Responder questionário e mandar mensagem em seu nome estão bloqueados e
> continuam bloqueados mesmo se alguém ligar a permissão de escrita. Duas
> coisas podem ser ligadas, e vêm desligadas: entregar trabalho e abrir uma
> tentativa de questionário. As seções *Entregando trabalho* e *Abrindo
> questionário* explicam com que cuidados.

**2. Seção nova, *Abrindo questionário*, logo depois de *Entregando
trabalho*:**

> ## Abrindo questionário
>
> Por padrão o projeto só lê. Abrir uma tentativa de questionário no
> e-Disciplinas pode ser ligado, e vem desligado: enquanto você não ligar,
> essa ferramenta nem aparece para o assistente.
>
> São duas chaves separadas, porque errar tem dois preços. Um questionário
> com tentativas ilimitadas pode ser aberto de novo quantas vezes for
> preciso, então abrir o errado não custa nada. Um questionário com número
> fixo de tentativas gasta uma delas na hora em que é aberto, e essa
> tentativa não volta.
>
> Para ligar só os de tentativas ilimitadas, ponha
> `USP_MCP_QUESTIONARIO_ILIMITADO=1` no arquivo `.env` e reinicie. Para ligar
> também os de tentativas limitadas, ponha `USP_MCP_QUESTIONARIO_LIMITADO=1`.
> Dá para ligar uma, a outra ou as duas. Quem diz de que tipo é cada
> questionário é o próprio e-Disciplinas, e o projeto usa a chave certa
> sozinho. Se o e-Disciplinas não informar quantas tentativas um questionário
> permite, ele não abre com nenhuma das duas.
>
> Abrir nunca acontece no primeiro pedido. O primeiro devolve um plano: qual
> questionário, quantas tentativas você já usou e quantas vão sobrar, se há
> tempo limite e de quanto, até quando ele aceita respostas, se vale nota, e
> o que o e-Disciplinas faz se o tempo acabar com a tentativa aberta. Só o
> segundo pedido, confirmando aquele plano, abre. Se alguma coisa mudou entre
> um e outro (você abriu ou terminou uma tentativa pelo site, o professor
> mudou o prazo), a confirmação é recusada e o plano volta atualizado.
>
> Quatro coisas para saber antes de ligar:
>
> - Abrir uma tentativa não tem desfazer, nem aqui nem pelo site.
> - Este projeto só abre. Ele não lê as perguntas, não responde e não
>   finaliza. Depois de aberta, a tentativa continua na página do
>   e-Disciplinas, e é lá que você responde.
> - Questionário com tempo limite começa a contar no momento em que abre, e o
>   relógio não para. Se você abrir e sair, o que acontece com a tentativa
>   depende de como o professor configurou, e o plano diz qual é o caso quando
>   o e-Disciplinas informa.
> - Se você já tem uma tentativa aberta, o projeto recusa abrir outra e manda
>   para a página.
>
> A confirmação em duas etapas protege contra acidente e contra frase
> ambígua. Ela não é um cadeado: quem roda o projeto dentro de um assistente
> que também tem acesso ao terminal pode contornar qualquer trava que o
> programa tente impor. Ligar ou não é decisão sua, e a chave dos limitados é
> a que merece mais pensamento, porque é a que gasta o que não volta.

**3. Em *O que o projeto não responde*, o parágrafo de questionário** ganha
uma frase no fim:

> "Já entreguei o EP1?" responde só sobre tarefa. Para questionário a pergunta
> é outra ferramenta, que diz se você já fez, quantas tentativas sobram e se
> algum fechou sem você ter feito. Abrir uma tentativa é opcional e vem
> desligado; a seção *Abrindo questionário* explica.

**4. Em *Detalhes técnicos*:** a linha "Três servidores MCP, treze
ferramentas, quinze com a escrita de entrega ligada" passa a contar "catorze
ferramentas, quinze com a abertura de questionário ligada, dezesseis com a
escrita de entrega ligada, dezessete com as duas" (as três leituras de 17/09
já mudaram a base; a implementação confere o número no fio antes de escrever).
A tabela ganha a linha:

| Servidor | Ferramentas |
|---|---|
| `usp-moodle`, só com `USP_MCP_QUESTIONARIO_ILIMITADO=1` ou `USP_MCP_QUESTIONARIO_LIMITADO=1` | `abrir_questionario` |

E o parágrafo "**As duas ferramentas que escrevem não existem por padrão**"
passa a "As três ferramentas que escrevem", com `abrir_questionario` e as
duas variáveis dela na mesma frase que já explica o plano com código.

## Bateria de testes

Camada `politica`, offline, em `tests/moodle/test_politica_tentativa.py` (e
mudanças declaradas em `test_politica_entrega.py` e
`test_politica_questionario.py`):

- **QF1** `decidir("mod_quiz_start_attempt")` sem nenhuma das duas variáveis
  é recusa, e o motivo cita **as duas** variáveis pelo nome (constantes, não
  literais).
- **QF2** com `USP_MCP_QUESTIONARIO_ILIMITADO=1`, `classe="ilimitadas"` e
  `confirmada=True`: permitida. Com a mesma variável e `classe="limitadas"`:
  recusa, e o motivo cita `USP_MCP_QUESTIONARIO_LIMITADO`. O espelho com a
  outra variável ligada.
- **QF3** com as **duas** ligadas e `classe=None`: recusa, e o motivo diz que
  o site não informou o total de tentativas. É o teste da terceira linha da
  Camada 1.
- **QF4** com variável e classe certas mas `confirmada=False`: recusa que
  manda pedir o plano. `confirmada=True` sem variável: a mesma recusa de QF1.
- **QF5** `USP_MCP_ENTREGA=1` sozinha não abre `start_attempt`, e as duas
  variáveis novas não abrem `mod_assign_submit_for_grading`: as três flags
  não se cruzam.
- **QF6** `USP_MCP_ALLOW_WRITES=1` não muda nenhuma das decisões acima.
- **QF7** `process_attempt`, `save_attempt`, `get_attempt_data` e
  `get_attempt_summary` seguem recusados com as três variáveis ligadas,
  `confirmada=True` e qualquer `classe`. QO1 e QO2 mudam para tirar
  `start_attempt` do conjunto que exigem recusado.
- **QF8** `BLOQUEIO_PERMANENTE` tem 39 nomes e não contém `start_attempt`;
  `TENTATIVA_CONFIRMADA` tem 1; os quatro conjuntos são disjuntos dois a dois.
  E5 muda de 40 para 39.
- **QF9** só o valor `"1"` liga cada uma; `"true"`, `"sim"` e `"0"` não ligam.
- **QF10** o fonte de `questionarios.py` continua sem nome de escrita (QO7
  segue), e o fonte do módulo novo (`tentativa.py`) contém `start_attempt` e
  **não** contém `process_attempt`, `save_attempt`, `get_attempt_data` nem
  `get_attempt_summary`, nem em docstring.
- **QF11** o `inputSchema` de `abrir_questionario` tem exatamente
  `{disciplina, questionario, confirmacao}`, `required` é
  `["disciplina", "questionario"]`, e nenhuma ferramenta do Moodle tem
  `attemptid`, `quizid`, `cmid` ou `id` em nenhuma combinação das três
  variáveis (QO6 ganha as combinações).

Camada `contrato`, offline, em `tests/moodle/test_tentativa.py`, com dublê
que registra parâmetros:

- **QF12** a primeira chamada não toca `mod_quiz_start_attempt`: um dublê que
  registre esse nome reprova.
- **QF13** o plano envia `courseids[0]` explícito e `status="all"` literal em
  `get_user_attempts`, com `userid` derivado do token; e `questionarios`
  continua enviando `status="finished"` (QO9 segue). Sobre o parâmetro enviado.
- **QF14** o código muda quando muda cada uma das sete coisas do material, uma
  por vez; e o código do plano de abrir não confirma nenhum plano de
  `entrega.py` para o mesmo estado (o verbo entra).
- **QF15** confirmação com código velho é recusada e a resposta traz o plano
  novo; depois de uma abertura bem sucedida no dublê (a contagem de
  tentativas sobe), repetir o mesmo código é recusado.
- **QF16** as recusas da Camada 5, uma mensagem distinta cada: `attempts`
  ausente; restam zero; tentativa em andamento; fechado; ainda não abriu.
- **QF17** `forcenew` nunca está entre os parâmetros enviados a
  `start_attempt`, em nenhum caminho.
- **QF18** o `attemptid` presente na resposta do dublê (tentativa em
  andamento ou finalizada) não aparece no plano nem em nenhuma saída.
- **QF19** as linhas condicionais do plano: `timelimit` ausente diz "não
  informou se há limite"; `overduehandling` ausente diz "não informou o que
  faz"; `grade` ausente diz "não informado"; `grade == 0` diz "não vale nota";
  `grademethod` "primeira" em ilimitado imprime a linha de atenção (depende da
  decisão 3).
- **QF20** cliente sem elicitação não bloqueia, e a saída distingue "não pude
  perguntar" de "perguntaram e recusaram" (E11 desta família).
- **QF21** erro do cliente sobe sem ser capturado: credencial recusada não vira
  "questionário não encontrado".
- **QF22** forma real: se `fixtures/moodle/quizzes_*.json` e
  `quiz_attempts_all_*.json` existem, toda chave que o plano lê existe nelas;
  se não existem, skip **com o comando de captura na razão**, a exceção
  declarada de 17/09, com o mesmo prazo (fecha quando a captura entrar).
- **QF23** `capacidades`: nos quatro estados de questionário, o texto diz
  `DESLIGADO` ou a classe ligada, nomeia as duas variáveis (constantes), não
  nomeia função do Moodle, não tem palavra de convite, e a versão curta é o
  começo exato da inteira (C1 a C6 ganham a segunda capacidade).
- **QF24** o teto de C7 sobe para 3000 e o pior caso (as três variáveis
  ligadas) cabe.
- **QF25** `diagnostico` ecoa o estado de questionário nos dois caminhos de
  saída, e a tabela por ferramenta não ganha linha de `abrir_questionario`.
- **QF26** `grep` de suíte: nenhuma ocorrência de "não há flag que" nem de
  "não há configuração que" em `usp_mcp/` e `.env.example`; QO20 passa a
  exigir só "não abre" e a ausência de nome bloqueado.

Camada `handshake`, processo de verdade, em
`tests/handshake/test_tentativa_no_fio.py`:

- **QF27** com as três variáveis em "0", `abrir_questionario` não está no
  `tools/list` e a contagem é 11; o `instructions` traz o parágrafo de
  questionário com `DESLIGADO` e as duas variáveis. No **mesmo processo**, como
  G1 e G2.
- **QF28** com `ILIMITADO=1` sozinha: a ferramenta aparece, a contagem é 12, a
  descrição diz "ilimitadas" e o `instructions` diz a classe ligada. O espelho
  com `LIMITADO=1`.
- **QF29** com as três ligadas: 14 ferramentas, `destructiveHint` verdadeiro
  nas três de escrita, `readOnlyHint` nas outras onze.
- **QF30** em todas as combinações, o `instructions` no fio não nomeia função
  do Moodle.

Camada `live`, atrás de `USP_MCP_LIVE=1` **e** de uma das duas variáveis:

- **QF31** o plano de um questionário real bate com o que a página do
  e-Disciplinas mostra (tentativas usadas, tempo, prazo), **sem escrever**.
  Conferência humana, uma vez, registrada no §9.
- Abertura ao vivo **não entra na suíte em fase nenhuma**: um teste que abre
  tentativa de verdade é o acidente que este spec existe para evitar. A
  primeira abertura real é medição do dono, num questionário ilimitado e sem
  nota, e vai para o §9 com a resposta que `start_attempt` devolveu.

## Critério de parada

As trinta e uma passam; a suíte inteira fica verde em **quatro** configurações
(nenhuma variável; só ILIMITADO; só LIMITADO; as três de escrita ligadas) e o
`gate.sh` passa. A contagem de ferramentas do Moodle é 11, 12, 12 e 14 nessas
configurações. Os sete lugares da tabela *Onde a informação vive* mudaram no
mesmo commit que a política. A medição do pré-requisito está em `notas/` com
origem rotulada, **antes** da primeira linha de código, e a decisão está no
§9.

E as quatro decisões pendentes têm escolha registrada pelo dono, no §9, antes
do merge. Um spec com quatro "pendente" não vira código.

## O que precisa ir para o §9

1. Que o §2.2 foi reaberto pela terceira vez, em 18/09, por decisão do dono,
   com a forma dele: duas variáveis, por classe de custo.
2. Que a entrada de 15/09 **errou** ao dizer que o plano de questionário não
   era construível, com a correção nas palavras da seção *A correção*: a API
   sabe dizer; o que muda entre as classes é o custo do engano.
3. Que `mod_quiz_start_attempt` sai do bloqueio permanente (40 para 39) para
   `TENTATIVA_CONFIRMADA`, alcançável só pela variável da classe do
   questionário e confirmação por chamada; que as outras quatro da família
   ficam; e que `USP_MCP_ENTREGA` e `USP_MCP_ALLOW_WRITES` não abrem
   questionário.
4. As quatro decisões pendentes, com a escolha do dono em cada uma e a data.
5. Que a distinção entre as classes depende de `attempts` chegar à conta de
   aluno, o que foi medido em (data) com (resultado), ou que não foi e o
   desenho recusa por classe desconhecida.
6. Que responder é fase própria, com a dimensão escrita aqui, e que ela herda
   as duas variáveis e provavelmente precisa de uma recusa a mais.
7. Que a fraqueza contra um modelo com shell continua conhecida e aceita, e
   que a variável de limitadas é a que gasta o que não volta.
