# Comunicado no cardápio vira aviso — Plano de Implementação

> **Para quem executa:** SUB-SKILL OBRIGATÓRIA — use `superpowers:subagent-driven-development`
> (recomendado) ou `superpowers:executing-plans` para implementar tarefa por tarefa.
> Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** a linha `**Os Restaurantes Universitários não fornecem copos descartáveis.
Tragam suas canecas.**`, que o RUCard passou a anexar ao campo de cardápio em 14/09/2026,
deixa de sair como prato (três vezes por resposta) e vira **um** aviso no rodapé, nomeando
os RUs em que apareceu.

**Arquitetura:** só projeção. `_itens_e_opcao` em `usp_mcp/rucard/ferramentas.py` passa a
separar comunicado de prato e a devolver um quarto valor; `_projetar_refeicao` guarda isso
no campo novo `avisos_publicados`; `bandejao` agrega por texto e escreve um aviso por
comunicado distinto. `server.formatar` já imprime `avisos` com `⚠` e não muda.

**Stack:** Python 3.13, stdlib. Testes com pytest, offline, contra fixture.

**Spec:** `docs/superpowers/specs/2026-09-14-rucard-aviso-no-cardapio-design.md` — leia
antes de começar.

## Restrições globais

- **Nenhuma requisição de rede na suíte.** Tudo com o `Gravador` de `tests/rucard/conftest.py`.
- **Nenhuma rota nem allowlist nova.** Este plano não toca `politica.py` nem `cliente.py`.
- **Português** em docstring, mensagem e comentário.
- **Nada é descartado em silêncio** (Invariante 7): o comunicado sai da lista de itens e
  entra nos avisos; nunca some.
- **Antes de cada commit:** `./scripts/gate.sh` verde. O gate roda a suíte inteira offline.
- **Mensagem de commit:** `feat|fix|test|docs(rucard): descrição`. Se o seu harness pedir
  uma linha de coautoria, acrescente-a ao fim.
- **Branch:** `fix/rucard-comunicado-no-cardapio`, saindo da `main`.
- Rode a suíte com `.venv/bin/python -m pytest tests/rucard -q` (o venv já existe no
  checkout; se não existir: `uv venv && uv pip install -e ".[dev]"`).

---

### Tarefa 1: a fixture real entra na fatia

A fixture `fixtures/rucard/menu_7_semana_14-09.json` já foi capturada (2.784 B, RU 7,
semana 14/09 a 20/09/2026, dado público). Ela ainda não está no git nem na lista que a
suíte conhece.

**Arquivos:**
- Modificar: `tests/rucard/conftest.py` (dicionário `FATIA`, linhas ~21-33)
- Adicionar ao git: `fixtures/rucard/menu_7_semana_14-09.json`

**Interfaces:**
- Produz: a chave `"menu_7_avisos"` em `FATIA`, lida por `texto("menu_7_avisos")`.

- [ ] **Passo 1: confirmar que a fixture existe e tem o comunicado**

```bash
grep -c "canecas" fixtures/rucard/menu_7_semana_14-09.json
```
Esperado: `6` (cinco almoços de dia útil mais uma linha do JSON com o mesmo texto).
Se o arquivo não existir, pare: ele foi capturado em 14/09 e deve estar no checkout.

- [ ] **Passo 2: acrescentar a chave em `FATIA`**

Em `tests/rucard/conftest.py`, dentro de `FATIA`, depois da linha
`"menu_9_semana_seguinte": "menu_9_semana_31-08.json",` acrescente:

```python
    # O 7 na semana de 14/09: a primeira captura em que o campo de cardápio traz
    # um COMUNICADO em negrito markdown no fim de cada almoço. É a fixture do
    # caso "comunicado não é prato".
    "menu_7_avisos": "menu_7_semana_14-09.json",
```

- [ ] **Passo 3: rodar os testes de inventário**

```bash
git add fixtures/rucard/menu_7_semana_14-09.json
.venv/bin/python -m pytest tests/rucard/test_fixtures.py -q
```
Esperado: todos verdes (R1 exige que a fixture exista; R3 exige que não esteja
ignorada pelo git).

- [ ] **Passo 4: commit**

```bash
git add tests/rucard/conftest.py fixtures/rucard/menu_7_semana_14-09.json
git commit -m "test(rucard): fixture do RU 7 na semana de 14/09, com comunicado no cardápio"
```

---

