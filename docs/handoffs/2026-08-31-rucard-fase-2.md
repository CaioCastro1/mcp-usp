# HANDOFF — Fase 2 do RUCard (fatia vertical `bandejao`) — 2026-08-31 — sessão de implementação

> Este handoff existe para o que NÃO cabe no §9 nem no git: o que ficou fora de
> escopo, o que não tem teste, e onde a próxima sessão pisa em falso. A decisão
> fechada com dado está no §9 do `SPEC1.md`, entrada de 31/08/2026 ("Fase 2 do
> RUCard implementada contra a suíte").

## Objetivo da sessão
Implementar as pendências do RUCard seguindo os moldes do Jupiter e do Moodle: o
único dos três sistemas com Fase 1 fechada e Fase 2 nunca começada.

## Estado
CONCLUÍDO e **verificado contra a USP**. `./scripts/gate.sh`: 253 verdes, 6
pulados, 0 falhas (80 testes novos). Camada `live` do RUCard: **2 passed, 1
skipped**. Handshake stdio real: `initialize` → `tools/list` → `tools/call`
devolveu o cardápio de hoje dos quatro RUs em 975 caracteres.

A camada `live` do Moodle **não** foi rodada aqui (consome credencial pessoal e
cada chamada fica no log da conta). A do Jupiter também não: nada nesta sessão
tocou aquela trilha.

## O que foi feito
1. **Medição antes do desenho** (regra 9 do `CLAUDE.md`): segunda captura do
   RUCard, quatro dias depois da Fase 1. Ela é o que fechou o TTL do cache —
   sem ela, o desenho teria sido opinião.
2. Desenho em `docs/superpowers/specs/2026-08-31-rucard-fase-2-design.md`, com
   os 44 testes nomeados antes de existir código.
3. Suíte primeiro, esqueleto vermelho: 58 vermelhos por `NotImplementedError`,
   19 verdes (só testes de fixture), **zero erro de coleta**.
4. Implementação: `erros`, `politica`, `catalogo`, `cliente`, `ferramentas`,
   `server`. `.mcp.json` registra `usp-rucard`.
5. §1.2 corrigido em quatro pontos pela medição, nota da Fase 1 estendida,
   decisão no §9, backlog atualizado.

## O que falta
- **Histórico de cardápio.** A API não tem parâmetro de data. Prometer exige
  persistir por conta própria, e isso é outro escopo (e outra conversa sobre
  onde guardar).
- **Saldo, extrato e recarga do cartão.** Área autenticada nunca mapeada. O
  §2.2 não deixa adivinhar rota de escrita, e a allowlist nega por default.
- **Os outros 14 RUs.** Negados com motivo. Incluir é decisão de §9.
- **A hora exata da virada da semana.** Fechado o suficiente para o cache,
  aberto para quem quiser prever a virada (ver nota da Fase 1).
- **Teste do `main()`** — terceira trilha com o mesmo buraco, agora no backlog
  com a sugestão de um teste de handshake compartilhado.

## Arquivos tocados
`usp_mcp/rucard/*.py`, `tests/rucard/*.py`, `fixtures/rucard/{menu_6_semana_31-08.json,
erro-500-get-menu6.html}`, `.mcp.json`, `SPEC1.md` (§1.2 e §9),
`notas/fase1-rucard.md`, `docs/decisions/BACKLOG-correcoes.md`, `CLAUDE.md`,
`README.md`, `docs/domains/README.md`,
`docs/superpowers/specs/2026-08-31-rucard-fase-2-design.md`.

## Como retomar

```bash
# se o venv não existir NESTE diretório (cada worktree precisa do seu):
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt -r requirements.txt

./scripts/gate.sh                                              # 253 passed, 6 skipped
.venv/bin/python -m usp_mcp.rucard.server --auto-verificar
USP_MCP_LIVE=1 .venv/bin/python -m pytest tests/rucard -m live  # 3 requisições, dado público
```

## Cuidados

**Não troque o cruzamento com `workinghours` por uma leitura só do `/menu`.** A
tentação é óbvia: o cardápio já diz `FECHADO`, para que buscar o catálogo? Porque
`FECHADO` significa três coisas diferentes — "não serve essa refeição em dia
nenhum" (o 7 no jantar), "não serve nesse dia" (o 6 no sábado) e "fechado hoje
apesar de servir" (feriado). Quem responde só com o `/menu` manda o aluno voltar
amanhã à mesma hora num RU que nunca serve jantar.

**Não substitua a validação de semana do cache por um TTL maior ou menor.** As
duas regras cobrem coisas diferentes: TTL protege a USP, validação protege a
resposta. Só TTL devolve o cardápio da semana passada na segunda-feira, e o
teste que pega isso (R15) usa o par de fixtures do mesmo RU em semanas
diferentes — se alguém apagar uma delas, o teste vira decoração.

**Não converta preço nem calorias para número.** Os dois são string na API,
preço com vírgula decimal. `float("2,00")` explode e `int("")` explode; e
calorias `"0"` num dia fechado, exibida como número, é número certo respondendo
pergunta errada. Por isso dia fechado **não tem** a chave `calorias`.

**Não chame a opção do dia de vegetariana.** 100% das refeições abertas têm uma
linha `Opção: …`; a marca `(V)` aparece em algumas do RU 6 e em nenhuma dos 7, 8
e 9. `opcao` e `opcao_vegetariana_marcada` são campos separados de propósito, e o
teste R33b existe para impedir a fusão.

**Não leia o campo de "tem caixa" do `/restaurants`.** Ele vem `"false"` nos 18
RUs, inclusive nos 14 que têm caixa — e é a *string* `"false"`, truthy em JS. Use
o tamanho de `cashiers`. Há teste que varre o fonte do `catalogo.py` procurando o
nome do campo fora da docstring.

**Não hardcode a hash em teste nenhum.** O gate reprovou este commit por isso
uma vez: a isenção é por par (variável, arquivo), e vale só para `.env.example` e
`SPEC1.md`. Um teste que procura um segredo é um lugar por onde o segredo vaza —
leia o valor do ambiente e falhe com `pytest.fail`, nunca com
`assert valor not in fonte` (que imprime os dois lados).

**Cuidado ao mexer em `cliente.py`:** há teste de política que varre o fonte
procurando nome de variável com credencial pessoal, cookie e sessão. Não é
paranoia — é o que mantém verdadeira a decisão do §6 de que **este** é o servidor
que pode ser hospedado.
