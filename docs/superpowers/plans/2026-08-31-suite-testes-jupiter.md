# Suíte de testes do Jupiter — plano de implementação

> **Estado, 31/08/2026: EXECUTADO.** As sete tarefas foram cumpridas e, na sequência,
> a Fase 2 foi implementada contra a suíte resultante. O plano fica como registro do
> caminho — inclusive dos quatro achados do §1, que continuam valendo para quem
> escrever a próxima fatia. Handoff da sessão em
> `docs/handoffs/2026-08-31-jupiter-fase-2.md`.

**Goal:** Escrever as 40 funções de teste que especificam a ferramenta `disciplina` do MCP do Jupiter, conforme `docs/superpowers/specs/2026-08-31-testes-jupiter-design.md`.

**Leia o spec primeiro.** Ele é a fonte; este plano é a ordem de execução, o que já foi medido e o que faz um teste mentir. O spec define os 40 testes (T1–T40) e o que cada um trava.

**Este plano não traz o código dos testes de propósito.** Derive cada teste do spec, das fixtures e dos invariantes do §2 do `SPEC1.md`. Se o seu teste divergir do que este plano descreve, investigue antes de ajustar — pode ser que você tenha visto algo que o spec não viu, e nesse caso o spec é que muda, com registro no §9.

---

## 1. Fatos já verificados — não gaste tempo redescobrindo

Quatro coisas foram medidas empiricamente antes deste plano. Todas mudam o que você vai escrever.

**1.1 — pytest não está instalado no Python do sistema.** `python3 -m pytest` devolve `No module named pytest`. Crie um venv, acrescente-o ao `.gitignore`, e declare a dependência em `requirements-dev.txt`.

**1.2 — Módulo ausente aborta a coleta inteira.** Com `usp_mcp` inexistente, o pytest devolve `Interrupted: N errors during collection` e **os testes verdes não rodam** — a saída nem os menciona. Testado nas duas formas. Portanto o plano cria um **esqueleto** de `usp_mcp/jupiter/{dwr,cliente,ferramentas}.py` cujos símbolos levantam `NotImplementedError`. Com ele o vermelho vira contável — na execução real, `56 failed, 10 passed, 2 skipped` (40 funções, 68 casos).

O esqueleto **não é a Fase 2**: ele não decide ferramenta, nome nem formato de saída, e nenhuma função tem corpo. Se você se pegar escrevendo lógica dentro dele, parou de fazer andaime e começou a Fase 2 — o que o §4.10 do `CLAUDE.md` proíbe.

Cuidado conhecido: `__getattr__` de módulo (PEP 562) intercepta também os dunder e quebra `from pacote.modulo import x`. Deixe passar o que começa e termina com `__`.

**1.3 — Varredura de fonte passa espuriamente contra o esqueleto.** Três testes do spec leem o fonte do módulo para provar uma ausência (T12: nada de `eval`; T19: nada de `MOODLE_TOKEN`; T25: a ferramenta não chama o choke point). Contra um arquivo praticamente vazio, os três ficam **verdes verificando nada** — confirmado rodando. Ponha um sentinela no esqueleto e faça toda leitura de fonte recusar-se a rodar enquanto ele estiver lá. Sem isso, três dos 40 testes são decoração.

**1.4 — Os números do custo já estão medidos.** Não os recalcule de cabeça, e não os copie das notas sem conferir contra o que foram medidos — os 11,5× de `notas/jupiter-recon.md` comparam DWR com HTML, e o spec explica por que isso não serve como asserção. O §4.6 do spec tem a tabela válida.

---

## 2. O que é vinculante e o que é sua escolha

**Vinculante — mudar quebra o merge ou contraria dado registrado:**

| | |
|---|---|
| Fixtures da fatia | exatamente as 4 listadas no §4.1 do spec, todas versionadas |
| Layout | `usp_mcp/jupiter/`, `tests/jupiter/`, nenhum `server.py` na raiz do pacote |
| Marcadores | `politica`, `contrato`, `live` — os mesmos da suíte irmã do Moodle |
| Gate de rede | `USP_MCP_LIVE=1`; sem a variável, skip **com motivo escrito** |
| Corpo da requisição DWR | §4.2 de `notas/jupiter-recon.md`, verbatim |
| Números de custo | §4.6 do spec |

**Sua escolha — o spec não decide e você não precisa perguntar:** nomes de função e de parâmetro, forma exata do transporte injetado, como o cache é representado, se a allowlist é dict ou set, organização interna dos arquivos de teste, uso de `parametrize`.

**Nunca leia payload cru na janela.** Use `head -c` e medição (§0 do `CONVENTIONS.md`). A maior fixture da fatia tem 7,1 kB, mas o hábito é o que protege das de 251k tokens.

---

## 3. Tarefas

