# Requisitos agrupados por combinação — Plano de Implementação

> **Para quem executa:** implemente tarefa por tarefa, na ordem em que estão escritas.
> Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** o texto de `requisitos` deixa de repetir o mesmo par de exigências 18 vezes:
currículos com o **mesmo conjunto** de (sigla, tipo) saem sob um cabeçalho só. MAT2455 cai de
6.238 B para menos de 3.500 B sem perder um currículo nem um tipo.

**Arquitetura:** só formatação. `ferramentas.agrupar_curriculos` (pura) agrupa a lista que
`ferramentas.requisitos` já devolve; `server.formatar_requisitos` imprime por grupo. A projeção,
o recorte HTML, a política e a descrição não mudam.

**Stack:** Python 3.13, stdlib. Testes com pytest, offline, contra fixture.

**Spec:** `docs/superpowers/specs/2026-09-14-jupiter-requisitos-agrupados-design.md` — leia
antes de começar.

**Pré-requisito:** nenhum. Independe do plano `disciplina-secoes`, mas os dois editam
`usp_mcp/jupiter/server.py`; se forem em paralelo, faça rebase antes do PR.

## Restrições globais

- **Nenhuma requisição de rede na suíte.** Fixtures `mat2455_html`, `psi3323_html`,
  `ptc3313_html`, `ingresso_poli`, `colegiados` de `tests/jupiter/conftest.py`, com os dublês
  `Gravador` (DWR) e `GravadorGet` (HTML, em `tests/jupiter/test_requisitos_cliente.py`).
- **O tipo da exigência é propriedade do currículo.** Dois currículos só se juntam se o
  conjunto de (sigla, nome, tipo, rótulo) for **idêntico**. Nunca agrupe por sigla só.
- **T70, T71 e T72 continuam verdes sem edição** (correquisito, fraco × duro, silêncio).
- **Português** em docstring, mensagem e comentário.
- **Antes de cada commit:** `./scripts/gate.sh` verde.
- **Mensagem de commit:** `feat|test|docs(jupiter): descrição`. Se o seu harness pedir uma
  linha de coautoria, acrescente-a ao fim.
- **Branch:** `feat/jupiter-requisitos-agrupados`, saindo da `main`.
- Suíte: `.venv/bin/python -m pytest tests/jupiter -q`.

---

### Tarefa 1: `agrupar_curriculos`

**Arquivos:**
- Modificar: `usp_mcp/jupiter/ferramentas.py` — função nova, no fim do arquivo
- Testar: `tests/jupiter/test_requisitos_cliente.py` (acrescentar no fim; o arquivo já
  constrói `ferramentas.requisitos` contra `mat2455_html`)

**Interfaces:**
- Produz: `agrupar_curriculos(curriculos: list[dict]) -> list[tuple[tuple, list[dict]]]`.
  A chave é `tuple(sorted((sigla, nome, tipo, rotulo) das exigências))`; grupos maiores
  primeiro, o grupo vazio `()` por último; dentro do grupo, a ordem de entrada.

- [ ] **Passo 1: escrever os testes que falham**

No fim de `tests/jupiter/test_requisitos_cliente.py` (confira no topo do arquivo como ele
constrói o cliente para MAT2455 e reutilize o mesmo padrão):

