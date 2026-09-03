# `baixar_arquivo` — Plano de Implementação

> **Para quem executa:** SUB-SKILL OBRIGATÓRIA — use `superpowers:subagent-driven-development`
> (recomendado) ou `superpowers:executing-plans` para implementar tarefa por tarefa.
> Os passos usam checkbox (`- [ ]`) para acompanhamento.

**Objetivo:** acrescentar ao servidor MCP do Moodle uma terceira ferramenta que baixa
um arquivo do e-Disciplinas para o disco local e devolve o **caminho**, para que o
agente que chamou o abra com a própria ferramenta de leitura.

**Arquitetura:** três camadas novas sobre o que já existe. `ClienteMoodle.baixar()`
faz o transporte do download e aplica a allowlist de origem; `deposito.py` decide
onde o byte mora e como se chama; `arquivo.py` orquestra (resolve sigla, casa nome,
decide, baixa, monta a resposta) e é pura — não sabe o que é MCP nem o que é disco
além de pedir ao depósito. `server.py` só registra a ferramenta.

**Stack:** Python 3.13, só stdlib no runtime (o projeto tem exatamente uma
dependência de runtime, `mcp`, e este plano **não acrescenta nenhuma**). Testes com
pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-moodle-baixar-arquivo-design.md` — leia
antes de começar. Ele explica *por quê*; este plano diz *como*.

## Restrições globais

Valem em toda tarefa, sem repetição:

- **Nenhuma dependência de runtime nova.** Só stdlib. `pypdf` foi explicitamente
  descartado no §9 de 01/09.
- **Nunca leia, imprima ou ecoe `MOODLE_TOKEN`.** Nem em mensagem de erro, nem em
  log, nem em nome de arquivo, nem em URL.
- **Nenhuma chamada de rede na suíte padrão.** Tudo com dublê. A camada `live` fica
  atrás de `USP_MCP_LIVE=1`.
- **Nunca varra funções do Moodle.** Uma função por invocação, escolhida à mão. Este
  plano usa apenas funções **já** na allowlist — nada é acrescentado a
  `politica.ALLOWLIST`.
- **Português** em toda docstring, mensagem de erro e comentário — é o idioma do repo.
- **Erro legível vence silêncio** (Invariante 6) e **nada de limite silencioso**
  (Invariante 7): se cortou, a saída diz.
- **Asserte sobre o que foi ENVIADO, não sobre a saída.** O dublê devolve o que o
  teste mandou. Onde o teste prova que algo *não* aconteceu, asserte sobre a lista de
  chamadas do dublê.
- **Verifique cada asserção por sabotagem** antes de dar a tarefa por pronta: quebre
  a produção de propósito, veja o teste ficar vermelho, desfaça pelo **inverso exato**
  da sabotagem (nunca `git checkout` num arquivo com trabalho não commitado).
- **Comando de teste:** `.venv/bin/python -m pytest <caminho> -v`. Gate completo:
  `./scripts/gate.sh`.

## Mapa de arquivos

| arquivo | responsabilidade | tarefa |
|---|---|---|
| `usp_mcp/moodle/cliente.py` (modificar) | `baixar()`, allowlist de origem, tradução de erro extraída | 1 |
| `usp_mcp/moodle/deposito.py` (criar) | caminho, slug seguro, reuso do que já está em disco | 2 |
| `usp_mcp/moodle/texto.py` (criar) | `normalizar()` e `casa()` — casamento de nome num lugar só | 3 |
| `usp_mcp/moodle/material.py` (modificar) | `Item` ganha campos internos; `busca` passa a usar `casa()` | 3 |
| `usp_mcp/moodle/arquivo.py` (criar) | orquestra: resolve, casa, decide, baixa, formata | 4 e 5 |
| `usp_mcp/moodle/server.py` (modificar) | registra a ferramenta na fronteira MCP | 6 |
| `tests/moodle/test_cliente.py` (modificar) | T91, T93, T94, T99 | 1 |
| `tests/moodle/test_deposito.py` (criar) | T92, T95, T96 | 2 |
| `tests/moodle/test_material.py` (modificar) | T102 (acento na busca), T68/T69 seguem verdes | 3 |
| `tests/moodle/test_arquivo.py` (criar) | T84–T90, T96b, T97, T98 | 4 e 5 |
| `tests/moodle/test_server_mcp.py` (modificar) | T100, T101 | 6 |

---

### Tarefa 1: `ClienteMoodle.baixar()` — transporte e allowlist de origem

**Arquivos:**
- Modificar: `usp_mcp/moodle/cliente.py`
- Testar: `tests/moodle/test_cliente.py`

**Interfaces:**
- Consome: `politica`, `erros` (já existentes).
- Produz, e as tarefas 4 e 5 dependem destes nomes exatos:
  - `ClienteMoodle.baixar(fileurl: str, *, tamanho_esperado: int | None = None, teto_bytes: int = TETO_ARQUIVO_BYTES) -> bytes`
  - `cliente.TETO_ARQUIVO_BYTES: int`
  - `ClienteMoodle.__init__` ganha o parâmetro `transporte_download=None`.

**Por que a allowlist de origem mora aqui e não na ferramenta:** o token vai no
**corpo** do POST. Uma `fileurl` apontando para outro host mandaria a credencial do
dono para esse host. O cliente é o único ponto por onde toda requisição passa — é o
mesmo argumento que já pôs a allowlist de funções aqui dentro.

- [ ] **Passo 1: escrever os testes que falham**

Acrescente ao fim de `tests/moodle/test_cliente.py`:

```python
# --- T91, T93, T94, T99: o download ---------------------------------------

TOKEN_DE_TESTE = "TOKEN-SINTETICO-NAO-E-CREDENCIAL"
URL_TESTE = "https://edisciplinas.usp.br"
URL_ARQUIVO = f"{URL_TESTE}/webservice/pluginfile.php/9599792/mod_resource/content/26/a.pdf"


class _DownloadFalso:
    """Grava o que recebeu e devolve (content_type, bytes) combinados."""

    def __init__(self, content_type="application/pdf", corpo=b"%PDF-1.4 conteudo"):
        self.chamadas: list[dict] = []
        self._content_type = content_type
        self._corpo = corpo

    def __call__(self, *, url, dados, teto_bytes):
        self.chamadas.append({"url": url, "dados": dados, "teto_bytes": teto_bytes})
        return self._content_type, self._corpo


def _cliente_com(download):
    return ClienteMoodle(
        token=TOKEN_DE_TESTE,
        url=URL_TESTE,
        transporte=lambda **k: {},
        transporte_download=download,
    )


def test_T91_url_de_outro_host_e_recusada_antes_de_qualquer_io():
    """A credencial vai no CORPO do POST: outro host receberia o token."""
    download = _DownloadFalso()
    cliente = _cliente_com(download)

    with pytest.raises(FuncaoBloqueada) as erro:
        cliente.baixar("https://evil.example.com/webservice/pluginfile.php/1/x.pdf")

    # O que prova a regra é o transporte NÃO ter sido chamado — não a mensagem.
    assert download.chamadas == []
    assert "evil.example.com" in str(erro.value)


def test_T91b_url_no_host_certo_mas_fora_do_pluginfile_e_recusada():
    download = _DownloadFalso()
    cliente = _cliente_com(download)

    with pytest.raises(FuncaoBloqueada):
        cliente.baixar(f"{URL_TESTE}/login/token.php")

    assert download.chamadas == []


def test_T93_json_com_http_200_vira_erro_legivel():
    """Falha de credencial no pluginfile.php NÃO vem como 4xx (§9, 01/09)."""
    download = _DownloadFalso(
        content_type="application/json; charset=utf-8",
        corpo=b'{"errorcode":"invalidtoken","error":"Token invalido"}',
    )
    cliente = _cliente_com(download)

    with pytest.raises(TokenInvalido):
        cliente.baixar(URL_ARQUIVO)


def test_T93b_json_de_erro_generico_preserva_o_errorcode():
    download = _DownloadFalso(
        content_type="application/json",
        corpo=b'{"errorcode":"missingparam","error":"faltou"}',
    )
    cliente = _cliente_com(download)

    with pytest.raises(ErroMoodle) as erro:
        cliente.baixar(URL_ARQUIVO)

    assert "missingparam" in str(erro.value)


def test_T94_tamanho_divergente_do_esperado_vira_erro():
    """Entregar arquivo truncado como bom é o pior resultado possível."""
    download = _DownloadFalso(corpo=b"12345")
    cliente = _cliente_com(download)

    with pytest.raises(ErroMoodle) as erro:
        cliente.baixar(URL_ARQUIVO, tamanho_esperado=999)

    assert "999" in str(erro.value) and "5" in str(erro.value)


def test_T94b_tamanho_batendo_devolve_os_bytes():
    download = _DownloadFalso(corpo=b"12345")
    cliente = _cliente_com(download)

    assert cliente.baixar(URL_ARQUIVO, tamanho_esperado=5) == b"12345"


def test_T99_o_token_vai_no_corpo_e_nunca_na_url():
    download = _DownloadFalso()
    cliente = _cliente_com(download)

    cliente.baixar(URL_ARQUIVO)

    enviado = download.chamadas[0]
    assert enviado["dados"]["token"] == TOKEN_DE_TESTE
    assert TOKEN_DE_TESTE not in enviado["url"]


def test_T99b_o_token_nao_aparece_em_nenhuma_mensagem_de_erro():
    download = _DownloadFalso(
        content_type="application/json", corpo=b'{"errorcode":"invalidtoken"}'
    )
    cliente = _cliente_com(download)

    with pytest.raises(ErroMoodle) as erro:
        cliente.baixar(URL_ARQUIVO)

    assert TOKEN_DE_TESTE not in str(erro.value)