### Tarefa 2: `_itens_e_opcao` separa comunicado de prato

**Arquivos:**
- Modificar: `usp_mcp/rucard/ferramentas.py` — função `_itens_e_opcao` (linhas ~95-118) e
  constantes logo acima dela
- Testar: `tests/rucard/test_bandejao.py` (acrescentar no fim)

**Interfaces:**
- Produz: `_itens_e_opcao(bruto) -> tuple[list[str], str | None, bool, list[str]]` — o
  quarto valor é a lista de comunicados (sem `**`, sem duplicata, na ordem em que apareceram).
- Produz: `_comunicado(linha: str) -> str | None`.

- [ ] **Passo 1: escrever os testes que falham**

No fim de `tests/rucard/test_bandejao.py`:

```python
# --- R42: comunicado no cardápio não é prato (14/09/2026) -------------------


def test_r42_itens_e_opcao_separa_comunicado_em_negrito_de_prato():
    itens, opcao, marcada, avisos = ferramentas._itens_e_opcao(
        "Arroz / feijão\nOpção: Falafel (V)\nMinipão / refresco\n\n"
        "**Os Restaurantes Universitários não fornecem copos descartáveis. "
        "Tragam suas canecas.**"
    )
    assert itens == ["Arroz / feijão", "Minipão / refresco"]
    assert opcao == "Falafel (V)" and marcada is True
    assert avisos == [
        "Os Restaurantes Universitários não fornecem copos descartáveis. "
        "Tragam suas canecas."
    ], "o comunicado tem que sair SEM os asteriscos e sem sumir"


def test_r42b_frase_longa_com_ponto_final_e_comunicado_mesmo_sem_negrito():
    itens, _, _, avisos = ferramentas._itens_e_opcao(
        "Arroz / feijão\n"
        "Os restaurantes estarão fechados na sexta-feira por causa do feriado.\n"
        "Maçã"
    )
    assert itens == ["Arroz / feijão", "Maçã"]
    assert avisos == [
        "Os restaurantes estarão fechados na sexta-feira por causa do feriado."
    ]


def test_r42c_prato_curto_com_ponto_nao_vira_comunicado():
    # A regra de frase exige 6+ palavras: um prato com ponto no fim continua prato.
    itens, _, _, avisos = ferramentas._itens_e_opcao("Bife à rolê.\nSalada de alface")
    assert itens == ["Bife à rolê.", "Salada de alface"]
    assert avisos == []


def test_r42d_o_mesmo_comunicado_duas_vezes_na_refeicao_sai_uma_vez():
    _, _, _, avisos = ferramentas._itens_e_opcao(
        "Arroz\n**Tragam suas canecas para o almoço de hoje.**\n"
        "**Tragam suas canecas para o almoço de hoje.**"
    )
    assert avisos == ["Tragam suas canecas para o almoço de hoje."]
```

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/rucard/test_bandejao.py -q -k r42
```
Esperado: 4 FAILED com `ValueError: not enough values to unpack (expected 4, got 3)`.

- [ ] **Passo 3: implementar**

Em `usp_mcp/rucard/ferramentas.py`, logo depois de
`_TAG_HTML = re.compile(r"<[^>]+>")`, acrescente:

```python
# Comunicado dentro do campo de cardápio — medido em 14/09/2026 no RU 7
# (`fixtures/rucard/menu_7_semana_14-09.json`): a linha inteira vem em negrito
# markdown, separada por linha em branco, nos cinco almoços de dia útil. Duas
# regras reconhecem comunicado, e as duas são declaradas aqui: negrito de ponta
# a ponta, ou frase de 6+ palavras terminada em ponto/exclamação — nome de prato
# não termina em ponto em nenhuma das ~120 refeições de fixture.
_AVISO_NEGRITO = re.compile(r"^\*\*(.+?)\*\*$")
_FIM_DE_FRASE = (".", "!")
_MINIMO_PALAVRAS_DE_FRASE = 6


def _comunicado(linha: str) -> str | None:
    """Texto do comunicado se a linha for aviso e não prato; `None` se for prato.

    Não descarta nada: quem chama põe o texto nos avisos da resposta. A regra é
    a medida, não a imaginada — um comunicado sem negrito e sem ponto final
    passa como prato, e esse é o limite declarado.
    """
    casou = _AVISO_NEGRITO.match(linha)
    if casou:
        return casou.group(1).strip()
    if linha.endswith(_FIM_DE_FRASE) and len(linha.split()) >= _MINIMO_PALAVRAS_DE_FRASE:
        return linha
    return None
