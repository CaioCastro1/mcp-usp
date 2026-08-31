# Suíte de testes do Jupiter — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Escrever as 40 funções de teste que especificam a ferramenta `disciplina(sigla, curso=None)` do MCP do Jupiter, conforme `docs/superpowers/specs/2026-08-31-testes-jupiter-design.md`.

**Architecture:** TDD puro. A implementação (`usp_mcp/jupiter/*.py`) **não é escrita neste plano** — ela é a Fase 2, e o §4.10 do `CLAUDE.md` proíbe começá-la por conveniência. O entregável é a suíte vermelha. Três marcadores (`politica`, `contrato`, `live`) e transporte injetado; os testes leem fixture de `fixtures/jupiter/` e gravam a requisição que teria saído.

**Tech Stack:** Python 3 (stdlib) + pytest. Sem dependência de rede fora do marcador `live`.

## Global Constraints

- **O plano NÃO cria `usp_mcp/`.** Ao fim, 37 dos 40 testes falham por `ImportError`. Só T1–T3 passam — são a guarda de fixture, e não importam `usp_mcp`.
- **Critério de verde por tarefa:** os testes novos falham por `ImportError: No module named 'usp_mcp...'`, **não** por `SyntaxError`, `FileNotFoundError`, `fixture not found` nem erro de coleta. Um teste que falha pelo motivo errado não verifica nada (§6 do `CONVENTIONS.md`).
- **Fixtures da fatia** — exatamente estas quatro, todas versionadas em `fixtures/jupiter/`:
  `dwr-pubObterDisciplina-PSI3323.txt`, `dwr-pubObterDisciplina-PTC3314.txt`,
  `dwr-pubListarRequisitoDisciplina-MAT2454.txt`, `dwr-pubObterDisciplina-ERRO-sigla-inexistente.txt`.
- **Nunca ler fixture crua na janela.** `head -c` e medição, nunca `cat` de payload (§0 do `CONVENTIONS.md`).
- **Nomes de módulo, acordados com a suíte irmã do Moodle** (§7 do spec): `usp_mcp/jupiter/{dwr,cliente,ferramentas}.py`, testes em `tests/jupiter/`, nenhum `server.py` na raiz do pacote.
- **Mensagem de commit:** `feat|fix|chore|docs|test(escopo): descrição` (§4 do `CONVENTIONS.md`).
- **Marcador de rede:** `@pytest.mark.live` + `USP_MCP_LIVE=1`. Sem a variável, skip **com motivo escrito**.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `pytest.ini` | registra os 3 marcadores, `--strict-markers` |
| `requirements-dev.txt` | `pytest` — única dependência nova |
| `tests/jupiter/conftest.py` | caminho das fixtures, o transporte-gravador, fixtures de texto |
| `tests/jupiter/test_fixtures.py` | T1–T3 — guarda de fixture (`politica`) |
| `tests/jupiter/test_dwr.py` | T4–T12 — decodificação do envelope (`contrato`) |
| `tests/jupiter/test_cliente.py` | T13–T25 — corpo da requisição, cache, allowlist |
| `tests/jupiter/test_disciplina.py` | T26–T33 — a ferramenta |
| `tests/jupiter/test_custo.py` | T34–T37 — teto, núcleo, trava categórica |
| `tests/jupiter/test_live.py` | T38–T40 — canário (`live`) |

A allowlist mora em `test_cliente.py`, e não em arquivo próprio, porque a allowlist **é** a fronteira do cliente — o §4.4 do spec é uma seção, não um arquivo.

## Interfaces que os testes assumem

Os testes são a especificação destas assinaturas. A Fase 2 as implementa; nenhum teste as inventa em outro lugar.

```python
# usp_mcp/jupiter/dwr.py
class JupiterErro(Exception):
    """handleException do Jupiter. Tem .mensagem (a localizedMessage, em pt)."""
    mensagem: str

class RespostaInvalida(Exception):
    """Corpo que não é um envelope DWR íntegro."""

def decodificar(texto: str) -> dict | list: ...
def serializar(*, metodo: str, consulta: str, params: dict[str, object]) -> str: ...

# usp_mcp/jupiter/cliente.py
CONSULTAS_PERMITIDAS: dict[str, str]   # {"pubObterDisciplina": "obter", ...}
AGENTE: str
URL_BASE: str                          # https://uspdigital.usp.br/jupiterweb/dwr/call/plaincall

class ConsultaNegada(Exception): ...

class ClienteJupiter:
    def __init__(self, transporte, *, agente=AGENTE, relogio=time.monotonic): ...
    def _chamar(self, *, metodo: str, consulta: str, params: dict) -> dict | list: ...
    def obter_disciplina(self, sigla: str) -> dict: ...
    def listar_requisito(self, *, coddis: str, codcur: str, codhab: str) -> list[dict]: ...

def transporte_http(url: str, corpo: str, cabecalhos: dict[str, str]) -> tuple[int, str]: ...

# usp_mcp/jupiter/ferramentas.py
CAMPOS_SAIDA: frozenset[str]
def disciplina(sigla: str, curso: tuple[str, str] | None = None, *,
               cliente, idiomas: tuple[str, ...] = ("pt",)) -> dict: ...
```

**Contrato do transporte:** `transporte(url, corpo, cabecalhos) -> (status, texto)`.

**Forma da saída de `disciplina`:** `sigla, nome, creditos_aula, creditos_trabalho, carga_horaria_total, tipo, ativacao, ementa, objetivos, programa, bibliografia, metodo_avaliacao, criterio_avaliacao, norma_recuperacao, pre_requisito, avisos`. Com `idiomas=("pt","en")` acrescenta os sufixos `_en`. `avisos` é uma lista de strings — é onde vive o que a ferramenta **não** sabe (Invariante 7).

---

### Task 1: Andaime e guarda de fixture (T1–T3)

**Files:**
- Create: `pytest.ini`
- Create: `requirements-dev.txt`
- Create: `tests/jupiter/conftest.py`
- Test: `tests/jupiter/test_fixtures.py`

**Interfaces:**
- Consumes: nada.
- Produces: `RAIZ`, `FIXTURES`, `FATIA`, `caminho(chave)`, `texto(chave)`, a classe `Gravador`, e as fixtures pytest `psi3323`, `ptc3314`, `requisito`, `erro`, `gravador`. Todas as tarefas seguintes dependem destes nomes.

Esta é a única tarefa que termina **verde**: T1–T3 verificam fixture, não implementação.

- [ ] **Step 1: Criar `pytest.ini` e `requirements-dev.txt`**

`pytest.ini`:

