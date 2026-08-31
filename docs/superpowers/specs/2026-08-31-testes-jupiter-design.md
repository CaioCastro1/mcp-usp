# Suíte de testes do Jupiter — desenho

> Data: 31/08/2026. Autoridade continua sendo o `SPEC1.md`; este documento é o
> desenho de uma suíte, não um fato novo sobre a USP.
> Escrito em par com a suíte do Moodle (`moodle-mcp-tests-e77611`), que está em
> desenho simultâneo. Os acordos de estrutura entre as duas estão no §7.

## 1. O problema

Não existe servidor MCP. A Fase 2 não começou. Escrever testes antes da
implementação é a escolha deliberada: **os testes são a especificação executável da
Fase 2**, e falham hoje por `NotImplementedError`.

Isso resolve um risco concreto do projeto. O §5 do `SPEC1.md` manda derivar a
ferramenta da pergunta do dono, e o §7 registra a tentação oposta — uma tabela de 8
ferramentas derivada do que a API oferece. Um teste escrito antes trava a pergunta;
código escrito antes trava a API.

## 2. Escopo: uma fatia vertical

A suíte cobre **uma pergunta**, ponta a ponta:

> *Essa disciplina tem quantos créditos e qual o pré-requisito?*

É literalmente a pergunta candidata do §5, e é a única do Jupiter que o §9 de
31/08 já sustentou com dado: duas chamadas DWR, custo medido, dado estático com TTL
semestral.

Uma ferramenta, `disciplina(sigla, curso=None)`.

**Fora desta fatia, deliberadamente:**

- **Grade curricular** e **navegação unidade→curso** — decididas como úteis, mas
  viram fatias seguintes. Cobrir as três de uma vez deixaria ~30 testes vermelhos
  por semanas: TDD no nome, waterfall no comportamento.
- **Horário, sala e vagas da turma** — o §9 de 31/08 registrou "não prometer sem
  manutenção semestral explícita". Há uma amostra só de `obterTurma`, e é justamente
  a parte frágil. A fixture correspondente está no `.gitignore`; a suíte não pode
  depender dela (§4, T3).

Consequência aceita: nesta fatia o parâmetro `curso` é o par `codcur`/`codhab` cru.
Resolver "Poli elétrica" para esse par é a fatia de navegação, e o teste T22 existe
para impedir que a ferramenta finja que já resolve.

## 3. Arquitetura

```
usp_mcp/jupiter/dwr.py          # decodificar o envelope; serializar o corpo
usp_mcp/jupiter/cliente.py      # transporte, allowlist, cache
usp_mcp/jupiter/ferramentas.py  # disciplina(sigla, curso=None)

tests/jupiter/{conftest,test_fixtures,test_dwr,test_cliente,test_disciplina,
               test_custo,test_live}.py
pytest.ini
```

**Runtime: Python + pytest.** O repo já roda `python3` (`scripts/reduzir.py`, o bloco
embutido no `capture.sh`) e não tem gerenciador de pacote nenhum. `pytest` é a única
dependência nova. Fecha o `<TODO>` do §3 do `CONVENTIONS.md`, e `pytest -m "not live"`
vira o gate do §4.

**Três marcadores, ortogonais ao arquivo** (mesmo eixo da suíte do Moodle):

| Marcador | O que roda | Rede |
|---|---|---|
| `politica` | invariantes que não dependem de resposta nenhuma | não |
| `contrato` | forma da resposta e da requisição, contra fixture | não |
| `live` | canário contra `uspdigital.usp.br` | sim, opt-in |

`live` exige `USP_MCP_LIVE=1`. **Sem a variável o teste dá skip com o motivo escrito**,
em vez de sumir da coleta — a diferença entre "não rodou" e "não rodou, e aqui está
por quê" é o Invariante 6 aplicado à própria suíte. O §1.1 do `SPEC1.md` garante que
o sandbox não alcança a USP; `live` só roda no terminal do dono.

**Transporte injetado.** O cliente recebe a função de transporte como parâmetro. Nos
testes ela lê fixture e **registra a requisição que teria sido feita** — é o que
torna T13–T19 possíveis.

