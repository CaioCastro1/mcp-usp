# Saída sem jargão de projeto — Plano de Implementação

> **Para quem executa:** SUB-SKILL OBRIGATÓRIA — use `superpowers:subagent-driven-development`
> (recomendado) ou `superpowers:executing-plans` para implementar tarefa por tarefa.
> Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** nenhuma string que o modelo ou o usuário leem cita `§`, `Invariante`, `SPEC1`,
`Medido em`, `Fase 1/2` ou `Regra de Ouro`. A regra ganha um teste que varre `usp_mcp/` por
AST, ignorando docstrings e comentários. De quebra, o README deixa de dizer "cinco
ferramentas" e os comandos de ambiente passam a `uv`.

**Arquitetura:** um teste novo (`tests/test_jargao.py`) e reescritas pontuais de strings em
nove arquivos. Nenhuma lógica muda. Cada reescrita segue a mesma regra: **tirar a referência,
manter o fato e a instrução**.

**Stack:** Python 3.13, stdlib (`ast`). Testes com pytest, offline.

**Spec:** `docs/superpowers/specs/2026-09-14-saida-sem-jargao-design.md` — leia antes de
começar.

**Pré-requisito:** rodar **depois** dos planos `jupiter-disciplina-secoes` e
`rucard-semana-e-vocabulario` (eles reescrevem algumas das strings; fazer este antes gera
conflito). Se `usp_mcp/jupiter/ferramentas.py` ainda tiver "Medido em 14/09" quando você
chegar, o teste J1 vai apontar — trate como qualquer outro achado da Tarefa 3.

## Restrições globais

- **Docstrings e comentários não mudam.** São o mapa de quem mantém; a regra é só para
  string que sai do processo.
- **Toda reescrita mantém o fato e a instrução.** "Negado porque X; faça Y" continua
  dizendo X e Y — só sem o "(§n do SPEC1)".
- **Duas asserções da suíte dependem do texto** e continuam válidas depois da reescrita:
  `tests/rucard/test_politica.py:36` exige `"escopo"` na negativa de RU fora de escopo, e
  `tests/moodle/test_cliente.py:71` e `:173` aceitam `"§8"` **ou** `".env"` na mensagem de
  token inválido — a nova mensagem tem `.env`.
- **A mensagem de SDK ausente (`pip install -r requirements.txt`) não muda:** tem teste que
  exige a frase exata. Trocar para `uv` ali é decisão separada.
- **Português** em tudo.
- **Antes de cada commit:** `./scripts/gate.sh` verde.
- **Mensagem de commit:** `fix|test|docs(escopo): descrição`. Se o seu harness pedir uma linha
  de coautoria, acrescente-a ao fim.
- **Branch:** `fix/saida-sem-jargao`, saindo da `main`.
- Suíte completa: `.venv/bin/python -m pytest -q`.

---

### Tarefa 1: o teste que varre as strings

**Arquivos:**
- Criar: `tests/test_jargao.py`

**Interfaces:**
- Produz: teste `test_j1_...` parametrizado por arquivo de `usp_mcp/`, marcador `politica`.

- [ ] **Passo 1: criar o teste**

