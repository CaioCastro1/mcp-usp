# Ficha por seção, e uma ferramenta por pergunta — Plano de Implementação

> **Para quem executa:** implemente tarefa por tarefa, na ordem em que estão escritas.
> Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** `disciplina` ganha o parâmetro `secoes` (padrão: só a ementa), perde
`codcur`/`codhab` (o pré-requisito é da ferramenta `requisitos`), deduplica parágrafo
repetido na fonte, e passa a ter teto de custo sobre o **texto** que o modelo lê.
"Quantos créditos tem PTC3314" cai de 3.880 B para menos de 1.200 B.

**Arquitetura:** o filtro de seção é na projeção (`ferramentas.disciplina`), não só na
formatação; `server.py` declara o schema, formata e despacha; `cliente.py` e `politica.py`
**perdem** a consulta `pubListarRequisitoDisciplina` (allowlist 4 → 3). Nada é acrescentado
à superfície contra a USP.

**Stack:** Python 3.13, stdlib. Testes com pytest, offline, contra fixture.

**Spec:** `docs/superpowers/specs/2026-09-14-jupiter-disciplina-secoes-design.md` — leia
antes de começar.

## Restrições globais

- **Nenhuma requisição de rede na suíte.** Tudo com o `Gravador` de `tests/jupiter/conftest.py`.
- **A allowlist só encolhe.** Nenhuma consulta nova; `pubListarRequisitoDisciplina` sai.
- **O `enum` declarado e o `Literal` de `main()` têm de ser iguais.** O handshake H6–H8 compara
  os dois no fio; rode `tests/handshake` sempre que tocar o schema.
- **Carga horária continua calculada** (`creaul*15 + cretrb*30`); nada lê `cgahoreto`.
- **Português** em docstring, mensagem e comentário.
- **Antes de cada commit:** `./scripts/gate.sh` verde.
- **Mensagem de commit:** `feat|fix|test|docs(jupiter): descrição`. Se o seu harness pedir
  uma linha de coautoria, acrescente-a ao fim.
- **Branch:** `feat/jupiter-disciplina-secoes`, saindo da `main`.
- Suíte: `.venv/bin/python -m pytest tests/jupiter tests/handshake -q`.

---

### Tarefa 1: `disciplina` por seção, sem curso, sem parágrafo repetido

**Arquivos:**
- Modificar: `usp_mcp/jupiter/ferramentas.py` — imports, `CAMPOS_PT`, e todo o trecho entre
  `_TEXTO_EN = (...)` e o comentário `# --- a fatia de 14/09: o requisito pela sigla, não pelo curso`
- Modificar: `tests/jupiter/test_disciplina.py` — T28, T29, T30 (ajustar), T31 e T33
  (remover), T80–T80g (novos)

**Interfaces:**
- Produz: `SECOES = ("ementa", "objetivos", "programa", "bibliografia", "avaliacao")`,
  `SECOES_PADRAO = ("ementa",)`, `AVISO_PRE_REQUISITO: str`,
  `resolver_secoes(pedidas) -> tuple[str, ...]`,
  `disciplina(sigla, *, cliente, secoes=SECOES_PADRAO, idiomas=("pt",)) -> dict` com as chaves
  novas `secoes: list[str]` e `secoes_omitidas: list[str]`, e **sem** `pre_requisito`.

- [ ] **Passo 1: ajustar os testes existentes e escrever os novos (falham primeiro)**

Em `tests/jupiter/test_disciplina.py`:

(a) No import, troque `from usp_mcp.jupiter import cliente, dwr, ferramentas` por
`from usp_mcp.jupiter import cliente, dwr, erros, ferramentas`.

(b) Em `test_t28_...`, troque `d = ferramentas.disciplina("PSI3323", cliente=c)` por
`d = ferramentas.disciplina("PSI3323", cliente=c, secoes=("ementa", "programa"))`.

(c) Em `test_t29_...`, troque
`    assert not [k for k, v in d.items() if v in ("", None) and k != "pre_requisito"]`
por
`    assert not [k for k, v in d.items() if v in ("", None)]`.

(d) Substitua `test_t30_sem_curso_a_ferramenta_diz_o_que_nao_sabe` inteira por:

```python
def test_t30_a_ferramenta_diz_onde_esta_o_pre_requisito_em_vez_de_calar(gravador, psi3323):
    g = gravador([psi3323])
    d = ferramentas.disciplina("PSI3323", cliente=cliente.ClienteJupiter(g))

    assert len(g.chamadas) == 1, "uma ficha é UMA chamada"
    assert "pre_requisito" not in d, "o pré-requisito é da ferramenta `requisitos` desde 14/09"

    avisos = " ".join(d["avisos"]).lower()
    assert "requisitos" in avisos, "Invariante 7: diz onde está, em vez de omitir calado"
    for mentira in ("sem pré-requisito", "não tem pré-requisito", "nenhum pré-requisito"):
        assert mentira not in avisos, f"afirmou {mentira!r} sem ter consultado"
```

