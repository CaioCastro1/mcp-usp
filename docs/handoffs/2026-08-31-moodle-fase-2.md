# HANDOFF — Fase 2 do Moodle (fatia vertical `o_que_vence`) — 2026-08-31 — sessão de implementação

> Este handoff existe para o que NÃO cabe no §9 nem no git: o que ficou fora de
> escopo, o que não tem teste, e onde a próxima sessão pisa em falso. A decisão
> fechada com dado está no §9 do `SPEC1.md`, entrada de 31/08/2026.

## Objetivo da sessão
Implementar a Fase 2 do Moodle contra `tests/moodle/`, tratando a suíte como
especificação executável e sem alterar nenhum teste, até ficar verde.

## Estado
CONCLUÍDO — **97 verdes, 0 vermelhos, 2 pulados**. Nada ficou vermelho.

Os 2 pulados são a camada `live` (`tests/moodle/test_live.py`), e **pular era o
comportamento correto**, não uma falha contornada: `USP_MCP_LIVE` ficou
desmarcada de propósito (o contrato desta sessão proíbe falar com a USP) e o
skip imprime o motivo por escrito, que é justamente o Invariante 6 aplicado à
suíte. Eles voltam a rodar no terminal do Caio com `USP_MCP_LIVE=1`.

Nenhum teste parou a implementação. Nenhuma verificação foi afrouxada: o diff
contra a base é só `usp_mcp/`, verificável com
`git diff --name-only 8125f20..HEAD -- tests/ fixtures/`, que sai vazio.

## O que foi feito
Cinco commits, um por módulo verde, na ordem do grafo de dependência dos testes:

| Commit | Módulo | Testes |
|---|---|---|
| `5de34eb` | `politica.py` — allowlist + bloqueio permanente | 58 |
| `814e217` | `projecao.py` — 528 kB de transporte → ~7 kB | 10 |
| `93f7801` | `cliente.py` — transporte + política na fronteira | 11 |
| `ae7acb9` | `o_que_vence.py` — a ferramenta ponta a ponta | 10 |
| `088fa98` | `server.py` — fronteira MCP | 3 |
| `3079e3f` | registro datado no §9 do `SPEC1.md` | — |

Medido na implementação (números no §9): projeção em **7.170 B / 204,9 B por
evento**; texto final em **2.728 caracteres** para 35 eventos com janela de 30
dias, contra teto de 4.000.

## O que falta
- **Rodar a camada `live` na máquina do Caio.** É o único pedaço da suíte que
  esta sessão não pôde executar. `USP_MCP_LIVE=1 .venv/bin/python -m pytest -m live`
  — uma chamada, `limitnum=5`, compara só a forma. A fixture é de 28/08 e
  congela; sem esse canário a USP pode mudar a API por baixo com a suíte verde.
- **Capturar um `invalidtoken` real** (backlog, já declarado no §6 do documento
  de desenho). Token propositalmente inválido, não toca na conta. Enquanto não
  existir, os testes de erro asseguram o contrato da camada e **nunca** a forma
  do erro do Moodle.
- **Gate de pré-commit.** O `<TODO>` do §4 do `CONVENTIONS.md` e do §3 do
  `CLAUDE.md` continua aberto — agora existe código para o gate rodar
  (`.venv/bin/python -m pytest`), então dá para fechá-lo.
- **`.venv` não existe no repositório nem em worktree novo.** Esta sessão criou
  o dela com `python3 -m venv .venv && .venv/bin/pip install pytest`. Vale
  decidir se isso vira `requirements-dev.txt` ou fica na mão.
- As demais perguntas do §5 continuam abertas. Isto é **uma** ferramenta.

## Arquivos tocados
- `usp_mcp/moodle/{politica,projecao,cliente,o_que_vence,server}.py` — implementados
- `SPEC1.md` — entrada datada no §9
- `docs/handoffs/2026-08-31-moodle-fase-2.md` — este arquivo
- **Não tocados:** `tests/`, `fixtures/`, `pytest.ini`, `scripts/`

## Como retomar
```bash
# branch: claude/moodle-fase-2-156479
python3 -m venv .venv && .venv/bin/pip install pytest   # se o venv não existir
.venv/bin/python -m pytest              # esperado: 97 passed, 2 skipped
```
Depois: rodar a camada `live` no terminal do Caio, e só então tratar a fatia
como validada contra a USP de verdade.

## Cuidados
- **Dois números da allowlist estão travados por teste, de propósito.**
  `politica.ALLOWLIST` tem exatamente 1 nome (T7) e `server.listar_ferramentas()`
  devolve exatamente 1 ferramenta (T42). Se você precisar de "só mais uma", o
  teste vai ficar vermelho — e ele está certo. O caminho é entrada nova no §9,
  não editar a asserção.
- **Não mexa nos campos da projeção sem remedir.** `activityname` (e não `name`)
  e `url` (e não `viewurl`) foram escolhidos pelo orçamento de bytes, e `viewurl`
  sozinho já joga a medida para fora da faixa da suíte. O motivo está no §9.
- **Três caminhos de código não têm teste offline**, e nenhum deles é coberto
  pelo verde: o transporte HTTP real de `cliente._transporte_padrao`, o caminho
  autenticado de `server.chamar_ferramenta` e o adaptador stdio de
  `server.main()`. Verde na suíte não é verde neles.
- **O import do SDK do MCP fica dentro de `server.main()`.** Movê-lo para o topo
  do módulo quebra a coleta da suíte inteira, porque o SDK não é dependência de
  teste. Isso parece um erro de estilo e não é.
- **A rede da USP não é alcançável do sandbox** (§1.1). Qualquer verificação real
  roda no terminal do Caio.
