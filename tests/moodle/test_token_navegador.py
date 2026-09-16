"""O `token.sh` sem terminal: abre o navegador, guarda o passaporte, sai aguardando.

Ate 16/09/2026 o `open` do passo 3 morava dentro de `[ -t 0 ]`. Um agente de
codigo roda o script sem terminal, entao ele via a URL impressa, navegador
nenhum, e o script morrendo em "Nada foi colado". Na rodada seguinte, com o
payload por `pbpaste |`, o passaporte era outro e a conferencia do passo 5
avisava em toda rodada boa — que e como se ensina alguem a ignorar um aviso
(BACKLOG, 11/09).

O desenho de 16/09 e uma rodada em duas invocacoes: a primeira abre a pagina
certa e guarda o passaporte em `.cache/passaporte` (0600, 10 min, uma vez); a
segunda o reaproveita. Estes testes afirmam as propriedades desse desenho com um
`open` dublado no PATH que grava o que recebeu — o `open` de verdade nunca roda
na suite (ver `navegador_dublado` em test_token_decode.py):

  N1  sem terminal e sem payload: abre a URL certa, guarda o passaporte com 0600,
      sai 3, e nao toca o .env nem chama o curl;
  N2  a segunda invocacao reaproveita o passaporte, a conferencia BATE, o token e
      gravado e o arquivo morre (uso unico); ela NAO abre navegador;
  N3  passaporte vencido nao e reaproveitado: outro nasce, e o passo 5 diz por
      que nao bateu — sem bloquear, porque o passo 6 e quem decide. O limite e o
      limite: por pouco dentro ainda vale;
  N4  uso unico de verdade: o mesmo payload de novo nao confere; consumir nao
      depende de bater; e um erro ANTES do passo 5 (a URL de ida) preserva o
      passaporte para a tentativa seguinte;
  N5  o caminho antigo intacto: `pbpaste | token.sh` sem rodada anterior nao abre
      navegador e grava como sempre; e a pessoa no terminal (pty de verdade)
      continua vendo o navegador abrir, colando e gravando numa invocacao so.

Mais os cantos de "abrir sem terminal pode surpreender": USP_MCP_NAO_ABRIR=1,
sessao SSH e maquina sem `open`/`xdg-open` — nos tres o script nao abre nada e
diz o que fez. Tudo offline; o `curl` e sempre um dube.

Nenhum token real entra aqui: o payload e montado com o WSTOKEN sintetico do
test_token_decode.py, e o siteid e md5(MOODLE_URL + passaporte) calculado no
teste — a mesma formula que o passo 5 usa, para que "bate" seja bate de verdade.
"""
from __future__ import annotations

import hashlib
import os
import pty
import re
import select
import shutil
import signal
import stat
import time

import pytest

from tests.git import esta_ignorado
from tests.moodle.conftest import RAIZ
from tests.moodle.test_token_decode import (  # noqa: F401 — as fixtures entram pelo namespace
    PRIVATE,
    URL_DE_IDA,
    WSTOKEN,
    curl_dublado,
    navegador_dublado,
    payload,
    raiz_falsa,
    raiz_token,
    token_sh,
)

pytestmark = pytest.mark.politica

# O que `raiz_token` grava no .env. A URL de abertura e derivada dela.
MOODLE_URL = "https://exemplo.invalid"
RE_URL_MANUAL = re.compile(
    re.escape(MOODLE_URL)
    + r"/admin/tool/mobile/launch\.php\?service=moodle_mobile_app"
    r"&passport=(\d{10})&urlscheme=moodlemobile&confirmed=1"
)
JSON_OK = '{"userid": 4242, "sitename": "dube"}'
SAIDA_AGUARDANDO = 3
VALIDADE = 600


# ------------------------------------------------------------------- ajudantes


def aberturas(raiz) -> list[str]:
    """Cada linha e o argv de uma chamada ao `open` dublado."""
    log = raiz / "open.log"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def passaporte_da_url(texto: str) -> str:
    m = RE_URL_MANUAL.search(texto)
    assert m, f"nao achei a URL do launch.php em: {texto[:300]!r}"
    return m.group(1)