```ini
[pytest]
testpaths = tests
addopts = --strict-markers -q
markers =
    politica: invariante que não depende de resposta nenhuma
    contrato: forma da resposta e da requisição, contra fixture versionada
    live: canário contra uspdigital.usp.br; exige USP_MCP_LIVE=1
```

`requirements-dev.txt`:

```
pytest>=8.0
```

- [ ] **Step 2: Escrever `tests/jupiter/conftest.py`**

```python
"""Peças compartilhadas da suíte do Jupiter.

Nenhum caminho absoluto de máquina: tudo sai da posição deste arquivo.
Nenhuma fixture crua é impressa — só lida (§0 do CONVENTIONS.md).
"""
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "fixtures" / "jupiter"

# As quatro fixtures da fatia vertical. Acrescentar uma quinta aqui é
# alargar o escopo do spec, e T23 vai reclamar.
FATIA = {
    "psi3323": "dwr-pubObterDisciplina-PSI3323.txt",
    "ptc3314": "dwr-pubObterDisciplina-PTC3314.txt",
    "requisito": "dwr-pubListarRequisitoDisciplina-MAT2454.txt",
    "erro": "dwr-pubObterDisciplina-ERRO-sigla-inexistente.txt",
}


def caminho(chave: str) -> pathlib.Path:
    return FIXTURES / FATIA[chave]


def texto(chave: str) -> str:
    return caminho(chave).read_text(encoding="utf-8")


class Gravador:
    """Transporte falso: devolve fixture e guarda a requisição que teria saído.

    É o que torna T13-T19 possíveis — sem isto, o corpo DWR malformado
    passaria despercebido, porque o Jupiter responde 200 de qualquer jeito.
    """

    def __init__(self, respostas):
        self._respostas = list(respostas)
        self.chamadas = []

    def __call__(self, url, corpo, cabecalhos):
        self.chamadas.append({"url": url, "corpo": corpo, "cabecalhos": dict(cabecalhos)})
        if len(self._respostas) > 1:
            return 200, self._respostas.pop(0)
        return 200, self._respostas[0]


@pytest.fixture
def psi3323():
    return texto("psi3323")


@pytest.fixture
def ptc3314():
    return texto("ptc3314")


@pytest.fixture
def requisito():
    return texto("requisito")


@pytest.fixture
def erro():
    return texto("erro")


@pytest.fixture
def gravador():
    return Gravador
```

- [ ] **Step 3: Escrever `tests/jupiter/test_fixtures.py` (T1–T3)**

```python
"""T1-T3: a suíte não pode passar verde sem as fixtures que ela diz testar.

O raciocínio é da suíte irmã do Moodle e vale igual aqui: um skip por
fixture ausente passa verde noutra máquina SEM TER TESTADO NADA. Isso é
o Invariante 6 aplicado à própria suíte.
"""
import pathlib
import subprocess

import pytest

from conftest import FATIA, FIXTURES, RAIZ, caminho

pytestmark = pytest.mark.politica


@pytest.mark.parametrize("chave", sorted(FATIA))
def test_t1_fixture_da_fatia_existe_e_nao_esta_vazia(chave):
    p = caminho(chave)
    assert p.is_file(), (
        f"fixture da fatia ausente: {p}\n"
        "Ausência é FALHA, não skip. Um skip aqui deixaria a suíte verde "
        "numa máquina sem fixture nenhuma."
    )
    assert p.stat().st_size > 0, f"fixture vazia: {p}"


def test_t2_nenhum_caminho_absoluto_de_maquina():
    fonte = (pathlib.Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")
    for agulha in ("/Users/", "/home/", "C:\\", "/private/tmp"):
        assert agulha not in fonte, (
            f"caminho absoluto de máquina no conftest: {agulha!r}. "
            "As fixtures têm que ser resolvidas a partir da posição do arquivo."
        )
    assert FIXTURES == RAIZ / "fixtures" / "jupiter"


@pytest.mark.parametrize("chave", sorted(FATIA))
def test_t3_fatia_nao_depende_de_arquivo_fora_do_git(chave):
    p = caminho(chave)
    r = subprocess.run(
        ["git", "check-ignore", "-q", str(p)],
        cwd=RAIZ,
        capture_output=True,
    )
    assert r.returncode == 1, (
        f"{p.name} está no .gitignore. A suíte não pode depender de arquivo "
        "que outra máquina não tem — é o caso de html-obterTurma-*.html, que "
        "o §2 do spec deixou fora da fatia de propósito."
    )
```

- [ ] **Step 4: Rodar e verificar que T1–T3 passam**

```bash
python3 -m pytest tests/jupiter/test_fixtures.py -v
```

Esperado: **9 passed** (T1 e T3 são parametrizados em 4 fixtures cada, T2 é único).
Se algum falhar, a causa é real: fixture ausente, caminho absoluto, ou arquivo ignorado pelo git. Não afrouxe a asserção (§6 do `CONVENTIONS.md`).

- [ ] **Step 5: Verificar que o teste sabe falhar**

```bash
mv fixtures/jupiter/dwr-pubObterDisciplina-PSI3323.txt /tmp/guarda.txt
python3 -m pytest tests/jupiter/test_fixtures.py -q
mv /tmp/guarda.txt fixtures/jupiter/dwr-pubObterDisciplina-PSI3323.txt
```

Esperado: **falha** em T1 e T3 com a mensagem sobre ausência ser falha, não skip. Uma verificação que não pode falhar não verifica nada.

- [ ] **Step 6: Commit**

```bash
git add pytest.ini requirements-dev.txt tests/jupiter/conftest.py tests/jupiter/test_fixtures.py
git commit -m "test(jupiter): andaime da suíte e guarda de fixture (T1-T3)

Três marcadores (politica/contrato/live) e o transporte-gravador que
torna o corpo da requisição testável. T1-T3 travam a única coisa que
pode fazer a suíte inteira mentir: fixture ausente virando skip verde."
```

---

### Task 2: Decodificação do envelope DWR (T4–T12)

**Files:**
- Test: `tests/jupiter/test_dwr.py`

**Interfaces:**
- Consumes: `psi3323`, `ptc3314`, `requisito`, `erro` do `conftest.py`.
- Produces: nada (arquivo de teste). Fixa `dwr.decodificar`, `dwr.JupiterErro.mensagem`, `dwr.RespostaInvalida`.

- [ ] **Step 1: Escrever `tests/jupiter/test_dwr.py`**