```

Confira o topo de `tests/moodle/test_cliente.py`: os imports precisam incluir
`FuncaoBloqueada`, `TokenInvalido` e `ErroMoodle` de `usp_mcp.moodle.erros`, e
`ClienteMoodle` de `usp_mcp.moodle.cliente`. Acrescente o que faltar.

- [ ] **Passo 2: rodar e ver falhar**

```bash
.venv/bin/python -m pytest tests/moodle/test_cliente.py -v -k "T91 or T93 or T94 or T99"
```

Esperado: FAIL — `TypeError: ClienteMoodle.__init__() got an unexpected keyword
argument 'transporte_download'`.

- [ ] **Passo 3: extrair a tradução de erro que hoje vive embutida em `chamar`**

Em `usp_mcp/moodle/cliente.py`, recorte o bloco final de `chamar` (o
`if isinstance(resposta, dict) and "errorcode" in resposta:` com o `raise
TokenInvalido` e o `raise ErroMoodle`) para uma função de módulo, e chame-a de
dentro de `chamar` no lugar de onde estava:

```python
def _levantar_se_erro(rotulo: str, resposta) -> None:
    """Traduz o erro do Moodle, e é chamada pelos DOIS caminhos.

    Existe como função e não embutida em `chamar` porque o download
    (`baixar`) recebe o mesmo formato de erro por outro transporte. Duplicar a
    tradução criaria duas mensagens diferentes para `invalidtoken`, e a
    divergência só apareceria no dia em que o token expirasse.
    """
    if not (isinstance(resposta, dict) and "errorcode" in resposta):
        return
    errorcode = resposta["errorcode"]
    if errorcode == "invalidtoken":
        raise TokenInvalido(
            "Token do Moodle inválido ou expirado — gere um novo e "
            "atualize MOODLE_TOKEN no .env (ver §8 do SPEC1.md)."
        )
    mensagem = resposta.get("message", "") or resposta.get("error", "")
    raise ErroMoodle(f"Moodle recusou {rotulo}: {errorcode} — {mensagem}")
```

Em `chamar`, substitua o bloco recortado por `_levantar_se_erro(funcao, resposta)`
imediatamente antes do `return resposta`.

Rode agora os testes de erro que já existiam, para garantir que a extração não mudou
comportamento:

```bash
.venv/bin/python -m pytest tests/moodle/test_cliente.py -v
```

Esperado: os testes antigos (T52/T56/T57 entre eles) continuam **PASS**; os novos
seguem falhando.

- [ ] **Passo 4: implementar `baixar()`**

Ainda em `usp_mcp/moodle/cliente.py`, no topo, junto das outras constantes:

```python
# Caminho que caracteriza arquivo servido pelo webservice — a allowlist do
# download. Não é o mesmo endpoint das funções (`/webservice/rest/server.php`).
_PREFIXO_ARQUIVO = "/webservice/pluginfile.php/"

# Timeout do download. Maior arquivo medido em 01/09: 6,3 MB. Mais generoso que o
# das funções porque aqui o custo é banda, não processamento do Moodle.
_TIMEOUT_DOWNLOAD_SEGUNDOS = 120

# Teto por arquivo. Maior medido: 6,3 MB — folga deliberada de ~8x.
TETO_ARQUIVO_BYTES = 50 * 1024 * 1024
```

O transporte de download, ao lado de `_transporte_padrao`:

```python
def _transporte_download_padrao(*, url: str, dados: dict, teto_bytes: int):
    """POST form-urlencoded que devolve (content_type, bytes). Só stdlib.

    Lê no máximo `teto_bytes + 1` de propósito: é assim que um arquivo sem
    `filesize` utilizável ainda respeita o teto, e o byte extra é o que permite
    detectar que o teto foi ultrapassado em vez de truncar calado.
    """
    corpo = urllib.parse.urlencode(dados).encode("utf-8")
    requisicao = urllib.request.Request(url, data=corpo, method="POST")
    with urllib.request.urlopen(requisicao, timeout=_TIMEOUT_DOWNLOAD_SEGUNDOS) as resp:
        return resp.headers.get("Content-Type", ""), resp.read(teto_bytes + 1)
```

Em `__init__`, acrescente o parâmetro (depois de `transporte`, antes de
`permitir_escrita`) e o atributo:

```python
        transporte_download=None,
```
```python
        self.transporte_download = (
            transporte_download
            if transporte_download is not None
            else _transporte_download_padrao
        )
```

E o método, depois de `chamar`:

```python
    def baixar(
        self,
        fileurl: str,
        *,
        tamanho_esperado: int | None = None,
        teto_bytes: int = TETO_ARQUIVO_BYTES,
    ) -> bytes:
        """Baixa UM arquivo do webservice do Moodle. O token vai no CORPO.

        Medido em 01/09/2026 (§9): o corpo do POST autentica igual à query
        string, e por isso a credencial nunca precisa entrar numa URL. Também
        medido: erro de credencial chega com **HTTP 200** e `Content-Type:
        application/json` — checar status não serve de nada aqui.

        A restrição de origem é a allowlist deste caminho. Ela roda antes de
        qualquer I/O: como o token viaja no corpo, uma URL de outro host
        entregaria a credencial do dono a esse host.
        """
        esperado = f"{self.url}{_PREFIXO_ARQUIVO}"
        if not fileurl.startswith(esperado):
            raise FuncaoBloqueada(
                f"Download recusado: {fileurl!r} não começa com {esperado!r}. "
                "O token vai no corpo da requisição, então baixar de outro "
                "endereço entregaria a sua credencial a ele."
            )

        try:
            content_type, corpo = self.transporte_download(
                url=fileurl,
                dados={"token": self._token.get()},
                teto_bytes=teto_bytes,
            )
        except OSError as exc:
            raise MoodleIndisponivel(
                "O e-Disciplinas não respondeu ao download (timeout ou conexão "
                "recusada). Tente de novo mais tarde."
            ) from exc

        if "json" in (content_type or "").lower():
            try:
                _levantar_se_erro("o download do arquivo", json.loads(corpo))
            except ValueError as exc:
                raise RespostaIlegivel(
                    "O e-Disciplinas devolveu algo que não é o arquivo nem um "
                    "erro compreensível no lugar do download."
                ) from exc
            raise RespostaIlegivel(
                "O e-Disciplinas devolveu JSON no lugar do arquivo, sem "
                "`errorcode` para explicar o motivo."
            )

        if len(corpo) > teto_bytes:
            raise ErroMoodle(
                f"O arquivo passa do teto de {teto_bytes} bytes e não foi "
                "gravado. Baixe pelo e-Disciplinas."
            )

        if tamanho_esperado is not None and len(corpo) != tamanho_esperado:
            raise ErroMoodle(
                f"O download veio incompleto: esperava {tamanho_esperado} bytes "
                f"e recebeu {len(corpo)}. Nada foi gravado."
            )

        return corpo
```

- [ ] **Passo 5: rodar e ver passar**

```bash
.venv/bin/python -m pytest tests/moodle/test_cliente.py -v
```

Esperado: todos PASS, inclusive os antigos.

- [ ] **Passo 6: sabotar para verificar as asserções**

Três sabotagens, uma de cada vez, desfazendo pelo inverso exato:

1. Troque `if not fileurl.startswith(esperado)` por `if False:` → T91 e T91b vermelhos.
2. Remova o bloco `if "json" in ...` → T93 e T93b vermelhos.
3. Troque `!= tamanho_esperado` por `== tamanho_esperado` → T94 vermelho, T94b vermelho.

Se alguma sabotagem **não** deixar o teste vermelho, o teste é fraco: conserte o
teste antes de seguir.

- [ ] **Passo 7: commit**

```bash
git add usp_mcp/moodle/cliente.py tests/moodle/test_cliente.py
git commit -m "feat(moodle): ClienteMoodle.baixar com allowlist de origem

O token vai no CORPO do POST (medido em 01/09), entao uma fileurl de outro
host entregaria a credencial do dono a ele: a checagem de origem roda antes de
qualquer I/O e o teste asserta que o transporte NAO foi chamado.

Erro de credencial no pluginfile.php chega como HTTP 200 com JSON — checar
status nao serve. A traducao de errorcode sai de dentro de chamar() para
_levantar_se_erro e passa a ser compartilhada pelos dois caminhos.