**Esqueleto de pacote, não implementação.** `usp_mcp/jupiter/{dwr,cliente,ferramentas}.py`
existem e cada símbolo levanta `NotImplementedError` apontando para o teste que o define.
Isso não é Fase 2 — o esqueleto não decide ferramenta, nome nem formato de saída; é
infraestrutura de teste, e existe por uma razão medida: com o módulo **ausente**, o pytest
aborta a coleta (`Interrupted: N errors during collection`) e **os testes verdes nem
rodam**. Verificado. Com o esqueleto, o vermelho vira contável e a guarda de fixture
sobrevive.

Efeito colateral que o esqueleto cria e que a suíte tem que neutralizar: **varredura de
fonte passa espuriamente contra arquivo vazio.** T12, T19 e T25 leem o fonte do módulo;
contra o esqueleto elas ficariam verdes verificando nada. Por isso toda leitura de fonte
passa por `fonte_de(modulo)`, que falha enquanto o sentinela `ESQUELETO-FASE2` estiver
lá.

## 4. Os testes

### 4.1 Fixtures — `politica`

| # | Teste |
|---|---|
| T1 | As 4 fixtures da fatia existem e não estão vazias. **Ausência é falha, não skip.** |
| T2 | O caminho das fixtures é resolvido a partir do repo, nunca absoluto de máquina. |
| T3 | Nenhuma fixture da fatia casa com `fixtures/jupiter/html-obterTurma-*` — a suíte não depende de arquivo que o `.gitignore` exclui. |

T1 e T3 vêm da suíte do Moodle. O raciocínio é dela e vale igual aqui: um skip por
fixture ausente passa verde noutra máquina **sem ter testado nada**.

Fixtures da fatia: `dwr-pubObterDisciplina-PSI3323.txt`,
`dwr-pubObterDisciplina-PTC3314.txt`, `dwr-pubListarRequisitoDisciplina-MAT2454.txt`,
`dwr-pubObterDisciplina-ERRO-sigla-inexistente.txt`.

### 4.2 Decoder DWR — `contrato`

| # | Teste |
|---|---|
| T4 | `handleCallback` com objeto → `dict` de 26 chaves (PSI3323 e PTC3314). |
| T5 | `handleCallback` com array → `list`. **Array de 1 elemento não colapsa em dict** (a fixture de pré-requisito tem exatamente 1 — é a armadilha). |
| T6 | `handleException` levanta `JupiterErro`. Nunca lista vazia, nunca `None`, nunca sucesso. |
| T7 | O erro exposto **não** carrega `stackTrace` nem `javaClassName`. |
| T8 | A mensagem do erro é a `localizedMessage` em português, íntegra. |
| T9 | Escapes: `á`→`á`, `\/`→`/`, `null`→`None`, `\n` preservado dentro do texto. |
| T10 | Envelope sem `//#DWR-END#` → erro explícito, nunca parse parcial. |
| T11 | Corpo que é HTML (o 302 para login que o balanceador devolve) → erro explícito. |
| T12 | **O decoder não executa código.** Fixture com efeito colateral injetado no literal não dispara nada: sem `eval`, sem `exec`. |

T6 é o Invariante 6 no seu ponto mais afiado: o Jupiter devolve **HTTP 200 no erro**.
Quem checar status code produz exatamente o silêncio proibido.

### 4.3 Cliente — `contrato` e `politica`

| # | Teste | Marcador |
|---|---|---|
| T13 | O corpo de `obter_disciplina("PSI3323")` bate linha a linha com o §4.2 do recon. | contrato |
| T14 | Cada `c0-eN` em linha própria; `c0-param1` referencia por `prop:reference:c0-eN`. | contrato |
| T15 | Valor string é percent-encoded. | contrato |
| T16 | Roteamento: `obter`→`ControlePublicoDWR.obter.dwr`, `listar`→`.listar.dwr`. | contrato |
| T17 | **Stateless:** nenhum cookie enviado, `scriptSessionId` constante, nenhum handshake `__System.generateId`. | contrato |
| T18 | `User-Agent` identificável com contato. | politica |
| T19 | **Sem credencial:** o cliente não lê env de segredo e não emite `Authorization` nem `Cookie`. | politica |
| T20 | Duas chamadas iguais → **uma** requisição HTTP. | contrato |
| T21 | TTL colado na taxa de mudança do dado (semestral), não na frequência da pergunta. | politica |
| T22 | Concorrência 1 — as requisições não saem em paralelo. | contrato |