```python
"""T4-T12: decodificar o envelope DWR.

O Jupiter devolve HTTP 200 no erro. Quem checar status code produz
exatamente o silêncio que o Invariante 6 proíbe — daí T6.
"""
import pathlib

import pytest

from usp_mcp.jupiter import dwr

pytestmark = pytest.mark.contrato


def test_t4_objeto_unico_vira_dict_de_26_chaves(psi3323, ptc3314):
    for bruto, sigla in ((psi3323, "PSI3323"), (ptc3314, "PTC3314")):
        o = dwr.decodificar(bruto)
        assert isinstance(o, dict)
        assert len(o) == 26, f"{sigla}: pubObterDisciplina tem 26 campos"
        assert o["coddis"] == sigla


def test_t5_array_de_um_elemento_nao_colapsa_em_dict(requisito):
    # A armadilha: a fixture de pré-requisito tem EXATAMENTE 1 elemento.
    # Um decoder que "simplifique" listas de 1 quebra a ferramenta em silêncio.
    r = dwr.decodificar(requisito)
    assert isinstance(r, list), "array de 1 elemento virou dict"
    assert len(r) == 1
    assert r[0]["coddisreq"] == "MAT2453"


def test_t6_handle_exception_levanta_nunca_devolve_vazio(erro):
    with pytest.raises(dwr.JupiterErro):
        dwr.decodificar(erro)


def test_t7_erro_exposto_nao_carrega_stacktrace_nem_classe_java(erro):
    with pytest.raises(dwr.JupiterErro) as exc:
        dwr.decodificar(erro)
    despejo = "".join((repr(exc.value), str(exc.value), repr(vars(exc.value))))
    for vazamento in ("stackTrace", "javaClassName", "usp.erro.USPException", "br.usp.comum"):
        assert vazamento not in despejo, (
            f"{vazamento!r} sobreviveu ao erro. São 46 frames: o erro cru custa "
            "~1.978 tokens contra ~17 da mensagem — 116x, e é a resposta errada."
        )


def test_t8_mensagem_do_erro_e_a_localized_message_em_portugues(erro):
    with pytest.raises(dwr.JupiterErro) as exc:
        dwr.decodificar(erro)
    assert exc.value.mensagem == "Disciplina inválida ou ainda não ativada !"


def test_t9_escapes_do_envelope(psi3323):
    o = dwr.decodificar(psi3323)
    assert o["nomdis"] == "Laboratório de Eletrônica I"   # \u00F3 e \u00F4
    assert o["dtaatvdis"] == "01/01/2025"                 # \/ desescapado
    assert o["dtadtvdis"] is None                         # null, não "null"
    assert "\n" in o["objdis"]                            # quebra preservada


def test_t10_envelope_truncado_e_erro_explicito(psi3323):
    truncado = psi3323.replace("//#DWR-END#", "")
    with pytest.raises(dwr.RespostaInvalida):
        dwr.decodificar(truncado)


def test_t11_corpo_html_e_erro_explicito():
    # O balanceador devolve 302 para /wsusuario/ em qualquer rota desconhecida
    # (§9 do recon). O corpo que chega é a tela de login, não DWR.
    html = "<html><head><title>Senha unica USP</title></head><body></body></html>"
    with pytest.raises(dwr.RespostaInvalida):
        dwr.decodificar(html)


def test_t12_decoder_nao_executa_codigo(psi3323, tmp_path):
    alvo = tmp_path / "efeito.txt"
    hostil = psi3323.replace(
        '{coddis:"PSI3323"',
        '{x:__import__("pathlib").Path(%r).write_text("executou"),coddis:"PSI3323"'
        % str(alvo),
        1,
    )
    try:
        dwr.decodificar(hostil)
    except (dwr.RespostaInvalida, dwr.JupiterErro):
        pass
    assert not alvo.exists(), "o decoder EXECUTOU código vindo do payload"

    fonte = pathlib.Path(dwr.__file__).read_text(encoding="utf-8")
    for perigo in ("eval(", "exec(", "literal_eval"):
        assert perigo not in fonte, f"{perigo!r} em dwr.py: o decoder tem que ler, não rodar"
```

- [ ] **Step 2: Rodar e verificar que falha pelo motivo certo**

```bash
python3 -m pytest tests/jupiter/test_dwr.py -q 2>&1 | tail -5
```

Esperado: erro de **coleta** com `ModuleNotFoundError: No module named 'usp_mcp'`.
Se aparecer `SyntaxError`, `fixture ... not found` ou `FileNotFoundError`, o teste está quebrado, não vermelho — conserte antes de commitar.

- [ ] **Step 3: Commit**

```bash
git add tests/jupiter/test_dwr.py
git commit -m "test(jupiter): decodificação do envelope DWR (T4-T12)

Fixa o que o §4.2/4.3 do recon mediu: objeto vs array (T5 trava o array
de 1 elemento, que é a armadilha), erro com HTTP 200 que levanta em vez
de devolver vazio, stackTrace descartado (116x), e um decoder que lê
sem executar."
```

---

### Task 3: Cliente, cache e allowlist (T13–T25)

**Files:**
- Test: `tests/jupiter/test_cliente.py`

**Interfaces:**
- Consumes: `Gravador`, `psi3323`, `requisito`, `erro`.
- Produces: fixa `ClienteJupiter.__init__(transporte, *, agente, relogio)`, `_chamar`, `obter_disciplina`, `listar_requisito`, `CONSULTAS_PERMITIDAS`, `ConsultaNegada`, `AGENTE`, `URL_BASE`.

- [ ] **Step 1: Escrever `tests/jupiter/test_cliente.py`**

