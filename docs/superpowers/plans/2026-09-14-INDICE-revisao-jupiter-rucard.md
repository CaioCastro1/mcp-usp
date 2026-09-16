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

## Prompts prontos para uma sessão nova

Um por plano. Cada um é autossuficiente: copie inteiro numa sessão limpa do Claude Code
neste repositório.

### 1 — comunicado no cardápio (RUCard)

```
Execute o plano docs/superpowers/plans/2026-09-14-rucard-aviso-no-cardapio.md, tarefa por tarefa, na ordem.

Antes de começar: leia CLAUDE.md, depois o spec docs/superpowers/specs/2026-09-14-rucard-aviso-no-cardapio-design.md, depois o plano. Crie a branch fix/rucard-comunicado-no-cardapio a partir da main atualizada. Se estiver num worktree novo, crie o venv com `uv venv && uv pip install -e ".[dev]"` antes de rodar qualquer teste.

Regras: siga o plano tarefa por tarefa, na ordem, com os testes falhando antes da implementação. Não toque a rede da USP. Se um trecho citado pelo plano não existir mais, procure a função pelo nome, aplique a intenção do spec e registre a diferença no PR. Rode ./scripts/gate.sh antes de cada commit. Termine com o §9 do SPEC1.md atualizado e o PR aberto contra a main.

Ao final me diga: PR aberto (link), o que divergiu do plano, e o texto real que a ferramenta devolve para a fixture nova.
```

### 2 — semana e vocabulário (RUCard) — depois do 1

```
Execute o plano docs/superpowers/plans/2026-09-14-rucard-semana-e-vocabulario.md, tarefa por tarefa, na ordem.

Pré-requisito: o PR "comunicado no cardápio vira aviso" já mergeado na main. Confira com `git log origin/main --oneline | grep -i comunicado`; se não estiver, pare e me avise.

Antes de começar: leia CLAUDE.md, depois o spec docs/superpowers/specs/2026-09-14-rucard-semana-e-vocabulario-design.md, depois o plano. Crie a branch feat/rucard-semana-e-vocabulario a partir da main atualizada. Se estiver num worktree novo, crie o venv com `uv venv && uv pip install -e ".[dev]"`.

Regras: siga o plano tarefa por tarefa, testes primeiro. Sempre que tocar o schema em server.py, rode também tests/handshake. Nenhuma requisição a mais à USP: a semana inteira tem de custar 5 rotas no dublê. Os tetos de bytes são medidos; se um falhar, olhe o que engordou em vez de subir o número. Rode ./scripts/gate.sh antes de cada commit. Termine com o §9 do SPEC1.md, o README e o PR contra a main.

Ao final me diga: PR aberto (link), o que divergiu do plano, e cole a saída de dia="semana", refeicao="almoco" para as fixtures.
```

### 3 — disciplina por seção (Jupiter)

```
Execute o plano docs/superpowers/plans/2026-09-14-jupiter-disciplina-secoes.md, tarefa por tarefa, na ordem.

Antes de começar: leia CLAUDE.md, depois o spec docs/superpowers/specs/2026-09-14-jupiter-disciplina-secoes-design.md, depois o plano. Crie a branch feat/jupiter-disciplina-secoes a partir da main atualizada. Se estiver num worktree novo, crie o venv com `uv venv && uv pip install -e ".[dev]"`.

Regras: siga o plano tarefa por tarefa, testes primeiro. A allowlist do Jupiter só encolhe neste plano (4 para 3 consultas); nenhuma consulta nova. Sempre que tocar o schema em server.py, rode tests/handshake e `.venv/bin/python -m usp_mcp.jupiter.server --auto-verificar`. Se algum teste de tests/jupiter/test_server_stdio.py enumerar os parâmetros de disciplina, atualize-o para {sigla, secoes, ingles}. Não toque a rede da USP. Rode ./scripts/gate.sh antes de cada commit. Termine com o §9 do SPEC1.md, o README e o PR contra a main.

Ao final me diga: PR aberto (link), o que divergiu do plano, quantos bytes tem o texto padrão de PTC3314 e o de secoes=["todas"].
```

### 4 — requisitos agrupados (Jupiter) — depois do 3, ou com rebase

```
Execute o plano docs/superpowers/plans/2026-09-14-jupiter-requisitos-agrupados.md, tarefa por tarefa, na ordem.

Antes de começar: leia CLAUDE.md, depois o spec docs/superpowers/specs/2026-09-14-jupiter-requisitos-agrupados-design.md, depois o plano. Crie a branch feat/jupiter-requisitos-agrupados a partir da main atualizada. Se o PR "ficha por seção" já tiver sido mergeado, parta dele; se estiver aberto, avise no PR que os dois tocam usp_mcp/jupiter/server.py e faça rebase antes de pedir merge. Se estiver num worktree novo, crie o venv com `uv venv && uv pip install -e ".[dev]"`.

Regras: só formatação. A projeção, o recorte HTML, a política e a descrição da ferramenta não mudam. Dois currículos só entram no mesmo grupo se o conjunto de (sigla, nome, tipo, rótulo) for idêntico. T70, T71 e T72 têm de continuar verdes sem edição. Rode ./scripts/gate.sh antes de cada commit. Termine com o §9 do SPEC1.md e o PR contra a main.

Ao final me diga: PR aberto (link), o que divergiu do plano, e cole a saída de requisitos para MAT2455 com a contagem de bytes.
```

### 5 — saída sem jargão — depois do 2 e do 3

```
Execute o plano docs/superpowers/plans/2026-09-14-saida-sem-jargao.md, tarefa por tarefa, na ordem.

Pré-requisito: os PRs "semana numa chamada" (RUCard) e "ficha por seção" (Jupiter) já mergeados na main. Confira com `git log origin/main --oneline | grep -iE "semana|seção|secoes"`; se faltar algum, pare e me avise.

Antes de começar: leia CLAUDE.md, depois o spec docs/superpowers/specs/2026-09-14-saida-sem-jargao-design.md, depois o plano. Crie a branch fix/saida-sem-jargao a partir da main atualizada. Se estiver num worktree novo, crie o venv com `uv venv && uv pip install -e ".[dev]"`.

Regras: primeiro o teste tests/test_jargao.py, e a lista que ele imprime é a lista de trabalho. Docstrings e comentários não mudam; só string que sai do processo. Cada reescrita tira a referência e mantém o fato e a instrução. A mensagem de SDK ausente com `pip install -r requirements.txt` não muda. Faça a sabotagem da Tarefa 4 e me mostre o resultado. Rode ./scripts/gate.sh antes de cada commit. Termine com o §9 do SPEC1.md e o PR contra a main.

Ao final me diga: PR aberto (link), a lista de arquivos e linhas que o teste apontou, e se algum arquivo fora dos listados no plano apareceu.
```