```

E substitua a função `_itens_e_opcao` inteira por:

```python
def _itens_e_opcao(bruto: str) -> tuple[list[str], str | None, bool, list[str]]:
    """Texto livre do cardápio → itens, opção do dia, se a opção é marcada, e os
    comunicados que vieram misturados.

    O §1.2 registra que o texto às vezes vem com HTML e às vezes com ` - ` no
    lugar do `\\n`. Nenhuma das duas apareceu em três semanas de captura, então
    o tratamento aqui é tolerância, não teste: HTML sai, e ` - ` só é usado como
    separador quando não há quebra de linha nenhuma para usar.

    O que APARECEU, em 14/09/2026, foi comunicado em negrito no fim do cardápio
    ("Tragam suas canecas"). Ele sai da lista de itens e volta como aviso — a
    lista de pratos não pode ter um prato que não existe, e o comunicado não
    pode sumir (Invariante 7).
    """
    limpo = html.unescape(_TAG_HTML.sub(" ", bruto or ""))
    linhas = [l.strip() for l in limpo.splitlines() if l.strip()]
    if len(linhas) == 1 and " - " in linhas[0]:
        linhas = [p.strip() for p in linhas[0].split(" - ") if p.strip()]

    itens: list[str] = []
    avisos: list[str] = []
    opcao: str | None = None
    for linha in linhas:
        comunicado = _comunicado(linha)
        if comunicado is not None:
            if comunicado not in avisos:
                avisos.append(comunicado)
            continue
        if opcao is None and _PREFIXO_OPCAO.match(linha):
            opcao = _PREFIXO_OPCAO.sub("", linha).strip()
            continue
        itens.append(re.sub(r"\s{2,}", " ", linha))

    marcada = bool(opcao and _MARCA_VEGETARIANA.search(opcao))
    return itens, opcao, marcada, avisos
```

Em `_projetar_refeicao`, troque a linha
`itens, opcao, marcada = _itens_e_opcao(cru.get("menu", ""))` por
`itens, opcao, marcada, avisos_publicados = _itens_e_opcao(cru.get("menu", ""))`
(o campo novo entra no dicionário na Tarefa 3; por enquanto só o desempacotamento).

- [ ] **Passo 4: rodar os testes**

```bash
.venv/bin/python -m pytest tests/rucard -q
```
Esperado: tudo verde, inclusive R33c (os itens da Fase 1 não mudam).

- [ ] **Passo 5: commit**

```bash
git add usp_mcp/rucard/ferramentas.py tests/rucard/test_bandejao.py
git commit -m "fix(rucard): comunicado em negrito no cardápio deixa de sair como prato"
```

---

### Tarefa 3: o comunicado chega à resposta como um aviso só

**Arquivos:**
- Modificar: `usp_mcp/rucard/ferramentas.py` — `CAMPOS_REFEICAO` (linha ~50),
  `_projetar_refeicao` (ramo aberto, linhas ~185-196) e `bandejao` (laço dos RUs e bloco
  final de avisos)
- Testar: `tests/rucard/test_bandejao.py`

**Interfaces:**
- Consome: `_itens_e_opcao` de 4 valores (Tarefa 2), `texto("menu_7_avisos")` (Tarefa 1).
- Produz: chave `"avisos_publicados": list[str]` em toda refeição `aberto`; um aviso
  `aviso publicado no cardápio de <RU1>, <RU2>: <texto>` em `resposta["avisos"]` por
  comunicado distinto.

- [ ] **Passo 1: escrever os testes que falham**

No fim de `tests/rucard/test_bandejao.py`:

```python
SEGUNDA_14_09 = datetime.date(2026, 9, 14)  # semana da fixture `menu_7_avisos`

COMUNICADO_CANECAS = (
    "Os Restaurantes Universitários não fornecem copos descartáveis. "
    "Tragam suas canecas."
)