```python
"""T13-T25: o corpo da requisição é contrato.

O DWR responde 200 para corpo malformado. Sem estes testes, um erro de
serialização aparece como campo vazio, não como falha — e nenhuma outra
camada da suíte pega isso.
"""
import concurrent.futures
import json
import pathlib

import pytest

from usp_mcp.jupiter import cliente, dwr, ferramentas

# §4.2 do notas/jupiter-recon.md, verbatim.
CORPO_ESPERADO = [
    "callCount=1",
    "windowName=",
    "c0-scriptName=ControlePublicoDWR",
    "c0-methodName=obter",
    "c0-id=0",
    "c0-param0=string:pubObterDisciplina",
    "c0-e1=string:PSI3323",
    "c0-e2=number:0",
    "c0-param1=Object_Object:{coddis:reference:c0-e1, verdis:reference:c0-e2}",
    "batchId=0",
    "instanceId=0",
    "page=%2Fjupiterweb%2FjupCarreira.jsp",
    "scriptSessionId=0000000000000000",
]


@pytest.fixture
def cli(gravador, psi3323):
    g = gravador([psi3323])
    return cliente.ClienteJupiter(g), g


@pytest.mark.contrato
def test_t13_corpo_bate_linha_a_linha_com_o_recon(cli):
    c, g = cli
    c.obter_disciplina("PSI3323")
    assert g.chamadas[0]["corpo"].splitlines() == CORPO_ESPERADO


@pytest.mark.contrato
def test_t14_objeto_serializado_por_referencia(cli):
    c, g = cli
    c.obter_disciplina("PSI3323")
    corpo = g.chamadas[0]["corpo"]
    assert "\nc0-e1=string:PSI3323\n" in corpo, "cada c0-eN em linha própria"
    assert "\nc0-e2=number:0\n" in corpo
    assert "reference:c0-e1" in corpo and "reference:c0-e2" in corpo
    assert "coddis:string:" not in corpo, "valor embutido no param1 em vez de referência"


@pytest.mark.contrato
def test_t15_valor_string_e_percent_encoded():
    # O charset exato do encode não foi verificado na Fase 1 (§8 do recon),
    # então a asserção é sobre o que É observável: nada de espaço cru na linha.
    corpo = dwr.serializar(
        metodo="obter",
        consulta="pubObterDisciplina",
        params={"coddis": "MAT 2454", "verdis": 0},
    )
    linha = next(l for l in corpo.splitlines() if l.startswith("c0-e1="))
    assert " " not in linha, f"espaço cru na linha do valor: {linha!r}"
    assert "%20" in linha


@pytest.mark.contrato
@pytest.mark.parametrize(
    "consulta,sufixo",
    [
        ("pubObterDisciplina", "ControlePublicoDWR.obter.dwr"),
        ("pubListarRequisitoDisciplina", "ControlePublicoDWR.listar.dwr"),
    ],
)
def test_t16_roteamento_do_metodo(gravador, psi3323, requisito, consulta, sufixo):
    g = gravador([psi3323 if consulta == "pubObterDisciplina" else requisito])
    c = cliente.ClienteJupiter(g)
    if consulta == "pubObterDisciplina":
        c.obter_disciplina("PSI3323")
    else:
        c.listar_requisito(coddis="MAT2454", codcur="3033", codhab="0")
    assert g.chamadas[0]["url"].endswith(sufixo)


@pytest.mark.contrato
def test_t17_stateless_sem_cookie_e_sem_handshake(cli):
    c, g = cli
    c.obter_disciplina("PSI3323")
    assert len(g.chamadas) == 1, "houve handshake antes: __System.generateId é dispensável (§4.4)"
    assert "Cookie" not in g.chamadas[0]["cabecalhos"]
    assert "scriptSessionId=0000000000000000" in g.chamadas[0]["corpo"]
    assert "generateId" not in g.chamadas[0]["url"]


@pytest.mark.politica
def test_t18_user_agent_identificavel_com_contato(cli):
    c, g = cli
    c.obter_disciplina("PSI3323")
    ua = g.chamadas[0]["cabecalhos"].get("User-Agent", "")
    assert "usp-mcp" in ua, f"User-Agent não identifica o projeto: {ua!r}"
    assert "http" in ua or "@" in ua, f"User-Agent sem contato: {ua!r}"
    for anonimo in ("curl", "python-urllib", "python-requests"):
        assert anonimo not in ua.lower()


@pytest.mark.politica
def test_t19_cliente_nao_le_segredo_nem_emite_credencial(monkeypatch, cli):
    monkeypatch.setenv("MOODLE_TOKEN", "NUNCA_DEVE_SER_LIDO_0000")
    monkeypatch.setenv("RUCARD_HASH", "NUNCA_DEVE_SER_LIDO_1111")
    c, g = cli
    c.obter_disciplina("PSI3323")

    cab = g.chamadas[0]["cabecalhos"]
    assert "Authorization" not in cab and "Cookie" not in cab
    assert "NUNCA_DEVE_SER_LIDO" not in json.dumps(g.chamadas, ensure_ascii=False)

    fonte = pathlib.Path(cliente.__file__).read_text(encoding="utf-8")
    for segredo in ("MOODLE_TOKEN", "RUCARD_HASH", "Authorization"):
        assert segredo not in fonte, (
            f"{segredo!r} em cliente.py. O Jupiter é público e o §6 do SPEC1 "
            "põe ele num servidor hospedado — ele não pode virar portador de "
            "credencial num refactor futuro."
        )


@pytest.mark.contrato
def test_t20_duas_chamadas_iguais_uma_requisicao(cli):
    c, g = cli
    c.obter_disciplina("PSI3323")
    c.obter_disciplina("PSI3323")
    assert len(g.chamadas) == 1, "sem cache: duas perguntas iguais bateram duas vezes na USP"


@pytest.mark.politica
def test_t21_ttl_colado_na_taxa_de_mudanca_do_dado(gravador, psi3323):
    relogio = {"t": 0.0}
    g = gravador([psi3323])
    c = cliente.ClienteJupiter(g, relogio=lambda: relogio["t"])

    c.obter_disciplina("PSI3323")
    relogio["t"] = 60 * 60 * 24 * 29
    c.obter_disciplina("PSI3323")
    assert len(g.chamadas) == 1, (
        "TTL curto demais: ementa muda por semestre, não por dia. "
        "Invariante 5 — o TTL segue a taxa de mudança do dado, não a "
        "frequência da pergunta."
    )

    relogio["t"] = 60 * 60 * 24 * 181
    c.obter_disciplina("PSI3323")
    assert len(g.chamadas) == 2, "TTL infinito: a ementa muda entre semestres"


@pytest.mark.contrato
def test_t22_concorrencia_um(psi3323):
    estado = {"dentro": False, "sobreposicoes": 0, "chamadas": 0}

    def transporte(url, corpo, cabecalhos):
        if estado["dentro"]:
            estado["sobreposicoes"] += 1
        estado["dentro"] = True
        estado["chamadas"] += 1
        try:
            return 200, psi3323
        finally:
            estado["dentro"] = False

    c = cliente.ClienteJupiter(transporte)
    siglas = ["PSI3323", "PTC3314", "MAT2454", "PME3344"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(c.obter_disciplina, siglas))

    assert estado["sobreposicoes"] == 0, (
        "requisições sobrepostas. O §7 do recon pede concorrência 1, e o rate "
        "limit do Jupiter continua sem evidência (§8): 26 requisições sem 429 "
        "não provam que não exista."
    )


# --- Allowlist (§4.4 do spec): a fronteira é o cliente ---

CONSULTAS_FORA_DA_FATIA = [
    "pubGradeCurricular",
    "pubListarColegiado",
    "pubListarCursoEntrada",
    "pubObterInfoCurso",
    "pubObterInfoCursoWeb",
    "pubListarDiscipResp",
    "recuperarProjetoPedagogico",
]
METODOS_GENERICOS = [
    "executarBatch",
    "executar",
    "obterArquivo",
    "obterRelatorio",
    "obterCsv",
    "obterPdf",
    "obterZip",
    "obterWebdoc",
    "obterProgresso",
]


@pytest.mark.politica
@pytest.mark.parametrize(
    "metodo,consulta",
    [("listar", q) for q in CONSULTAS_FORA_DA_FATIA]
    + [(m, "pubObterDisciplina") for m in METODOS_GENERICOS],
)
def test_t23_superficie_travada_em_duas_consultas(cli, metodo, consulta):
    c, _ = cli
    with pytest.raises(cliente.ConsultaNegada):
        c._chamar(metodo=metodo, consulta=consulta, params={})
    assert set(cliente.CONSULTAS_PERMITIDAS) == {
        "pubObterDisciplina",
        "pubListarRequisitoDisciplina",
    }, "a fatia vertical tem duas consultas; uma terceira precisa de decisão registrada"


@pytest.mark.politica
def test_t24_negado_continua_negado_com_allow_writes(monkeypatch, cli):
    monkeypatch.setenv("USP_MCP_ALLOW_WRITES", "1")
    c, _ = cli
    with pytest.raises(cliente.ConsultaNegada):
        # executarBatch é o análogo exato de tool_mobile_call_external_functions:
        # executor genérico que anula qualquer filtro por nome de consulta.
        c._chamar(metodo="executarBatch", consulta="pubObterDisciplina", params={})


@pytest.mark.politica
def test_t25_ferramenta_nao_expoe_nome_de_consulta():
    import inspect

    parametros = set(inspect.signature(ferramentas.disciplina).parameters)
    proibidos = {"consulta", "metodo", "funcao", "query", "scriptName", "methodName"}
    assert not (parametros & proibidos), (
        f"a ferramenta aceita {parametros & proibidos} como argumento. Uma "
        "ferramenta que recebe o nome da consulta deixa de ter superfície, e a "
        "allowlist inteira vira decoração."
    )
    fonte = pathlib.Path(ferramentas.__file__).read_text(encoding="utf-8")
    assert "_chamar" not in fonte, (
        "a ferramenta chama o choke point direto; o nome da consulta tem que "
        "estar fixo em cliente.py, não montado na camada de ferramenta."
    )
```