T13–T16 são a razão de o cliente ter camada própria: o DWR responde **200 para corpo
malformado**, então um erro de serialização aparece como campo vazio, não como falha.
Nenhuma outra camada pega isso.

T18, T20–T22 são o Invariante 5 e a higiene recomendada no §9 do recon — nada disso
está implementado, e é justamente por isso que vira teste.

T19 é o Invariante 3 na forma que o Jupiter permite. O Jupiter não usa credencial
nenhuma; o teste existe para garantir que o servidor público do §6 **não vire portador
de credencial num refactor futuro**.

### 4.4 Allowlist — `politica`

| # | Teste |
|---|---|
| T23 | Tabela parametrizada: só `pubObterDisciplina` e `pubListarRequisitoDisciplina` passam. `executarBatch`, `obterArquivo`, `obterRelatorio`, `obterCsv`, `obterPdf`, `obterZip`, `obterWebdoc`, `obterProgresso` são negados. |
| T24 | Negado **continua negado** com `USP_MCP_ALLOW_WRITES=1`. |
| T25 | Nome de consulta **nunca** vem de argumento de ferramenta. |

`executarBatch` é o análogo exato do `tool_mobile_call_external_functions` registrado
no §9 de 31/08: um executor genérico que anula qualquer filtro por nome de consulta.
T25 é a mesma lição — uma ferramenta que aceite o nome da consulta como parâmetro
deixa de ter superfície, e a allowlist inteira vira decoração.

A superfície desta fatia é travada em **duas** consultas. Acrescentar uma terceira
sem passar por decisão registrada quebra T23.

### 4.5 A ferramenta — `contrato`

| # | Teste |
|---|---|
| T26 | Normalização: `psi3323`, `PSI 3323`, ` psi 3323 ` → `PSI3323`. |
| T27 | **Carga horária é calculada** — `creaul*15 + cretrb*30` = 45 h (PSI3323) e 60 h (PTC3314). O campo `cgahoreto` vem `"0"` nas duas e nunca é usado. |
| T28 | Ementa é `pgmrsudis`; `pgmdis` é Conteúdo Programático. Inverter é o erro provável. |
| T29 | Os 5 campos vazios e as versões em espanhol são omitidos; inglês só sob pedido. |
| T30 | **Sem `curso`:** a saída declara que o pré-requisito depende do curso e não foi consultado. Não devolve "sem pré-requisito". |
| T31 | **Com `curso`:** duas chamadas, pré-requisito estruturado, `tipreq:"PR"` legível. |
| T32 | Erro da USP chega em português, sem stack trace. |
| T33 | A discrepância `codcur` 3032 (HTML) vs 3033 (DWR) tem comportamento travado em teste — documentada, não resolvida por invenção. |

T27 é a pegadinha mais cara da fatia: quem ler `cgahoreto` devolve **zero hora com
cara de resposta certa**. É o silêncio do Invariante 6 sem erro nenhum no caminho.

T30 é o Invariante 7. O pré-requisito é condicional ao curso (§5.2 do recon) — uma
ferramenta que responda sem `curso` está omitindo, e omitir calado é o que o
invariante proíbe.

T33 fecha um item de "não verificado" do §8 do recon sem fingir que o fechou.

### 4.6 Custo — `contrato`

| # | Teste |
|---|---|
| T34 | Teto absoluto por amostra, com folga declarada no próprio teste. |
| T35 | Custo do **núcleo estruturado da saída** dentro de 140–210 B. |
| T36 | **Categórico:** o conjunto de chaves da saída é exatamente o declarado — nenhum `*epa`, nenhum `*igl` sem pedido, nenhum `stackTrace`, nada fora da lista. |
| T37 | A resposta de erro projetada nunca custa mais que a de sucesso. |