```python
"""J1: o que sai do processo não cita o SPEC.

"§9 do SPEC1", "Invariante 2", "medido em 14/09" são referências para quem MANTÉM
o projeto. Para quem usa a ferramenta — o modelo, o usuário — são palavras sem
referente: não ajudam a agir e custam tokens. Docstring e comentário continuam
livres; a regra é só para string literal, que é o que chega ao fio.

A varredura é por AST, como o R40/T43 (import de topo): o primeiro `Expr` string
de módulo, classe e função é docstring e fica de fora. Comentário não está na AST.
"""
import ast
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PACOTE = RAIZ / "usp_mcp"

PROIBIDOS = (
    "§", "Invariante", "SPEC1", "Medido em", "medido em",
    "Fase 1", "Fase 2", "Regra de Ouro",
)

pytestmark = pytest.mark.politica


def _docstrings(arvore: ast.Module) -> set[int]:
    ids = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            corpo = getattr(no, "body", [])
            if (
                corpo
                and isinstance(corpo[0], ast.Expr)
                and isinstance(corpo[0].value, ast.Constant)
                and isinstance(corpo[0].value.value, str)
            ):
                ids.add(id(corpo[0].value))
    return ids


def strings_que_saem(caminho: pathlib.Path):
    """(linha, texto) de toda string literal que NÃO é docstring."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    docstrings = _docstrings(arvore)
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str) and id(no) not in docstrings:
            yield no.lineno, no.value


ARQUIVOS = sorted(p.relative_to(RAIZ) for p in PACOTE.rglob("*.py"))


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=str)
def test_j1_nenhuma_string_que_sai_do_processo_cita_o_spec(arquivo):
    achados = [
        (linha, palavra, texto.strip()[:80])
        for linha, texto in strings_que_saem(RAIZ / arquivo)
        for palavra in PROIBIDOS
        if palavra in texto
    ]
    assert not achados, (
        f"{arquivo}: referência de projeto em string que o modelo/usuário lê. "
        "Tire a referência e mantenha o fato:\n  "
        + "\n  ".join(f"linha {l}: {p!r} em {t!r}" for l, p, t in achados)
    )


def test_j1b_a_varredura_pega_string_e_ignora_docstring(tmp_path):
    # Sabotagem controlada: sem isto, um bug na varredura deixaria J1 verde sem ver nada.
    fonte = tmp_path / "x.py"
    fonte.write_text(
        '"""Docstring com §9 e Invariante 2 — permitida."""\n'
        "def f():\n"
        '    """Também docstring, §1."""\n'
        '    return "negado (Invariante 2)"\n',
        encoding="utf-8",
    )
    achados = [(l, t) for l, t in strings_que_saem(fonte) if any(p in t for p in PROIBIDOS)]
    assert achados == [(4, "negado (Invariante 2)")]
```

- [ ] **Passo 2: rodar e anotar os achados**

```bash
.venv/bin/python -m pytest tests/test_jargao.py -q 2>&1 | grep -E "linha [0-9]+:|FAILED|passed|failed"
```
Esperado: J1b PASSED; J1 FAILED em `rucard/politica.py`, `rucard/cliente.py`,
`rucard/server.py`, `jupiter/politica.py`, `jupiter/cliente.py`, `jupiter/server.py`,
`moodle/cliente.py`, `moodle/diagnostico.py`, `moodle/disciplinas.py`, `moodle/material.py`,
`moodle/politica.py`, `moodle/server.py` — e em qualquer outro que a varredura ache. **A
lista impressa é a lista de trabalho das Tarefas 2–4.** Se aparecer um arquivo que não está
nas tarefas abaixo, aplique a mesma regra a ele.

- [ ] **Passo 3: commit do teste (vermelho, de propósito)**

```bash
git add tests/test_jargao.py
git commit -m "test(jargao): string que sai do processo não cita §, Invariante nem SPEC1"
```

---

### Tarefa 2: RUCard

**Arquivos:**
- Modificar: `usp_mcp/rucard/politica.py` (função `decidir`, três strings)
- Modificar: `usp_mcp/rucard/cliente.py` (`HashAusente` no `__init__`)
- Modificar: `usp_mcp/rucard/server.py` (`_auto_verificar`)

- [ ] **Passo 1: reescrever**

`usp_mcp/rucard/politica.py` — troque:

```python
                f"rota {rota!r} não está na allowlist do RUCard (Invariante 2: "
                f"allowlist, não denylist). Permitidas: {sorted(ROTAS_PERMITIDAS)}. "
                "Saldo, extrato e recarga do cartão não foram mapeados na Fase 1 "
                "e nenhuma flag os libera."
```
por
```python
                f"rota {rota!r} não é uma das que esta ferramenta consulta no "
                f"RUCard ({', '.join(sorted(ROTAS_PERMITIDAS))}; a lista é fechada). "
                "Saldo, extrato e recarga do cartão não estão disponíveis por aqui, "
                "e nenhuma configuração os libera."
```

e troque
```python
                "Incluir outro é decisão registrada no §9 do SPEC1."
```
por
```python
                "Incluir outro restaurante é mudança do projeto, não opção de chamada."
```

`usp_mcp/rucard/cliente.py` — troque
```python
                "O valor é público (§1.2 do SPEC1): a hash é compartilhada e "
                "embutida no app oficial, não é credencial de ninguém."
```
por
```python
                "O valor é público: a hash é compartilhada e embutida no app "
                "oficial, não é credencial de ninguém."
```