(e) **Remova** `test_t31_com_curso_duas_chamadas_e_requisito_estruturado` e
`test_t33_discrepancia_codcur_e_declarada_nao_resolvida` inteiros (o caminho por curso
deixa de existir; a decisão vai para o §9 na Tarefa 4).

(f) No fim do arquivo, acrescente:

```python
# --- T80: a ficha por seção (14/09/2026) -------------------------------------


def test_t80_por_padrao_vem_o_cabecalho_e_a_ementa_e_mais_nada(gravador, ptc3314):
    d = ferramentas.disciplina("PTC3314", cliente=cliente.ClienteJupiter(gravador([ptc3314])))

    assert d["creditos_aula"] == 4 and d["carga_horaria_total"] == 60
    assert "ementa" in d
    for fora in ("objetivos", "programa", "bibliografia",
                 "metodo_avaliacao", "criterio_avaliacao", "norma_recuperacao"):
        assert fora not in d, f"{fora} veio sem ser pedido"
    assert d["secoes"] == ["ementa"]
    assert d["secoes_omitidas"] == ["objetivos", "programa", "bibliografia", "avaliacao"]
    assert d["avisos"] == [ferramentas.AVISO_PRE_REQUISITO]


def test_t80b_avaliacao_junta_os_tres_campos(gravador, ptc3314):
    d = ferramentas.disciplina(
        "PTC3314", cliente=cliente.ClienteJupiter(gravador([ptc3314])), secoes=("avaliacao",)
    )
    assert {"metodo_avaliacao", "criterio_avaliacao", "norma_recuperacao"} <= set(d)
    assert "ementa" not in d
    assert d["secoes_omitidas"] == ["ementa", "objetivos", "programa", "bibliografia"]


def test_t80c_todas_traz_as_cinco_e_nao_omite_nada(gravador, ptc3314):
    d = ferramentas.disciplina(
        "PTC3314", cliente=cliente.ClienteJupiter(gravador([ptc3314])), secoes=ferramentas.SECOES
    )
    for dentro in ("ementa", "objetivos", "programa", "bibliografia", "metodo_avaliacao"):
        assert dentro in d
    assert d["secoes_omitidas"] == []


@pytest.mark.parametrize(
    "pedido,esperado",
    [
        (None, ("ementa",)),
        ([], ("ementa",)),
        (["programa", "ementa"], ("ementa", "programa")),  # ordem da ficha, não do pedido
        (["TODAS"], ferramentas.SECOES),
        (["todas", "ementa"], ferramentas.SECOES),
        (["Avaliacao", "avaliacao"], ("avaliacao",)),
    ],
)
def test_t80d_resolver_secoes(pedido, esperado):
    assert ferramentas.resolver_secoes(pedido) == esperado


def test_t80e_secao_desconhecida_e_erro_legivel_citando_as_validas():
    with pytest.raises(erros.ErroJupiter) as exc:
        ferramentas.resolver_secoes(["horario"])
    mensagem = str(exc.value)
    assert "horario" in mensagem and "ementa" in mensagem and "todas" in mensagem


def test_t80f_paragrafo_repetido_na_fonte_sai_uma_vez(gravador, ptc3314):
    d = ferramentas.disciplina(
        "PTC3314", cliente=cliente.ClienteJupiter(gravador([ptc3314])), secoes=("bibliografia",)
    )
    assert d["bibliografia"].count("Mariotto") == 1
    cru = dwr.decodificar(ptc3314)
    assert cru["dscbbgdis"].count("Mariotto") == 2, (
        "a fixture mudou e a dedupe perdeu o caso que a motivou; refaça a medição"
    )


def test_t80g_a_ferramenta_nao_aceita_curso():
    import inspect

    parametros = inspect.signature(ferramentas.disciplina).parameters
    assert "curso" not in parametros and "codcur" not in parametros
    assert "secoes" in parametros
```

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/jupiter/test_disciplina.py -q
```
Esperado: T28 falha com `TypeError: unexpected keyword argument 'secoes'`; T80* falham.

- [ ] **Passo 3: implementar**

Em `usp_mcp/jupiter/ferramentas.py`:

(a) No topo, troque `from . import requisitos as _recorte` por:

```python
import re