def arquivo_passaporte(raiz):
    return raiz / ".cache" / "passaporte"


def ler_passaporte(raiz) -> tuple[str, int]:
    """(passaporte, criado). Afirma a FORMA inteira do arquivo: duas linhas e
    nada mais — em particular, nem payload nem token moram ali."""
    texto = arquivo_passaporte(raiz).read_text(encoding="utf-8")
    m = re.fullmatch(r"passaporte=(\d{10})\ncriado=(\d+)\n", texto)
    assert m, f"forma inesperada do arquivo do passaporte: {texto!r}"
    return m.group(1), int(m.group(2))


def envelhecer(raiz, segundos: int) -> None:
    """Recua o `criado` do passaporte guardado, sem mexer no valor."""
    p, c = ler_passaporte(raiz)
    arquivo_passaporte(raiz).write_text(
        f"passaporte={p}\ncriado={c - segundos}\n", encoding="utf-8"
    )


def payload_para(passaporte: str) -> str:
    """A URL de volta que o Moodle emitiria para ESTE passaporte."""
    siteid = hashlib.md5((MOODLE_URL + passaporte).encode()).hexdigest()
    return f"moodlemobile://token={payload(siteid, WSTOKEN, PRIVATE)}"


def curl_registrado(raiz) -> str:
    """Como `curl_dublado`, mas deixa rastro em `raiz/curl.log` a cada chamada.

    Serve para afirmar que a invocacao de abertura NAO chega ao passo 6: um
    `curl` que nao e chamado nao deixa arquivo.
    """
    binario = raiz / "bin"
    binario.mkdir(exist_ok=True)
    falso = binario / "curl"
    falso.write_text(
        "#!/bin/sh\n"
        f"printf 'chamado\\n' >> '{raiz / 'curl.log'}'\n"
        "cat >/dev/null\n"
        f"cat <<'JSON'\n{JSON_OK}\nJSON\n",
        encoding="utf-8",
    )
    falso.chmod(0o755)
    return f"{binario}:{os.environ['PATH']}"


def abrir(raiz, **kw):
    """A invocacao de abertura: sem terminal e com stdin vazio."""
    kw.setdefault("path", curl_registrado(raiz))
    return token_sh(raiz, "", **kw)


def entregar(raiz, colado: str, *args: str):
    """A invocacao de entrega: `pbpaste | ./scripts/token.sh [args]`."""
    return token_sh(raiz, colado, path=curl_dublado(raiz, JSON_OK), args=args)


# ------------------------------------------------------------ N1: a abertura


def test_n1_sem_terminal_e_sem_payload_abre_a_pagina_certa_e_sai_aguardando(raiz_token):
    """N1 — o que um agente de codigo ve na primeira invocacao.

    O que se afirma e o argv que o `open` recebeu (regra 11 do CLAUDE.md: o
    parametro enviado, nao a saida), a forma e a permissao do passaporte
    guardado, o codigo de saida proprio, e as duas coisas que NAO podem ter
    acontecido: o .env mudar e o curl ser chamado.
    """
    antes = (raiz_token / ".env").read_text(encoding="utf-8")
    r = abrir(raiz_token)
    saida = r.stdout + r.stderr

    assert r.returncode == SAIDA_AGUARDANDO, saida
    ab = aberturas(raiz_token)
    assert len(ab) == 1, f"esperava UMA chamada ao open, houve {len(ab)}: {ab}"
    p_url = passaporte_da_url(ab[0])
    assert ab[0].strip() == (
        f"{MOODLE_URL}/admin/tool/mobile/launch.php?service=moodle_mobile_app"
        f"&passport={p_url}&urlscheme=moodlemobile&confirmed=1"
    ), "o open recebeu algo alem da URL manual"

    p_arq, criado = ler_passaporte(raiz_token)
    assert p_arq == p_url, "o passaporte guardado nao e o da pagina aberta"
    assert abs(time.time() - criado) < 60
    modo = stat.S_IMODE(arquivo_passaporte(raiz_token).stat().st_mode)
    assert modo == 0o600, f"passaporte com permissao {oct(modo)}, esperava 0600"

    assert "abri a URL no navegador padrao" in saida
    assert "pbpaste | ./scripts/token.sh" in saida
    assert "Saida 3 = aguardando" in saida
    assert "6/7" not in saida, "chegou ao passo 6 sem payload"
    assert not (raiz_token / "curl.log").exists(), "chamou o curl sem ter token"
    assert (raiz_token / ".env").read_text(encoding="utf-8") == antes