T91, T91b, T93, T93b, T94, T94b, T99, T99b."
```

---

### Tarefa 2: `deposito.py` — onde o byte mora

**Arquivos:**
- Criar: `usp_mcp/moodle/deposito.py`
- Criar: `tests/moodle/test_deposito.py`

**Interfaces:**
- Consome: nada do projeto — só stdlib. Isto é deliberado: o depósito não conhece
  Moodle.
- Produz, e a tarefa 4 depende destes nomes exatos:
  - `deposito.RAIZ_PADRAO: Path`
  - `deposito.caminho_para(*, courseid: int, fileid: str, timemodified: int, filename: str, raiz: Path | None = None) -> Path`
  - `deposito.ja_baixado(caminho: Path) -> bool`
  - `deposito.gravar(caminho: Path, dados: bytes) -> Path`

- [ ] **Passo 1: escrever os testes que falham**

Crie `tests/moodle/test_deposito.py`:

```python
"""T92, T95, T96 — o depósito: caminho seguro, nome legível, reuso.

`filename` vem do Moodle e é entrada não confiável. Na amostra de PSI3323 nenhum
tem separador de caminho, mas amostra não prova ausência — este repo já registrou
esse erro três vezes.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from usp_mcp.moodle import deposito


def _caminho(tmp_path, **troca):
    base = dict(
        courseid=142033,
        fileid="9599792",
        timemodified=1753400000,
        filename="Prova-PSI3323.pdf",
        raiz=tmp_path,
    )
    base.update(troca)
    return deposito.caminho_para(**base)


def test_T92_filename_com_travessia_nao_escapa_do_deposito(tmp_path):
    for veneno in ("../../etc/passwd", "..", ".", "/etc/passwd", "a/b/c.pdf"):
        caminho = _caminho(tmp_path, filename=veneno)
        assert caminho.resolve().is_relative_to(tmp_path.resolve()), veneno
        assert ".." not in caminho.parts


def test_T92b_o_nome_legivel_do_arquivo_e_preservado(tmp_path):
    caminho = _caminho(tmp_path, filename="Roteiro Exp2 - Fonte Linear.pdf")
    # Espaço e hífen viram sublinhado/hífen, mas o nome continua reconhecível
    # e a extensão sobrevive — é o que o agente vê quando abre o arquivo.
    assert caminho.name.endswith(".pdf")
    assert "Roteiro" in caminho.name
    assert "Exp2" in caminho.name


def test_T92c_nome_absurdamente_longo_e_truncado(tmp_path):
    caminho = _caminho(tmp_path, filename="x" * 500 + ".pdf")
    assert len(caminho.name) <= 128


def test_T92d_filename_vazio_ainda_produz_um_nome(tmp_path):
    caminho = _caminho(tmp_path, filename="")
    assert caminho.name


def test_T95_arquivo_ja_gravado_e_reconhecido(tmp_path):
    caminho = _caminho(tmp_path)
    assert deposito.ja_baixado(caminho) is False

    deposito.gravar(caminho, b"%PDF-1.4")

    assert deposito.ja_baixado(caminho) is True
    assert caminho.read_bytes() == b"%PDF-1.4"


def test_T95b_arquivo_gravado_vazio_nao_conta_como_baixado(tmp_path):
    """Zero byte em disco é resto de gravação interrompida, não cache válido."""
    caminho = _caminho(tmp_path)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(b"")

    assert deposito.ja_baixado(caminho) is False


def test_T96_timemodified_diferente_produz_caminho_diferente(tmp_path):
    antigo = _caminho(tmp_path, timemodified=1753400000)
    novo = _caminho(tmp_path, timemodified=1753499999)

    assert antigo != novo
    assert antigo.parent != novo.parent


def test_T96b_fileid_diferente_produz_caminho_diferente(tmp_path):
    """A colisão real de PSI3323: mesmo filename, dois ids."""
    um = _caminho(tmp_path, fileid="9599793", filename="Dicas para a Prova.pdf")
    outro = _caminho(tmp_path, fileid="9599833", filename="Dicas para a Prova.pdf")

    assert um != outro


def test_T96c_timemodified_ausente_vira_zero_e_nao_quebra(tmp_path):
    caminho = _caminho(tmp_path, timemodified=0)
    assert caminho.resolve().is_relative_to(tmp_path.resolve())


def test_a_raiz_padrao_fica_fora_do_repositorio():
    """Num `pip install` não existe repositório; e material do professor não
    deve ficar na árvore de trabalho protegido só pelo .gitignore."""
    assert deposito.RAIZ_PADRAO.is_absolute()
    assert "usp-mcp" in str(deposito.RAIZ_PADRAO)
    assert Path.cwd() not in deposito.RAIZ_PADRAO.parents
```

- [ ] **Passo 2: rodar e ver falhar**

```bash
.venv/bin/python -m pytest tests/moodle/test_deposito.py -v
```

Esperado: FAIL na coleta — `ImportError: cannot import name 'deposito'`.

- [ ] **Passo 3: implementar**

Crie `usp_mcp/moodle/deposito.py`:

```python
"""Onde o arquivo baixado mora, e por que o caminho tem essa forma.

Fica **fora do repositório**, em `~/.cache/usp-mcp/moodle/`, por dois motivos:
numa instalação via `pip` não existe repositório nenhum (o §6 decide que cada
pessoa roda o servidor na própria máquina, com o próprio token), e material do
professor não deve ficar dentro da árvore de trabalho protegido só pelo
`.gitignore`.

A forma do caminho é

    <raiz>/<courseid>/<fileid>-<timemodified>/<slug>.<ext>

e cada segmento resolve um problema medido:

- **`fileid`** resolve uma colisão real: em PSI3323, `Dicas para a Prova.pdf`
  existe duas vezes, com ids diferentes (9599793 na seção *Geral*, 9599833 na
  *AULA 6*). Só o nome não distingue.
- **`timemodified`** faz o Invariante 5 valer de graça: arquivo já baixado e não
  modificado não é rebaixado, porque o diretório já existe. Arquivo alterado no
  Moodle ganha diretório novo, sem invalidação explícita nenhuma.
- **`slug`** preserva o nome legível para quem abre o arquivo, mas nunca é o
  `filename` cru: ele vem do Moodle e é entrada não confiável.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ_PADRAO = Path.home() / ".cache" / "usp-mcp" / "moodle"

# Teto do nome em disco. Nomes de arquivo de disciplina passam de 60 chars com
# facilidade; 128 preserva o reconhecível e não estoura limite de filesystem.
_MAX_NOME = 128

_PROIBIDOS = re.compile(r"[^A-Za-z0-9._-]")


def _slug(filename: str) -> str:
    """`filename` cru → nome seguro, ainda legível.

    Três passos, e o terceiro é o que importa: `..` sobrevive à whitelist,
    porque `.` está nela. Um nome que seja só pontos viraria travessia de
    diretório se alguém compusesse caminho com ele — então pontos iniciais caem.
    """
    bruto = (filename or "").strip().replace("\\", "/").split("/")[-1]
    limpo = _PROIBIDOS.sub("_", bruto).lstrip(".")
    limpo = limpo[:_MAX_NOME]
    return limpo or "arquivo"


def caminho_para(
    *,
    courseid: int,
    fileid: str,
    timemodified: int,
    filename: str,
    raiz: Path | None = None,
) -> Path:
    """O caminho deste arquivo, sem tocar o disco.

    `raiz` é injetável para que o teste não escreva no cache de verdade da
    máquina de quem roda a suíte.
    """
    base = Path(raiz) if raiz is not None else RAIZ_PADRAO
    caminho = (
        base
        / str(int(courseid))
        / f"{_slug(str(fileid))}-{int(timemodified or 0)}"
        / _slug(filename)
    )
    # Cinto e suspensório: se algum dia um segmento escapar da sanitização, é
    # aqui que o erro aparece, em vez de num arquivo escrito fora do depósito.
    if not caminho.resolve().is_relative_to(base.resolve()):
        raise ValueError(
            f"caminho calculado sairia do depósito: {caminho}. "
            "Isto é bug de sanitização, não entrada inesperada."
        )
    return caminho


def ja_baixado(caminho: Path) -> bool:
    """Existe e não está vazio.

    Zero byte em disco é resto de gravação interrompida, não cache válido —
    tratá-lo como pronto entregaria um arquivo vazio com cara de sucesso.
    """
    return caminho.is_file() and caminho.stat().st_size > 0