from . import requisitos as _recorte
from .erros import ErroJupiter
```

(b) Substitua `CAMPOS_PT` por:

```python
CAMPOS_PT = (
    "sigla", "nome", "creditos_aula", "creditos_trabalho", "carga_horaria_total",
    "tipo", "ativacao", "ementa", "objetivos", "programa", "bibliografia",
    "metodo_avaliacao", "criterio_avaliacao", "norma_recuperacao",
    "secoes", "secoes_omitidas", "avisos",
)
```

(c) Substitua **tudo** que está entre o fim de `_TEXTO_EN = (...)` e a linha de comentário
`# --- a fatia de 14/09: o requisito pela sigla, não pelo curso ---------------`
(isto é: o comentário e o dicionário `_DISCREPANCIA_CODCUR`, `normalizar_sigla`,
`_preencher` e a função `disciplina` inteira) por:

```python
# As seções da ficha que o modelo pode pedir, na ordem em que a pessoa lê. O
# cabeçalho (sigla, nome, créditos, carga, tipo, ativação) vem sempre e não é
# seção: é a resposta de "quantos créditos". `avaliacao` junta três campos
# porque ninguém pergunta "qual a norma de recuperação" separado do resto.
SECOES: tuple[str, ...] = ("ementa", "objetivos", "programa", "bibliografia", "avaliacao")
SECOES_PADRAO: tuple[str, ...] = ("ementa",)
_CAMPOS_DA_SECAO: dict[str, tuple[str, ...]] = {
    "ementa": ("ementa", "ementa_en"),
    "objetivos": ("objetivos", "objetivos_en"),
    "programa": ("programa", "programa_en"),
    "bibliografia": ("bibliografia",),
    "avaliacao": ("metodo_avaliacao", "criterio_avaliacao", "norma_recuperacao"),
}

# Curto e fixo: a descrição da ferramenta já diz o mesmo, e o aviso existe para
# a resposta não parecer completa quando a pergunta era sobre pré-requisito.
AVISO_PRE_REQUISITO = (
    "Pré-requisito não vem por aqui: use a ferramenta requisitos com a mesma sigla."
)

_PARAGRAFO = re.compile(r"\n\s*\n")


def normalizar_sigla(bruta: str) -> str:
    """`psi 3323` e `  PSI3323 ` são a mesma disciplina para quem pergunta."""
    return "".join(bruta.split()).upper()


def resolver_secoes(pedidas) -> tuple[str, ...]:
    """Lista pedida pelo modelo → seções válidas, na ordem fixa da ficha.

    Vazio é o padrão (só a ementa); 'todas' expande; nome desconhecido é erro
    legível citando as válidas, não silêncio (Invariante 6).
    """
    if not pedidas:
        return SECOES_PADRAO
    escolhidas: set[str] = set()
    for pedida in pedidas:
        chave = str(pedida).strip().lower()
        if chave == "todas":
            return SECOES
        if chave not in SECOES:
            raise ErroJupiter(
                f"seção {pedida!r} não existe na ficha. Use "
                f"{', '.join(SECOES)} ou 'todas'."
            )
        escolhidas.add(chave)
    return tuple(s for s in SECOES if s in escolhidas)


def _sem_paragrafos_repetidos(texto: str) -> str:
    """A fonte às vezes repete um parágrafo inteiro — a bibliografia de PTC3314
    vem duplicada. Parágrafo idêntico (comparado sem diferença de espaçamento)
    sai uma vez, na primeira posição. Não é perda: é a fonte que se repetiu."""
    vistos: set[str] = set()
    saida: list[str] = []
    for paragrafo in _PARAGRAFO.split(texto.strip()):
        chave = re.sub(r"\s+", " ", paragrafo).strip()
        if chave and chave not in vistos:
            vistos.add(chave)
            saida.append(paragrafo.strip())
    return "\n\n".join(saida)


def _preencher(destino: dict, cru: dict, pares, campos: set[str]) -> None:
    for saida, campo in pares:
        if saida not in campos:
            continue
        valor = cru.get(campo)
        if valor in ("", None):
            continue
        destino[saida] = _sem_paragrafos_repetidos(valor) if isinstance(valor, str) else valor


def disciplina(sigla: str, *, cliente, secoes: tuple[str, ...] = SECOES_PADRAO,
               idiomas: tuple[str, ...] = ("pt",)) -> dict:
    """Ficha da disciplina: cabeçalho sempre, e as seções pedidas.

    Pré-requisito não é desta ferramenta desde 14/09 (§9): o único `codcur` que
    a API deixa descobrir devolve zero linha, e `requisitos(sigla)` responde sem
    código de curso. O aviso fixo aponta para lá, e o schema não oferece `codcur`.
    """
    sigla = normalizar_sigla(sigla)
    cru = cliente.obter_disciplina(sigla)

    aula, trabalho = int(cru["creaul"]), int(cru["cretrb"])
    ficha: dict = {
        "sigla": cru["coddis"],
        "nome": cru["nomdis"],
        "creditos_aula": aula,
        "creditos_trabalho": trabalho,
        # Calculada. O campo cgahoreto do DWR vem "0" e não é usado.
        "carga_horaria_total": aula * 15 + trabalho * 30,
        "tipo": _TIPOS.get(cru["tipdis"], cru["tipdis"]),
        "ativacao": cru["dtaatvdis"],
    }

    campos = {campo for secao in secoes for campo in _CAMPOS_DA_SECAO[secao]}
    _preencher(ficha, cru, _TEXTO_PT, campos)
    if "en" in idiomas:
        # O nome em inglês é cabeçalho, não seção: vem sempre que inglês é pedido.
        _preencher(ficha, cru, _TEXTO_EN, campos | {"nome_en"})
    # Espanhol nunca sai: os quatro campos vêm vazios nas duas amostras da
    # Fase 1, e campo vazio é token gasto para dizer nada.

    ficha["secoes"] = list(secoes)
    # Invariante 7: o que ficou de fora é dito, não omitido.
    ficha["secoes_omitidas"] = [s for s in SECOES if s not in secoes]
    ficha["avisos"] = [AVISO_PRE_REQUISITO]
    return ficha
```