```python
# --- T81: agrupar currículos com a mesma combinação de exigências (14/09) -----


def _mat2455(mat2455_html, ingresso_poli, colegiados):
    from usp_mcp.jupiter import cliente as _cliente, ferramentas
    from tests.jupiter.conftest import Gravador

    c = _cliente.ClienteJupiter(
        Gravador([colegiados, ingresso_poli]), transporte_get=GravadorGet(mat2455_html)
    )
    return ferramentas.requisitos("MAT2455", cliente=c)


def test_t81_mat2455_tem_23_curriculos_em_4_combinacoes(mat2455_html, ingresso_poli, colegiados):
    from usp_mcp.jupiter import ferramentas

    grupos = ferramentas.agrupar_curriculos(_mat2455(mat2455_html, ingresso_poli, colegiados)["curriculos"])

    assert len(grupos) == 4
    assert sum(len(membros) for _, membros in grupos) == 23
    assert [len(membros) for _, membros in grupos] == [13, 7, 2, 1], "maiores primeiro"


def test_t81b_o_tipo_separa_grupos_mesmo_com_as_mesmas_siglas(mat2455_html, ingresso_poli, colegiados):
    from usp_mcp.jupiter import ferramentas

    grupos = ferramentas.agrupar_curriculos(_mat2455(mat2455_html, ingresso_poli, colegiados)["curriculos"])
    por_codcur = {c["codcur"]: chave for chave, membros in grupos for c in membros}

    # 3250 exige MAT2454 + MAT3458 como requisito DURO; 3033 exige as mesmas como
    # FRACO. Mesmas siglas, grupos diferentes — é a informação que decide a matrícula.
    assert por_codcur["3250"] != por_codcur["3033"]
    assert {s for s, _, _, _ in por_codcur["3250"]} == {s for s, _, _, _ in por_codcur["3033"]}
    # 3033, 3032 e 3045 exigem a mesma coisa nos mesmos termos: um grupo só.
    assert por_codcur["3033"] == por_codcur["3032"] == por_codcur["3045"]
    # Os sete do projeto piloto (2000101) ficam juntos.
    piloto = {"3023", "3073", "3084", "3093", "3123", "3201", "3251"}
    assert len({por_codcur[c] for c in piloto}) == 1


def test_t81c_curriculo_sem_exigencia_forma_o_grupo_vazio_por_ultimo():
    from usp_mcp.jupiter import ferramentas

    a = {"codcur": "1", "exigencias": [{"sigla": "X", "nome": "x", "tipo": "requisito", "rotulo": "Requisito"}]}
    vazio = {"codcur": "2", "exigencias": []}
    grupos = ferramentas.agrupar_curriculos([vazio, a])
    assert grupos[-1][0] == () and grupos[-1][1] == [vazio]
```

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/jupiter/test_requisitos_cliente.py -q -k t81
```
Esperado: 3 FAILED com `AttributeError: ... 'agrupar_curriculos'`.

- [ ] **Passo 3: implementar**

No fim de `usp_mcp/jupiter/ferramentas.py`:

```python
def agrupar_curriculos(curriculos: list[dict]) -> list[tuple[tuple, list[dict]]]:
    """Currículos com o MESMO conjunto de exigências, nos mesmos termos, juntos.

    A chave é o conjunto ordenado de (sigla, nome, tipo, rótulo). O tipo entra
    de propósito: MAT2454 é dura em 3250 e fraca em 3032, e os dois NÃO podem
    cair no mesmo grupo — é a informação que decide a matrícula (§9, 14/09).
    Em MAT2455, 23 currículos viram 4 grupos sem perder um currículo nem um tipo.

    Maiores primeiro; o grupo sem exigência (`()`) por último; dentro do grupo,
    a ordem em que vieram (a da página, crescente de codcur).
    """
    grupos: dict[tuple, list[dict]] = {}
    for curriculo in curriculos:
        chave = tuple(
            sorted((e["sigla"], e["nome"], e["tipo"], e["rotulo"]) for e in curriculo["exigencias"])
        )
        grupos.setdefault(chave, []).append(curriculo)
    return sorted(grupos.items(), key=lambda item: (item[0] == (), -len(item[1]), item[0]))
```

- [ ] **Passo 4: rodar os testes**

```bash
.venv/bin/python -m pytest tests/jupiter/test_requisitos_cliente.py -q
```
Esperado: tudo verde.

- [ ] **Passo 5: commit**

```bash
git add usp_mcp/jupiter/ferramentas.py tests/jupiter/test_requisitos_cliente.py
git commit -m "feat(jupiter): agrupar currículos com a mesma combinação de exigências"
```

---

### Tarefa 2: `formatar_requisitos` por grupo, com teto

**Arquivos:**
- Modificar: `usp_mcp/jupiter/server.py` — `formatar_requisitos` (substituir) e duas funções
  auxiliares novas; import de `agrupar_curriculos`
- Testar: `tests/jupiter/test_requisitos_fronteira.py`

**Interfaces:**
- Consome: `agrupar_curriculos` (Tarefa 1), `rotulo_de` (já existe em `server.py`).

- [ ] **Passo 1: escrever os testes que falham**

No fim de `tests/jupiter/test_requisitos_fronteira.py`:

```python
def _texto_de(sigla, html, ingresso_poli, colegiados):
    c = cliente.ClienteJupiter(
        Gravador([colegiados, ingresso_poli]), transporte_get=GravadorGet(html)
    )
    return server.chamar_ferramenta("requisitos", {"sigla": sigla}, cliente=c)