def test_n1b_abrir_de_novo_dentro_da_validade_abre_a_mesma_pagina(raiz_token):
    """N1b — a abertura e idempotente: um agente que repete o comando nao
    invalida a aba que a pessoa ja tem aberta, e a validade NAO desliza."""
    abrir(raiz_token)
    p1, c1 = ler_passaporte(raiz_token)
    abrir(raiz_token)
    p2, c2 = ler_passaporte(raiz_token)
    assert (p1, c1) == (p2, c2), "reabrir cunhou outro passaporte ou renovou a validade"
    ab = aberturas(raiz_token)
    assert len(ab) == 2
    assert passaporte_da_url(ab[0]) == passaporte_da_url(ab[1]) == p1


# --------------------------------------------------------- N2: a reutilizacao


def test_n2_a_segunda_invocacao_reaproveita_o_passaporte_e_a_conferencia_bate(raiz_token):
    """N2 — o fluxo inteiro em duas invocacoes, e a conferencia com valor.

    "Bate" aqui e calculado, nao presumido: o siteid do payload e a md5 do
    passaporte que a PRIMEIRA invocacao guardou. Se a segunda cunhasse outro
    (o comportamento antigo), esta assercao falha com "nao confere".
    """
    abrir(raiz_token)
    p, _ = ler_passaporte(raiz_token)

    r = entregar(raiz_token, payload_para(p))
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida
    assert "reaproveitando o da rodada de ha" in saida
    assert "confere: o payload responde a ESTA rodada" in saida
    assert "nao confere" not in saida
    assert f"MOODLE_TOKEN={WSTOKEN}\n" in (raiz_token / ".env").read_text(encoding="utf-8")
    assert not arquivo_passaporte(raiz_token).exists(), "uso unico: devia ter sido consumido"
    assert len(aberturas(raiz_token)) == 1, "a invocacao de entrega abriu navegador"
    assert WSTOKEN not in saida, "ecoou o token (Invariante 3)"
    assert PRIVATE not in saida, "ecoou o privatetoken (§2.2)"


# ------------------------------------------------------------- N3: a validade


def test_n3_passaporte_vencido_nao_e_reaproveitado_e_o_passo_5_diz_por_que(raiz_token):
    """N3 — vencido e descartado, outro nasce, e a pessoa fica sabendo.

    Nao bloqueia: o desenho de 10/09 (§3.1) diz que a conferencia avisa porque
    a formula e recordada, e este teste nao muda isso. O que muda e a mensagem:
    ela nomeia a idade e a validade, em vez de deixar a pessoa adivinhar.
    """
    abrir(raiz_token)
    p_velho, _ = ler_passaporte(raiz_token)
    envelhecer(raiz_token, VALIDADE + 1)

    r = entregar(raiz_token, payload_para(p_velho))
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida  # o passo 6 decide, e o dube autenticou
    assert "reaproveitando" not in saida
    assert f"acima dos {VALIDADE}s de validade" in saida
    assert "nao confere" in saida
    assert "foi descartado no passo 2" in saida
    assert not arquivo_passaporte(raiz_token).exists()
    assert f"MOODLE_TOKEN={WSTOKEN}\n" in (raiz_token / ".env").read_text(encoding="utf-8")