def test_r42e_o_comunicado_vira_um_aviso_nomeando_o_ru(
    gravador, chamar, respostas_da_fatia
):
    respostas = dict(respostas_da_fatia)
    respostas["menu/7"] = texto("menu_7_avisos")
    resposta, _ = chamar(
        transporte=gravador(respostas), hoje=SEGUNDA_14_09,
        restaurantes=["7"], refeicao="almoco",
    )

    almoco = refeicao_de(resposta, "7", "almoco")
    assert almoco["situacao"] == "aberto"
    assert not [i for i in almoco["itens"] if "canecas" in i or "**" in i], (
        "o comunicado continua na lista de pratos"
    )
    assert almoco["itens"][-1] == "Minipão / refresco"
    assert almoco["avisos_publicados"] == [COMUNICADO_CANECAS]

    (aviso,) = [a for a in resposta["avisos"] if "canecas" in a]
    assert "PUSP-CB" in aviso and "**" not in aviso


def test_r42f_o_mesmo_comunicado_em_dois_rus_e_um_aviso_com_os_dois_nomes(
    gravador, chamar, respostas_da_fatia
):
    # O payload do /menu não carrega o id do RU, então a mesma fixture serve
    # para o 7 e para o 8: é exatamente o caso real de 14/09, em que três RUs
    # publicaram o mesmo texto.
    respostas = dict(respostas_da_fatia)
    respostas["menu/7"] = texto("menu_7_avisos")
    respostas["menu/8"] = texto("menu_7_avisos")
    resposta, _ = chamar(
        transporte=gravador(respostas), hoje=SEGUNDA_14_09,
        restaurantes=["7", "8"], refeicao="almoco",
    )

    com_canecas = [a for a in resposta["avisos"] if "canecas" in a]
    assert len(com_canecas) == 1, com_canecas
    assert "PUSP-CB" in com_canecas[0] and "FÍSICA" in com_canecas[0]


def test_r42g_refeicao_sem_comunicado_tem_a_lista_vazia_e_nenhum_aviso(chamar):
    resposta, _ = chamar(hoje=SEGUNDA)
    for ru in resposta["restaurantes"]:
        for dados in ru["refeicoes"].values():
            if dados["situacao"] == "aberto":
                assert dados["avisos_publicados"] == []
    assert not [a for a in resposta["avisos"] if "publicado no cardápio" in a]
```

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/rucard/test_bandejao.py -q -k "r42e or r42f or r42g"
```
Esperado: 3 FAILED com `KeyError: 'avisos_publicados'`.

- [ ] **Passo 3: implementar**

Em `usp_mcp/rucard/ferramentas.py`:

(a) `CAMPOS_REFEICAO` passa a ser:

```python
CAMPOS_REFEICAO = (
    "situacao", "detalhe", "itens", "opcao", "opcao_vegetariana_marcada",
    "calorias", "horario", "preco_aluno", "avisos_publicados",
)
```

(b) No `return` do ramo aberto de `_projetar_refeicao`, acrescente a chave depois de
`"preco_aluno": ficha.precos_aluno.get(qual),`:

```python
        # Comunicado que veio dentro do cardápio (14/09/2026). Fica aqui por
        # refeição para a projeção ser fiel; quem agrega e nomeia os RUs é
        # `bandejao`, que enxerga os quatro.
        "avisos_publicados": avisos_publicados,
```

(c) Em `bandejao`, junto das outras listas de controle (depois de
`sem_o_dia: list[tuple[str, str, str]] = []`), acrescente:

```python
    # {texto do comunicado: [nomes dos RUs em que apareceu]} — um aviso por texto
    # distinto, e não um por RU por refeição: em 14/09 o mesmo texto veio em
    # três RUs e sairia três vezes.
    publicados: dict[str, list[str]] = {}
```

(d) Ainda em `bandejao`, logo depois do laço
`for q, projetada in refeicoes_projetadas.items(): ... sem_horario.append(...)`,
acrescente:

```python
        for projetada in refeicoes_projetadas.values():
            for comunicado in projetada.get("avisos_publicados") or ():
                nomes = publicados.setdefault(comunicado, [])
                if ficha.nome not in nomes:
                    nomes.append(ficha.nome)
```

(e) No bloco final de avisos, depois do `if sem_horario: ...` e antes do `return`,
acrescente:

```python
    for comunicado, nomes in publicados.items():
        avisos.append(
            f"aviso publicado no cardápio de {', '.join(nomes)}: {comunicado}"
        )
```

- [ ] **Passo 4: rodar a suíte do RUCard**

```bash
.venv/bin/python -m pytest tests/rucard -q
```
Esperado: tudo verde. R36 (trava categórica) passa porque `CAMPOS_REFEICAO` ganhou a
chave; R34 (teto de 4.500 B) passa porque as listas vazias custam ~200 B sobre os
3.367 B medidos.