(d) Na docstring do módulo, substitua o parágrafo que começa com `**O pré-requisito é
condicional ao curso.**` por:

```
**O pré-requisito não é desta ferramenta.** Ele depende do currículo, e o único
`codcur` que a API deixa descobrir devolve zero linha para as disciplinas do dono
(§9, 14/09). `requisitos(sigla)` responde sem código de curso; esta ficha só aponta
para lá — e não oferece `codcur` no schema para o modelo não trilhar o caminho errado.

**A ficha vem por seção.** "Quantos créditos" é o cabeçalho (139 B); a ficha inteira
de PTC3314 são 3.880 B, 38% deles a lista de competências dos objetivos. Por padrão
sai só a ementa, o resto sob pedido — e o que ficou de fora é declarado no fim.
```

- [ ] **Passo 4: rodar os testes da ferramenta**

```bash
.venv/bin/python -m pytest tests/jupiter/test_disciplina.py -q
```
Esperado: tudo verde. (Outros arquivos da suíte ainda quebram — `server.py` e `test_custo`
são a Tarefa 3.)

- [ ] **Passo 5: commit parcial**

```bash
git add usp_mcp/jupiter/ferramentas.py tests/jupiter/test_disciplina.py
git commit -m "feat(jupiter): ficha por seção, sem código de curso, sem parágrafo repetido"
```

---

### Tarefa 2: a consulta de requisito por curso sai do cliente e da allowlist

**Arquivos:**
- Modificar: `usp_mcp/jupiter/cliente.py` — remover o método `listar_requisito`
- Modificar: `usp_mcp/jupiter/politica.py` — `CONSULTAS_PERMITIDAS`
- Modificar: `tests/jupiter/test_cliente.py` — T16 e T23
- Modificar: `tests/jupiter/conftest.py` — `FATIA` e a fixture `requisito`
- Modificar: `tests/jupiter/test_requisitos_fronteira.py` — remover T76, T78, T79

**Interfaces:**
- Produz: `set(CONSULTAS_PERMITIDAS) == {"pubObterDisciplina", "pubListarCursoEntrada", "pubListarColegiado"}`.

- [ ] **Passo 1: ajustar os testes (falham primeiro)**

Em `tests/jupiter/test_cliente.py`:

(a) Substitua `test_t16_roteamento_do_metodo` inteira por:

```python
@pytest.mark.contrato
def test_t16_roteamento_do_metodo(gravador, psi3323, ingresso_poli):
    g1 = gravador([psi3323])
    cliente.ClienteJupiter(g1).obter_disciplina("PSI3323")
    assert g1.chamadas[0]["url"].endswith("ControlePublicoDWR.obter.dwr")

    g2 = gravador([ingresso_poli])
    cliente.ClienteJupiter(g2).listar_cursos_entrada("3")
    assert g2.chamadas[0]["url"].endswith("ControlePublicoDWR.listar.dwr")
```

(b) Em `test_t23_superficie_travada_em_quatro_consultas`, renomeie para
`test_t23_superficie_travada_em_tres_consultas` e troque o `assert` do conjunto por:

```python
    assert set(cliente.CONSULTAS_PERMITIDAS) == {
        "pubObterDisciplina",
        "pubListarCursoEntrada",
        "pubListarColegiado",
    }, "a fatia tem três consultas; uma quarta precisa de decisão registrada no §9"
```

(c) Se o arquivo tiver a lista `CONSULTAS_FORA_DA_FATIA`, acrescente
`"pubListarRequisitoDisciplina"` a ela (a consulta removida tem de ser negada como
qualquer outra).