def test_n3b_por_pouco_dentro_da_validade_ainda_vale(raiz_token):
    """N3b — o limite e o limite. Sem isto, um `-ge` no lugar de `-gt` passaria
    no N3 e recusaria um passaporte de 600 s por engano."""
    abrir(raiz_token)
    p, _ = ler_passaporte(raiz_token)
    envelhecer(raiz_token, VALIDADE - 5)
    r = entregar(raiz_token, payload_para(p))
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida
    assert "reaproveitando" in saida
    assert "confere: o payload responde a ESTA rodada" in saida


def test_n3c_abrir_de_novo_depois_de_vencido_cunha_outro(raiz_token):
    """N3c — a abertura tambem respeita a validade: um passaporte de ontem nao
    e o que vai para a pagina de hoje."""
    abrir(raiz_token)
    p1, _ = ler_passaporte(raiz_token)
    envelhecer(raiz_token, 3600)
    r = abrir(raiz_token)
    p2, c2 = ler_passaporte(raiz_token)
    assert p1 != p2
    assert abs(time.time() - c2) < 60
    assert "descartado" in r.stdout + r.stderr
    ab = aberturas(raiz_token)
    assert [passaporte_da_url(a) for a in ab] == [p1, p2]


def test_n3d_arquivo_ilegivel_e_lixo_e_nao_erro(raiz_token):
    """N3d — material de sessao nao merece conserto: forma estranha sai do
    caminho e a rodada segue com passaporte novo."""
    arquivo_passaporte(raiz_token).parent.mkdir(parents=True)
    arquivo_passaporte(raiz_token).write_text("passaporte=abc\ncriado=ontem\n", encoding="utf-8")
    r = abrir(raiz_token)
    assert r.returncode == SAIDA_AGUARDANDO, r.stdout + r.stderr
    p, _ = ler_passaporte(raiz_token)
    assert passaporte_da_url(aberturas(raiz_token)[0]) == p


# ------------------------------------------------------------ N4: o uso unico


def test_n4_o_mesmo_payload_de_novo_nao_confere(raiz_token):
    """N4 — uso unico: depois de consumido, o passaporte nao volta."""
    abrir(raiz_token)
    p, _ = ler_passaporte(raiz_token)
    assert entregar(raiz_token, payload_para(p)).returncode == 0

    # --sobrescrever porque o .env agora TEM token valido e nao ha terminal para
    # perguntar: e a protecao do passo 1 funcionando, nao o assunto deste teste.
    r = entregar(raiz_token, payload_para(p), "--sobrescrever")
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida  # a formula segue como aviso; o passo 6 decide
    assert "reaproveitando" not in saida
    assert "nao confere" in saida
    assert not arquivo_passaporte(raiz_token).exists()


def test_n4b_consumir_nao_depende_de_bater(raiz_token):
    """N4b — um payload de OUTRA rodada tambem gasta o passaporte: ele foi
    confrontado, e um passaporte confrontado nao serve para uma segunda
    tentativa de acertar por comparacao."""
    abrir(raiz_token)
    r = entregar(raiz_token, payload_para("1111111111"))
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida
    assert "nao confere" in saida
    assert not arquivo_passaporte(raiz_token).exists()


def test_n4c_erro_antes_do_passo_5_preserva_o_passaporte(raiz_token):
    """N4c — o erro nº 1 medido (colar a URL de ida) nao pode custar o
    passaporte: a pessoa volta a pagina, copia certo, e a conferencia ainda
    fecha. Se o arquivo morresse na leitura, a tentativa seguinte daria
    "nao confere" por culpa do script, nao dela."""
    abrir(raiz_token)
    p, c = ler_passaporte(raiz_token)

    r = entregar(raiz_token, URL_DE_IDA)
    assert r.returncode != 0
    assert "URL de IDA" in r.stdout + r.stderr
    assert ler_passaporte(raiz_token) == (p, c), "o erro de colagem consumiu o passaporte"

    r = entregar(raiz_token, payload_para(p))
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida
    assert "confere: o payload responde a ESTA rodada" in saida
    assert not arquivo_passaporte(raiz_token).exists()