def gravar(caminho: Path, dados: bytes) -> Path:
    """Grava, criando o diretório. Devolve o caminho para encadear."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(dados)
    return caminho
```

- [ ] **Passo 4: rodar e ver passar**

```bash
.venv/bin/python -m pytest tests/moodle/test_deposito.py -v
```

Esperado: todos PASS.

- [ ] **Passo 5: sabotar**

1. Troque `.lstrip(".")` por nada → T92 fica vermelho no caso `".."`.
2. Tire o `fileid` do nome do diretório → T96b fica vermelho.
3. Troque `st_size > 0` por `st_size >= 0` → T95b fica vermelho.

- [ ] **Passo 6: commit**

```bash
git add usp_mcp/moodle/deposito.py tests/moodle/test_deposito.py
git commit -m "feat(moodle): deposito — caminho seguro, nome legivel, reuso por timemodified

Fora do repositorio (~/.cache/usp-mcp/moodle/): num pip install nao ha repo, e
material do professor nao deve ficar na arvore protegido so pelo gitignore.

<courseid>/<fileid>-<timemodified>/<slug> resolve tres coisas medidas: a colisao
real de PSI3323 (mesmo filename, dois ids), o reuso sem invalidacao explicita, e
filename como entrada nao confiavel.

T92, T92b-d, T95, T95b, T96, T96b, T96c."
```

---

### Tarefa 3: casamento de nome num lugar só, e o `Item` ganha o que o download precisa

**Arquivos:**
- Criar: `usp_mcp/moodle/texto.py`
- Modificar: `usp_mcp/moodle/disciplinas.py` (passa a importar de `texto`)
- Modificar: `usp_mcp/moodle/material.py` (`Item` e o filtro de `busca`)
- Modificar: `tests/moodle/test_material.py` (T68b, T68c, T102)

**Interfaces:**
- Produz, e as tarefas 4 e 5 dependem destes nomes exatos:
  - `texto.normalizar(s: str) -> str`
  - `texto.casa(termo: str, alvo: str) -> bool`
  - `material.Item` com os campos novos `fileurl_bruta: str | None`,
    `fileid: str | None`, `secao: str`, `modulo: str` (todos com default, para
    não quebrar construção posicional existente).

**Por que esta tarefa existe.** Medido em 01/09: `material` filtra com
`filtro in i.nome.lower()`, **sem** normalização — `"formulario"` não acha
`"Formulário Provas Substitutivas.pdf"`. É o mesmo bug do acento corrigido em
31/08 (T83), sobrevivendo em outro lugar do mesmo módulo. Criar uma terceira
semântica de busca em `arquivo.py` deixaria três comportamentos diferentes para
"casar nome" no mesmo servidor. Registrado no `BACKLOG-correcoes.md` em 01/09.

**O risco desta tarefa, e ele tem nome.** Acrescentar `fileurl_bruta` ao `Item`
é exatamente a mudança que pode fazer `material` voltar a emitir a URL interna —
o que T68 existe para impedir (Invariante 3). Mas **T68 hoje olha só
`i.url_externa`**: um campo novo passaria por baixo dele sem ser visto. Por isso
esta tarefa **fortalece T68** antes de tocar no `Item`.

- [ ] **Passo 1: escrever os testes que falham**

Acrescente ao fim de `tests/moodle/test_material.py`:

```python
# --- T68b, T68c, T102 -------------------------------------------------------

@pytest.mark.politica
def test_T68b_o_texto_entregue_ao_modelo_nunca_contem_url_interna(
    conteudo_bruto, disciplinas_brutas
):
    """T68 olha só `url_externa`; um campo novo no Item passaria por baixo dele.

    Esta asserção é sobre o que de fato chega ao modelo: o texto da resposta.
    """
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 1},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "core_course_get_contents": conteudo_bruto,
        }
    )
    dis.limpar_cache()
    resposta = mat.material(cliente, "PSI3323")

    assert "pluginfile.php" not in resposta.texto
    assert "/webservice/" not in resposta.texto
    assert "token" not in resposta.texto.lower()


@pytest.mark.politica
def test_T68c_como_dict_nao_carrega_a_url_interna(conteudo_bruto):
    """`como_dict` alimenta a medição de custo e é fácil de estender sem pensar."""
    import json as _json

    c = mat.projetar_material(conteudo_bruto)
    serializado = _json.dumps(mat.como_dict(c), ensure_ascii=False)

    assert "pluginfile.php" not in serializado
    assert "/webservice/" not in serializado


@pytest.mark.contrato
def test_T102_busca_por_nome_ignora_acento(conteudo_bruto, disciplinas_brutas):
    """Medido em 01/09: 'formulario' não achava 'Formulário Provas
    Substitutivas.pdf'. Mesmo bug do acento de T83, em outro lugar."""
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 1},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "core_course_get_contents": conteudo_bruto,
        }
    )
    dis.limpar_cache()
    resposta = mat.material(cliente, "PSI3323", busca="formulario")

    assert resposta.mostrados >= 1
    assert "Formulário" in resposta.texto


@pytest.mark.contrato
def test_T102b_o_item_carrega_secao_modulo_e_fileid(conteudo_bruto):
    """O que `arquivo.py` precisa para desempatar a colisão real."""
    c = mat.projetar_material(conteudo_bruto)
    itens = [i for s in c.secoes for i in s.itens if i.nome == "Dicas para a Prova.pdf"]

    assert len(itens) == 2, "a colisão real de PSI3323 sumiu da fixture"
    assert {i.fileid for i in itens} == {"9599793", "9599833"}
    assert all(i.secao and i.modulo for i in itens)
    assert all(i.fileurl_bruta and "pluginfile.php" in i.fileurl_bruta for i in itens)
```

Confira o topo de `tests/moodle/test_material.py`: precisa importar `ClienteFalso`
do `conftest` e `usp_mcp.moodle.disciplinas as dis` (veja como os testes existentes
do arquivo já fazem — siga o padrão que estiver lá, não invente outro).

- [ ] **Passo 2: rodar e ver falhar**

```bash
.venv/bin/python -m pytest tests/moodle/test_material.py -v -k "T68b or T68c or T102"
```

Esperado: T102 FAIL (`mostrados` é 0 — o bug do acento), T102b FAIL
(`AttributeError: 'Item' object has no attribute 'fileid'`). **T68b e T68c devem
PASSAR** desde já — eles são a rede de proteção, não a novidade. Se algum dos dois
falhar agora, pare: há um vazamento de URL interna que ninguém sabia que existia.

- [ ] **Passo 3: criar `texto.py`**

```python
"""Casar o que a pessoa digita com o que o Moodle escreveu.

Um lugar só, porque já houve dois. `disciplinas._normalizar` nasceu para resolver
sigla e ganhou o `NFD` em 31/08, quando o dono digitou "eletronica" e o filtro
descartou a letra acentuada inteira (T83). O filtro `busca` de `material` nasceu
no mesmo dia com `filtro in nome.lower()` e **não** ganhou a correção: medido em
01/09, "formulario" não achava "Formulário Provas Substitutivas.pdf". Duas
semânticas de casamento no mesmo servidor, e a terceira estava prestes a nascer
em `arquivo.py`.
"""
from __future__ import annotations

import re
import unicodedata


def normalizar(s: str) -> str:
    """"psi 3323" → "PSI3323"; "Eletrônica" → "ELETRONICA".

    O `NFD` é o que faz isso funcionar e não é decoração: ele separa "ô" em "o"
    mais a marca combinante, e aí o filtro descarta só a marca. Sem ele o filtro
    descartava o "ô" inteiro, "Eletrônica" virava "ELETRNICA", e deixava de casar
    com "eletronica". T83 fica vermelho se alguém o remover por parecer supérfluo.
    """
    decomposto = unicodedata.normalize("NFD", s or "")
    return re.sub(r"[^A-Z0-9]", "", decomposto.upper())


def casa(termo: str, alvo: str) -> bool:
    """Substring, sem acento, sem caixa, sem pontuação. Termo vazio casa com tudo.

    Termo vazio casando com tudo é o que faz `material` sem `busca` continuar
    listando o espaço inteiro — não é permissividade acidental.
    """
    return normalizar(termo) in normalizar(alvo)
```

- [ ] **Passo 4: `disciplinas.py` passa a usar `texto`**

Remova a função `_normalizar` de `usp_mcp/moodle/disciplinas.py` (e os imports `re`
e `unicodedata`, se ficarem órfãos) e ponha, junto dos outros imports:

```python
from .texto import normalizar as _normalizar
```

O alias preserva o nome usado no corpo do módulo — nenhuma outra linha muda. Rode
já para confirmar que nada quebrou:

```bash
.venv/bin/python -m pytest tests/moodle -v
```

Esperado: tudo que passava continua passando; T102 e T102b seguem vermelhos.

- [ ] **Passo 5: `Item` ganha os campos, e `busca` passa a usar `casa`**

Em `usp_mcp/moodle/material.py`:

1. Importe: `from .texto import casa`
2. No dataclass `Item`, acrescente ao fim (com default, para não quebrar
   construção posicional):

```python
    # Campos para consumo INTERNO de `arquivo.py`, nunca impressos: T68b e T68c
    # são os guardas disso. `fileurl_bruta` é a `fileurl` como o Moodle a
    # devolveu — para um `resource` ela é a URL do webservice, para um `url` é o
    # endereço externo. O nome diz "bruta" e não "interna" porque as duas coisas
    # passam por aqui, e é `fileid` (ausente no link externo) que as separa.
    fileurl_bruta: str | None = None
    fileid: str | None = None
    mimetype: str | None = None
    secao: str = ""
    modulo: str = ""
```

3. Acrescente a extração do id, ao lado de `_url_publica`:

```python
def _fileid(bruto: str | None) -> str | None:
    """O primeiro segmento depois de `pluginfile.php/` — o id do arquivo.

    Não é segredo (a URL inteira é que exige credencial para servir de algo), e
    é o que distingue dois arquivos de mesmo nome: em PSI3323, `Dicas para a
    Prova.pdf` existe duas vezes, com ids 9599793 e 9599833.
    """
    if not bruto or "pluginfile.php/" not in bruto:
        return None
    return bruto.split("pluginfile.php/", 1)[1].split("/", 1)[0] or None
```

4. Em `projetar_material`, dentro do laço, o `Item(...)` ganha os quatro campos:

```python
                        fileurl_bruta=conteudo.get("fileurl"),
                        fileid=_fileid(conteudo.get("fileurl")),
                        mimetype=conteudo.get("mimetype"),
                        secao=secao.get("name") or "",
                        modulo=modulo.get("name") or "",
```

5. Em `material()`, troque o filtro:

```python
        itens = [i for i in secao.itens if not filtro or filtro in i.nome.lower()]
```

por

```python
        itens = [i for i in secao.itens if casa(filtro, i.nome)]
```

e, logo acima, troque `filtro = (busca or "").strip().lower()` por
`filtro = (busca or "").strip()` — `casa` já normaliza, e deixar o `.lower()`
aqui seria a segunda normalização parcial que esta tarefa existe para eliminar.

- [ ] **Passo 6: rodar tudo**

```bash
.venv/bin/python -m pytest tests/moodle -v
```

Esperado: **todos PASS**, incluindo T68, T68b, T68c, T69, T102 e T102b.

- [ ] **Passo 7: sabotar**

1. Em `texto.normalizar`, troque `"NFD"` por `"NFC"` → T102 vermelho (e T83, via
   `disciplinas`).
2. Em `material.como_dict`, acrescente `"fileurl": i.fileurl_bruta` ao dicionário
   → **T68c vermelho**. Esta é a sabotagem mais importante da tarefa: ela prova que
   o guarda novo pega o vazamento que o antigo não pegava. Desfaça.
3. Em `_formatar_item`, acrescente `linha += f"\n    {item.fileurl_bruta}"` →
   **T68b vermelho**. Desfaça.

- [ ] **Passo 8: commit**

```bash
git add usp_mcp/moodle/texto.py usp_mcp/moodle/disciplinas.py usp_mcp/moodle/material.py tests/moodle/test_material.py
git commit -m "fix(moodle): casamento de nome num lugar so; Item carrega o que o download precisa