Medido em 31/08, duas amostras (script em scratchpad, não versionado):

| Recorte | PSI3323 | PTC3314 |
|---|---:|---:|
| Objeto DWR inteiro (26 campos) | ~864 tok | ~1.619 tok |
| Só português, sem campos vazios | ~536 | ~903 |
| Núcleo: créditos + carga calculada, sem texto livre | ~101 | ~129 |
| Saída projetada da ferramenta (14 campos) | 2.148 B | 3.615 B |
| Núcleo estruturado **da saída** (7 campos) | 179 B | 164 B |

| Erro (`handleException`) | tokens |
|---|---:|
| Objeto inteiro (46 frames) | ~1.978 |
| Só `localizedMessage` | ~17 |

**Uma asserção de razão de redução foi desenhada e descartada por medição.** Ela vinha
de uma correção proposta à suíte do Moodle, e ao aplicá-la aqui não sobreviveu:

| | PSI3323 | PTC3314 | spread |
|---|---:|---:|---:|
| Razão vs cru | 1,73 | 1,98 | 14% |
| Bytes por campo | 126 B | 212 B | **68%** |
| Núcleo estruturado (nomes DWR) | 153 B | 138 B | 12% |
| Núcleo estruturado (nomes da saída) | 179 B | 164 B | **9%** |
| Texto livre | 1.937 B | 3.419 B | **77%** |

Duas conclusões, e as duas mudam o teste:

1. **A razão de redução do Jupiter é ~1,8×, não 11,5×.** Os 11,5× do recon comparam
   DWR com HTML. Contra o próprio DWR quase não há o que reduzir — o payload **é** a
   resposta. Uma asserção de razão ali mediria uma redução que não existe.
2. **Bytes por campo varia 68%** porque 90% do peso é texto livre (ementa, programa,
   bibliografia), de tamanho intrínseco à disciplina. O que a ferramenta controla é o
   *conjunto de campos*, não o tamanho de cada um.

Daí T35 e T36: o número fica no núcleo estruturado da saída, que é estável em 9%, e a trava
de regressão é **categórica**. É a mesma lição que a suíte do Moodle tirou do dado
dela — o que trava regressão é "nenhum objeto `course` sobrevive à projeção", não uma
razão — chegando ao mesmo lugar por caminhos opostos: lá o numerador é ruidoso, aqui
não há redução a medir.

T37 continua numérico e continua valendo: descartar o `stackTrace` é **116×**
(1.978 → 17 tokens). Um erro cru custa mais que duas disciplinas inteiras **e é a
resposta errada** — inversão fácil de introduzir e invisível em teste de forma.

### 4.7 Canário ao vivo — `live`

| # | Teste |
|---|---|
| T38 | `pubObterDisciplina` real ainda devolve `handleCallback` com **as mesmas chaves** da fixture — diff de chaves, nunca de valores. |
| T39 | Sigla inexistente ainda devolve `handleException` com HTTP 200. |
| T40 | Sem `USP_MCP_LIVE=1`, o skip diz o motivo por escrito. |

**Duas requisições reais por execução, no máximo**, escolhidas à mão. Nenhum laço,
nenhuma enumeração de sigla — a Regra de Ouro do §3.1 foi escrita para o Moodle, mas
o §7 do recon pede a mesma gentileza aqui, e o rate limit do Jupiter continua sem
evidência (§8 do recon: 26 requisições sem 429 **não provam** que não exista).

T38 compara chaves porque valor muda por semestre sem que nada tenha quebrado.

**Total: 40 funções de teste, 68 casos** (parametrização). Executado: **56 falham, 10
passam, 2 pulam**. As 56 falhas são todas `NotImplementedError`. Os verdes são a guarda
de fixture (9 casos) e T40, que testa o próprio gate de rede.

## 5. Invariantes cobertos

