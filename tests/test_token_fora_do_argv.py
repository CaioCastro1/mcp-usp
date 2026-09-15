"""T1-T5: o `MOODLE_TOKEN` não passa pela linha de comando do `curl`.

Argumento de processo não é privado. Enquanto o `curl` roda, qualquer processo
da máquina lê o argv dele por `ps aux` — e o `scripts/ws.sh` mandava
`--data-urlencode "wstoken=$MOODLE_TOKEN"` ali. O token do Moodle é credencial
pessoal do dono (Invariante 4), cada chamada feita com ele fica no log da conta
dele na USP, e o Invariante 3 diz que esse valor não se lê, não se imprime e não
se ecoa. Argv é eco.

A cura já existia no repositório: o passo 6 do `scripts/token.sh` resolveu o
mesmo problema com `curl -K -`, que lê a configuração pelo **stdin**. Estes
testes existem para que o repositório tenha uma solução e não duas, e para que
ela não se desfaça sozinha num refactor.

**Por que cinco testes e não um.** T1 é a varredura: nenhum script de
`scripts/` põe `wstoken=` em argv. Ela varre o diretório em vez de consultar
uma lista escrita à mão, então um script novo com o mesmo defeito reprova no
dia em que nascer. T2 é o anti-vácuo dela: uma varredura que não acha arquivo
nenhum, ou um repositório onde `wstoken` deixou de existir, deixaria T1 verde
sem ter verificado nada. T3 sabota a varredura de propósito, provando que ela
acha o defeito quando ele existe e que não acusa a forma correta — sem isso um
regex quebrado passaria exatamente no caso para o qual foi escrito.

T4 e T5 não olham para o texto do script: eles **rodam** o `ws.sh`. É a regra 11
do `CLAUDE.md` — antes de confiar num parâmetro, asserte sobre o parâmetro
enviado, não sobre a saída. T4 põe um `curl` dublê no PATH e afirma sobre o argv
que ele recebeu e sobre o stdin que ele leu. T5 vai além e usa o `curl` de
verdade contra um servidor HTTP em `127.0.0.1`: quem desfaz as aspas do arquivo
de configuração é o parser real do `curl`, e o que se confere é o corpo POST que
chegou do outro lado. Sem T5, o escape ficaria conferido contra uma
reimplementação minha das regras do `curl`, que concordaria comigo mesmo estando
errada.

Tudo offline. T5 fala com `127.0.0.1` e nunca com a USP.

Nenhum destes testes conhece o token de verdade: o valor usado é sintético, com
a forma certa (32 hex) e obviamente falso, como já faz o `tests/test_ws.py`.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"

# Forma válida e valor obviamente sintético (Invariante 3 vale também para o que
# se escreve em teste).
TOKEN_FALSO = "a1b2c3d4" * 4

# ----------------------------------------------------------------- a varredura

# O `curl` aceita a continuação de linha do shell, então o defeito pode estar
# partido em duas linhas físicas. Juntar antes de olhar é o que impede que
# quebrar a linha vire uma forma de escapar da varredura.
CONTINUACAO = re.compile(r"\\\n[ \t]*")

# As opções pelas quais um valor vai para o argv do `curl`. Ordem do mais longo
# para o mais curto só para a mensagem de erro ficar legível; o casamento
# retrocede de qualquer jeito.
FLAGS_DE_DADO = (
    "data-urlencode", "data-binary", "data-raw", "data-ascii", "data",
    "form-string", "form", "url-query", "header",
    "d", "F", "G", "H",
)

# `--data-urlencode "wstoken=..."`, `-d wstoken=...` e também a forma Python
# `["--data-urlencode", "wstoken=..."]` — daí vírgula e colchete entre os dois.
# O separador NÃO aceita letra, e é isso que separa o defeito da cura: a linha
# boa escreve `data-urlencode = "wstoken=%s"` para dentro de um arquivo de
# configuração, sem o `-` na frente, e não casa aqui.
TOKEN_EM_ARGV = re.compile(
    r"--?(?:" + "|".join(FLAGS_DE_DADO) + r")[\s='\"\[\],]*wstoken="
)

# A outra porta para o argv: o token pendurado na query string da URL.
TOKEN_EM_URL = re.compile(r"[?&]wstoken=")


def _arquivos_de_scripts() -> list[pathlib.Path]:
    """Todo arquivo de `scripts/`, sem lista escrita à mão.

    Varredura do diretório e não enumeração: a única forma de um script novo
    com este defeito ser pego no dia em que nascer, em vez de no dia em que
    alguém lembrar de acrescentá-lo a uma lista.
    """
    return sorted(p for p in SCRIPTS.rglob("*") if p.is_file())


def _ofensas(texto: str) -> list[tuple[int, str]]:
    """(linha, trecho) de cada lugar onde o token iria para o argv.

    Comentário é isento: ele não roda, e proibir a palavra no comentário
    impediria o script de explicar por que o token não vai por ali.
    """
    achados = []
    for numero, linha in enumerate(CONTINUACAO.sub(" ", texto).splitlines(), 1):
        if linha.lstrip().startswith("#"):
            continue
        for padrao in (TOKEN_EM_ARGV, TOKEN_EM_URL):
            m = padrao.search(linha)
            if m:
                achados.append((numero, linha.strip()[:120]))
                break
    return achados


@pytest.mark.politica
def test_t1_nenhum_script_passa_o_wstoken_pela_linha_de_comando():
    """T1 — o teste que teria pego a linha 51 do `ws.sh`.

    A numeração da linha é a do texto com as continuações já juntadas, então ela
    aponta o começo do comando e não necessariamente o `wstoken`.
    """
    erradas = [
        (arquivo, numero, trecho)
        for arquivo in _arquivos_de_scripts()
        for numero, trecho in _ofensas(arquivo.read_text(encoding="utf-8", errors="replace"))
    ]
    assert not erradas, (
        "script passando `wstoken=` como argumento de linha de comando:\n  "
        + "\n  ".join(
            f"{a.relative_to(RAIZ)}, comando que começa na linha {n}: {t}"
            for a, n, t in erradas
        )
        + "\n\nArgv é legível por `ps aux` enquanto o processo roda, e este valor é"
        "\ncredencial pessoal (Invariantes 3 e 4). A cura já existe no repositório:"
        "\nescreva a configuração do curl no stdin dele, como o passo 6 do"
        "\n`scripts/token.sh` e o `scripts/ws.sh` fazem:"
        "\n\n    printf 'data-urlencode = \"wstoken=%s\"\\n' \"$tok\" | curl -sS -K - \"$url\""
        "\n\nSe o valor do parâmetro puder vir de fora, escape `\\`, `\"`, tab, CR, VT"
        "\ne quebra de linha antes de escrever — o arquivo de configuração do curl"
        "\ndesfaz essas sequências (ver `escapar_para_config` no `ws.sh`)."
    )


@pytest.mark.politica
def test_t2_a_varredura_tem_o_que_varrer():
    """T2 — anti-vácuo: T1 fica verde à toa se não houver o que olhar.

    Duas formas de falso-verde, e as duas já aconteceram em projetos com testes
    de varredura: o diretório mudar de lugar (a varredura passa a olhar o nada)
    e o nome do parâmetro mudar (a regra passa a falar de algo que não existe).
    """
    arquivos = _arquivos_de_scripts()
    assert len(arquivos) >= 10, (
        f"`scripts/` tem {len(arquivos)} arquivo(s). Eram 13 em 15/09/2026. Se o "
        "diretório mudou de lugar, mova a constante SCRIPTS deste teste junto: "
        "sem arquivo nenhum, T1 passa sem ter olhado para nada."
    )
    com_token = [
        a.relative_to(RAIZ)
        for a in arquivos
        if "wstoken" in a.read_text(encoding="utf-8", errors="replace")
    ]
    assert com_token, (
        "nenhum script menciona `wstoken`. Ou o parâmetro do Moodle mudou de "
        "nome — e aí T1 vigia uma palavra que não existe mais e precisa ser "
        "atualizado —, ou o `ws.sh` parou de mandar o token, o que é bug."
    )


@pytest.mark.politica
def test_t3_a_varredura_pega_o_defeito_e_nao_acusa_a_cura(tmp_path):
    """T3 — sabotagem controlada da própria varredura.

    Sem isto, um regex quebrado deixaria T1 verde sem achar nada, passando
    justamente no caso que ele foi escrito para pegar. O lado de baixo é tão
    importante quanto: uma varredura que acusasse a forma correta obrigaria a
    próxima sessão a desligá-la, e aí não sobra teste nenhum.
    """
    defeituoso = tmp_path / "ruim.sh"
    defeituoso.write_text(
        'curl -sS "$URL" --data-urlencode "wstoken=$MOODLE_TOKEN"\n'
        'curl -sS "$URL" \\\n  --data-urlencode "wstoken=$MOODLE_TOKEN"\n'
        'curl -sS -d wstoken=$MOODLE_TOKEN "$URL"\n'
        'curl -sS "$URL?wstoken=$MOODLE_TOKEN"\n'
        'subprocess.run(["curl", "--data-urlencode", "wstoken=" + tok])\n',
        encoding="utf-8",
    )
    linhas_ruins = {n for n, _ in _ofensas(defeituoso.read_text(encoding="utf-8"))}
    assert linhas_ruins == {1, 2, 3, 4, 5}, (
        "a varredura não pegou todas as formas de pôr o token em argv. "
        f"Pegou as linhas {sorted(linhas_ruins)}; esperava 1 (argumento direto), "
        "2 (partido por continuação de linha), 3 (`-d` sem aspas), 4 (query "
        "string) e 5 (lista de argumentos em Python). Conserte TOKEN_EM_ARGV / "
        "TOKEN_EM_URL antes de confiar no T1."
    )

    correto = tmp_path / "bom.sh"
    correto.write_text(
        '# o token vai por -K, nunca por --data-urlencode "wstoken=..."\n'
        "printf 'data-urlencode = \"wstoken=%s\"\\n' \"$tok\" | curl -sS -K - \"$URL\" \\\n"
        '  --data-urlencode "wsfunction=$fn"\n'
        'config "wstoken=$MOODLE_TOKEN"\n',
        encoding="utf-8",
    )
    assert _ofensas(correto.read_text(encoding="utf-8")) == [], (
        "a varredura acusou a forma CORRETA: token pelo stdin do `curl -K -`, e "
        "a palavra `wstoken` num comentário que explica a regra. Uma regra que "
        "reprova a cura acaba desligada, e aí não sobra vigilância nenhuma."
    )


# --------------------------------------------------- exercitar o ws.sh de fato


def _repo_falso(tmp_path: pathlib.Path, url: str) -> pathlib.Path:
    """Um checkout mínimo onde o `ws.sh` roda: `.env`, `usp_mcp/` e o script.

    Cópia e não symlink, pela mesma razão do `tests/test_ws.py`: `achar_env`
    resolve o caminho real, e um `usp_mcp/` apontando para o repositório de
    verdade acharia o `.env` de verdade — o teste ficaria verde exercitando o
    ambiente do dono, com o token do dono.
    """
    repo = tmp_path / "repo"
    (repo / "usp_mcp").mkdir(parents=True)
    (repo / "scripts").mkdir()
    for nome in ("__init__.py", "env.py"):
        shutil.copy2(RAIZ / "usp_mcp" / nome, repo / "usp_mcp" / nome)
    shutil.copy2(RAIZ / "scripts" / "ws.sh", repo / "scripts" / "ws.sh")
    (repo / ".env").write_text(
        f"MOODLE_TOKEN={TOKEN_FALSO}\nMOODLE_URL={url}\n", encoding="utf-8"
    )
    return repo


def _ambiente(extra_path: pathlib.Path) -> dict[str, str]:
    """Ambiente do filho com `extra_path` na frente e sem token herdado.

    Tirar `MOODLE_TOKEN`/`MOODLE_URL` não é zelo: o `usp_mcp.env` já pode ter
    posto o `.env` de verdade em `os.environ`, e o filho herdaria um token que
    este teste não escolheu — as asserções passariam sem o `ws.sh` ter lido o
    `.env` sintético.
    """
    amb = {k: v for k, v in os.environ.items() if k not in ("MOODLE_TOKEN", "MOODLE_URL")}
    amb["PATH"] = f"{extra_path}{os.pathsep}{amb.get('PATH', '')}"
    return amb


def _rodar_ws(repo: pathlib.Path, bin_dir: pathlib.Path, *args: str):
    return subprocess.run(
        ["bash", "scripts/ws.sh", *args],
        cwd=repo,
        env=_ambiente(bin_dir),
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.contrato
def test_t4_o_ws_nao_poe_o_token_no_argv_do_curl_e_ainda_assim_o_manda(tmp_path):
    """T4 — o `ps aux` do teste: o argv que o `curl` recebeu de verdade.

    O dublê grava o próprio argv e o próprio stdin. As duas metades importam: a
    primeira é a regra (o token não está em argv) e a segunda é o anti-vácuo
    dela — um `ws.sh` que simplesmente parasse de mandar o token passaria na
    primeira com louvor.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_txt = tmp_path / "argv.txt"
    stdin_txt = tmp_path / "stdin.txt"
    dublê = bin_dir / "curl"
    dublê.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\0' \"$@\" > '{argv_txt}'\n"
        f"cat > '{stdin_txt}'\n"
        "printf '{}'\n",
        encoding="utf-8",
    )
    dublê.chmod(0o755)

    repo = _repo_falso(tmp_path, "http://127.0.0.1:1/webservice")
    r = _rodar_ws(repo, bin_dir, "core_webservice_get_site_info")
    assert r.returncode == 0, (
        f"o ws.sh não chegou a chamar o curl (código {r.returncode}).\n"
        f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    )

    argv = [a for a in argv_txt.read_bytes().decode("utf-8").split("\0") if a]
    entregue = stdin_txt.read_text(encoding="utf-8")

    vazados = [a for a in argv if TOKEN_FALSO in a or "wstoken" in a]
    assert not vazados, (
        f"o token foi para o argv do curl: {vazados!r}\n"
        "Isso é o que `ps aux` mostra para qualquer processo da máquina enquanto "
        "a chamada acontece. Escreva a configuração no stdin do `curl -K -`, "
        "como o passo 6 do `scripts/token.sh` faz."
    )
    assert "-K" in argv, (
        f"o curl foi chamado sem `-K`: {argv!r}. Este projeto tem UMA solução "
        "para tirar segredo do argv, e é a do `token.sh`. Se você inventou "
        "outra, unifique as duas antes de seguir."
    )
    assert TOKEN_FALSO in entregue, (
        "o token não foi para o argv, mas também não foi para o stdin — ou "
        "seja, não foi mandado. O que o curl leu pelo -K foi:\n"
        + entregue.replace(TOKEN_FALSO, "<token>")
    )