Medido em 01/09: 'formulario' nao achava 'Formulario Provas Substitutivas.pdf'
— o filtro de busca de material usava nome.lower() sem o NFD que disciplinas
ganhou em 31/08 (T83). Mesmo bug do acento, outro lugar do mesmo modulo. As
duas semanticas viram uma em texto.casa(), antes que arquivo.py criasse a
terceira.

Item ganha fileurl_bruta/fileid/secao/modulo para consumo interno. T68 olhava
so url_externa e nao veria um campo novo vazar: T68b (o texto entregue ao
modelo) e T68c (como_dict) fecham o buraco, e a sabotagem confirmou que pegam.

T68b, T68c, T102, T102b."
```

---

### Tarefa 4: `arquivo.py` — resolver, casar, baixar um

**Arquivos:**
- Criar: `usp_mcp/moodle/arquivo.py`
- Criar: `tests/moodle/test_arquivo.py`
- Modificar: `tests/moodle/conftest.py` (o dublê aprende a baixar)

**Interfaces:**
- Consome: `disciplinas.carregar/resolver`, `material.projetar_material`,
  `texto.casa`, `deposito.*`, `ClienteMoodle.baixar` (tarefa 1).
- Produz, e a tarefa 6 depende destes nomes exatos:
  - `arquivo.baixar_arquivo(cliente, disciplina: str, nome: str, todos: bool = False, agora=None, raiz=None) -> RespostaArquivo`
  - `arquivo.RespostaArquivo` com os campos `texto`, `baixados`, `links`,
    `recusados`, `candidatos`.

**Convenção de erro, e ela segue `material`:** sigla que não resolve **levanta**
`ErroMoodle` (é pergunta malformada, e resolver antes de chamar evita gastar
chamada da conta). Todo o resto — nada casou, casou demais, é link, passou do teto
— **devolve** `RespostaArquivo` com texto explicativo. O spec chama os dois de
"erro legível" porque o efeito para quem lê é o mesmo; a diferença é que só o
primeiro é malformação da pergunta.

- [ ] **Passo 1: o dublê aprende a baixar**

Em `tests/moodle/conftest.py`, dentro da classe `ClienteFalso`, acrescente o
parâmetro e o método (mantendo tudo que já existe):

```python
    def __init__(self, respostas: dict, arquivos: dict | None = None):
        self._respostas = respostas
        self._arquivos = arquivos or {}
        self.chamadas: list[tuple[str, dict]] = []
        self.downloads: list[str] = []

    def baixar(self, fileurl: str, *, tamanho_esperado=None, teto_bytes=None) -> bytes:
        """Grava a URL pedida — asserção sobre o que foi ENVIADO, não sobre a saída.

        `downloads` vazio é o que prova que um caminho NÃO baixou; a saída não
        prova isso, porque o dublê devolveria bytes de qualquer jeito.
        """
        self.downloads.append(fileurl)
        if fileurl in self._arquivos:
            return self._arquivos[fileurl]
        conteudo = b"%PDF-1.4 " + b"x" * max((tamanho_esperado or 9) - 9, 0)
        return conteudo
```

- [ ] **Passo 2: escrever os testes que falham**

Crie `tests/moodle/test_arquivo.py`:

```python
"""T84–T90, T95c — a terceira ferramenta do Moodle, no singular.

Tudo offline: nenhum teste deste arquivo toca a rede. O `raiz` do depósito é
sempre `tmp_path`, para não escrever no cache real de quem roda a suíte.
"""
from __future__ import annotations

import pytest

from usp_mcp.moodle import arquivo as arq
from usp_mcp.moodle import disciplinas as dis
from usp_mcp.moodle.erros import ErroMoodle

from .conftest import ClienteFalso


@pytest.fixture(autouse=True)
def _cache_limpo():
    """Cache de processo compartilhado entre casos produz verde que nunca chamou
    nada — o mesmo motivo pelo qual `limpar_cache` existe."""
    dis.limpar_cache()
    yield
    dis.limpar_cache()


def _cliente(conteudo_bruto, disciplinas_brutas, **extra):
    return ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 1},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "core_course_get_contents": conteudo_bruto,
        },
        **extra,
    )


@pytest.mark.contrato
def test_T84_sigla_que_nao_resolve_nao_gasta_chamada_de_conteudo(disciplinas_brutas):
    """Consultar o Moodle para descobrir que a pergunta estava errada é gastar
    chamada da conta do dono à toa."""
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 1},
            "core_enrol_get_users_courses": disciplinas_brutas,
        }
    )

    with pytest.raises(ErroMoodle):
        arq.baixar_arquivo(cliente, "XYZ9999", "prova")

    chamadas = [nome for nome, _ in cliente.chamadas]
    assert "core_course_get_contents" not in chamadas
    assert cliente.downloads == []


@pytest.mark.contrato
def test_T85_nenhum_casamento_diz_o_total_da_disciplina(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """'nada com esse nome' e 'disciplina vazia' têm curas diferentes."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "zzz-nao-existe", raiz=tmp_path)

    assert r.baixados == ()
    assert cliente.downloads == []
    assert "29" in r.texto  # o total de itens de PSI3323


@pytest.mark.contrato
def test_T86_um_casamento_baixa_grava_e_devolve_o_caminho(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert len(r.baixados) == 1
    baixado = r.baixados[0]
    assert baixado.nome == "Prova-PSI3323-2026-Grupos.pdf"
    assert baixado.caminho.is_file()
    assert baixado.caminho.read_bytes().startswith(b"%PDF")
    assert str(baixado.caminho) in r.texto
    assert len(cliente.downloads) == 1


@pytest.mark.contrato
def test_T86b_a_resposta_diz_que_quem_abre_o_arquivo_e_quem_chamou(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Sem isso, um cliente que não saiba ler arquivo local recebe um caminho e
    não entende o que fazer com ele (Invariante 6)."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert "disco" in r.texto.lower()
    assert "abra" in r.texto.lower() or "abrir" in r.texto.lower()


@pytest.mark.contrato
def test_T87_ambiguidade_recusa_e_lista_secao_e_modulo(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """A colisão REAL de PSI3323: 'Dicas para a Prova.pdf' existe duas vezes,
    com ids 9599793 (seção Geral) e 9599833 (seção AULA 6). O nome sozinho não
    distingue — por isso o desempate mostra seção e módulo, não o id."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", raiz=tmp_path)

    assert r.baixados == ()
    assert cliente.downloads == [], "recusou e mesmo assim baixou"
    assert len(r.candidatos) == 2
    assert "Geral" in r.texto and "AULA 6" in r.texto
    assert "todos" in r.texto.lower()


@pytest.mark.contrato
def test_T89_casamento_ignora_acento(conteudo_bruto, disciplinas_brutas, tmp_path):
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "formulario", raiz=tmp_path)

    assert len(r.baixados) == 1
    assert r.baixados[0].nome.startswith("Formul")


@pytest.mark.politica
def test_T90_link_externo_nao_e_baixado(conteudo_bruto, disciplinas_brutas, tmp_path):
    """Os 7 `url` de PSI3323 apontam para fora (YouTube, Google Docs). Baixá-los
    mandaria o token para outro host — e a allowlist do cliente recusaria."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Planilha de Notas", raiz=tmp_path)

    assert r.baixados == ()
    assert cliente.downloads == []
    assert len(r.links) == 1
    assert r.links[0].url.startswith("http")
    assert "link" in r.texto.lower()


@pytest.mark.contrato
def test_T95c_segunda_chamada_reusa_o_disco_sem_baixar_de_novo(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Invariante 5: TTL colado na taxa de mudança do dado. Aqui o 'TTL' é o
    `timemodified` no caminho — arquivo não modificado não é rebaixado."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    primeira = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)
    assert len(cliente.downloads) == 1

    segunda = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert len(cliente.downloads) == 1, "baixou de novo o que já estava em disco"
    assert segunda.baixados[0].caminho == primeira.baixados[0].caminho
    assert segunda.baixados[0].reusado is True
    assert primeira.baixados[0].reusado is False


@pytest.mark.politica
def test_T99c_nenhuma_url_interna_aparece_no_texto_da_resposta(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """A ferramenta que BAIXA também não emite a URL — o caminho local é a
    entrega, e a URL continua sendo o que não sai (Invariante 3)."""
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert "pluginfile.php" not in r.texto
    assert "/webservice/" not in r.texto
```

- [ ] **Passo 3: rodar e ver falhar**

```bash
.venv/bin/python -m pytest tests/moodle/test_arquivo.py -v
```

Esperado: FAIL na coleta — `ImportError: cannot import name 'arquivo'`.

- [ ] **Passo 4: implementar `arquivo.py`**

```python
"""Baixar UM arquivo do espaço da disciplina, e entregar o CAMINHO.

A ferramenta não lê o arquivo: quem lê é o agente que chamou. A decisão é do §9
de 01/09/2026 e veio com número — entregar os bytes pelo canal MCP custaria
~302.000 tokens no PDF médio da amostra (base64), contra ~50 do caminho; e
extrair o texto no servidor custaria ~2.679, mas **perderia as figuras**, que num
acervo de eletrônica (circuitos, formas de onda, esquemas) são o conteúdo. Os
slides medidos têm 280–440 B de texto por página: são quase só imagem.