# --------------------------------------------------- N5: o caminho antigo intacto


def test_n5_pbpaste_por_cano_sem_rodada_anterior_nao_abre_navegador_e_grava(raiz_token):
    """N5 — `pbpaste | ./scripts/token.sh` do jeito antigo, sem abertura antes.

    Tres coisas nao podem mudar: nao abre navegador (quem chegou com o payload
    nao quer uma aba nova), grava o token, e a conferencia avisa como sempre
    avisou — o payload nao e desta rodada, e a mensagem diz que esta tudo bem.
    """
    r = entregar(raiz_token, payload_para("1234567890"))
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida
    assert aberturas(raiz_token) == [], "o caminho por cano abriu navegador"
    assert "li do stdin." in saida
    assert "aguardando" not in saida
    assert "nao confere" in saida
    assert "esta tudo certo" in saida
    assert f"MOODLE_TOKEN={WSTOKEN}\n" in (raiz_token / ".env").read_text(encoding="utf-8")
    assert not arquivo_passaporte(raiz_token).exists()


def _rodar_com_tty(raiz, ambiente: dict[str, str], responder, timeout: float = 90.0):
    """Roda o `token.sh` atras de um pseudo-terminal de verdade.

    `[ -t 0 ]` e verdadeiro e `/dev/tty` e o pty: o script segue o caminho da
    pessoa. `responder(saida_ate_agora)` devolve o que "digitar" quando o
    prompt do passo 3 aparecer — so entao, porque e o `read -s` que desliga o
    eco, e digitar antes ecoaria o payload na tela que este teste afirma limpa.
    Devolve (saida, codigo).
    """
    pid, fd = pty.fork()
    if pid == 0:  # filho: vira o script
        try:
            os.chdir(raiz)
            os.execve(shutil.which("bash"), ["bash", "scripts/token.sh"], ambiente)
        finally:
            os._exit(127)

    saida = b""
    respondido = False
    fim = time.monotonic() + timeout
    try:
        while time.monotonic() < fim:
            pronto, _, _ = select.select([fd], [], [], 0.2)
            if not pronto:
                continue
            try:
                bloco = os.read(fd, 65536)
            except OSError:  # EIO: o outro lado fechou — o script terminou
                break
            if not bloco:
                break
            saida += bloco
            if not respondido and b"Cole e aperte Enter" in saida:
                texto = saida.decode("utf-8", "replace").replace("\r", "")
                os.write(fd, responder(texto).encode() + b"\n")
                respondido = True
        else:
            os.kill(pid, signal.SIGKILL)
    finally:
        os.close(fd)
    _, status = os.waitpid(pid, 0)
    return saida.decode("utf-8", "replace").replace("\r", ""), os.waitstatus_to_exitcode(status)


def test_n5b_a_pessoa_no_terminal_continua_vendo_tudo_numa_invocacao_so(raiz_token):
    """N5b — o caminho de quem roda no terminal, com pty de verdade.

    O desenho de 10/09 (§7) media isto a mao, com pty, e dizia que a suite nao
    alcancava. Com o `open` dublado ela alcanca: navegador aberto UMA vez na URL
    com o passaporte desta invocacao, payload colado sem eco, conferencia
    batendo, token gravado, passaporte consumido. Tudo numa invocacao, como
    sempre foi — e sem "li do stdin" nem "aguardando", que sao dos outros dois
    caminhos.
    """
    ambiente = {k: v for k, v in os.environ.items() if k not in ("SSH_CONNECTION", "SSH_TTY")}
    ambiente["PATH"] = f"{navegador_dublado(raiz_token)}:{curl_dublado(raiz_token, JSON_OK)}"
    ambiente["TERM"] = "dumb"

    digitado: dict[str, str] = {}

    def responder(texto: str) -> str:
        digitado["valor"] = payload_para(passaporte_da_url(texto))
        return digitado["valor"]

    saida, codigo = _rodar_com_tty(raiz_token, ambiente, responder)

    assert codigo == 0, saida
    ab = aberturas(raiz_token)
    assert len(ab) == 1, f"esperava UMA chamada ao open, houve {len(ab)}: {ab}"
    assert passaporte_da_url(ab[0]) == passaporte_da_url(saida)
    assert "confere: o payload responde a ESTA rodada" in saida
    assert "li do stdin" not in saida
    assert "aguardando" not in saida
    assert f"MOODLE_TOKEN={WSTOKEN}\n" in (raiz_token / ".env").read_text(encoding="utf-8")
    assert not arquivo_passaporte(raiz_token).exists()
    assert WSTOKEN not in saida, "ecoou o token (Invariante 3)"
    assert PRIVATE not in saida, "ecoou o privatetoken (§2.2)"
    # O `read -s` e o que impede a credencial de ficar no scrollback. So o
    # prefixo do esquema pode aparecer (a conferencia o cita); o base64 depois
    # do `token=`, nunca.
    base64_digitado = digitado["valor"].split("token=", 1)[1]
    assert base64_digitado[:16] not in saida, "o payload colado ecoou no terminal"