`usp_mcp/rucard/server.py` — troque
```python
    print("credencial pessoal   : NENHUMA (hash pública e compartilhada, §1.2)")
```
por
```python
    print("credencial pessoal   : NENHUMA (hash pública e compartilhada)")
```

- [ ] **Passo 2: rodar**

```bash
.venv/bin/python -m pytest tests/test_jargao.py tests/rucard -q
```
Esperado: J1 verde para os três arquivos do RUCard; `test_politica` verde (`"escopo"` continua
na negativa de RU fora de escopo, `"13"` e `"4242"` continuam).

- [ ] **Passo 3: commit**

```bash
git add usp_mcp/rucard/politica.py usp_mcp/rucard/cliente.py usp_mcp/rucard/server.py
git commit -m "fix(rucard): negativas e erros sem referência ao SPEC"
```

---

### Tarefa 3: Jupiter

**Arquivos:**
- Modificar: `usp_mcp/jupiter/politica.py` (`decidir` e `decidir_caminho`)
- Modificar: `usp_mcp/jupiter/cliente.py` (`transporte_http` e `transporte_get_http`)
- Modificar: `usp_mcp/jupiter/server.py` (`_auto_verificar`)
- Modificar, se ainda houver achado: `usp_mcp/jupiter/ferramentas.py`

- [ ] **Passo 1: reescrever**

`usp_mcp/jupiter/politica.py` — troque
```python
                f"consulta {consulta} não está na allowlist (Invariante 2, "
                "allowlist e não denylist). A fatia atual tem "
                f"{len(CONSULTAS_PERMITIDAS)} consultas."
```
por
```python
                f"consulta {consulta} não é uma das que esta ferramenta faz ao "
                f"JupiterWeb (a lista é fechada: {len(CONSULTAS_PERMITIDAS)} consultas)."
```
e troque
```python
            f"caminho {caminho} não está na allowlist (Invariante 2, allowlist e "
            f"não denylist). A fatia atual tem {len(CAMINHOS_PERMITIDOS)} caminho."
```
por
```python
            f"caminho {caminho} não é uma das páginas que esta ferramenta lê no "
            f"JupiterWeb (a lista é fechada: {len(CAMINHOS_PERMITIDOS)} caminho)."
```

`usp_mcp/jupiter/cliente.py` — nas **duas** ocorrências, troque
```python
            f"o JupiterWeb não respondeu ({e}). Se você está num sandbox, a rede "
            "da USP não é alcançável de lá — ver §1.1 do SPEC1."
```
por
```python
            f"o JupiterWeb não respondeu ({e}). Num ambiente sem acesso à rede da "
            "USP (um sandbox em nuvem, por exemplo) a chamada não tem como sair."
```

`usp_mcp/jupiter/server.py` — troque
```python
    print("credencial exigida   : NENHUMA (bean público e stateless, §4.4 do recon)")
```
por
```python
    print("credencial exigida   : NENHUMA (bean público e stateless)")
```

`usp_mcp/jupiter/ferramentas.py` — **só se J1 ainda apontar** este arquivo (o plano
`disciplina-secoes` remove os avisos com "medido em 14/09"): em cada aviso, apague a
oração que começa com "Medido em 14/09:" / "medido em 14/09," mantendo o resto da frase
gramatical. Exemplo: `"...sem precisar de código de curso. Medido em 14/09: o código que a
API deixa descobrir é justamente o que devolve lista vazia aqui."` →
`"...sem precisar de código de curso. O código que a API deixa descobrir é justamente o
que devolve lista vazia aqui."`

- [ ] **Passo 2: rodar**

```bash
.venv/bin/python -m pytest tests/test_jargao.py tests/jupiter -q
```
Esperado: J1 verde para o Jupiter; `test_requisitos_cliente.py:39` (`"obterTurma"` no motivo)
continua verde.

- [ ] **Passo 3: commit**

```bash
git add usp_mcp/jupiter
git commit -m "fix(jupiter): negativas e erros sem referência ao SPEC"
```

---

### Tarefa 4: Moodle