Em `tests/jupiter/conftest.py`: remova a linha
`    "requisito": "dwr-pubListarRequisitoDisciplina-MAT2454.txt",` de `FATIA` e a fixture

```python
@pytest.fixture
def requisito():
    return texto("requisito")
```

Em `tests/jupiter/test_requisitos_fronteira.py`: **remova** as funções
`test_t76_o_caminho_dwr_tambem_distingue_fraco_de_duro`,
`test_t78_requisito_vazio_cita_a_terceira_causa_e_manda_para_requisitos` e
`test_t79_o_aviso_da_discrepancia_nao_diz_mais_nao_verificada` inteiras, com os
decoradores. Mantenha T73 (`disciplina` sem curso aponta para `requisitos`).

Confirme que nada mais usa a fixture removida:

```bash
grep -rn "requisito\b" tests/jupiter --include="*.py" | grep -v "requisitos\|_recorte\|# "
```
Esperado: nenhuma linha que use `requisito` como parâmetro de teste.

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/jupiter/test_cliente.py -q -k "t16 or t23"
```
Esperado: T23 FAILED (o conjunto ainda tem quatro).

- [ ] **Passo 3: implementar**

Em `usp_mcp/jupiter/cliente.py`, remova o método `listar_requisito` inteiro (da linha
`    def listar_requisito(self, *, coddis: str, codcur: str, codhab: str) -> list:` até o
`)` que fecha o `return self._chamar(...)`).

Em `usp_mcp/jupiter/politica.py`, substitua `CONSULTAS_PERMITIDAS` por:

```python
# Fatia vertical: a ficha da disciplina, e as duas consultas de navegação que
# marcam se um `codcur` é curso de ingresso (fatia de requisitos, 14/09).
# `pubListarRequisitoDisciplina` SAIU em 14/09: exigia um `codcur` que a API não
# deixa descobrir corretamente, e `requisitos(sigla)` responde sem ele (§9).
# Crescer isto é decisão registrada no §9, não conveniência.
CONSULTAS_PERMITIDAS: dict[str, str] = {
    "pubObterDisciplina": "obter",
    "pubListarCursoEntrada": "listar",
    "pubListarColegiado": "listar",
}
```

- [ ] **Passo 4: rodar a suíte do Jupiter (menos a fronteira, que é a Tarefa 3)**

```bash
.venv/bin/python -m pytest tests/jupiter -q --ignore=tests/jupiter/test_server_mcp.py --ignore=tests/jupiter/test_custo.py --ignore=tests/jupiter/test_requisitos_fronteira.py --ignore=tests/jupiter/test_server_stdio.py
```
Esperado: tudo verde.

- [ ] **Passo 5: commit**

```bash
git add usp_mcp/jupiter/cliente.py usp_mcp/jupiter/politica.py tests/jupiter/test_cliente.py tests/jupiter/conftest.py tests/jupiter/test_requisitos_fronteira.py
git commit -m "feat(jupiter): pubListarRequisitoDisciplina sai da allowlist — a allowlist encolhe de 4 para 3"
```

---

### Tarefa 3: schema, descrição, formatação e o teto sobre o texto

**Arquivos:**
- Modificar: `usp_mcp/jupiter/server.py` — `listar_ferramentas()` (ferramenta `disciplina`),
  `formatar`, `chamar_ferramenta`, `main()`, `_auto_verificar`
- Modificar: `tests/jupiter/test_server_mcp.py` — T44 e novos T85–T87
- Modificar: `tests/jupiter/test_custo.py` — helper `saida`, T34, novos T34b–T34d

**Interfaces:**
- Consome: `resolver_secoes`, `SECOES`, `disciplina(secoes=...)` (Tarefa 1).
- Produz: schema de `disciplina` com propriedades exatamente `{"sigla", "secoes", "ingles"}`;
  `secoes.items.enum == ["ementa", "objetivos", "programa", "bibliografia", "avaliacao", "todas"]`
  e `secoes.default == ["ementa"]`.

- [ ] **Passo 1: ajustar e escrever os testes (falham primeiro)**

Em `tests/jupiter/test_server_mcp.py`, em `test_t44_fronteira_ponta_a_ponta_offline`, troque
`    assert "⚠" in texto and "curso" in texto, "o aviso do Invariante 7 sumiu na formatação"`
por
`    assert "⚠" in texto and "requisitos" in texto, "o aviso que aponta para `requisitos` sumiu"`
e acrescente no fim do arquivo:

```python
@pytest.mark.politica
def test_t85_o_schema_de_disciplina_tem_secoes_e_nao_tem_curso():
    (ferramenta,) = [f for f in server.listar_ferramentas() if f["name"] == "disciplina"]
    propriedades = ferramenta["inputSchema"]["properties"]

    assert set(propriedades) == {"sigla", "secoes", "ingles"}
    assert propriedades["secoes"]["items"]["enum"] == [
        "ementa", "objetivos", "programa", "bibliografia", "avaliacao", "todas"
    ]
    assert propriedades["secoes"]["default"] == ["ementa"]
    descricao = ferramenta["description"]
    assert "requisitos" in descricao, "a descrição tem que apontar para quem responde pré-requisito"
    for vazamento in ("codcur", "codhab"):
        assert vazamento not in descricao


