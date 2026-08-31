# Fase 2 do RUCard — desenho da fatia `bandejao`

> **Estado, 31/08/2026: SATISFEITO.** A fatia foi implementada contra esta suíte e os
> 80 testes ficaram verdes (R1–R44 mais desdobramentos), com a camada `live` rodada à
> parte. Leia as seções abaixo como o *desenho*, não como o estado. Duas coisas mudaram
> em relação ao que está escrito aqui, e mudaram por medição: a razão de redução medida
> é **11,8x** (o §4.6 previa "grande" sem número), e a distinção de situações virou
> **três** e não duas — `nao_serve`, `fechado` e `sem_cardapio_publicado` —, porque
> "fechado hoje" só é a informação certa quando existe horário publicado para aquele
> dia. E um teste não previsto aqui nasceu da revisão da implementação: **R27b** — um
> RU que não publicou o dia pedido enquanto os outros publicaram desaparecia da
> resposta sem uma palavra, que é a forma mais difícil de notar de um limite
> silencioso (Invariante 7). Ele exigiu uma segunda fixture pareada
> (`menu_9_semana_31-08.json`). O registro do que mudou está no §9 do `SPEC1.md`,
> entrada "Fase 2 do RUCard implementada contra a suíte".

> Data: 31/08/2026. Autoridade continua sendo o `SPEC1.md`; este documento é o
> desenho de uma fatia vertical e da suíte que a especifica.
> Escrito depois das trilhas do Moodle e do Jupiter, e **segue os moldes delas** de
> propósito: mesma separação `politica`/`cliente`/`ferramentas`/`server`, mesmas três
> camadas de teste (`politica`, `contrato`, `live`), mesmo padrão de erro legível.

## 1. O problema

O RUCard é o único dos três sistemas em que a Fase 1 fechou (§9, 27/08/2026) e a
Fase 2 nunca começou. O que existe é fixture, medição e um `curl` no §8. A pergunta
do §5 do `SPEC1.md` está lá desde o começo:

> *O que tem no bandejão hoje, e onde vale a pena almoçar?*

É a única pergunta do §5 que não depende de credencial pessoal nenhuma, e é a que o
§6 já decidiu que **pode** morar num servidor hospedado — porque a hash do RUCard é
compartilhada, embutida no app oficial, e não identifica ninguém.

Três coisas herdadas da Fase 1 tornam esta fatia menos trivial do que "buscar JSON":

1. **A resposta é a semana inteira, e a pergunta é de um dia.** ~1/7 do payload
   responde. Sem projeção, "hoje nos 4 RUs" custa ~3.000 tokens crus para 8
   refeições.
2. **`/menu` isolado mente por omissão.** O RU 7 devolve os 7 jantares `FECHADO`, e
   isolado parece um RU quebrado — na verdade ele *nunca* serve jantar. A distinção
   só existe cruzando com `workinghours` de `/restaurants` (§1.2).
3. **`/restaurants` é a resposta mais cara do projeto** (27.661 B, ~6.900 tokens) e a
   mais estática: medida byte-idêntica em 27/08 e 31/08. É tabela de apoio, não
   resposta — devolvê-la crua é desperdício puro.

## 2. Medição de 31/08/2026 que sustenta o desenho

Segunda captura, quatro dias depois da Fase 1, do terminal do dono (dado público, sem
credencial pessoal — a regra 9 do `CLAUDE.md` manda medir antes de afirmar):

| Fato | Medida |
|---|---|
| `/menu/{6,7,8,9}` | HTTP 200; 2.928 / 2.303 / 3.084 / 3.624 B |
| Semana devolvida | **31/08→06/09**, na segunda 31/08 às 19:22 (-03) |
| Semana da Fase 1 | 24/08→30/08, capturada em 27/08 |
| `/restaurants` | 27.661 B, **byte-idêntico** ao de 27/08 |
| `GET /menu/6` | HTTP 500, `text/html`, 3.240 B de HTML do Tomcat |
| `"Fechado"` × `"FECHADO"` | 6 capitalizado; 7, 8 e 9 em caixa alta — estável nas duas semanas |
| HTML ou ` - ` no `menu` | zero em 2 semanas × 7 dias × 2 refeições × 4 RUs |