| Invariante | Testes |
|---|---|
| 1 — read-only por padrão | T23, T24, T25 |
| 2 — allowlist, nunca denylist | T23, T24, T25 |
| 3 — nenhum segredo | T19 |
| 5 — não martelar a USP | T18, T20, T21, T22, e o teto de 2 requisições em `live` |
| 6 — erro legível vence silêncio | T6, T8, T10, T11, T27, T32, e T1/T3 aplicados à própria suíte |
| 7 — sem limite silencioso | T29, T30 |

Invariante 4 (credencial não sai da máquina) não tem teste porque o Jupiter não tem
credencial — T19 é o que o impede de ganhar uma. Invariante 8 (termos de uso) não é
testável em código; continua aberto no §9 do recon.

## 6. O que este desenho não faz

- Não testa grade curricular, navegação nem horário de turma.
- Não decide o transporte MCP nem o formato exato de saída da ferramenta além do que
  T26–T33 exigem. O §6 do `SPEC1.md` continua aberto nesses pontos.
- Não resolve a discrepância `codcur` 3032/3033 — T33 trava o comportamento e mantém
  a questão aberta.
- Não mede rate limit. `live` faz duas requisições justamente para não virar a sonda
  que responderia essa pergunta por acidente.

## 7. Acordos com a suíte do Moodle

Fechados por troca direta entre as duas sessões, para não colidirem no merge:

| Item | Acordo |
|---|---|
| Runtime | Python + pytest nas duas (convergimos sem combinar) |
| Testes | `tests/jupiter/` e `tests/moodle/`, simétricos |
| Pacote | `usp_mcp/jupiter/server.py` e `usp_mcp/moodle/server.py`; **raiz do pacote sem server** — é o §6 do `SPEC1.md` virando diretório |
| `cliente.py` | mesmo nome para a mesma coisa: transporte + allowlist na fronteira |
| Marcador de rede | `@pytest.mark.live` + `USP_MCP_LIVE=1`, com skip explicado. Adotado o mecanismo do Moodle |
| Eixos | `politica` / `contrato` / `live` nas duas |

Divergência deliberada: a suíte do Moodle precisa de `scripts/higienizar.py` para
versionar fixture sem dado pessoal (§3.3). O Jupiter não precisa — o dado é público e
já está no git. Em compensação, a suíte do Moodle não cobre o Invariante 5, porque o
dado dela é diário; a daqui cobre, porque ementa é semestral.

Uma assimetria que vale registrar, porque decide quanto cada suíte pode afirmar: a
Fase 1 capturou **uma fixture de erro real do Jupiter**
(`dwr-pubObterDisciplina-ERRO-sigla-inexistente.txt`), e nenhuma do Moodle. T6–T8
asseram contra payload observado; os testes de erro equivalentes na suíte do Moodle
só podem asserir o contrato da camada dela, nunca a forma do erro do Moodle, que
continua não verificada. Capturar um `invalidtoken` real lá é barato e seguro (token
propositalmente inválido, sem tocar na conta) e está no backlog dela.

## 8. Definição de pronto

1. `pytest` roda em máquina limpa, sem rede, e reporta **56 falhas, 10 verdes e 2 skips**
   — as falhas todas por `NotImplementedError`, nenhuma por erro de coleta, erro de setup
   ou fixture ausente. Um teste que falha pelo motivo errado não verifica nada (§6 do
   `CONVENTIONS.md`), e a checagem tem que ser motivo a motivo (`--tb=line`): contar
   ocorrências no traceback não verifica coisa nenhuma.
2. `pytest -m live` sem `USP_MCP_LIVE=1` dá skip com motivo escrito.
2b. Nenhuma varredura de fonte está verde: `fonte_de()` recusa o esqueleto.
3. Nenhum segredo e nenhum dado pessoal novo entrou no git.
4. Ao virar código, o §3 e o §4 do `CONVENTIONS.md` e o §3 do `CLAUDE.md` perdem seus
   `<TODO>`: a estrutura passa a existir e `pytest -m "not live"` é o gate.