Convenção de erro, seguindo `material`: sigla que não resolve **levanta**, porque
é pergunta malformada e resolver antes evita gastar chamada da conta. O resto —
nada casou, casou demais, é link, passou do teto — **devolve** resposta com texto
explicativo, porque são resultados legítimos e o Invariante 6 pede que cada um
diga a própria cura.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import deposito
from .cliente import TETO_ARQUIVO_BYTES as _TETO_CLIENTE
from .disciplinas import carregar, resolver
from .erros import ErroMoodle
from .material import projetar_material
from .texto import casa

# Rebatizado como nome DESTE módulo de propósito: o cliente guarda o teto do
# transporte, este é o teto da ferramenta. Mesmo valor, dois donos com razões
# diferentes — e é este nome que o `monkeypatch` do teste alcança.
TETO_ARQUIVO_BYTES = _TETO_CLIENTE


@dataclass(frozen=True)
class Baixado:
    nome: str
    tipo: str
    mimetype: str | None
    tamanho: int
    caminho: Path
    fileid: str
    secao: str
    modulo: str
    reusado: bool


@dataclass(frozen=True)
class Link:
    nome: str
    url: str


@dataclass(frozen=True)
class Recusado:
    nome: str
    motivo: str


@dataclass(frozen=True)
class Candidato:
    nome: str
    tamanho: int | None
    secao: str
    modulo: str


@dataclass(frozen=True)
class RespostaArquivo:
    texto: str
    baixados: tuple[Baixado, ...] = ()
    links: tuple[Link, ...] = ()
    recusados: tuple[Recusado, ...] = ()
    candidatos: tuple[Candidato, ...] = ()


_AVISO_LEITURA = (
    "O arquivo está no disco DESTA máquina. Abra-o com a sua ferramenta de "
    "leitura de arquivos para ver o conteúdo — este servidor entrega o caminho, "
    "não o texto."
)


def _kb(n) -> str:
    return f"{n // 1024} kB" if n else "tamanho desconhecido"


def _baixar_um(cliente, item, courseid: int, raiz) -> Baixado:
    """Baixa se preciso, grava, devolve o registro. Reuso é a existência do arquivo."""
    caminho = deposito.caminho_para(
        courseid=courseid,
        fileid=item.fileid,
        timemodified=int(item.modificado.timestamp()) if item.modificado else 0,
        filename=item.nome,
        raiz=raiz,
    )
    reusado = deposito.ja_baixado(caminho)
    if not reusado:
        dados = cliente.baixar(item.fileurl_bruta, tamanho_esperado=item.tamanho)
        deposito.gravar(caminho, dados)

    return Baixado(
        nome=item.nome,
        tipo=item.tipo,
        mimetype=item.mimetype,
        tamanho=item.tamanho or caminho.stat().st_size,
        caminho=caminho,
        fileid=item.fileid,
        secao=item.secao,
        modulo=item.modulo,
        reusado=reusado,
    )


def baixar_arquivo(
    cliente,
    disciplina: str,
    nome: str,
    todos: bool = False,
    agora=None,
    raiz=None,
) -> RespostaArquivo:
    """Uma disciplina, um trecho de nome, um arquivo (ou vários com `todos`)."""
    lista = carregar(cliente, agora=agora)
    resolucao = resolver(lista, disciplina)
    if resolucao.disciplina is None:
        raise ErroMoodle(resolucao.motivo)

    alvo = resolucao.disciplina
    conteudo = projetar_material(
        cliente.chamar("core_course_get_contents", courseid=alvo.courseid)
    )
    itens = [i for s in conteudo.secoes for i in s.itens]
    casados = [i for i in itens if casa(nome, i.nome)]
    cabecalho = f"{alvo.sigla} ({alvo.rotulo})"

    if not casados:
        return RespostaArquivo(
            texto=(
                f"{cabecalho} — nenhum arquivo com {nome!r} no nome. "
                f"A disciplina tem {conteudo.total_itens} itens no total; use a "
                "ferramenta `material` para ver a lista e repita com um nome de lá."
            )
        )

    if len(casados) > 1 and not todos:
        candidatos = tuple(
            Candidato(nome=i.nome, tamanho=i.tamanho, secao=i.secao, modulo=i.modulo)
            for i in casados
        )
        linhas = [
            f"{cabecalho} — {nome!r} casa com {len(casados)} arquivos. "
            "Nenhum foi baixado."
        ]
        linhas += [
            f"  - {c.nome} [{_kb(c.tamanho)}] — seção {c.secao!r}, módulo {c.modulo!r}"
            for c in candidatos
        ]
        linhas.append(
            "Repita com um trecho mais específico, ou com todos=true para baixar "
            f"os {len(casados)}."
        )
        return RespostaArquivo(texto="\n".join(linhas), candidatos=candidatos)

    return _entregar(cliente, cabecalho, casados, alvo.courseid, raiz, todos)


def _entregar(cliente, cabecalho, casados, courseid, raiz, todos) -> RespostaArquivo:
    """Separa link de arquivo, baixa o que dá, e monta o texto. `todos` entra
    aqui para a tarefa 5 acrescentar os tetos sem mexer no roteamento acima."""
    baixados: list[Baixado] = []
    links: list[Link] = []
    recusados: list[Recusado] = []

    for item in casados:
        if not item.fileurl_bruta or not item.fileid:
            # Link externo (YouTube, Google Docs): a URL já é pública e sai
            # inteira. Baixá-lo mandaria o token para outro host — e a allowlist
            # do cliente recusaria, com razão.
            links.append(Link(nome=item.nome, url=item.url_externa or ""))
            continue
        if item.tamanho and item.tamanho > TETO_ARQUIVO_BYTES:
            recusados.append(
                Recusado(
                    nome=item.nome,
                    motivo=(
                        f"{_kb(item.tamanho)} passa do teto de "
                        f"{TETO_ARQUIVO_BYTES // (1024 * 1024)} MB por arquivo"
                    ),
                )
            )
            continue
        baixados.append(_baixar_um(cliente, item, courseid, raiz))

    linhas = [f"{cabecalho} — {len(baixados)} arquivo(s) baixado(s)."]
    for b in baixados:
        marca = " (já estava em disco)" if b.reusado else ""
        linhas.append(f"\n{b.nome} [{b.tipo}, {_kb(b.tamanho)}]{marca}")
        linhas.append(f"  {b.caminho}")
    for l in links:
        linhas.append(f"\n{l.nome} — é um link externo, não um arquivo do e-Disciplinas:")
        linhas.append(f"  {l.url}")
    # Invariante 7: o que não veio é NOMEADO, nunca omitido.
    for r in recusados:
        linhas.append(f"\n{r.nome} — não baixado: {r.motivo}")
    if baixados:
        linhas.append(f"\n⚠ {_AVISO_LEITURA}")

    return RespostaArquivo(
        texto="\n".join(linhas),
        baixados=tuple(baixados),
        links=tuple(links),
        recusados=tuple(recusados),
    )
```

- [ ] **Passo 5: rodar e ver passar**

```bash
.venv/bin/python -m pytest tests/moodle/test_arquivo.py -v
```

Esperado: todos PASS. Se T85 falhar por causa do número `29`, confirme o total com
`.venv/bin/python -c "import json;d=json.load(open('fixtures/moodle/course_contents_psi3323.json'));print(sum(len(m.get('contents') or []) for s in d for m in (s.get('modules') or [])))"`
e ajuste o teste para o valor real da fixture — não a produção.

- [ ] **Passo 6: sabotar**

1. Troque `if len(casados) > 1 and not todos:` por `if False:` → T87 vermelho
   (baixaria os dois calado).
2. Em `_baixar_um`, troque `reusado = deposito.ja_baixado(caminho)` por
   `reusado = False` → T95c vermelho.
3. Em `_entregar`, remova o `continue` do ramo de link → T90 vermelho.

- [ ] **Passo 7: commit**

```bash
git add usp_mcp/moodle/arquivo.py tests/moodle/test_arquivo.py tests/moodle/conftest.py
git commit -m "feat(moodle): arquivo.py — resolve, casa, baixa um, entrega o caminho

Terceira ferramenta do Moodle no singular. Ambiguidade recusa listando SECAO e
MODULO porque o nome sozinho nao distingue: em PSI3323 'Dicas para a Prova.pdf'
existe duas vezes, com ids 9599793 e 9599833. Link externo nao e baixado — a
URL ja e publica e o token iria para outro host.

Reuso e a existencia do arquivo no caminho <fileid>-<timemodified>: Invariante 5
sem invalidacao explicita. O dublê grava as URLs pedidas, porque 'nao baixou' so
se prova pelo que foi enviado.

T84, T85, T86, T86b, T87, T89, T90, T95c, T99c."
```

---

### Tarefa 5: modo plural e os tetos

**Arquivos:**
- Modificar: `usp_mcp/moodle/arquivo.py` (só `_entregar` e duas constantes)
- Modificar: `tests/moodle/test_arquivo.py`

**Interfaces:**
- Consome: tudo da tarefa 4.
- Produz: `arquivo.TETO_PLURAL_ARQUIVOS: int`, `arquivo.TETO_PLURAL_BYTES: int`.

- [ ] **Passo 1: escrever os testes que falham**

Acrescente a `tests/moodle/test_arquivo.py`:

```python
# --- T88, T97, T98: plural e tetos -----------------------------------------