- [ ] **Step 2: Rodar e verificar que falha pelo motivo certo**

```bash
python3 -m pytest tests/jupiter/test_cliente.py -q 2>&1 | tail -5
```

Esperado: `ModuleNotFoundError: No module named 'usp_mcp'` na coleta.

- [ ] **Step 3: Commit**

```bash
git add tests/jupiter/test_cliente.py
git commit -m "test(jupiter): corpo da requisição, cache e allowlist (T13-T25)

O corpo DWR é contrato porque o servidor responde 200 para corpo
malformado — erro de serialização vira campo vazio, não falha. T19
impede o cliente público de virar portador de credencial. T23-T25 são
o Invariante 2: executarBatch é o tool_mobile_call_external_functions
do Jupiter, e T24 prova que ALLOW_WRITES não o libera."
```

---

### Task 4: A ferramenta `disciplina` (T26–T33)

**Files:**
- Test: `tests/jupiter/test_disciplina.py`

**Interfaces:**
- Consumes: `Gravador`, `psi3323`, `ptc3314`, `requisito`, `erro`; `cliente.ClienteJupiter`; `dwr.decodificar`, `dwr.JupiterErro`.
- Produces: fixa `ferramentas.disciplina(sigla, curso=None, *, cliente, idiomas=("pt",))` e a forma da saída.

- [ ] **Step 1: Escrever `tests/jupiter/test_disciplina.py`**