Duas consequências de desenho saem daí, e nenhuma delas era opinião:

- **A semana vira na segunda, ou antes dela.** A questão aberta da nota da Fase 1
  ("a semana vira na segunda ou no domingo, e a que horas?") continua sem o instante
  exato, e é por isso que o cache **não** confia só em TTL: ele valida se a data
  pedida está na semana que o payload devolveu, e refaz a chamada se não estiver
  (§4.3, R14–R16). TTL protege a USP; a validação protege a resposta.
- **`/restaurants` merece TTL longo e `/menu` não.** Dois TTLs, não um.

## 3. Escopo: uma fatia vertical

Uma ferramenta, `bandejao(dia, refeicao, restaurantes)`, sobre os **4 RUs da Cidade
Universitária** (6 CENTRAL, 7 PUSP-CB, 8 FÍSICA, 9 QUÍMICAS) — o recorte que o §1.2
registra como decisão do dono.

**Fora desta fatia, deliberadamente:**

- **Os outros 14 RUs.** Existem, e a allowlist os nega com motivo legível. Crescer é
  decisão de §9, não conveniência (mesmo tratamento que a allowlist do Jupiter).
- **Histórico.** Não há parâmetro de data na API: só semana corrente. Persistir por
  conta própria é outro escopo, e prometer "o que teve semana passada" seria inventar
  fonte.
- **Saldo, extrato e recarga do cartão.** O RUCard tem app com área autenticada; nada
  disso foi mapeado na Fase 1, e o Invariante 1 mais o §2.2 não deixam adivinhar rota
  de escrita.
- **Café da manhã.** `workinghours` publica `breakfast` (6 e 7 em dia de semana; 9 no
  fim de semana), e o `/menu` **não tem café**. A ferramenta responde a pergunta
  dizendo que o serviço existe e o cardápio não é publicado — Invariante 6, resposta
  honesta em vez de `[]`.

## 4. Arquitetura

```
usp_mcp/rucard/erros.py        # erro legível; o HTML do Tomcat morre aqui
usp_mcp/rucard/politica.py     # allowlist de rota e de id de RU (Invariante 2)
usp_mcp/rucard/catalogo.py     # projeção de /restaurants: 27,7 kB -> ficha por RU
usp_mcp/rucard/cliente.py      # POST, dois TTLs, validação de semana
usp_mcp/rucard/ferramentas.py  # bandejao(dia, refeicao, restaurantes)
usp_mcp/rucard/server.py       # fronteira MCP (listar/chamar/formatar/main)

tests/rucard/{conftest,test_fixtures,test_politica,test_cliente,test_catalogo,
              test_bandejao,test_custo,test_server_mcp,test_live}.py
```

Numeração dos testes com prefixo **R** (R1, R2, …) porque `T1` já existe nas duas
suítes irmãs e a conversa sobre "T3" ficaria ambígua entre três trilhas.

### 4.1 Fixtures — `politica`

- **R1** cada fixture da fatia existe e não está vazia (ausência é falha, nunca skip).
- **R2** nenhum caminho absoluto de máquina no `conftest`.
- **R3** nenhuma fixture da fatia está no `.gitignore`.
- **R4** o par de semanas existe: `menu_6.json` (24/08) e `menu_6_semana_31-08.json`
  (31/08) são o MESMO RU em semanas diferentes — é o que torna R14–R16 possíveis.

### 4.2 Allowlist e segredo — `politica`