@pytest.mark.contrato
def test_T88_todos_baixa_a_colisao_inteira_em_caminhos_distintos(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    assert len(r.baixados) == 2
    caminhos = {b.caminho for b in r.baixados}
    assert len(caminhos) == 2, "mesmo nome sobrescreveu — o fileid não entrou no caminho"
    assert {b.fileid for b in r.baixados} == {"9599793", "9599833"}
    assert all(c.is_file() for c in caminhos)


@pytest.mark.contrato
def test_T97_arquivo_acima_do_teto_e_recusado_ANTES_de_baixar(
    conteudo_bruto, disciplinas_brutas, tmp_path, monkeypatch
):
    """O `filesize` vem na listagem: dá para recusar sem gastar banda nenhuma."""
    monkeypatch.setattr(arq, "TETO_ARQUIVO_BYTES", 1000)
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "Grupos", raiz=tmp_path)

    assert cliente.downloads == [], "recusou pelo teto e mesmo assim baixou"
    assert r.baixados == ()
    assert len(r.recusados) == 1
    assert "teto" in r.recusados[0].motivo.lower()
    assert r.recusados[0].nome in r.texto


@pytest.mark.contrato
def test_T98_plural_acima_do_teto_de_contagem_nomeia_o_que_ficou_de_fora(
    conteudo_bruto, disciplinas_brutas, tmp_path, monkeypatch
):
    """Invariante 7: cortou, a saída diz — e diz QUAIS, não só quantos."""
    monkeypatch.setattr(arq, "TETO_PLURAL_ARQUIVOS", 1)
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    assert len(r.baixados) == 1
    assert len(r.recusados) == 1
    assert r.recusados[0].nome in r.texto
    assert len(cliente.downloads) == 1


@pytest.mark.contrato
def test_T98b_plural_acima_do_teto_de_bytes_para_no_limite(
    conteudo_bruto, disciplinas_brutas, tmp_path, monkeypatch
):
    monkeypatch.setattr(arq, "TETO_PLURAL_BYTES", 1)
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    assert len(r.baixados) <= 1
    assert r.recusados


@pytest.mark.contrato
def test_T98c_a_ordem_do_corte_e_a_da_listagem(
    conteudo_bruto, disciplinas_brutas, tmp_path, monkeypatch
):
    """Quem leu a lista em `material` e pediu todos=true recebe o PREFIXO do que
    viu — nada de 'os menores primeiro' nem de ordenação implícita."""
    monkeypatch.setattr(arq, "TETO_PLURAL_ARQUIVOS", 1)
    cliente = _cliente(conteudo_bruto, disciplinas_brutas)

    r = arq.baixar_arquivo(cliente, "PSI3323", "dicas", todos=True, raiz=tmp_path)

    # 9599793 está na seção 'Geral', que vem antes de 'AULA 6' na listagem.
    assert r.baixados[0].fileid == "9599793"
```

- [ ] **Passo 2: rodar e ver falhar**

```bash
.venv/bin/python -m pytest tests/moodle/test_arquivo.py -v -k "T88 or T97 or T98"
```

Esperado: T88 pode até passar (a tarefa 4 já baixa a lista inteira quando
`todos=True`); T97 e T98 FAIL — `AttributeError: module has no attribute
'TETO_PLURAL_ARQUIVOS'` e ausência de recusa.

- [ ] **Passo 3: implementar**

Em `usp_mcp/moodle/arquivo.py`, acrescente os tetos do plural ao lado do
`TETO_ARQUIVO_BYTES` que a tarefa 4 já definiu:

```python
# Plural: os 19 PDFs de PSI3323 somam 15,9 MB (medido em 01/09). Dez arquivos e
# 100 MB é folga sobre o pior caso conhecido, e o corte é declarado.
TETO_PLURAL_ARQUIVOS = 10
TETO_PLURAL_BYTES = 100 * 1024 * 1024
```

Em `_entregar`, dentro do laço, **antes** do `baixados.append(...)`, insira a
contabilidade do plural:

```python
        if todos and len(baixados) >= TETO_PLURAL_ARQUIVOS:
            recusados.append(
                Recusado(
                    nome=item.nome,
                    motivo=f"teto de {TETO_PLURAL_ARQUIVOS} arquivos por chamada",
                )
            )
            continue
        if todos and acumulado + (item.tamanho or 0) > TETO_PLURAL_BYTES and baixados:
            recusados.append(
                Recusado(
                    nome=item.nome,
                    motivo=f"teto de {TETO_PLURAL_BYTES // (1024 * 1024)} MB por chamada",
                )
            )
            continue
```

Inicialize `acumulado = 0` junto das três listas, e depois do
`baixados.append(_baixar_um(...))` acrescente `acumulado += item.tamanho or 0`.

- [ ] **Passo 4: rodar e ver passar**

```bash
.venv/bin/python -m pytest tests/moodle/test_arquivo.py -v
```

Esperado: todos PASS.

- [ ] **Passo 5: sabotar**

1. Troque `recusados.append(...)` do teto de contagem por só `continue` → T98
   vermelho (cortou calado, que é o Invariante 7 quebrado).
2. Troque `>= TETO_PLURAL_ARQUIVOS` por `> TETO_PLURAL_ARQUIVOS` → T98 vermelho.
3. Ordene `casados` por tamanho antes do laço → T98c vermelho.

- [ ] **Passo 6: commit**

```bash
git add usp_mcp/moodle/arquivo.py tests/moodle/test_arquivo.py
git commit -m "feat(moodle): modo plural com teto declarado

todos=true baixa o conjunto casado ate 10 arquivos / 100 MB, e o que ficou de
fora e NOMEADO na saida (Invariante 7) — nao so contado. A ordem do corte e a
da listagem, para quem leu material e pediu todos receber o prefixo do que viu.

Arquivo acima do teto e recusado ANTES de baixar, pelo filesize que ja vem na
listagem: T97 asserta que o transporte nao foi chamado.

T88, T97, T98, T98b, T98c."
```

---

### Tarefa 6: a fronteira MCP

**Arquivos:**
- Modificar: `usp_mcp/moodle/server.py`
- Modificar: `tests/moodle/test_server_mcp.py`
- Modificar: `tests/moodle/test_server_stdio.py`

**Interfaces:**
- Consome: `arquivo.baixar_arquivo` (tarefas 4 e 5).
- Produz: a ferramenta `baixar_arquivo` exposta no fio.

**Atenção a um teste existente que VAI ficar vermelho, e está certo em ficar:**
T42 (`test_expoe_exatamente_uma_ferramenta`) trava o conjunto inteiro de nomes.
A docstring dele diz: *"uma terceira ferramenta aparecendo aqui sem passar pelo §9
deixa este teste vermelho, e ele está certo em ficar."* Esta ferramenta **passou**
pelo §9 (01/09), então atualize a lista esperada — não afrouxe a asserção para um
mínimo.

- [ ] **Passo 1: escrever os testes que falham**

Em `tests/moodle/test_server_mcp.py`, atualize T42 e acrescente T100/T101:

```python
def test_expoe_exatamente_uma_ferramenta():
    """T42 — três ferramentas. Cada crescimento é decisão registrada no §9:
    a segunda (`material`) em 31/08, a terceira (`baixar_arquivo`) em 01/09."""
    fs = server.listar_ferramentas()
    assert [f["name"] for f in fs] == ["o_que_vence", "material", "baixar_arquivo"]


def test_T100_o_descritor_de_baixar_arquivo_fala_a_lingua_de_quem_pergunta():
    f = [x for x in server.listar_ferramentas() if x["name"] == "baixar_arquivo"][0]

    assert "pluginfile" not in f["description"]
    assert "core_course_get_contents" not in f["description"]
    # A descrição TEM de dizer que devolve um caminho a ser aberto — sem isso o
    # modelo recebe um path e não sabe que o próximo passo é dele.
    assert "caminho" in f["description"].lower()
    props = f["inputSchema"]["properties"]
    assert set(props) == {"disciplina", "nome", "todos"}
    assert f["inputSchema"]["required"] == ["disciplina", "nome"]
    assert all(p.get("description") for p in props.values())


def test_T101_chamar_ferramenta_roteia_baixar_arquivo_com_cliente_injetado(
    conteudo_bruto, disciplinas_brutas, tmp_path
):
    """Sem credencial nenhuma: a injeção de cliente é o que torna a fronteira
    testável offline (§9, 31/08)."""
    from usp_mcp.moodle import disciplinas as dis

    from .conftest import ClienteFalso

    dis.limpar_cache()
    cliente = ClienteFalso(
        {
            "core_webservice_get_site_info": {"userid": 1},
            "core_enrol_get_users_courses": disciplinas_brutas,
            "core_course_get_contents": conteudo_bruto,
        }
    )

    saida = server.chamar_ferramenta(
        "baixar_arquivo",
        {"disciplina": "PSI3323", "nome": "Grupos", "raiz": str(tmp_path)},
        cliente=cliente,
    )

    dis.limpar_cache()
    assert isinstance(saida, str)
    assert "Prova-PSI3323-2026-Grupos.pdf" in saida
    assert "pluginfile.php" not in saida