def test_t82_mat2455_sai_por_combinacao_e_cabe_em_3500_bytes(
    mat2455_html, ingresso_poli, colegiados
):
    # Medido em 14/09/2026: 6.238 B por currículo → 2.458 B por combinação. Folga ~40%.
    saida = _texto_de("MAT2455", mat2455_html, ingresso_poli, colegiados)

    assert len(saida.encode()) <= 3_500, f"{len(saida.encode())} B"
    assert "23 currículos, 4 combinações" in saida
    assert saida.count("3033") == 1, "cada currículo aparece uma vez"
    assert saida.count("Cálculo Diferencial e Integral II") <= 3, "uma vez por grupo que a exige"


def test_t82b_a_marca_de_ingresso_sobrevive_ao_agrupamento(
    mat2455_html, ingresso_poli, colegiados
):
    saida = _texto_de("MAT2455", mat2455_html, ingresso_poli, colegiados)
    linha_3033 = next(l for l in saida.splitlines() if l.strip().startswith("3033 "))
    linha_3032 = next(l for l in saida.splitlines() if l.strip().startswith("3032 "))
    assert linha_3033.endswith("[curso de ingresso]")
    assert "[curso de ingresso]" not in linha_3032
    assert "Ciclo Básico - Engenharia Elétrica" in linha_3033
    assert "3º período ideal" in linha_3033


def test_t82c_duro_e_fraco_ficam_em_cabecalhos_diferentes(
    mat2455_html, ingresso_poli, colegiados
):
    saida = _texto_de("MAT2455", mat2455_html, ingresso_poli, colegiados)
    cabecalhos = [l for l in saida.splitlines() if l.startswith("• ")]
    assert len(cabecalhos) == 4
    assert any(l.startswith("• Pré-requisito: MAT2454") for l in cabecalhos), "o grupo do 3250 (duro)"
    assert any(l.startswith("• Requisito fraco (dá para matricular devendo): MAT2454") for l in cabecalhos)
    assert any("2000101" in l for l in cabecalhos)


def test_t82d_um_curriculo_so_continua_legivel(psi3323_html, ingresso_poli, colegiados):
    saida = _texto_de("PSI3323", psi3323_html, ingresso_poli, colegiados)
    assert saida.startswith("Exigências para cursar PSI3323, por currículo:")
    assert "combinações" not in saida
    assert "• Correquisito (cursa junto): PSI3322" in saida
    assert "3032 " in saida
```

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/jupiter/test_requisitos_fronteira.py -q -k t82
```
Esperado: 4 FAILED.

- [ ] **Passo 3: implementar**

Em `usp_mcp/jupiter/server.py`:

(a) troque o import `from .ferramentas import disciplina, requisitos` para incluir
`agrupar_curriculos` (por exemplo
`from .ferramentas import agrupar_curriculos, disciplina, requisitos` — mantenha o que mais
já estiver importado ali).

(b) substitua a função `formatar_requisitos` inteira por:

```python
def _cabecalho_do_grupo(chave: tuple) -> str:
    """As exigências de um grupo, agrupadas por rótulo: `Rótulo: A — nome; B — nome`."""
    if not chave:
        return "• (a página não traz linha de exigência para estes)"
    por_rotulo: dict[str, list[str]] = {}
    for sigla, nome, tipo, _rotulo in chave:
        por_rotulo.setdefault(rotulo_de({"tipo": tipo}), []).append(f"{sigla} — {nome}")
    return "• " + " | ".join(f"{r}: {'; '.join(itens)}" for r, itens in por_rotulo.items())


def _linha_do_curriculo(c: dict) -> str:
    marca = " [curso de ingresso]" if c["ingresso"] else ""
    return (
        f"    {c['codcur']} {c['habilitacao']} "
        f"({c['periodo']}, {c['periodo_ideal']}º período ideal){marca}"
    )


def formatar_requisitos(ficha: dict) -> str:
    """Texto para o modelo ler, agrupado por COMBINAÇÃO de exigências.

    O agrupamento não é estética: o tipo da exigência é propriedade do currículo
    (MAT2454 é dura em Minas e fraca em Elétrica), e a chave do grupo carrega o
    tipo — 3250 fica sozinho justamente por isso. O que sai é a repetição: em
    MAT2455, 18 dos 23 currículos tinham as mesmas duas linhas (§9, 14/09).
    """
    curriculos = ficha["curriculos"]
    # Sem currículo, o cabeçalho prometeria uma lista que não vem — e promessa
    # não cumprida na primeira linha é o que faz o modelo preencher o resto.
    if not curriculos:
        linhas = [f"Não há exigência listada para {ficha['sigla']} — leia o aviso:"]
    else:
        grupos = agrupar_curriculos(curriculos)
        if len(curriculos) == 1:
            linhas = [f"Exigências para cursar {ficha['sigla']}, por currículo:"]
        else:
            linhas = [
                f"Exigências para cursar {ficha['sigla']} — {len(curriculos)} "
                f"currículos, {len(grupos)} combinações diferentes:"
            ]
        for chave, membros in grupos:
            linhas.append("")
            linhas.append(_cabecalho_do_grupo(chave))
            linhas.extend(_linha_do_curriculo(c) for c in membros)

    for aviso in ficha.get("avisos") or ():
        linhas.append(f"\n⚠ {aviso}")

    return "\n".join(linhas)
```