Cada tarefa termina com commit próprio. Mensagem no formato `test|docs|chore(jupiter): descrição` (§4 do `CONVENTIONS.md`).

### Task 1 — Andaime, esqueleto e guarda de fixture (T1–T3)

**Entrega:** venv + `requirements-dev.txt`, `pytest.ini` com os três marcadores e `--strict-markers`, `.gitignore` atualizado, o esqueleto de `usp_mcp/jupiter/`, o `conftest.py` de `tests/jupiter/`, e `test_fixtures.py`.

O `conftest.py` precisa oferecer: o caminho das fixtures resolvido **a partir da posição do próprio arquivo** (nunca absoluto de máquina), acesso ao texto das 4 fixtures, o helper que recusa ler fonte de esqueleto (§1.3), e um **transporte-gravador** — um transporte falso que devolve fixture e guarda a requisição que teria saído. Ele é o que torna T13–T19 possíveis; sem ele, corpo DWR malformado passa despercebido, porque o Jupiter responde 200 de qualquer jeito.

**Os três testes:**

| Teste | Tem que estabelecer | Falso-verde a evitar |
|---|---|---|
| T1 | cada fixture da fatia existe e não está vazia | pular quando falta, em vez de falhar |
| T2 | o caminho das fixtures não contém caminho absoluto de máquina | asserção sobre uma constante em vez do fonte real |
| T3 | nenhuma fixture da fatia está no `.gitignore` | comparar por glob em vez de perguntar ao git |

T1 e T3 vêm da suíte irmã do Moodle. O raciocínio é dela: um skip por fixture ausente deixa a suíte verde noutra máquina **sem ter testado nada** — Invariante 6 aplicado à própria suíte.

**Aceite:** T1–T3 passam. Depois, **remova temporariamente uma fixture e confirme que falham**, com a mensagem certa. Uma verificação que não pode falhar não verifica nada (§6 do `CONVENTIONS.md`). Devolva a fixture antes de commitar.

---

### Task 2 — Decodificação do envelope DWR (T4–T12)

**Entrega:** `tests/jupiter/test_dwr.py`, marcador `contrato`.

Leia o §4.3 e o §4.5 de `notas/jupiter-recon.md` antes: eles descrevem o envelope e a forma do erro.

| Teste | Tem que estabelecer |
|---|---|
| T4 | `handleCallback` com objeto vira mapa de 26 campos, nas duas amostras de disciplina |
| T5 | `handleCallback` com array vira lista — **inclusive quando tem 1 elemento só** |
| T6 | `handleException` levanta; nunca devolve vazio, nunca devolve sucesso |
| T7 | o erro exposto não carrega `stackTrace`, `javaClassName` nem nome de classe Java |
| T8 | a mensagem do erro é a `localizedMessage`, em português, íntegra |
| T9 | escapes resolvidos: `\uXXXX`, `\/`, `null` distinto da string `"null"`, `\n` preservado |
| T10 | envelope truncado (sem o marcador de fim) é erro explícito, não parse parcial |
| T11 | corpo HTML — o 302 para login que o balanceador devolve — é erro explícito |
| T12 | o decoder **lê sem executar**: payload com efeito colateral não dispara nada |

**T5 é a armadilha:** a fixture de pré-requisito tem exatamente 1 elemento. Um decoder que "simplifique" lista de 1 em objeto quebra a ferramenta em silêncio.

**T6 é o Invariante 6 no seu ponto mais afiado:** o Jupiter devolve **HTTP 200 no erro**. Quem discriminar por status code produz exatamente o silêncio que o invariante proíbe.

**T12** precisa de duas coisas: um teste comportamental (o efeito colateral não aconteceu) e a varredura de fonte do §1.3 — que só significa algo depois que o esqueleto sair.

**Aceite:** falham por `NotImplementedError`. Se aparecer `SyntaxError`, `fixture not found` ou erro de coleta, o teste está quebrado, não vermelho.

**Armadilha, custou uma volta:** não construa o objeto sob teste dentro de uma fixture do pytest. O `NotImplementedError` no setup vira `ERROR` em vez de `FAILED` — 23 casos assim — e o vermelho deixa de ser contável, que era todo o motivo do esqueleto. A fixture entrega o insumo; o objeto nasce no corpo do teste.

---

### Task 3 — Cliente, cache e allowlist (T13–T25)

**Entrega:** `tests/jupiter/test_cliente.py`, marcadores `contrato` e `politica` conforme o §4.3/§4.4 do spec.

A allowlist mora aqui, e não em arquivo próprio, porque a allowlist **é** a fronteira do cliente.