```

**Nota sobre `raiz` no dicionário de argumentos:** o parâmetro **não** entra no
`inputSchema` (o modelo não escolhe onde gravar), mas `chamar_ferramenta` o aceita
para o teste não escrever no cache real. Implemente-o como
`argumentos.get("raiz")`.

- [ ] **Passo 2: rodar e ver falhar**

```bash
.venv/bin/python -m pytest tests/moodle/test_server_mcp.py -v
```

Esperado: T42, T100, T101 FAIL.

- [ ] **Passo 3: implementar em `server.py`**

1. Import: `from .arquivo import baixar_arquivo`
2. Constante, junto das outras: `_NOME_ARQUIVO = "baixar_arquivo"`
3. Acrescente o descritor ao fim da lista de `listar_ferramentas()`:

```python
        {
            "name": _NOME_ARQUIVO,
            "description": (
                "Baixa um arquivo publicado no espaço da disciplina no "
                "e-Disciplinas (Moodle da USP) e devolve o CAMINHO dele no disco "
                "desta máquina, para que você mesmo o abra com a sua ferramenta "
                "de leitura de arquivos. Use para 'me dá a lista 2 de PSI3323', "
                "'abre a apostila de amp op', 'pega a prova anterior'. Para saber "
                "que arquivos existem antes de escolher, use `material`."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "disciplina": {
                        "type": "string",
                        "description": (
                            "Sigla da disciplina como no e-Disciplinas, por "
                            "exemplo PSI3323. Espaço e caixa não importam. Casa "
                            "também com pedaço do nome."
                        ),
                    },
                    "nome": {
                        "type": "string",
                        "description": (
                            "Pedaço do nome do arquivo, como aparece em "
                            "`material` — 'lista 2', 'apostila', 'regras'. "
                            "Acento e caixa não importam. Se casar com mais de "
                            "um, a resposta lista os candidatos em vez de "
                            "escolher por você."
                        ),
                    },
                    "todos": {
                        "type": "boolean",
                        "description": (
                            "Baixa TODOS os arquivos que casarem, em vez de "
                            "recusar a ambiguidade. Padrão falso. Há teto por "
                            "chamada, e o que ficar de fora é nomeado na saída."
                        ),
                    },
                },
                "required": ["disciplina", "nome"],
                "additionalProperties": False,
            },
        },
```

4. Em `chamar_ferramenta`, acrescente `_NOME_ARQUIVO` à tupla de nomes conhecidos
   e à mensagem de erro, e o roteamento antes do `return o_que_vence(...)`:

```python
    if nome == _NOME_ARQUIVO:
        return baixar_arquivo(
            cliente,
            argumentos["disciplina"],
            argumentos["nome"],
            todos=bool(argumentos.get("todos")),
            raiz=argumentos.get("raiz"),
        ).texto
```

5. Em `main()`, troque o desempacotamento
   `porta_vence, porta_material = listar_ferramentas()` por
   `porta_vence, porta_material, porta_arquivo = listar_ferramentas()` e registre:

```python
    def _baixar_arquivo(disciplina, nome, todos=False) -> str:
        # `disciplina` e `nome` SEM default: no SDK é a ausência de default que
        # torna o parâmetro obrigatório no fio, e o `inputSchema` os declara em
        # `required`. Com `=None` os dois divergiriam — foi assim que H6 pegou
        # `material` em 31/08.
        return chamar_ferramenta(
            porta_arquivo["name"],
            {"disciplina": disciplina, "nome": nome, "todos": todos},
        )

    anotar(
        _baixar_arquivo,
        porta_arquivo["inputSchema"],
        {"disciplina": str, "nome": str, "todos": bool},
    )
    servidor.tool(
        name=porta_arquivo["name"], description=porta_arquivo["description"]
    )(_baixar_arquivo)
```

6. Em `_auto_verificar`, acrescente a sonda — sem ela a verificação imprime
   `SEM SONDA` e retorna 1, que é o comportamento certo mas não é o que queremos:

```python
    @servidor.tool(name="baixar_arquivo", description="verificação")
    def _sonda_arquivo(disciplina: str, nome: str, todos: bool = False) -> str:
        return ""
```

e acrescente `"baixar_arquivo": _sonda_arquivo` ao dicionário `sondas`.

- [ ] **Passo 4: rodar tudo, inclusive o handshake**

```bash
.venv/bin/python -m pytest tests/moodle tests/handshake -v
```

Esperado: todos PASS. O handshake descobre servidores por glob, então a ferramenta
nova é conferida no fio sem teste novo — é o H10 do spec, e ele nasce de graça.
Se algum teste de handshake reclamar de contagem de ferramentas, atualize o número
lá também.

- [ ] **Passo 5: verificar o entrypoint à mão**

```bash
.venv/bin/python -m usp_mcp.moodle.server --auto-verificar
```

Esperado: `ferramentas expostas : ['o_que_vence', 'material', 'baixar_arquivo']` e
`schema x assinatura : baixar_arquivo: OK`. Saída de status 0.

- [ ] **Passo 6: sabotar**

1. Em `_baixar_arquivo`, troque `def _baixar_arquivo(disciplina, nome, todos=False)`
   por `def _baixar_arquivo(disciplina=None, nome=None, todos=False)` → um teste de
   handshake deve ficar vermelho (parâmetro obrigatório que virou opcional no fio).
   **Se nenhum ficar vermelho, o handshake não está cobrindo obrigatoriedade para
   esta ferramenta — acrescente a asserção antes de seguir.**
2. Tire `anotar(...)` do registro → o handshake que compara descrição declarada com
   a do fio (H6–H8) deve ficar vermelho.

- [ ] **Passo 7: commit**

```bash
git add usp_mcp/moodle/server.py tests/moodle/test_server_mcp.py tests/moodle/test_server_stdio.py
git commit -m "feat(moodle): baixar_arquivo na fronteira MCP

Terceira ferramenta exposta. T42 travava o conjunto inteiro de nomes e ficou
vermelho de proposito — atualizado, nao afrouxado, porque a ferramenta passou
pelo §9 (01/09).

disciplina e nome SEM default: no SDK e a ausencia de default que torna o
parametro obrigatorio no fio, e foi assim que H6 pegou material em 31/08.
anotar() prende a descricao declarada a anotacao, senao ela nao chega ao modelo.

T42 atualizado, T100, T101; handshake cobre a nova ferramenta por descoberta."
```

---

### Tarefa 7: verificação ao vivo e registro

**Arquivos:**
- Modificar: `SPEC1.md` (§9), `docs/decisions/BACKLOG-correcoes.md`
- Criar: `docs/handoffs/2026-09-01-moodle-baixar-arquivo.md`

**Por que esta tarefa não é opcional.** A suíte não alcança o transporte HTTP real
— é linha aberta no backlog desde 31/08, e já custou o bug do timeout de 15 s
estourando numa chamada de 14,7 s com 201/201 verde. Verde na suíte não é verde no
que ela não alcança.

- [ ] **Passo 1: gate completo**

```bash
./scripts/gate.sh
```

Esperado: três checagens OK e a suíte verde. Não siga com nada vermelho.

- [ ] **Passo 2: verificação ao vivo — peça autorização ao dono antes**

Cada chamada fica no log da conta e a credencial é pessoal: **isto é decisão do
dono, não da sessão** (Regra de Ouro, §3.1). Com a autorização, rode em um cliente
MCP apontando para este diretório, ou por um script curto que construa
`ClienteMoodle` do `.env`. Exercite os quatro caminhos:

1. Um arquivo por nome exato, numa disciplina que **não** seja PSI3323 — uma
   disciplina só não prova resolução (a armadilha de T72 e T47).
2. A ambiguidade: um trecho que case com vários, e confira que a saída lista seção
   e módulo.
3. `todos=true` no mesmo trecho.
4. A **segunda** chamada do mesmo arquivo, para ver o reuso: deve responder na hora
   e dizer "já estava em disco".

Confira à mão, e anote os números: o tempo da primeira chamada (a lista de
matrículas custa ~14,7 s quando o cache está frio), o tempo do download, e o
tamanho do arquivo em disco contra o `filesize` que a listagem declarou.

- [ ] **Passo 3: registrar no §9 do `SPEC1.md`**

Acrescente uma entrada datada. Ela precisa conter, no mínimo: o que foi verificado
ao vivo e com que números; qualquer divergência entre o que este plano previu e o
que a realidade fez; e o que **continua** não verificado. Se a verificação ao vivo
não achou nada de novo, diga isso — é resultado, não ausência de resultado.

- [ ] **Passo 4: atualizar o backlog**

- Feche a linha de 01/09 sobre a normalização de `busca` em `material` (a tarefa 3
  a resolveu).
- Abra uma linha nova: **o depósito só cresce** — não há limpeza por idade nem teto
  agregado de disco. Apagar `~/.cache/usp-mcp/` à mão é seguro por construção, mas
  isso é dívida, não desenho.
- Se a verificação ao vivo revelou algo colateral, registre e **siga** — não desvie.

- [ ] **Passo 5: handoff**

Escreva `docs/handoffs/2026-09-01-moodle-baixar-arquivo.md` seguindo
`docs/handoffs/_TEMPLATE.md`. O que mais importa nele é a seção de **cuidados**: o
que a próxima sessão pode quebrar sem perceber. No mínimo:

- **Não faça `material` emitir a URL interna.** T68b e T68c são os guardas, e T68
  sozinho não pega campo novo.
- **Não relaxe a checagem de origem em `ClienteMoodle.baixar`.** O token vai no
  corpo; outro host receberia a credencial.
- **Não confie em status HTTP no download.** Erro de credencial vem como 200.
- **Não tire o `fileid` do caminho do depósito.** Dois arquivos de mesmo nome
  existem de verdade em PSI3323.

- [ ] **Passo 6: commit e PR**

```bash
./scripts/gate.sh && git add -A && git commit -m "docs(moodle): baixar_arquivo verificada ao vivo e registrada no §9"
```

Empurrar e abrir PR é decisão do dono — pergunte antes.

---

## Definição de pronto (a do spec, repetida aqui para quem lê só o plano)

1. `./scripts/gate.sh` verde, handshake incluído.
2. Verificada ao vivo em pelo menos duas disciplinas, com um caso de ambiguidade e
   um de reuso de cache.
3. Decisão e medição no §9 do `SPEC1.md`; achado colateral no backlog.
4. Nenhum segredo nem dado pessoal não higienizado no git.