- [ ] **Passo 4: rodar a suíte do Jupiter**

```bash
.venv/bin/python -m pytest tests/jupiter -q
```
Esperado: tudo verde, inclusive T70 (a linha de PSI3322 é o cabeçalho `• Correquisito
(cursa junto): PSI3322 — ...`, sem "pré-requisito"), T71 (`devendo`, `3032`, `3250`) e
T72 (o aviso de PTC3313).

- [ ] **Passo 5: olhar a saída**

```bash
.venv/bin/python - <<'PY'
from tests.jupiter.conftest import Gravador, html, FIXTURES, REQUISITOS
from tests.jupiter.test_requisitos_cliente import GravadorGet
from usp_mcp.jupiter import cliente, server
ler = lambda k: (FIXTURES / REQUISITOS[k]).read_text(encoding="utf-8")
c = cliente.ClienteJupiter(Gravador([ler("colegiados"), ler("ingresso_poli")]), transporte_get=GravadorGet(html("mat2455_html")))
t = server.chamar_ferramenta("requisitos", {"sigla": "MAT2455"}, cliente=c)
print(t); print("---", len(t.encode()), "bytes")
PY
```
Esperado: 4 cabeçalhos `• ...`, 23 linhas de currículo, o aviso no fim, menos de 3.500 bytes.

- [ ] **Passo 6: commit**

```bash
git add usp_mcp/jupiter/server.py tests/jupiter/test_requisitos_fronteira.py
git commit -m "feat(jupiter): requisitos por combinação — 23 currículos de MAT2455 em 4 blocos"
```

---

### Tarefa 3: registro e PR

**Arquivos:**
- Modificar: `SPEC1.md` (fim do §9)

- [ ] **Passo 1: §9 do `SPEC1.md`**

```markdown
### 14/09/2026 — `requisitos` agrupa currículos com a mesma combinação

Medido em `formatar_requisitos` sobre a fixture de MAT2455: 6.238 B, 23 blocos, 18 deles
com exatamente as mesmas duas linhas. Agrupando pelo conjunto exato de (sigla, nome, tipo,
rótulo): **4 combinações** — 13 currículos com MAT2454+MAT3458 fraco, 7 do piloto com
2000101, 2 com MAT2454+MAT2458 fraco, e o 3250 sozinho com as mesmas siglas como requisito
DURO. Texto agrupado: 2.458 B (2,5× menor). PSI3323 (1 currículo): 437 → 408 B.

**Decisão:** só formatação. A projeção continua por currículo; o texto sai por combinação,
com cada currículo numa linha (código, habilitação, período, período ideal, marca de
ingresso). O agrupamento preserva por construção o que o desenho de 14/09 protege — o tipo
é propriedade do currículo — porque o tipo está na chave. Teto: 3.500 B (T82). Testes
T81–T82d; T70–T72 não precisaram mudar.
```

- [ ] **Passo 2: gate, commit e PR**

```bash
./scripts/gate.sh
git add SPEC1.md
git commit -m "docs(spec): §9 — requisitos por combinação de exigências"
git push -u origin feat/jupiter-requisitos-agrupados
gh pr create --base main --title "feat(jupiter): requisitos agrupados por combinação" --body "Spec: docs/superpowers/specs/2026-09-14-jupiter-requisitos-agrupados-design.md. Plano: docs/superpowers/plans/2026-09-14-jupiter-requisitos-agrupados.md. Só formatação; projeção e política intactas."
```
Esperado: `gate: PASSOU`.