@pytest.mark.contrato
@pytest.mark.skipif(shutil.which("curl") is None, reason="sem `curl` no PATH")
def test_t5_o_corpo_que_chega_do_outro_lado_e_exatamente_o_pedido(tmp_path):
    """T5 — curl de verdade, servidor de verdade, corpo POST de verdade.

    Quem desfaz as aspas do arquivo de configuração é o `curl`, não este teste.
    Dentro de aspas duplas ele come a barra invertida e converte `\\t`, `\\n`,
    `\\r` e `\\v`; um parâmetro do usuário com aspa ou barra montaria uma linha
    diferente da pedida e a chamada sairia calada e errada, que é o defeito que
    o Invariante 6 persegue. Aqui os parâmetros hostis vão pela interface
    pública do script e o que se confere é o que o servidor recebeu.

    O servidor é `127.0.0.1` com porta sorteada pelo sistema: offline, e nunca a
    USP.
    """
    recebido: dict[str, str] = {}

    class Coletor(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 — nome imposto pela stdlib
            n = int(self.headers.get("Content-Length") or 0)
            recebido["corpo"] = self.rfile.read(n).decode("utf-8")
            corpo = json.dumps({"ok": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, *a):  # silêncio: o log do servidor não é o teste
            pass

    servidor = HTTPServer(("127.0.0.1", 0), Coletor)
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        repo = _repo_falso(tmp_path, f"http://127.0.0.1:{servidor.server_port}")

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        argv_txt = tmp_path / "argv.txt"
        # Embrulho e não dublê: grava o argv e passa a bola para o curl de
        # verdade. `exec` preserva o stdin, que é justamente por onde o token
        # anda. O caminho absoluto evita o embrulho chamar a si mesmo.
        embrulho = bin_dir / "curl"
        embrulho.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\0' \"$@\" > '{argv_txt}'\n"
            f"exec '{shutil.which('curl')}' \"$@\"\n",
            encoding="utf-8",
        )
        embrulho.chmod(0o755)

        # Cada um exercita uma regra do arquivo de configuração do curl: aspa
        # dupla, barra invertida seguida de letra que vira controle (`\t`, `\n`),
        # quebra de linha de verdade, tab de verdade, e os sinais que o
        # percent-encoding tem de carregar.
        hostis = [
            'nota=ele disse "oi" e saiu',
            "caminho=C:\\temp\\novo\\relatorio",
            "multi=linha um\nlinha dois",
            "aba=antes\tdepois",
            "sinais=a=b&c#d+e%20f",
        ]
        r = _rodar_ws(repo, bin_dir, "core_webservice_get_site_info", *hostis)
    finally:
        servidor.shutdown()
        servidor.server_close()

    assert r.returncode == 0, (
        f"o curl de verdade recusou a configuração (código {r.returncode}). "
        "Provavelmente a linha escrita para o -K está malformada.\n"
        f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    )
    assert "corpo" in recebido, (
        "o servidor local não recebeu POST nenhum. Sem corpo não há o que "
        f"conferir.\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    )

    chegou = urllib.parse.parse_qsl(recebido["corpo"], keep_blank_values=True)
    esperado = [
        ("wstoken", TOKEN_FALSO),
        ("wsfunction", "core_webservice_get_site_info"),
        ("moodlewsrestformat", "json"),
    ] + [tuple(p.split("=", 1)) for p in hostis]
    assert chegou == esperado, (
        "o que chegou ao servidor não é o que foi pedido na linha de comando.\n"
        f"  chegou:   {[(k, '<token>' if k == 'wstoken' else v) for k, v in chegou]}\n"
        f"  esperado: {[(k, '<token>' if k == 'wstoken' else v) for k, v in esperado]}\n"
        "Se a diferença for uma barra invertida ou uma aspa que sumiu, é o "
        "escape de `escapar_para_config` no `ws.sh`: dentro de aspas duplas o "
        "curl desfaz `\\\\`, `\\\"`, `\\t`, `\\n`, `\\r` e `\\v`, e come qualquer "
        "outra barra invertida junto com o caractere seguinte."
    )

    argv = [a for a in argv_txt.read_bytes().decode("utf-8").split("\0") if a]
    vazados = [a for a in argv if TOKEN_FALSO in a or "wstoken" in a]
    assert not vazados, (
        f"o token chegou certo, mas passou pelo argv no caminho: {vazados!r}. "
        "Chegar certo e vazar são coisas independentes — as duas metades deste "
        "teste precisam valer."
    )