```python
"""T26-T33: a ferramenta.

A pergunta do §5 do SPEC1: "essa disciplina tem quantos créditos e qual
o pré-requisito?". Os créditos são incondicionais; o pré-requisito NÃO é
— ele depende do curso (§5.2 do recon), e T30 existe para a ferramenta
não fingir o contrário.
"""
import pytest

from usp_mcp.jupiter import cliente, dwr, ferramentas

pytestmark = pytest.mark.contrato


@pytest.fixture
def cli(gravador, psi3323):
    g = gravador([psi3323])
    return cliente.ClienteJupiter(g), g


@pytest.mark.parametrize("entrada", ["PSI3323", "psi3323", "PSI 3323", "  psi 3323  "])
def test_t26_normalizacao_de_sigla(cli, entrada):
    c, _ = cli
    assert ferramentas.disciplina(entrada, cliente=c)["sigla"] == "PSI3323"


@pytest.mark.parametrize(
    "chave,sigla,carga", [("psi3323", "PSI3323", 45), ("ptc3314", "PTC3314", 60)]
)
def test_t27_carga_horaria_e_calculada_nunca_o_campo(
    gravador, psi3323, ptc3314, chave, sigla, carga
):
    bruto = psi3323 if chave == "psi3323" else ptc3314
    c = cliente.ClienteJupiter(gravador([bruto]))
    d = ferramentas.disciplina(sigla, cliente=c)

    assert d["carga_horaria_total"] == carga

    cru = dwr.decodificar(bruto)
    assert cru["cgahoreto"] == "0", "a fixture mudou; remeça a medição"
    assert d["carga_horaria_total"] == int(cru["creaul"]) * 15 + int(cru["cretrb"]) * 30
    # Ler cgahoreto devolveria 0 h com cara de resposta certa: o silêncio do
    # Invariante 6 sem erro nenhum no caminho.


def test_t28_ementa_e_pgmrsudis_nao_pgmdis(cli, psi3323):
    c, _ = cli
    d = ferramentas.disciplina("PSI3323", cliente=c)
    cru = dwr.decodificar(psi3323)
    assert d["ementa"] == cru["pgmrsudis"]
    assert d["programa"] == cru["pgmdis"]
    assert d["ementa"] != d["programa"], "ementa e conteúdo programático trocados"


def test_t29_vazios_e_espanhol_omitidos_ingles_sob_pedido(gravador, psi3323):
    c = cliente.ClienteJupiter(gravador([psi3323]))
    d = ferramentas.disciplina("PSI3323", cliente=c)
    assert not [k for k in d if k.endswith(("_en", "_es"))]
    assert not [k for k, v in d.items() if v in ("", None) and k != "pre_requisito"]

    c2 = cliente.ClienteJupiter(gravador([psi3323]))
    d_en = ferramentas.disciplina("PSI3323", cliente=c2, idiomas=("pt", "en"))
    assert d_en["nome_en"] == dwr.decodificar(psi3323)["nomdisigl"]
    assert not [k for k in d_en if k.endswith("_es")], (
        "os 4 campos *epa vêm vazios nas duas amostras; espanhol nunca sai"
    )


def test_t30_sem_curso_a_ferramenta_diz_o_que_nao_sabe(cli):
    c, g = cli
    d = ferramentas.disciplina("PSI3323", cliente=c)

    assert d["pre_requisito"] is None
    assert len(g.chamadas) == 1, "chamou a consulta de requisito sem ter curso"

    avisos = " ".join(d["avisos"]).lower()
    assert "requisito" in avisos and "curso" in avisos, (
        "Invariante 7: o pré-requisito é condicional ao curso. Omitir calado "
        "é o que o invariante proíbe."
    )
    for mentira in ("sem pré-requisito", "não tem pré-requisito", "nenhum pré-requisito"):
        assert mentira not in avisos, f"a ferramenta afirmou {mentira!r} sem ter consultado"


def test_t31_com_curso_duas_chamadas_e_requisito_estruturado(gravador, psi3323, requisito):
    # As duas respostas são stubs: a Fase 1 não amostrou disciplina e requisito
    # da MESMA disciplina. O que está sob teste é a COMPOSIÇÃO de duas chamadas,
    # não o pareamento — que continua não verificado (§8 do recon).
    g = gravador([psi3323, requisito])
    c = cliente.ClienteJupiter(g)
    d = ferramentas.disciplina("PSI3323", curso=("3033", "0"), cliente=c)

    assert len(g.chamadas) == 2
    assert g.chamadas[1]["corpo"].count("c0-e") >= 3, "requisito exige coddis+codcur+codhab"

    req = d["pre_requisito"]
    assert isinstance(req, list) and len(req) == 1
    assert req[0]["sigla"] == "MAT2453"
    assert req[0]["tipo"] == "PR"
    assert req[0]["nome"] == "Cálculo Diferencial e Integral I"


def test_t32_erro_da_usp_em_portugues_sem_stacktrace(gravador, erro):
    c = cliente.ClienteJupiter(gravador([erro]))
    with pytest.raises(dwr.JupiterErro) as exc:
        ferramentas.disciplina("ZZZ9999", cliente=c)
    assert exc.value.mensagem == "Disciplina inválida ou ainda não ativada !"
    assert "br.usp" not in str(exc.value)


def test_t33_discrepancia_codcur_3032_3033_e_declarada(gravador, psi3323, requisito):
    # §5.1 do recon: o Ciclo Básico Elétrica é 3033 no DWR e 3032 no HTML de
    # listarCursosRequisitos. Não investigado, e não se inventa explicação.
    # Comportamento travado: usar o codcur recebido sem traduzir, e AVISAR.
    c = cliente.ClienteJupiter(gravador([psi3323, requisito]))
    d = ferramentas.disciplina("PSI3323", curso=("3032", "0"), cliente=c)

    avisos = " ".join(d["avisos"])
    assert "3032" in avisos and "3033" in avisos
    assert "não verificad" in avisos.lower() or "não investigad" in avisos.lower()
```

- [ ] **Step 2: Rodar e verificar que falha pelo motivo certo**

```bash
python3 -m pytest tests/jupiter/test_disciplina.py -q 2>&1 | tail -5
```

Esperado: `ModuleNotFoundError: No module named 'usp_mcp'`.

- [ ] **Step 3: Commit**

```bash
git add tests/jupiter/test_disciplina.py
git commit -m "test(jupiter): a ferramenta disciplina (T26-T33)

T27 é a pegadinha mais cara da fatia: cgahoreto vem \"0\" nas duas
amostras, e quem ler o campo devolve zero hora com cara de resposta
certa. T30 é o Invariante 7 — sem curso o pré-requisito não existe, e
a ferramenta diz isso em vez de omitir. T33 declara a discrepância
codcur 3032/3033 sem fingir que a resolve."
```

---

### Task 5: Custo (T34–T37)

**Files:**
- Test: `tests/jupiter/test_custo.py`

**Interfaces:**
- Consumes: `ferramentas.disciplina`, `ferramentas.CAMPOS_SAIDA`, `cliente.ClienteJupiter`, `dwr.JupiterErro`.
- Produces: nada.

- [ ] **Step 1: Escrever `tests/jupiter/test_custo.py`**

```python
"""T34-T37: custo.

Uma asserção de razão de redução foi desenhada e DESCARTADA por medição
(§4.6 do spec): a razão do Jupiter é ~1,8x, não os 11,5x do recon — esses
comparam DWR com HTML, não DWR com a projeção. Contra o próprio DWR quase
não há o que reduzir, porque o payload É a resposta.

O que sobrou: teto absoluto, o núcleo estruturado (spread 9%) e uma trava
CATEGÓRICA, que é o que de fato impede regressão.
"""
import json

import pytest

from usp_mcp.jupiter import cliente, dwr, ferramentas

pytestmark = pytest.mark.contrato

# Medido em 31/08: 2.148 B (PSI3323) e 3.615 B (PTC3314). Folga de ~38%
# sobre a maior amostra. Duas amostras, não uma — a maior é quase o dobro
# da menor com a MESMA forma.
TETO_SAIDA_B = 5000

NUCLEO = (
    "sigla",
    "nome",
    "creditos_aula",
    "creditos_trabalho",
    "carga_horaria_total",
    "tipo",
    "ativacao",
)


def tamanho(o) -> int:
    return len(json.dumps(o, ensure_ascii=False).encode())


@pytest.fixture
def saidas(gravador, psi3323, ptc3314):
    saida = {}
    for sigla, bruto in (("PSI3323", psi3323), ("PTC3314", ptc3314)):
        c = cliente.ClienteJupiter(gravador([bruto]))
        saida[sigla] = ferramentas.disciplina(sigla, cliente=c)
    return saida


@pytest.mark.parametrize("sigla", ["PSI3323", "PTC3314"])
def test_t34_teto_absoluto_com_folga_declarada(saidas, sigla):
    assert tamanho(saidas[sigla]) <= TETO_SAIDA_B


@pytest.mark.parametrize("sigla", ["PSI3323", "PTC3314"])
def test_t35_nucleo_estruturado_e_estavel(saidas, sigla):
    # Medido: 179 B e 164 B — spread de 9%. É a parte que a ferramenta
    # controla; o texto livre varia 77% e é a resposta em si.
    n = {k: saidas[sigla][k] for k in NUCLEO}
    assert 140 <= tamanho(n) <= 210, f"núcleo de {sigla}: {tamanho(n)} B"


@pytest.mark.parametrize("sigla", ["PSI3323", "PTC3314"])
def test_t36_conjunto_de_chaves_e_exatamente_o_declarado(saidas, sigla):
    d = saidas[sigla]
    desconhecidas = set(d) - set(ferramentas.CAMPOS_SAIDA)
    assert not desconhecidas, f"campos fora do declarado: {sorted(desconhecidas)}"

    despejo = json.dumps(d, ensure_ascii=False)
    for vazamento in ("stackTrace", "javaClassName", "nomdisepa", "pgmrsudisepa"):
        assert vazamento not in despejo
    assert not [k for k in d if k.endswith(("_es", "epa"))]


def test_t37_erro_nunca_custa_mais_que_sucesso(gravador, psi3323, erro):
    c1 = cliente.ClienteJupiter(gravador([psi3323]))
    sucesso = tamanho(ferramentas.disciplina("PSI3323", cliente=c1))

    c2 = cliente.ClienteJupiter(gravador([erro]))
    with pytest.raises(dwr.JupiterErro) as exc:
        ferramentas.disciplina("ZZZ9999", cliente=c2)
    projetado = tamanho({"erro": exc.value.mensagem})

    assert projetado < sucesso, (
        f"erro projetado {projetado} B >= sucesso {sucesso} B. O erro cru são "
        "~1.978 tokens contra ~17 da mensagem: 116x, e é a resposta ERRADA."
    )
```