@pytest.mark.contrato
def test_t86_o_texto_declara_as_secoes_que_ficaram_de_fora(ptc3314):
    c = cliente.ClienteJupiter(Gravador([ptc3314]))
    padrao = server.chamar_ferramenta("disciplina", {"sigla": "PTC3314"}, cliente=c)
    assert "Ementa:" in padrao and "Objetivos:" not in padrao
    assert "Seções não incluídas" in padrao and "objetivos" in padrao

    c2 = cliente.ClienteJupiter(Gravador([ptc3314]))
    tudo = server.chamar_ferramenta(
        "disciplina", {"sigla": "PTC3314", "secoes": ["todas"]}, cliente=c2
    )
    assert "Objetivos:" in tudo and "Bibliografia:" in tudo and "Norma de recuperação:" in tudo
    assert "Seções não incluídas" not in tudo


@pytest.mark.contrato
def test_t87_secao_desconhecida_na_fronteira_e_erro_legivel(ptc3314):
    c = cliente.ClienteJupiter(Gravador([ptc3314]))
    with pytest.raises(erros.ErroJupiter) as exc:
        server.chamar_ferramenta("disciplina", {"sigla": "PTC3314", "secoes": ["horario"]}, cliente=c)
    assert "horario" in str(exc.value) and "todas" in str(exc.value)
```

Em `tests/jupiter/test_custo.py`:

(a) troque o helper `saida` por:

```python
def saida(gravador, bruto, sigla, secoes=ferramentas.SECOES):
    return ferramentas.disciplina(
        sigla, cliente=cliente.ClienteJupiter(gravador([bruto])), secoes=secoes
    )
```
(T34, T35 e T36 passam a medir a ficha **inteira**, que é o pior caso do dicionário.)

(b) acrescente `from usp_mcp.jupiter import server` ao import e, no fim do arquivo:

```python
# O que o modelo lê é o TEXTO, não o dicionário. Medido em 14/09/2026 (PTC3314):
# padrão ~700 B, `todas` 3.880 B, `todas` + inglês ~6.700 B. Folga de ~30%.
TETO_TEXTO_PADRAO_B = 1_200
TETO_TEXTO_TODAS_B = 5_000
TETO_TEXTO_TODAS_INGLES_B = 8_500


def test_t34b_o_texto_padrao_responde_quantos_creditos_por_menos_de_1200_bytes(gravador, ptc3314):
    ficha = saida(gravador, ptc3314, "PTC3314", secoes=ferramentas.SECOES_PADRAO)
    texto = server.formatar(ficha)
    assert len(texto.encode()) <= TETO_TEXTO_PADRAO_B, f"padrão: {len(texto.encode())} B"
    assert "Créditos: 4 aula" in texto


def test_t34c_o_texto_com_todas_as_secoes_tem_teto(gravador, ptc3314):
    texto = server.formatar(saida(gravador, ptc3314, "PTC3314"))
    assert len(texto.encode()) <= TETO_TEXTO_TODAS_B, f"todas: {len(texto.encode())} B"


def test_t34d_o_texto_com_ingles_tem_teto(gravador, ptc3314):
    ficha = ferramentas.disciplina(
        "PTC3314", cliente=cliente.ClienteJupiter(gravador([ptc3314])),
        secoes=ferramentas.SECOES, idiomas=("pt", "en"),
    )
    texto = server.formatar(ficha)
    assert len(texto.encode()) <= TETO_TEXTO_TODAS_INGLES_B, f"inglês: {len(texto.encode())} B"
    assert "Ementa (inglês):" in texto