- [ ] **Passo 5: ver o texto final com os próprios olhos**

```bash
.venv/bin/python - <<'PY'
import datetime
from tests.rucard.conftest import Gravador, HASH_DE_TESTE, texto
from usp_mcp.rucard import server
from usp_mcp.rucard.cliente import ClienteRucard
respostas = {"restaurants": texto("restaurantes"), "menu/7": texto("menu_7_avisos"), "menu/8": texto("menu_7_avisos")}
cli = ClienteRucard(Gravador(respostas), hash_rucard=HASH_DE_TESTE)
print(server.chamar_ferramenta("bandejao", {"dia": "14/09/2026", "refeicao": "almoco", "restaurantes": ["7", "8"]}, cliente=cli))
PY
```
Esperado: duas linhas de refeição sem "canecas" nos itens e, no fim, **uma** linha
`⚠ aviso publicado no cardápio de PUSP-CB, FÍSICA: Os Restaurantes Universitários ...`.

- [ ] **Passo 6: commit**

```bash
git add usp_mcp/rucard/ferramentas.py tests/rucard/test_bandejao.py
git commit -m "feat(rucard): comunicado do cardápio sai uma vez, como aviso, nomeando os RUs"
```

---

### Tarefa 4: registro da decisão e gate

**Arquivos:**
- Modificar: `SPEC1.md` (fim do §9, depois da última entrada de 14/09)
- Modificar: `usp_mcp/rucard/ferramentas.py` (docstring do módulo, parágrafo
  "**A opção do dia não é chamada de vegetariana sem a marca.**" — acrescentar um parágrafo)

- [ ] **Passo 1: acrescentar ao §9 do `SPEC1.md`**

No fim do arquivo:

```markdown
### 14/09/2026 — o RUCard passou a publicar comunicado dentro do cardápio

Chamada ao vivo `bandejao(hoje, almoco)` às 14h: três dos quatro RUs (7, 8 e 9)
terminam o campo `lunch.menu` com `**Os Restaurantes Universitários não fornecem
copos descartáveis. Tragam suas canecas.**` — negrito markdown, linha em branco antes,
nos cinco dias úteis da semana. Fixture pública capturada:
`fixtures/rucard/menu_7_semana_14-09.json` (2.784 B).

A ferramenta imprimia a linha como prato, três vezes na mesma resposta (~75 tokens
de lixo e um "prato" que não existe). É o caso que a docstring de `_itens_e_opcao`
previa como "tolerância, não teste" — para HTML e ` - `, que nunca vieram; o que
veio foi outro.

**Decisão:** linha em negrito de ponta a ponta, ou frase de 6+ palavras terminada em
ponto/exclamação, é comunicado: sai dos itens e entra em `avisos` **uma vez por texto
distinto**, nomeando os RUs. Campo novo `avisos_publicados` por refeição (trava R36
atualizada). Regra de 2 pontos medidos, não lei: comunicado sem negrito e sem ponto
final passa como prato, e isso está escrito no código. Testes R42–R42g.
```

- [ ] **Passo 2: atualizar a docstring do módulo**

Em `usp_mcp/rucard/ferramentas.py`, depois do parágrafo que começa com
`**A opção do dia não é chamada de vegetariana sem a marca.**`, acrescente:

```
**Comunicado não é prato.** Em 14/09/2026 o campo de cardápio passou a terminar
com um aviso em negrito ("Tragam suas canecas") em três RUs. Ele sai da lista de
itens e volta como UM aviso na resposta, nomeando os RUs — nunca some, e nunca
aparece como comida (§9, 14/09).
```

- [ ] **Passo 3: gate e commit**

```bash
./scripts/gate.sh
git add SPEC1.md usp_mcp/rucard/ferramentas.py
git commit -m "docs(spec): §9 — comunicado dentro do cardápio do RUCard, e a regra que o separa de prato"
```
Esperado: `gate: PASSOU`.

- [ ] **Passo 4: PR**

```bash
git push -u origin fix/rucard-comunicado-no-cardapio
gh pr create --base main --title "fix(rucard): comunicado no cardápio vira aviso, não prato" --body "Spec: docs/superpowers/specs/2026-09-14-rucard-aviso-no-cardapio-design.md. Plano: docs/superpowers/plans/2026-09-14-rucard-aviso-no-cardapio.md. Fixture pública nova: fixtures/rucard/menu_7_semana_14-09.json."
```