- [ ] **Step 2: Rodar e verificar que falha pelo motivo certo**

```bash
python3 -m pytest tests/jupiter/test_custo.py -q 2>&1 | tail -5
```

Esperado: `ModuleNotFoundError: No module named 'usp_mcp'`.

- [ ] **Step 3: Commit**

```bash
git add tests/jupiter/test_custo.py
git commit -m "test(jupiter): teto, núcleo estável e trava categórica (T34-T37)

A asserção de razão de redução foi descartada por medição: a razão do
Jupiter é ~1,8x, e os 11,5x do recon comparam DWR com HTML. O que é
estável é o núcleo da saída (9%); bytes por campo varia 68% porque 90%
do peso é texto livre. A trava de regressão virou categórica."
```

---

### Task 6: Canário ao vivo (T38–T40)

**Files:**
- Test: `tests/jupiter/test_live.py`

**Interfaces:**
- Consumes: `cliente.transporte_http`, `cliente.URL_BASE`, `dwr.decodificar`, `dwr.serializar`, `dwr.JupiterErro`, `psi3323`.
- Produces: nada.

- [ ] **Step 1: Escrever `tests/jupiter/test_live.py`**

```python
"""T38-T40: canário contra uspdigital.usp.br.

DUAS requisições reais por execução, no máximo, escolhidas à mão. Nenhum
laço, nenhuma enumeração de sigla: o §7 do recon pede a gentileza e o §8
registra que 26 requisições sem 429 NÃO provam que não haja rate limit.

Compara CHAVES, nunca valores — valor muda por semestre sem que nada
tenha quebrado.
"""
import os

import pytest

from usp_mcp.jupiter import cliente, dwr

pytestmark = pytest.mark.live

MOTIVO = (
    "canário ao vivo desligado. Exporte USP_MCP_LIVE=1 para bater em "
    "uspdigital.usp.br. O §1.1 do SPEC1 registra que o sandbox não alcança a "
    "rede da USP: este teste só roda no terminal do dono."
)

ao_vivo = pytest.mark.skipif(os.environ.get("USP_MCP_LIVE") != "1", reason=MOTIVO)


@ao_vivo
def test_t38_forma_da_resposta_real_bate_com_a_fixture(psi3323):
    corpo = dwr.serializar(
        metodo="obter",
        consulta="pubObterDisciplina",
        params={"coddis": "PSI3323", "verdis": 0},
    )
    status, texto = cliente.transporte_http(
        f"{cliente.URL_BASE}/ControlePublicoDWR.obter.dwr",
        corpo,
        {"Content-Type": "text/plain", "User-Agent": cliente.AGENTE},
    )
    assert status == 200

    vivo = dwr.decodificar(texto)
    esperado = dwr.decodificar(psi3323)
    assert sorted(vivo) == sorted(esperado), (
        "as chaves de pubObterDisciplina mudaram — a fixture está velha ou a "
        "API mudou de forma. Compare e atualize a fixture com decisão registrada."
    )


@ao_vivo
def test_t39_sigla_inexistente_ainda_e_handle_exception_com_200():
    corpo = dwr.serializar(
        metodo="obter",
        consulta="pubObterDisciplina",
        params={"coddis": "ZZZ9999", "verdis": 0},
    )
    status, texto = cliente.transporte_http(
        f"{cliente.URL_BASE}/ControlePublicoDWR.obter.dwr",
        corpo,
        {"Content-Type": "text/plain", "User-Agent": cliente.AGENTE},
    )
    assert status == 200, "o Jupiter sinaliza erro no CORPO, não no status"
    with pytest.raises(dwr.JupiterErro):
        dwr.decodificar(texto)


def test_t40_skip_diz_o_motivo_por_escrito():
    if os.environ.get("USP_MCP_LIVE") == "1":
        pytest.skip("canário ligado; este teste cobre o caminho desligado")
    assert "USP_MCP_LIVE=1" in MOTIVO
    assert "uspdigital" in MOTIVO
    assert len(MOTIVO) > 80, (
        "um skip sem motivo escrito é a diferença entre 'não rodou' e 'não "
        "rodou, e aqui está por quê'"
    )
```

- [ ] **Step 2: Rodar e verificar que falha pelo motivo certo**

```bash
python3 -m pytest tests/jupiter/test_live.py -q 2>&1 | tail -5
```

Esperado: `ModuleNotFoundError: No module named 'usp_mcp'` — a coleta importa `cliente`, então falha antes do skip.

- [ ] **Step 3: Commit**

```bash
git add tests/jupiter/test_live.py
git commit -m "test(jupiter): canário ao vivo, desligado por padrão (T38-T40)

Duas requisições reais no máximo, escolhidas à mão. Compara chaves e
não valores. Sem USP_MCP_LIVE=1 o skip diz o motivo por escrito — a
diferença entre 'não rodou' e 'não rodou, e aqui está por quê'."
```

---

### Task 7: Fechar os TODO de gate e registrar a decisão

**Files:**
- Modify: `docs/agents/CONVENTIONS.md` (§3 e §4 — os dois `<TODO>`)
- Modify: `CLAUDE.md:52` (o `<TODO>` do gate no §3)
- Modify: `SPEC1.md` (§9 — registro de decisão datado)