# ------------------------------------- abrir sem terminal, sem surpreender ninguem


def test_usp_mcp_nao_abrir_desliga_o_navegador_e_diz_isso(raiz_token):
    """A mesma chave que `_capturar_redirect.sh` ja honra. O resto da abertura
    (passaporte guardado, saida 3) continua, porque a pessoa vai abrir a URL
    a mao e voltar com o payload."""
    r = abrir(raiz_token, env={"USP_MCP_NAO_ABRIR": "1"})
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert aberturas(raiz_token) == []
    assert "USP_MCP_NAO_ABRIR=1: nao abri navegador nenhum" in saida
    assert arquivo_passaporte(raiz_token).exists()


def test_sessao_ssh_nao_abre_navegador_e_diz_por_que(raiz_token):
    """Por SSH, `open` abriria na maquina remota. O script percebe e manda
    abrir na maquina da pessoa, em vez de abrir uma aba que ninguem ve."""
    r = abrir(raiz_token, env={"SSH_CONNECTION": "10.0.0.2 51234 10.0.0.1 22"})
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert aberturas(raiz_token) == []
    assert "sessao SSH" in saida
    assert "SUA maquina" in saida
    assert arquivo_passaporte(raiz_token).exists()


def test_maquina_sem_open_nem_xdg_open_diz_e_segue(raiz_token, tmp_path):
    """Servidor sem interface: PATH minimo com so o que o script usa ate o passo
    3, e sem `open` nem `xdg-open`. Ele diz que nao ha como abrir, e o resto da
    abertura segue — a URL esta impressa para ser aberta em outro lugar."""
    minimo = tmp_path / "bin_minimo"
    minimo.mkdir()
    for nome in ("bash", "dirname", "grep", "sed", "head", "date", "mkdir", "rm",
                 "sleep", "cat", "wc", "tr", "cut", "cp"):
        real = shutil.which(nome)
        assert real, f"sem `{nome}` nesta maquina; o teste precisa dele para montar o PATH minimo"
        (minimo / nome).symlink_to(real)

    r = token_sh(
        raiz_token, "", path=str(minimo), navegador=False,
        env={"DISPLAY": "", "WAYLAND_DISPLAY": ""},
    )
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert "nao ha como abrir navegador desta maquina" in saida
    assert "Abra a URL acima" in saida
    assert not (raiz_token / "open.log").exists()
    assert arquivo_passaporte(raiz_token).exists()


def test_o_passaporte_guardado_e_gitignorado():
    """`.cache/` ja e ignorado por causa do userid; este teste prende que o
    passaporte mora la dentro e nao num caminho novo que alguem esqueca.
    A pergunta ao git mora em `tests.git.esta_ignorado`, e so la (G5)."""
    assert esta_ignorado(RAIZ / ".cache" / "passaporte", RAIZ), (
        ".cache/passaporte deixou de ser gitignorado"
    )