| Teste | Tem que estabelecer |
|---|---|
| T13 | o corpo da requisição bate com o §4.2 do recon, linha a linha |
| T14 | objeto serializado por referência: cada `c0-eN` em linha própria, o param referencia |
| T15 | valor string é percent-encoded — sem espaço cru na linha |
| T16 | roteamento: `obter` e `listar` vão para URLs diferentes |
| T17 | stateless: nenhum cookie, `scriptSessionId` fixo, **nenhum handshake antes** |
| T18 | `User-Agent` identifica o projeto e traz contato |
| T19 | o cliente não lê env de segredo e não emite `Authorization` nem `Cookie` |
| T20 | duas perguntas iguais fazem **uma** requisição |
| T21 | o TTL segue a taxa de mudança do dado: 29 dias não expira, um semestre expira |
| T22 | as requisições não se sobrepõem |
| T23 | a superfície está travada em duas consultas; os métodos genéricos são negados |
| T24 | o que é negado **continua negado** com `USP_MCP_ALLOW_WRITES=1` |
| T25 | a ferramenta não aceita nome de consulta como argumento |

**Sobre T13–T16:** é a razão de o cliente ter camada própria. O DWR responde **200 para corpo malformado**, então erro de serialização vira campo vazio, não falha. Nenhuma outra camada da suíte pega isso.

**Sobre T15:** o charset do encode **não foi verificado** na Fase 1 (§8 do recon). Não asserte sobre bytes de acento; asserte sobre o que é observável.

**Sobre T19:** o Jupiter não usa credencial nenhuma. O teste existe para impedir que o servidor público do §6 do `SPEC1.md` **vire portador de credencial num refactor futuro**.

**Sobre T21:** prefira um relógio injetado a asserir sobre a constante do TTL. Uma asserção sobre a constante testa o valor; uma sobre o comportamento testa a regra.

**Sobre T23–T25:** é o Invariante 2. `executarBatch` é o análogo exato do `tool_mobile_call_external_functions` registrado no §9 de 31/08 — executor genérico que anula qualquer filtro por nome de consulta. T25 é a mesma lição do outro lado: uma ferramenta que receba o nome da consulta deixa de ter superfície, e a allowlist inteira vira decoração. Os nomes dos métodos genéricos do bean estão no §4.1 do recon.

**Aceite:** falham por `NotImplementedError`.

---

### Task 4 — A ferramenta (T26–T33)

**Entrega:** `tests/jupiter/test_disciplina.py`, marcador `contrato`.

| Teste | Tem que estabelecer |
|---|---|
| T26 | a sigla é normalizada — caixa e espaço não mudam a resposta |
| T27 | a carga horária é **calculada**, nunca lida do campo |
| T28 | ementa e conteúdo programático vêm de campos diferentes e não estão trocados |
| T29 | campos vazios e espanhol são omitidos; inglês só sob pedido |
| T30 | **sem curso**, a ferramenta declara que não consultou o pré-requisito |
| T31 | **com curso**, são duas chamadas e o pré-requisito volta estruturado |
| T32 | erro da USP chega em português, sem stack trace |
| T33 | a discrepância `codcur` 3032 vs 3033 é declarada, não resolvida por invenção |

**T27 é a pegadinha mais cara da fatia.** O campo de carga horária vem `"0"` nas duas amostras; a carga real sai de uma conta sobre os créditos, e o §4.3 do recon tem a fórmula. Quem ler o campo devolve **zero hora com cara de resposta certa** — o silêncio do Invariante 6 sem erro nenhum no caminho. O teste tem que travar as duas coisas: o valor calculado e o fato de o campo cru não ser usado.

**T30 é o Invariante 7.** O pré-requisito é condicional ao curso (§5.2 do recon). Uma ferramenta que responda sem curso está omitindo, e omitir calado é o que o invariante proíbe. O teste precisa provar três coisas: que não houve segunda chamada, que a saída diz o que falta, e que ela **não afirma** "sem pré-requisito".

**T31 tem uma limitação que você deve declarar no próprio teste:** a Fase 1 nunca amostrou disciplina e pré-requisito da *mesma* disciplina. O que está sob teste é a composição de duas chamadas, não o pareamento — que continua não verificado (§8 do recon). Escreva isso no código; não deixe parecer cobertura que não existe.

**T33** fecha um "não verificado" do §8 do recon sem fingir que o fechou: o comportamento travado é usar o código recebido sem traduzir **e avisar**.

**Aceite:** falham por `NotImplementedError`.

---

### Task 5 — Custo (T34–T37)

**Entrega:** `tests/jupiter/test_custo.py`, marcador `contrato`.

Leia o §4.6 do spec inteiro antes de escrever. Ele registra uma asserção que foi **desenhada e descartada por medição**, e o motivo importa para você não reintroduzi-la.