**Arquivos:**
- Modificar: `usp_mcp/moodle/cliente.py` (`TokenInvalido`)
- Modificar: `usp_mcp/moodle/diagnostico.py` (o aviso `⚠` em `formatar`)
- Modificar: `usp_mcp/moodle/disciplinas.py` (`ErroMoodle` de userid ausente)
- Modificar: `usp_mcp/moodle/material.py` (primeiro item de `avisos` em `formatar`)
- Modificar: `usp_mcp/moodle/politica.py` (`decidir`, duas strings)
- Modificar: `usp_mcp/moodle/server.py` (`_auto_verificar`)

- [ ] **Passo 1: reescrever**

`usp_mcp/moodle/cliente.py` — troque
```python
            "Token do Moodle inválido ou expirado — gere um novo e "
            "atualize MOODLE_TOKEN no .env (ver §8 do SPEC1.md)."
```
por
```python
            "Token do Moodle inválido ou expirado — rode ./scripts/token.sh para "
            "gerar um novo e gravar MOODLE_TOKEN no .env."
```

`usp_mcp/moodle/diagnostico.py` — troque
```python
            f"\n⚠ {len(vivas)} das {len(politica.BLOQUEIO_PERMANENTE)} funções do "
            "bloqueio permanente (§2.2) existem neste site e são alcançáveis por "
            "este token. Elas não são chamadas — a allowlist nega por omissão e o "
            "§2.2 nega de novo — e é justamente esse número que faz as duas "
            "camadas valerem a pena."
```
por
```python
            f"\n⚠ {len(vivas)} das {len(politica.BLOQUEIO_PERMANENTE)} funções que "
            "esta ferramenta bloqueia permanentemente existem neste site e são "
            "alcançáveis por este token. Elas não são chamadas: a lista de "
            "permitidas nega por omissão e o bloqueio nega de novo — e é esse "
            "número que faz as duas camadas valerem a pena."
```

`usp_mcp/moodle/disciplinas.py` — troque
```python
            "'você não tem matrícula' (§9, 28/08)."
```
por
```python
            "'você não tem matrícula'."
```

`usp_mcp/moodle/material.py` — troque
```python
        "no seu contexto — por isso ele não sai desta máquina (Invariante 3), "
```
por
```python
        "no seu contexto — por isso ele não sai desta máquina, "
```

`usp_mcp/moodle/politica.py` — troque
```python
                f"{funcao} está no bloqueio permanente do §2.2 — negada mesmo "
                "com permitir_escrita=True, pois não há flag que libere."
```
por
```python
                f"{funcao} está no bloqueio permanente — negada mesmo com "
                "permitir_escrita=True, pois não há configuração que libere."
```
e troque
```python
            f"{funcao} não está na allowlist — default é negar (Invariante 2, "
            "allowlist e não denylist)."
```
por
```python
            f"{funcao} não é uma das funções que esta ferramenta chama no Moodle "
            "(a lista é fechada; o padrão é negar)."
```

`usp_mcp/moodle/server.py` — troque
```python
    print(".env encontrado      :", arquivo or "NÃO — copie .env.example (§8)")
```
por
```python
    print(".env encontrado      :", arquivo or "NÃO — copie .env.example")
```

- [ ] **Passo 2: rodar a suíte inteira**

```bash
.venv/bin/python -m pytest -q
```
Esperado: tudo verde, J1 incluído para **todos** os arquivos. Se J1 ainda apontar algum
arquivo não listado aqui (por exemplo `usp_mcp/env.py`), aplique a mesma regra: tire a
referência, mantenha o fato.

- [ ] **Passo 3: sabotagem, para provar que J1 vigia**

```bash
git add -A
sed -i '' 's/a lista é fechada; o padrão é negar/a lista é fechada (Invariante 2)/' usp_mcp/moodle/politica.py
.venv/bin/python -m pytest tests/test_jargao.py -q 2>&1 | tail -3
git checkout usp_mcp/moodle/politica.py
```
Esperado: `1 failed` apontando `usp_mcp/moodle/politica.py`; depois do `checkout`, verde de
novo. (O `git add -A` antes é a regra do §4 do CONVENTIONS: sabotagem sobre árvore limpa.)

- [ ] **Passo 4: commit**

```bash
git add usp_mcp/moodle
git commit -m "fix(moodle): negativas, erros e avisos sem referência ao SPEC"
```

---

### Tarefa 5: README e CLAUDE.md

**Arquivos:**
- Modificar: `README.md` (cabeçalho "Estado", frase das ferramentas, dois blocos de comandos)
- Modificar: `CLAUDE.md` (§3, o comando de venv)