```

- [ ] **Passo 2: rodar para ver falhar**

```bash
.venv/bin/python -m pytest tests/jupiter/test_server_mcp.py tests/jupiter/test_custo.py -q
```
Esperado: T44, T85, T86, T87 e T34b FAILED; os demais podem falhar por `formatar` ainda
procurar `pre_requisito` (não procura mais depois do passo 3).

- [ ] **Passo 3: implementar em `usp_mcp/jupiter/server.py`**

(a) Troque `from .ferramentas import disciplina, requisitos` por
`from .ferramentas import disciplina, requisitos, resolver_secoes`.

(b) Em `listar_ferramentas()`, na ferramenta `disciplina`, substitua o valor de
`"description"` por:

```python
            "description": (
                "Ficha de uma disciplina no catálogo público do JupiterWeb (USP), "
                "pela sigla: nome, créditos e carga horária sempre, e sob pedido "
                "ementa, objetivos, programa, bibliografia e avaliação. Use para "
                "'quantos créditos tem PTC3314', 'qual a ementa de MAT2454', 'o "
                "que cai em PME3344' (programa), 'como é a avaliação'. Por padrão "
                "vem só nome, créditos e ementa — peça as outras partes em "
                "`secoes`. Para pré-requisito use a ferramenta `requisitos`. NÃO "
                "traz horário de aula, sala nem vagas, e não busca por nome: "
                "precisa da sigla."
            ),
```

e substitua as propriedades `codcur` e `codhab` (as duas inteiras) por esta única
propriedade, mantendo `sigla` antes e `ingles` depois:

```python
                    "secoes": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "ementa", "objetivos", "programa",
                                "bibliografia", "avaliacao", "todas",
                            ],
                        },
                        "description": (
                            "Quais partes da ficha vir além de nome, créditos e "
                            "carga horária. Padrão: só a ementa. 'avaliacao' "
                            "junta método, critério e recuperação; 'objetivos' e "
                            "'programa' são os textos mais longos. Use ['todas'] "
                            "para a ficha inteira."
                        ),
                        "default": ["ementa"],
                    },
```

(c) Em `formatar`, remova o bloco

```python
    exigencias = ficha.get("pre_requisito")
    if exigencias:
        for r in exigencias:
            linhas.append(f"{rotulo_de(r)}: {r['sigla']} ({r['nome']})")
```

e, logo depois do laço `for campo, rotulo in _ROTULOS: ...`, acrescente:

```python
    # Invariante 7 na ficha: o que não veio é dito, para o modelo saber que
    # existe mais e como pedir.
    if ficha.get("secoes_omitidas"):
        linhas.append(
            "\n(Seções não incluídas: " + ", ".join(ficha["secoes_omitidas"])
            + '. Peça-as em secoes, ou secoes=["todas"].)'
        )
```

(d) Em `chamar_ferramenta`, substitua o trecho final (de `codcur = argumentos.get("codcur")`
até o `return formatar(...)`) por:

```python
    idiomas = ("pt", "en") if argumentos.get("ingles") else ("pt",)
    return formatar(
        disciplina(
            argumentos["sigla"], cliente=cliente,
            secoes=resolver_secoes(argumentos.get("secoes")), idiomas=idiomas,
        )
    )
```

(e) Em `main()`, substitua `_disciplina` e o `anotar` dela por:

```python
    def _disciplina(sigla, secoes=None, ingles=False) -> str:
        # Assinatura explícita em vez de **kwargs: o SDK deriva daqui o schema
        # que o modelo vê, e **kwargs produziria ferramenta sem parâmetro.
        try:
            return chamar_ferramenta(
                _NOME_FERRAMENTA, {"sigla": sigla, "secoes": secoes, "ingles": ingles}
            )
        except ErroJupiter as exc:
            raise ToolError(str(exc)) from exc
```
e
```python
    anotar(
        _disciplina,
        por_nome[_NOME_FERRAMENTA]["inputSchema"],
        {
            "sigla": str,
            "secoes": list[Literal[
                "ementa", "objetivos", "programa", "bibliografia", "avaliacao", "todas"
            ]] | None,
            "ingles": bool,
        },
    )
```
Acrescente `from typing import Literal` junto dos imports internos de `main()` (depois de
`from usp_mcp.adaptador import anotar`).

(f) Substitua o corpo de `_auto_verificar` a partir de `import inspect` por:

```python
    import inspect

    servidor = _M(name="verificacao", version="0.0.0")

    @servidor.tool(name="disciplina", description="verificação")
    def _sonda_disciplina(sigla: str, secoes: list[str] | None = None,
                          ingles: bool = False) -> str:
        return ""

    @servidor.tool(name="requisitos", description="verificação")
    def _sonda_requisitos(sigla: str) -> str:
        return ""

    # Uma sonda por ferramenta declarada, nunca só a [0]: foi esse índice que
    # deixou a segunda ferramenta declarada e não anunciada em 14/09.
    sondas = {"disciplina": _sonda_disciplina, "requisitos": _sonda_requisitos}
    tudo_ok = True
    for ferramenta in listar_ferramentas():
        declarados = set(ferramenta["inputSchema"]["properties"])
        sonda = sondas.get(ferramenta["name"])
        reais = set(inspect.signature(sonda).parameters) if sonda else set()
        ok = declarados == reais
        tudo_ok = tudo_ok and ok
        print(f"schema x assinatura  : {ferramenta['name']:11}",
              "OK" if ok else f"DIVERGEM {declarados ^ reais}")
    return 0 if tudo_ok else 1