| Teste | Tem que estabelecer |
|---|---|
| T34 | teto absoluto por amostra, com a folga declarada no próprio teste |
| T35 | o núcleo estruturado da saída fica na faixa medida |
| T36 | **categórico:** o conjunto de chaves da saída é exatamente o declarado |
| T37 | a resposta de erro projetada nunca custa mais que a de sucesso |

**T36 é o que de fato trava regressão.** T34 e T35 são numéricos e envelhecem; a asserção categórica não. O spec explica por quê: bytes por campo varia 68% entre as duas amostras, porque 90% do peso é texto livre e o texto livre **é a resposta**. O que a ferramenta controla é o *conjunto de campos*.

**T37 continua numérico e continua valendo:** descartar o stack trace é 116× (~1.978 → ~17 tokens). O erro cru custa mais que duas disciplinas inteiras **e é a resposta errada**.

**Aceite:** falham por `NotImplementedError`.

---

### Task 6 — Canário ao vivo (T38–T40)

**Entrega:** `tests/jupiter/test_live.py`, marcador `live`.

| Teste | Tem que estabelecer |
|---|---|
| T38 | a resposta real ainda tem **as mesmas chaves** da fixture |
| T39 | sigla inexistente ainda devolve erro no corpo com HTTP 200 |
| T40 | sem a variável de ambiente, o skip diz o motivo por escrito |

**Duas requisições reais por execução, no máximo, escolhidas à mão.** Nenhum laço, nenhuma enumeração de sigla: o §7 do recon pede a gentileza, e o §8 registra que 26 requisições sem 429 **não provam** que não haja rate limit.

**T38 compara chaves, nunca valores** — valor muda por semestre sem que nada tenha quebrado.

**T40 é o teste do próprio gate.** A diferença entre "não rodou" e "não rodou, e aqui está por quê" é o Invariante 6 aplicado à suíte; o motivo tem que citar a variável e o host.

**Aceite:** `2 skipped, 1 passed`. **Não** falham, ao contrário do resto da suíte: o esqueleto importa sem erro e só o *acesso a atributo* levanta, então um teste pulado nunca chega lá. T40 passa porque só inspeciona a mensagem do skip.

---

### Task 7 — Fechar os TODO de gate e registrar a decisão

**Entrega:** `docs/agents/CONVENTIONS.md` §3 e §4, `CLAUDE.md:52`, e um registro datado no §9 do `SPEC1.md`.

Os três `<TODO>` de gate do repo existem porque não havia código. Agora há suíte, e o gate passa a ser rodar pytest.

1. Rode a suíte inteira e **capture o número real** de verdes, vermelhos e pulados. Não escreva de memória: o §9 do `SPEC1.md` tem um registro chamado "número fabricado, removido".
2. `CONVENTIONS.md` §4 — troque o `<TODO>` pelo comando do gate, dizendo que `live` pula sem a variável e que teste que falha por erro de coleta está quebrado, não vermelho.
3. `CONVENTIONS.md` §3 — troque o `<TODO>` pela estrutura que agora existe, incluindo por que o `server.py` mora no subpacote (§6 do `SPEC1.md`: entrypoint local com credencial de um lado, servidor público cacheável do outro).
4. `CLAUDE.md:52` — mesmo comando de gate.
5. `SPEC1.md` §9 — registro datado. Precisa conter: o escopo de fatia vertical e por quê; a asserção de razão descartada por medição, com os números; o custo do stack trace; o gate passando a existir; os acordos com a suíte do Moodle; e **o que continua aberto** (discrepância `codcur`, pareamento disciplina↔requisito nunca amostrado, Invariante 8).
6. Rode o gate de novo e confira que bate com o que você registrou. Se não bater, **corrija o registro, nunca o teste**.

---

## 4. Definição de pronto

1. A suíte roda em máquina limpa, sem rede: **56 falhas, 10 verdes, 2 skips**. Confira o motivo de cada falha com `--tb=line`: todas `NotImplementedError`, nenhuma por erro de coleta, erro de setup ou fixture ausente. Contar ocorrências de `NotImplementedError` na saída inteira **não** verifica isso — as linhas `FAILED` vêm truncadas pela largura do terminal e o traceback infla a contagem.
2. Sem a variável de ambiente, os testes `live` pulam com motivo escrito.
3. Nenhuma varredura de fonte está verde: o helper do §1.3 recusa o esqueleto.
4. Nenhum segredo e nenhum dado pessoal entrou no git; o venv está ignorado.
5. Os três `<TODO>` de gate sumiram e o §9 do `SPEC1.md` tem o registro, com números capturados de uma execução real.

**O que este plano não entrega, de propósito:** a implementação. Ela é a Fase 2, e o §4.10 do `CLAUDE.md` é explícito — Fase 2 não começa por conveniência. A suíte vermelha é o entregável, e é ela que a Fase 2 vai ter que satisfazer.