**Interfaces:**
- Consumes: a suíte inteira das Tasks 1–6.
- Produces: nada em código. É o item 1 da Definição de Pronto do `CLAUDE.md` §5 — o dado que sustenta a mudança fica registrado, não só na janela da conversa.

- [ ] **Step 1: Rodar a suíte inteira e capturar o resultado real**

```bash
python3 -m pytest -q 2>&1 | tail -15
```

Esperado: T1–T3 passam (9 casos); todo o resto falha na coleta por `ModuleNotFoundError`. **Copie o número real** para os passos seguintes — não escreva de memória (§9 do `SPEC1.md`: "número fabricado, removido").

- [ ] **Step 2: Substituir o `<TODO>` do §4 do `CONVENTIONS.md`**

Trocar o bloco de gate por:

````markdown
## 4. Antes de cada commit

```bash
python3 -m pytest -q
```

Os testes marcados `live` dão skip sem `USP_MCP_LIVE=1`, e o skip diz o
motivo. Um teste que falha por fixture ausente ou erro de coleta não está
vermelho, está quebrado — conserte antes de commitar.
````

- [ ] **Step 3: Substituir o `<TODO>` do §3 do `CONVENTIONS.md`**

Trocar por:

```markdown
## 3. Estrutura de código

`usp_mcp/<sistema>/` por sistema (`jupiter/`, `moodle/`), cada um com
`cliente.py` (transporte + allowlist na fronteira) e `ferramentas.py`. O
`server.py` mora dentro do subpacote, nunca na raiz: o §6 do `SPEC1.md`
separa entrypoint local com credencial (Moodle, stdio) de servidor público
cacheável (Jupiter, RUCard), e a estrutura reflete isso. Testes em
`tests/<sistema>/`.

Erro da API sobe como exceção com mensagem legível em português; o cru da
API (stack trace, classe interna) é descartado antes de qualquer log.

Nome de ferramenta vem da pergunta do dono, não da função do Moodle:
`o_que_vence` é bom nome, `get_action_events_by_timesort` não é (§5 do
`SPEC1.md`).
```

- [ ] **Step 4: Substituir o `<TODO>` do gate no `CLAUDE.md` §3**

Trocar o bloco `# Gate antes de commit: <TODO...>` por:

```bash
# Gate antes de commit
python3 -m pytest -q
```

- [ ] **Step 5: Acrescentar o registro de decisão ao §9 do `SPEC1.md`**

Ao fim do §9, com a data de hoje. Use os números que você capturou no Step 1, não os deste plano:

```markdown
### 31/08/2026 — suíte do Jupiter escrita antes da implementação

Desenho em `docs/superpowers/specs/2026-08-31-testes-jupiter-design.md`, plano em
`docs/superpowers/plans/2026-08-31-suite-testes-jupiter.md`. 40 funções de teste;
T1–T3 passam, o resto falha por `ImportError` — a implementação é a Fase 2.

**Escopo: fatia vertical de uma pergunta**, a candidata do §5 ("quantos créditos e
qual o pré-requisito?"). Grade curricular, navegação unidade→curso e horário de turma
ficam de fora. O motivo veio da suíte irmã do Moodle: cobrir três superfícies de uma
vez deixaria os testes vermelhos por semanas, que é TDD no nome e waterfall no
comportamento.

**Uma asserção foi desenhada e descartada por medição.** A suíte ia fixar razão de
redução contra o cru. Medida nas duas amostras: 1,73 e 1,98 — e, mais grave, **a razão
do Jupiter é ~1,8×, não os 11,5× do recon**, que comparam DWR com HTML. Contra o
próprio DWR quase não há o que reduzir: o payload *é* a resposta. Bytes por campo varia
68% porque 90% do peso é texto livre. O que é estável é o núcleo estruturado da saída:
179 B e 164 B, spread de 9%. A trava de regressão virou **categórica** — o conjunto de
chaves da saída é exatamente o declarado.

**Descartar o `stackTrace` é 116×** (1.978 → 17 tokens): o erro cru custa mais que duas
disciplinas inteiras *e* é a resposta errada.

**Gate do projeto passa a existir:** `python3 -m pytest -q`. Fecha o `<TODO>` do §3 do
`CLAUDE.md` e os dois do `CONVENTIONS.md`.

**Acordos com a suíte do Moodle**, para as duas não colidirem no merge: `tests/{jupiter,
moodle}/` simétricos; `server.py` por subpacote e nenhum na raiz; `@pytest.mark.live` +
`USP_MCP_LIVE=1` com skip explicado; eixos `politica`/`contrato`/`live`.

**Continua aberto:** a discrepância `codcur` 3032 vs 3033 (T33 declara, não resolve); o
pareamento disciplina↔requisito nunca foi amostrado junto (T31 testa a composição, não
o pareamento); e o Invariante 8 (termos de uso), que não é testável em código.
```

- [ ] **Step 6: Rodar o gate recém-declarado**

```bash
python3 -m pytest -q 2>&1 | tail -5
```

Confirme que o resultado bate com o que você registrou no §9. Se não bater, o registro está errado — corrija o registro, nunca o teste.

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md SPEC1.md docs/agents/CONVENTIONS.md
git commit -m "docs(jupiter): gate do projeto passa a existir; decisão no §9

python3 -m pytest -q vira o gate antes de commit, fechando o TODO do §3
do CLAUDE.md e os dois do CONVENTIONS.md. §9 registra a fatia vertical,
a asserção de razão descartada por medição, e os acordos com a suíte do
Moodle."
```

---

## Self-review

**Cobertura do spec.** §4.1→Task 1; §4.2→Task 2; §4.3 e §4.4→Task 3; §4.5→Task 4; §4.6→Task 5; §4.7→Task 6; §8 (definição de pronto)→Task 7. Os 40 testes T1–T40 do spec têm uma função de teste cada, com o mesmo número.

**Consistência de tipos.** `transporte(url, corpo, cabecalhos) -> (status, texto)` é o mesmo em `Gravador` (Task 1), em `test_t22_concorrencia_um` (Task 3) e em `transporte_http` (Task 6). `ClienteJupiter(transporte, *, agente, relogio)` é usado com `relogio=` só em T21 e com o default no resto. `disciplina(sigla, curso=None, *, cliente, idiomas=("pt",))` tem a mesma assinatura nas Tasks 3, 4 e 5. `curso` é sempre a tupla `(codcur, codhab)`.

**Limitação declarada, não escondida.** T31 usa duas fixtures que não são da mesma disciplina — a Fase 1 nunca amostrou disciplina e requisito juntos. O teste verifica a composição de duas chamadas, e o comentário no código diz isso.