```

- [ ] **Passo 4: rodar tudo, inclusive o handshake e o `main()` em processo**

```bash
.venv/bin/python -m pytest tests/jupiter tests/handshake -q
.venv/bin/python -m usp_mcp.jupiter.server --auto-verificar
```
Esperado: tudo verde; o `--auto-verificar` imprime `OK` para `disciplina` e `requisitos`.
Se algum teste de `tests/jupiter/test_server_stdio.py` enumerar os parâmetros registrados
de `disciplina`, atualize-o para `{"sigla", "secoes", "ingles"}` — o teste está certo em
travar isso; só o conjunto mudou.

- [ ] **Passo 5: olhar o texto padrão**

```bash
.venv/bin/python - <<'PY'
from tests.jupiter.conftest import Gravador, texto
from usp_mcp.jupiter import cliente, server
c = cliente.ClienteJupiter(Gravador([texto("ptc3314")]))
t = server.chamar_ferramenta("disciplina", {"sigla": "PTC3314"}, cliente=c)
print(t); print("---", len(t.encode()), "bytes")
PY
```
Esperado: cabeçalho, `Ementa:`, a linha `(Seções não incluídas: ...)`, o aviso de
`requisitos`, e menos de 1.200 bytes.

- [ ] **Passo 6: commit**

```bash
git add usp_mcp/jupiter/server.py tests/jupiter/test_server_mcp.py tests/jupiter/test_custo.py
git commit -m "feat(jupiter): 'secoes' no schema, rodapé do que ficou de fora, e teto de custo sobre o texto"
```

---

### Tarefa 4: registro, README e PR

**Arquivos:**
- Modificar: `SPEC1.md` (fim do §9)
- Modificar: `README.md` (linha da tabela `usp-jupiter | disciplina`)

- [ ] **Passo 1: §9 do `SPEC1.md`**

```markdown
### 14/09/2026 — `disciplina` responde por seção, e deixa o pré-requisito com `requisitos`

Revisão de má prática nos servidores públicos. Medido em `server.formatar` sobre as
fixtures: "quantos créditos tem PTC3314" é respondida pelo cabeçalho (139 B) e a
ferramenta entregava 3.880 B — 28×; 38% disso era a lista de competências dos objetivos.
O teste de custo (T34) media o dicionário, não o texto, e `ingles=True` (6.452 B) não era
medido em lugar nenhum.

**Decisão:** (a) parâmetro `secoes` (`ementa`, `objetivos`, `programa`, `bibliografia`,
`avaliacao`, `todas`), padrão só `ementa`, cabeçalho sempre, e o que ficou de fora
declarado na última linha (Invariante 7); (b) `codcur`/`codhab` **saem** de `disciplina`:
o §9 de 14/09 já tinha medido que o único código descobrível devolve zero linha, e manter
o parâmetro era oferecer ao modelo o caminho que não responde, com três avisos para
explicar por quê; (c) `pubListarRequisitoDisciplina` sai da allowlist (4 → 3) e
`ClienteJupiter.listar_requisito` some — a fixture DWR dela fica no disco como evidência,
fora da `FATIA`; (d) parágrafo repetido na fonte (bibliografia de PTC3314) sai uma vez;
(e) tetos novos sobre o **texto**: 1.200 B padrão, 5.000 B `todas`, 8.500 B `todas`+inglês.

**Descartado:** um enum de "nível de detalhe" (`resumo`/`completo`). Perguntas reais pedem
uma seção específica ("o que cai", "como é a avaliação"), e o array deixa o modelo pedir
exatamente essa. Testes T80–T80g, T85–T87, T34b–T34d; T31, T33, T76, T78 e T79 removidos
com o caminho que exercitavam.
```

- [ ] **Passo 2: README**

Troque a linha do `disciplina` na tabela por:

```markdown
| `usp-jupiter` | `disciplina` | Créditos, carga horária e ementa pela sigla; programa, bibliografia e avaliação sob pedido |
```

- [ ] **Passo 3: gate, commit e PR**

```bash
./scripts/gate.sh
git add SPEC1.md README.md
git commit -m "docs(spec): §9 — disciplina por seção, e o pré-requisito só em requisitos"
git push -u origin feat/jupiter-disciplina-secoes
gh pr create --base main --title "feat(jupiter): ficha por seção, sem código de curso" --body "Spec: docs/superpowers/specs/2026-09-14-jupiter-disciplina-secoes-design.md. Plano: docs/superpowers/plans/2026-09-14-jupiter-disciplina-secoes.md. Allowlist encolhe de 4 para 3 consultas."
```
Esperado: `gate: PASSOU`.