- **R5** rota fora de `{menu, restaurants}` é negada, com motivo.
- **R6** id de RU fora de `{6,7,8,9}` é negado, e o motivo cita que o RU existe e está
  fora de escopo (as duas negativas têm curas diferentes: "não existe" e "existe mas
  não foi liberado").
- **R7** `permitir_escrita=True` não libera nada aqui: não há rota de escrita mapeada,
  e a flag não inventa uma.
- **R8** o valor de `RUCARD_HASH` não aparece em nenhum fonte de `usp_mcp/rucard/`
  (gate por par, §9 de 31/08 — a hash é isenta em `.env.example` e `SPEC1.md`, e em
  mais nenhum arquivo).
- **R9** o cliente não lê nenhuma variável de ambiente de credencial pessoal
  (`MOODLE_TOKEN` & cia. não aparecem no fonte) — este é o servidor que o §6 quer
  hospedar, e ele não pode virar portador de credencial num refactor futuro.
- **R10** a política nega por default: uma rota nova, ainda não pensada, é negada sem
  ninguém precisar acrescentá-la a uma denylist.

### 4.3 Cliente — `contrato`

- **R11** a requisição é **POST** form-urlencoded com a hash no corpo; `GET` não é
  usado em nenhum caminho (o `GET` real devolve 500 com HTML).
- **R12** hash ausente/vazia falha cedo, com mensagem que aponta o `.env.example` —
  não sai requisição sem ela.
- **R13** HTTP 500 com HTML do Tomcat vira erro legível **sem** arrastar o HTML: 3.240
  B de página de erro não entram na janela do modelo (mesmo raciocínio do stack trace
  do Jupiter, §9 de 31/08).
- **R14** duas chamadas para o mesmo RU na mesma semana → **uma** requisição (cache).
- **R15** cache com a semana ERRADA para a data pedida → refaz a requisição, mesmo
  dentro do TTL. É o par de fixtures do R4 que prova isto.
- **R16** TTL expirado → refaz. Relógio injetável: o teste verifica a REGRA, não o
  valor da constante.
- **R17** `/restaurants` e `/menu` têm TTLs diferentes, e o do catálogo é maior (dado
  medido byte-idêntico em 4 dias).
- **R18** JSON inválido com HTTP 200 vira erro legível, não `KeyError` três camadas
  adiante.
- **R19** timeout/conexão recusada vira `RucardIndisponivel` com mensagem em
  português.
- **R20** uma requisição por vez (o mesmo `Lock` do cliente do Jupiter: Invariante 5,
  não thread-safety por acaso).

### 4.4 Catálogo — `contrato`

- **R21** `hasCashier` é ignorado: os 4 RUs têm `cashiers` preenchido e o campo vem
  `"false"` nos 18. Quem lê o campo responde "não tem caixa" para um RU que tem.
- **R22** a projeção derruba 27,7 kB para uma ficha curta por RU, e o teto é medido.
- **R23** `serve(id, data, refeicao)` responde pelos horários publicados: o 7 não serve
  jantar em dia nenhum; o 9 serve sábado (almoço e jantar) e domingo (só almoço).
- **R24** o preço de aluno sai de `cashiers[].prices.students`, com a vírgula decimal
  preservada como veio (é string na API; converter para float é inventar precisão).
- **R25** RU fora da allowlist não aparece na projeção nem por acidente de iteração.

### 4.5 A ferramenta — `contrato`

- **R26** "hoje" resolve para a data de hoje no fuso de São Paulo, e o dia é escolhido
  **por data** (`DD/MM/AAAA`), nunca por índice na lista de 7.
- **R27** dia fora da semana devolvida → não devolve vazio: diz que só existe a semana
  corrente e qual é (Invariante 7).
- **R28** `"Fechado"` e `"FECHADO"` são reconhecidos igual — comparação
  case-insensitive, as duas grafias na mesma asserção.
- **R29** fechado hoje × nunca serve: o 7 no jantar diz "não serve jantar", e um sábado
  no 6 diz "fechado neste dia". Este é o teste que justifica o cruzamento com
  `workinghours` existir.
- **R30** café da manhã: responde que o serviço existe (horário publicado) e que o
  cardápio não é publicado nesta API. Nunca `[]`, nunca cardápio inventado.
- **R31** a comparação entre RUs sai numa chamada só de ferramenta (critério 2 do §5),
  e o texto traz calorias e preço para o "vale a pena".
- **R32** um RU que falhe (500, timeout) não derruba a resposta dos outros três, e a
  falha **aparece** no texto — parcial declarado, nunca parcial silencioso.
- **R33** as calorias vêm como o texto que a API manda (string), sem virar número:
  `"0"` num dia fechado não pode ser exibido como "0 kcal de comida".

### 4.6 Custo — `contrato`

- **R34** teto absoluto da saída, com folga declarada, medido contra as duas semanas.
- **R35** razão de redução: cru (4 menus + catálogo) ÷ saída projetada, com o número
  medido no próprio teste — é a asserção que o Jupiter não conseguiu ter, porque lá o
  payload *era* a resposta; aqui 6/7 do payload é semana que ninguém pediu.
- **R36** trava categórica: o conjunto de chaves da saída é exatamente o declarado
  (é o que impede campo novo de sobreviver por descuido).
- **R37** erro nunca custa mais que sucesso.

### 4.7 Fronteira MCP — `politica` e `contrato`

- **R38** a descrição fala a língua de quem pergunta ("bandejão", "almoço", "hoje",
  "vegetariana") e não vaza `/menu`, `hash` nem `workinghours`.
- **R39** nome de ferramenta desconhecido levanta erro legível citando o nome pedido.
- **R40** importar o servidor não exige o SDK do MCP (import de topo quebraria a
  coleta da suíte).
- **R41** ponta a ponta offline: fixture → `chamar_ferramenta` → texto. Como o Jupiter
  e diferente do Moodle, aqui não falta credencial nenhuma para isso rodar.

### 4.8 Canário ao vivo — `live`

- **R42** `/menu/6` real: HTTP 200 e as MESMAS chaves da fixture (chaves, nunca
  valores — o cardápio muda toda semana sem que nada tenha quebrado).
- **R43** `GET /menu/6` real ainda é HTTP 500 com HTML — o fato que obriga o POST.
- **R44** o skip diz o motivo por escrito.

Três requisições reais por execução, no máximo. Sem laço, sem enumerar id de RU.

## 5. Invariantes cobertos

| Invariante | Onde |
|---|---|
| 1 read-only | R7 (não há rota de escrita; a flag não inventa) |
| 2 allowlist | R5, R6, R10 |
| 3 sem segredo | R8, R9 |
| 4 credencial não sai da máquina | vacuamente: não há credencial pessoal aqui — e R9 é o que mantém verdade |
| 5 não martelar | R14–R17, R20 |
| 6 erro legível | R12, R13, R18, R19, R30, R39 |
| 7 sem limite silencioso | R27, R29, R32 |
| 8 nunca ler cru grande | `capture.sh`; e R22/R35, que provam a projeção |

## 6. O que este desenho NÃO faz

- Não promete café da manhã, histórico, saldo do cartão nem os 14 RUs fora do recorte.
- Não testa o adaptador stdio `main()` — mesmo buraco já registrado no backlog para as
  duas trilhas irmãs. `--auto-verificar` reduz, não elimina.
- Não constrói fixture com HTML no `menu`: 2 semanas de captura não produziram uma, e
  fixture inventada à mão testaria a imaginação de quem a escreveu. O parser tolera, e
  o backlog registra a ausência.
- Não fecha o instante exato da virada da semana. Fecha o suficiente para o cache:
  a validação por data não depende de saber a hora.

## 7. Definição de pronto

1. `./scripts/gate.sh` passa (segredo, cru ignorado, suíte offline).
2. A camada `live` roda verde no terminal do dono com `USP_MCP_LIVE=1`.
3. `python -m usp_mcp.rucard.server --auto-verificar` passa.
4. Decisão registrada no §9 do `SPEC1.md` com as medidas, e §1.2 corrigido onde a
   medição de 31/08 o contradisse.
5. Achado colateral no `docs/decisions/BACKLOG-correcoes.md`.
