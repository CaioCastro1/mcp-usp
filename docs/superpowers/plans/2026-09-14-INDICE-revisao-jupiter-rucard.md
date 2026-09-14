# Revisão de 14/09/2026 — índice dos specs e planos

> Cinco mudanças saídas da revisão de má prática nos servidores RUCard e Jupiter, cada uma
> com spec (o *porquê*, com medição) e plano (o *como*, passo a passo, TDD). Feitos para
> serem executados por um agente sem contexto desta conversa — inclusive um modelo menor.

| # | Spec | Plano | Mexe em | Depende de |
|---|---|---|---|---|
| 1 | `specs/2026-09-14-rucard-aviso-no-cardapio-design.md` | `plans/2026-09-14-rucard-aviso-no-cardapio.md` | `rucard/ferramentas.py` | — |
| 2 | `specs/2026-09-14-rucard-semana-e-vocabulario-design.md` | `plans/2026-09-14-rucard-semana-e-vocabulario.md` | `rucard/ferramentas.py`, `rucard/server.py` | **1** mergeado |
| 3 | `specs/2026-09-14-jupiter-disciplina-secoes-design.md` | `plans/2026-09-14-jupiter-disciplina-secoes.md` | `jupiter/ferramentas.py`, `server.py`, `cliente.py`, `politica.py` | — |
| 4 | `specs/2026-09-14-jupiter-requisitos-agrupados-design.md` | `plans/2026-09-14-jupiter-requisitos-agrupados.md` | `jupiter/ferramentas.py`, `jupiter/server.py` | — (rebase se paralelo a 3) |
| 5 | `specs/2026-09-14-saida-sem-jargao-design.md` | `plans/2026-09-14-saida-sem-jargao.md` | strings nos três sistemas, README, CLAUDE.md | **2 e 3** mergeados |

## Ordem sugerida

1 → 2 (RUCard, em sequência) e 3 → 4 (Jupiter, em sequência) podem correr **em paralelo**
entre si; 5 por último. Cada plano é uma branch e um PR contra a `main`, com o `§9` do
`SPEC1.md` atualizado na última tarefa.

## O que todo executor precisa saber, além do plano

- **Leia o spec antes do plano.** O plano diz o que digitar; o spec diz por que — e é o spec
  que resolve dúvida quando o código encontrado divergir do que o plano cita.
- **O gate é o juiz:** `./scripts/gate.sh` antes de cada commit. Ele roda a suíte offline
  inteira, inclusive o handshake que sobe cada servidor de verdade.
- **Não toque a rede da USP** para executar nenhum destes planos: toda verificação é contra
  fixture. A fixture nova do plano 1 já foi capturada.
- **Se um passo do plano citar um trecho que não existe mais** (outro PR mudou a linha),
  procure a função pelo nome, aplique a intenção descrita no spec e registre a diferença no
  PR. Não invente um trecho para casar com o plano.
- **Números nos tetos são medidos, não chutados.** Se um teto falhar por poucos bytes, a
  resposta certa é olhar o que engordou, não subir o número.

## O que ficou de fora, de propósito

- **Busca de disciplina por nome** ("qual a ementa de Cálculo 3?"): é a maior lacuna de
  entendimento do Jupiter, mas é ferramenta nova, e pelo §5 do SPEC1 nasce de decisão do
  dono, não de revisão. Fica registrada como questão aberta.
- **Cache em disco** para o RUCard/Jupiter: tolerável no Desktop (o processo vive a sessão);
  vale reabrir se o uso via `uvx` one-shot crescer.
