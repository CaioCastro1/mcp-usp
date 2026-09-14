# O que o modelo lê não cita o SPEC — design

> 14/09/2026. Revisão de má prática nos três servidores, achado transversal. Texto
> escrito para quem mantém o projeto vazou para as strings que o modelo e o usuário
> leem. Mais três ajustes de documentação achados na mesma revisão.

## O que foi medido

`grep` por `§`, `Invariante`, `SPEC1`, `Medido em`, `Fase 1`, `Fase 2` em string
literal (não em comentário nem docstring) dentro de `usp_mcp/`. Ocorrências que
chegam ao modelo via `ToolError`, aviso ou texto de resposta:

| arquivo:linha | trecho | quem lê |
|---|---|---|
| `usp_mcp/rucard/politica.py:80-82` | `(Invariante 2: allowlist, não denylist)`, `não foram mapeados na Fase 1` | modelo (erro de rota) |
| `usp_mcp/rucard/politica.py:106` | `Incluir outro é decisão registrada no §9 do SPEC1.` | modelo (RU fora de escopo) |
| `usp_mcp/rucard/cliente.py:139` | `O valor é público (§1.2 do SPEC1)` | usuário (hash ausente) |
| `usp_mcp/jupiter/politica.py:111`, `:138` | `(Invariante 2, allowlist e não denylist)` | modelo (consulta/caminho negado) |
| `usp_mcp/jupiter/cliente.py:68`, `:89` | `ver §1.1 do SPEC1` | modelo (timeout) |
| `usp_mcp/jupiter/ferramentas.py:109`, `:117`, `:145` | `Medido em 14/09`, `medido em 14/09` | modelo (avisos) — **somem no plano `disciplina-secoes`** |
| `usp_mcp/moodle/cliente.py:112` | `(ver §8 do SPEC1.md)` | usuário (token inválido) |
| `usp_mcp/moodle/diagnostico.py:109-111` | `bloqueio permanente (§2.2)`, `o §2.2 nega de novo` | modelo (diagnóstico) |
| `usp_mcp/moodle/disciplinas.py:174` | `(§9, 28/08)` | modelo (erro de userid) |
| `usp_mcp/moodle/material.py:482` | `(Invariante 3)` | modelo (aviso de `material`) |
| `usp_mcp/moodle/politica.py:140`, `:151` | `do §2.2`, `(Invariante 2, allowlist e não denylist)` | modelo (função negada) |
| `usp_mcp/rucard/server.py:253`, `usp_mcp/jupiter/server.py:342`, `usp_mcp/moodle/server.py:384` | `§1.2`, `§4.4 do recon`, `(§8)` | dev (`--auto-verificar`) |

Para quem usa a ferramenta, "§9 do SPEC1" e "Invariante 2" são referências sem
referente: não ajudam a agir e custam tokens. A informação que essas frases carregam
(por que foi negado, o que fazer) é o que deve ficar.

Nenhum teste da suíte **exige** essas referências: `tests/moodle/test_cliente.py:71`
e `:173` aceitam `"§8"` **ou** `".env"` na mensagem de token inválido, e o resto só
as cita em mensagens de asserção ou comentários.

Documentação, achado na mesma revisão:

- `README.md:13` diz "cinco ferramentas" e a tabela lista seis.
- `README.md` ("Rodando") e `CLAUDE.md` §3 mandam `python3 -m venv .venv` +
  `pip install`. A preferência global do dono é `uv` (`~/.claude/CLAUDE.md`), que
  instala por hardlink e é o motivo declarado de 38 venvs terem chegado a 20 GB.

## Decisão

### 1. Regra, travada por teste

**Nenhuma string literal de `usp_mcp/` que não seja docstring contém `§`,
`Invariante`, `SPEC1`, `Medido em`, `medido em`, `Fase 1`, `Fase 2` ou `Regra de
Ouro`.** Comentários e docstrings continuam livres: são para quem mantém.

Teste novo `tests/test_jargao.py` (marcador `politica`), um caso por arquivo `.py`
de `usp_mcp/`, lendo o fonte por `ast` e ignorando o primeiro `Expr` string de
módulo, classe e função (docstring). É a mesma técnica de `test_r40` (import de
topo por AST) — verificação, não convenção.

### 2. Reescrita: tirar a referência, manter o fato

Cada ocorrência da tabela é reescrita dizendo **o que** aconteceu e **o que fazer**,
sem citar onde está registrado. Exemplos (o plano traz todos):

- `rota {rota!r} não está na allowlist do RUCard (Invariante 2: allowlist, não
  denylist). Permitidas: [...]. Saldo, extrato e recarga do cartão não foram
  mapeados na Fase 1 e nenhuma flag os libera.` →
  `rota {rota!r} não é uma das que esta ferramenta consulta ({permitidas}). Saldo,
  extrato e recarga do cartão não estão disponíveis por aqui, e nenhuma
  configuração os libera.`
- `Token do Moodle inválido ou expirado — gere um novo e atualize MOODLE_TOKEN no
  .env (ver §8 do SPEC1.md).` →
  `Token do Moodle inválido ou expirado — rode ./scripts/token.sh para gerar um
  novo e gravar MOODLE_TOKEN no .env.`

### 3. Documentação

- `README.md`: "cinco" → "seis", e a data do bloco "Estado" para 14/09/2026.
- `README.md` e `CLAUDE.md`: comandos de ambiente em `uv` (`uv venv` e
  `uv pip install -e ".[dev]"`), mantendo a ordem `cp .env.example .env` antes do
  gate que `tests/test_documentacao.py` (D1/D2) exige. O comentário do `CLAUDE.md`
  sobre venv por worktree continua verdadeiro e fica.
- O `pyproject.toml` e o `scripts/servidor.sh` não mudam: `uv venv` cria o mesmo
  `.venv/` que o lançador procura.

## O que NÃO muda

- Docstrings e comentários com `§` e `Invariante`: são o mapa para quem mantém.
- A mensagem de SDK ausente (`pip install -r requirements.txt`) tem teste que exige
  a frase exata (`tests/{jupiter,moodle}/test_server_stdio.py`) e fica fora desta
  mudança; trocar para `uv` ali é decisão separada.

## Aceite

- `tests/test_jargao.py` verde para todos os arquivos de `usp_mcp/`, e vermelho se
  alguém devolver `"§"` a qualquer string que não seja docstring (sabotagem).
- Suíte inteira verde: nenhuma asserção dependia das referências.
- `grep -c "cinco ferramentas" README.md` → 0; `grep -c "uv venv" README.md CLAUDE.md`
  → 1 em cada.