- [ ] **Passo 1: README**

Troque `## Estado — 09/09/2026` por `## Estado — 14/09/2026`.

Troque
`**Três servidores MCP rodando, cinco ferramentas, todas verificadas contra a USP.**`
por
`**Três servidores MCP rodando, seis ferramentas, todas verificadas contra a USP.**`

Na seção **Rodando**, troque
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./scripts/gate.sh
```
por
```bash
uv venv
uv pip install -e ".[dev]"
cp .env.example .env
./scripts/gate.sh
```

No passo **1. Clone e monte o ambiente**, troque
```bash
git clone git@github.com:CaioCastro1/mcp-usp.git && cd mcp-usp
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```
por
```bash
git clone git@github.com:CaioCastro1/mcp-usp.git && cd mcp-usp
uv venv
uv pip install -e ".[dev]"
```

Logo abaixo desse bloco, onde o texto diz `O `-e` instala o pacote **apontando para este
checkout**`, acrescente antes dele o parágrafo:

```markdown
`uv` cria o mesmo `.venv/` que `python3 -m venv` criaria (é o que `scripts/servidor.sh` e o
`.mcp.json` procuram), com uma diferença que importa neste Mac: instala por hardlink a partir
de um cache único, então dez checkouts não custam dez cópias do SDK. Se não tiver `uv`,
`python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"` continua funcionando.
```

- [ ] **Passo 2: CLAUDE.md**

Em §3, troque
```bash
python3 -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"
```
por
```bash
uv venv && uv pip install -e ".[dev]"
```
e, no comentário logo acima (o que começa com `# O venv é POR DIRETÓRIO`), troque a frase
`O `-e` instala o pacote` por `uv cria o mesmo .venv/ do python3 -m venv, por hardlink. O `-e` instala o pacote`.

- [ ] **Passo 3: rodar os testes de documentação e o gate**

```bash
.venv/bin/python -m pytest tests/test_documentacao.py tests/test_pacote.py -q
./scripts/gate.sh
```
Esperado: verde (D1/D2 só exigem `cp .env.example .env` antes do gate, e a ordem não mudou).

- [ ] **Passo 4: commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: seis ferramentas, e o ambiente com uv"
```

---

### Tarefa 6: registro e PR

- [ ] **Passo 1: §9 do `SPEC1.md`**

```markdown
### 14/09/2026 — o que o modelo lê deixa de citar o SPEC

Revisão transversal: doze strings que chegam ao modelo ou ao usuário — negativas de
allowlist, timeout, token inválido, avisos de `material` e `diagnostico` — citavam
"§9 do SPEC1", "Invariante 2", "medido em 14/09". Para quem usa a ferramenta é referência
sem referente, e custa token. Nenhum teste dependia delas (dois aceitavam `"§8"` OU
`".env"`).

**Decisão:** regra travada por teste (`tests/test_jargao.py`, J1): nenhuma string literal
de `usp_mcp/` que não seja docstring contém `§`, `Invariante`, `SPEC1`, `Medido em`,
`Fase 1/2` ou `Regra de Ouro`. Varredura por AST, como R40/T43; docstring e comentário
seguem livres, porque são para quem mantém. Cada string foi reescrita mantendo o fato e a
instrução. Verificado por sabotagem (J1 reprova ao devolver "(Invariante 2)" a uma negativa).

No mesmo PR: README dizia "cinco ferramentas" com seis na tabela; e os comandos de ambiente
passam a `uv` (mesmo `.venv/`, por hardlink) — a mensagem de SDK ausente segue com `pip`
porque tem teste sobre a frase exata, e trocá-la é decisão à parte.
```

- [ ] **Passo 2: gate, commit e PR**

```bash
./scripts/gate.sh
git add SPEC1.md
git commit -m "docs(spec): §9 — saída sem jargão, travada por teste"
git push -u origin fix/saida-sem-jargao
gh pr create --base main --title "fix: o que o modelo lê não cita o SPEC (e README com seis ferramentas, uv)" --body "Spec: docs/superpowers/specs/2026-09-14-saida-sem-jargao-design.md. Plano: docs/superpowers/plans/2026-09-14-saida-sem-jargao.md. Teste novo tests/test_jargao.py."
```
Esperado: `gate: PASSOU`.
