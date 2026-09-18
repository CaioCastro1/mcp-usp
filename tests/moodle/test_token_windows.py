"""O `token.sh` em Windows: que leitor de clipboard, que lancador e que Python ele
escolhe quando o chao e o do Git Bash ou do WSL.

Sintoma, vivido pelo dono em 17/09/2026: instalou em Windows e a vigia do
clipboard nao funcionou. Motivo, medido no proprio script: o leitor era escolhido
entre `pbpaste`, `wl-paste` e `xclip`, e Windows nao tem nenhum dos tres; o
lancador de navegador era `open` ou `xdg-open`, idem; e o Python preferido era
`.venv/bin/python`, que em Windows nao existe (o venv la tem `Scripts\\`).

O desenho de 18/09 (docs/superpowers/specs/2026-09-18-windows-design.md) e a
opcao (a): manter o bash e acrescentar, a cada uma dessas tres escolhas, o
candidato que Windows tem — sem mudar a ordem do que ja existia, e sempre como
ULTIMO recurso. Estes testes afirmam a ESCOLHA e o ARGUMENTO ENVIADO (regra 11
do CLAUDE.md), com dubles no PATH:

  WIN1  sem pbpaste/wl-paste/xclip, o leitor e o PowerShell, chamado com
        `-NoProfile -Command Get-Clipboard`; a vigia le por ele e grava;
  WIN2  os quatro nomes que o PowerShell pode ter no PATH (`.exe` para o WSL,
        sem extensao para o Git Bash; `pwsh` para o PowerShell 7) sao aceitos;
  WIN3  onde ha `pbpaste`, ele continua sendo o leitor: o PowerShell nao toma
        o lugar de nada;
  WIN4  o CRLF que o Get-Clipboard poe no fim nao atrapalha a forma nem a
        conferencia;
  WIN5  as mensagens do fluxo em duas invocacoes ensinam o comando do Windows,
        e a maquina sem leitor nenhum nomeia o PowerShell entre os que faltam;
  WIN6  o lancador: `rundll32` recebe `url.dll,FileProtocolHandler <url>`;
        `wslview` recebe a URL e vence o `open` (no Ubuntu do WSL, `open` e o
        `openvt` do console); e `open` continua vencendo o `rundll32`;
  WIN7  o Python: `.venv/Scripts/python.exe` serve quando `.venv/bin/python`
        nao existe, e `python` serve quando `python3` nao existe.

O LIMITE, dito com todas as letras: isto prova que o script ESCOLHE o certo
conforme o que existe no PATH, num Mac. Nao prova que `Get-Clipboard` devolve o
clipboard, que `rundll32` abre o navegador, nem que o MSYS engole os caminhos
com barra invertida que o Python do Windows devolve. Isso precisa de alguem com
Windows, e o spec diz o que conferir.

Nenhum token real entra aqui, e o clipboard real desta maquina nunca e lido: o
"PowerShell" e o mesmo roteiro de `clipboard_dublado`, atras de outro nome.
"""
from __future__ import annotations

import os
import shutil
import sys

import pytest

from tests.moodle.test_token_decode import (  # noqa: F401 — as fixtures entram pelo namespace
    MARCADOR_PAYLOAD,
    PRIVATE,
    WSTOKEN,
    clipboard_dublado,
    navegador_dublado,
    raiz_falsa,
    raiz_token,
    token_sh,
)
from tests.moodle.test_token_navegador import (
    JSON_OK,
    SAIDA_AGUARDANDO,
    arquivo_passaporte,
    leituras,
    passaporte_da_url,
    path_minimo,
    roteiro,
)

pytestmark = pytest.mark.politica

LEITORES_WINDOWS = ("powershell.exe", "powershell", "pwsh.exe", "pwsh")
ARGV_GET_CLIPBOARD = "-NoProfile -Command Get-Clipboard"
COMANDO_WINDOWS = "powershell -NoProfile -Command Get-Clipboard | ./scripts/token.sh"
SEM_SESSAO_GRAFICA = {"DISPLAY": "", "WAYLAND_DISPLAY": ""}


# ------------------------------------------------------------------- dubles


def duble(raiz, nome: str, corpo: str) -> str:
    """Um executavel de mentira chamado `nome`, sozinho na propria pasta, que
    registra o argv em `raiz/<nome>.log` (uma linha por chamada) e depois faz
    `corpo`. Devolve a pasta, para entrar no PATH. Uma pasta por dube e o que
    permite dizer exatamente o que existe em cada cenario."""
    pasta = raiz / "dubles" / nome
    pasta.mkdir(parents=True, exist_ok=True)
    falso = pasta / nome
    falso.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{raiz / (nome + '.log')}'\n"
        f"{corpo}\n",
        encoding="utf-8",
    )
    falso.chmod(0o755)
    return str(pasta)


def argv_de(raiz, nome: str) -> list[str]:
    log = raiz / (nome + ".log")
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def leitor_windows(raiz, nome: str) -> str:
    """O PowerShell dublado: mesmo roteiro do `pbpaste` de `clipboard_dublado`
    (que escreve `raiz/pbpaste.py` e conta as leituras em `pbpaste.log`), atras
    do nome que Windows teria. O `bin/pbpaste` que a fixture tambem cria NAO
    entra no PATH aqui — so a pasta deste dube."""
    clipboard_dublado(raiz)
    return duble(raiz, nome, f"exec '{sys.executable}' '{raiz / 'pbpaste.py'}'")


def curl_windows(raiz) -> str:
    """O `curl` dublado, fora de `raiz/bin` para nao trazer o `pbpaste` junto."""
    return duble(raiz, "curl", f"cat >/dev/null\ncat <<'JSON'\n{JSON_OK}\nJSON")


def lancador(raiz, nome: str) -> str:
    return duble(raiz, nome, "exit 0")


def rodar(raiz, tmp_path, *pastas: str, segundos: int = 1, env=None, **kw):
    """A invocacao de abertura (sem terminal, stdin vazio) num PATH que tem SO o
    minimo do script, o `curl` dublado e as pastas pedidas. Sem `open`, sem
    `pbpaste`, sem sessao grafica: o chao de um Windows, salvo o que o teste
    acrescenta."""
    caminho = ":".join([*pastas, curl_windows(raiz), path_minimo(tmp_path)])
    ambiente = dict(SEM_SESSAO_GRAFICA)
    ambiente["USP_MCP_VIGIA_SEGUNDOS"] = str(segundos)
    if env:
        ambiente.update(env)
    return token_sh(raiz, "", path=caminho, navegador=False, clipboard=False, env=ambiente, **kw)


def token_gravado(raiz) -> bool:
    return f"MOODLE_TOKEN={WSTOKEN}\n" in (raiz / ".env").read_text(encoding="utf-8")


# ------------------------------------------------ WIN1: o PowerShell e o leitor


def test_win1_sem_pbpaste_wl_paste_nem_xclip_o_leitor_e_o_powershell(raiz_token, tmp_path):
    """WIN1 — o sintoma do dono, fechado: num PATH sem os tres leitores de sempre
    e com `powershell.exe`, a vigia existe, se anuncia citando o PowerShell, le por
    ele e segue ate gravar. O que se afirma e o argv ENVIADO ao PowerShell: e ele
    que um Windows de verdade vai receber."""
    ps = leitor_windows(raiz_token, "powershell.exe")
    roteiro(raiz_token, {0: "um texto que ja estava no clipboard", 2: MARCADOR_PAYLOAD})

    r = rodar(raiz_token, tmp_path, ps, segundos=3)
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida
    assert "vou LER o clipboard desta maquina (`powershell.exe`)" in saida
    assert "nao ha clipboard para vigiar" not in saida

    chamadas = argv_de(raiz_token, "powershell.exe")
    assert chamadas, "o PowerShell dublado nunca foi chamado"
    assert all(c == ARGV_GET_CLIPBOARD for c in chamadas), chamadas
    assert leituras(raiz_token) == 3, "marco + 2 leituras ate a mudanca no indice 2"

    assert "Seguindo sozinho a partir daqui" in saida
    assert "confere: o payload responde a ESTA rodada" in saida
    assert token_gravado(raiz_token)
    assert not arquivo_passaporte(raiz_token).exists(), "uso unico: devia ter sido consumido"
    assert WSTOKEN not in saida, "ecoou o token (Invariante 3)"
    assert PRIVATE not in saida, "ecoou o privatetoken (§2.2)"


# ---------------------------------------------- WIN2: os nomes que ele pode ter


@pytest.mark.parametrize("nome", LEITORES_WINDOWS)
def test_win2_cada_nome_do_powershell_e_aceito_sozinho(raiz_token, tmp_path, nome):
    """WIN2 — no WSL o Linux nao completa a extensao, entao e `powershell.exe`;
    no Git Bash completa, e `powershell` basta; `pwsh` e o PowerShell 7, que a
    pessoa pode ter instalado. Cada um, sozinho no PATH, e escolhido e chamado
    com o mesmo argv."""
    ps = leitor_windows(raiz_token, nome)
    roteiro(raiz_token, {0: "nada muda"})
    r = rodar(raiz_token, tmp_path, ps, segundos=1)
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert f"vou LER o clipboard desta maquina (`{nome}`)" in saida
    assert argv_de(raiz_token, nome) == [ARGV_GET_CLIPBOARD] * (1 + 2), "marco + 2 por segundo"


# -------------------------------------------- WIN3: ele nao toma o lugar de nada


def test_win3_onde_ha_pbpaste_o_powershell_nao_e_escolhido(raiz_token, tmp_path):
    """WIN3 — a ordem: o PowerShell e o ultimo candidato. Num Mac com um
    `powershell` instalado por acaso, o leitor continua sendo o `pbpaste`, e o
    PowerShell nao e chamado nem uma vez."""
    ps = leitor_windows(raiz_token, "powershell.exe")
    pb = str(clipboard_dublado(raiz_token))  # raiz/bin, com o `pbpaste` dublado
    roteiro(raiz_token, {0: "nada muda"})
    r = rodar(raiz_token, tmp_path, ps, pb, segundos=1)
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert "vou LER o clipboard desta maquina (`pbpaste`)" in saida
    assert argv_de(raiz_token, "powershell.exe") == [], "chamou o PowerShell com pbpaste no PATH"
    assert leituras(raiz_token) == 3


# ------------------------------------------------------------- WIN4: o CRLF


def test_win4_o_crlf_do_get_clipboard_nao_estraga_a_forma_nem_a_conferencia(raiz_token, tmp_path):
    """WIN4 — o Get-Clipboard termina a linha em CRLF. O `\\r` nao pode virar
    parte do endereco: a forma tem de conferir e o payload tem de decodificar."""
    ps = leitor_windows(raiz_token, "powershell.exe")
    roteiro(raiz_token, {0: "", 2: MARCADOR_PAYLOAD + "\r\n"})
    r = rodar(raiz_token, tmp_path, ps, segundos=3)
    saida = r.stdout + r.stderr
    assert r.returncode == 0, saida
    assert "o clipboard mudou para algo que comeca com `moodlemobile://token=`" in saida
    assert "confere: o payload responde a ESTA rodada" in saida
    assert token_gravado(raiz_token)
    assert "\r" not in (raiz_token / ".env").read_text(encoding="utf-8")


# --------------------------------------------- WIN5: as mensagens ensinam o Windows


def test_win5_a_vigia_que_venceu_ensina_o_comando_do_windows(raiz_token, tmp_path):
    """WIN5 — o fluxo em duas invocacoes continua existindo em Windows, e a saida
    3 tem de dizer o comando de la, nao so o `pbpaste |` do Mac."""
    ps = leitor_windows(raiz_token, "powershell.exe")
    roteiro(raiz_token, {0: "nada muda"})
    r = rodar(raiz_token, tmp_path, ps, segundos=1)
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert "vigia encerrada sem o endereco" in saida
    assert COMANDO_WINDOWS in saida
    assert "pbpaste | ./scripts/token.sh" in saida, "o comando do Mac sumiu"


def test_win5b_sem_leitor_nenhum_a_falta_nomeia_o_powershell(raiz_token, tmp_path):
    """WIN5b — a maquina sem leitor (V6) agora lista o PowerShell entre os que
    faltam: quem le a mensagem num Windows sem PowerShell no PATH fica sabendo o
    que instalar ou onde procurar."""
    r = rodar(raiz_token, tmp_path, segundos=90)
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert "sem pbpaste/wl-paste/xclip/powershell nesta maquina" in saida
    assert "nao ha clipboard para vigiar" in saida
    assert COMANDO_WINDOWS in saida
    assert "AVISO, antes de comecar" not in saida, "anunciou uma vigia que nao existe"


# ------------------------------------------------------------ WIN6: o lancador


def test_win6_rundll32_recebe_a_url_pelo_file_protocol_handler(raiz_token, tmp_path):
    """WIN6 — sem `open`, `xdg-open` nem `wslview`, o lancador e o `rundll32`,
    e o argv e `url.dll,FileProtocolHandler <url>`: a URL vai como argumento,
    sem passar pelo `cmd.exe` (que quebraria a URL no `&`)."""
    rd = lancador(raiz_token, "rundll32.exe")
    r = rodar(raiz_token, tmp_path, rd)
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert "abri a URL no navegador padrao (`rundll32.exe`)" in saida
    chamadas = argv_de(raiz_token, "rundll32.exe")
    assert len(chamadas) == 1, chamadas
    prefixo, _, url = chamadas[0].partition(" ")
    assert prefixo == "url.dll,FileProtocolHandler"
    assert passaporte_da_url(url) == passaporte_da_url(saida)


def test_win6b_rundll32_sem_extensao_tambem_serve(raiz_token, tmp_path):
    """WIN6b — no Git Bash o nome sem `.exe` resolve; no WSL, nao. Os dois valem."""
    rd = lancador(raiz_token, "rundll32")
    r = rodar(raiz_token, tmp_path, rd)
    assert r.returncode == SAIDA_AGUARDANDO, r.stdout + r.stderr
    assert "abri a URL no navegador padrao (`rundll32`)" in r.stdout + r.stderr
    assert len(argv_de(raiz_token, "rundll32")) == 1


def test_win6c_wslview_recebe_a_url_e_vence_o_open(raiz_token, tmp_path):
    """WIN6c — no WSL, `wslview` abre o navegador do WINDOWS, que e onde a pessoa
    esta logada na Senha Unica. E ele tem de vir antes do `open`: no Ubuntu,
    `/usr/bin/open` e o `openvt` do console, que nao abre URL nenhuma."""
    wv = lancador(raiz_token, "wslview")
    op = str(navegador_dublado(raiz_token))  # raiz/bin, com o `open` dublado
    r = rodar(raiz_token, tmp_path, wv, op)
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert "abri a URL no navegador padrao (`wslview`)" in saida
    chamadas = argv_de(raiz_token, "wslview")
    assert len(chamadas) == 1, chamadas
    assert passaporte_da_url(chamadas[0]) == passaporte_da_url(saida)
    assert not (raiz_token / "open.log").exists(), "chamou o `open` com `wslview` no PATH"


def test_win6d_open_continua_vencendo_o_rundll32(raiz_token, tmp_path):
    """WIN6d — o Mac nao muda: com `open` e `rundll32` no PATH, o lancador e o
    `open` de sempre. O `rundll32` e ultimo recurso."""
    rd = lancador(raiz_token, "rundll32.exe")
    op = str(navegador_dublado(raiz_token))
    r = rodar(raiz_token, tmp_path, rd, op)
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert "abri a URL no navegador padrao (`open`)" in saida
    assert argv_de(raiz_token, "rundll32.exe") == []
    assert (raiz_token / "open.log").exists()


def test_win6e_sem_lancador_nenhum_a_falta_nomeia_os_do_windows(raiz_token, tmp_path):
    """WIN6e — a mensagem da maquina sem lancador lista `wslview` e `rundll32`
    junto de `open` e `xdg-open`, e o resto da abertura segue como sempre."""
    r = rodar(raiz_token, tmp_path)
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert "nao ha como abrir navegador desta maquina" in saida
    assert "wslview" in saida and "rundll32" in saida
    assert arquivo_passaporte(raiz_token).exists()


# ------------------------------------------------------------ WIN7: o Python


def python_dublado(destino, log) -> None:
    """Um interpretador de mentira que anota a chamada e passa tudo ao de verdade."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        "#!/bin/sh\n"
        f"printf 'chamado\\n' >> '{log}'\n"
        f"exec '{sys.executable}' \"$@\"\n",
        encoding="utf-8",
    )
    destino.chmod(0o755)


def test_win7_o_venv_do_windows_tem_scripts_e_nao_bin(raiz_token, tmp_path):
    """WIN7 — `python -m venv` em Windows cria `.venv/Scripts/python.exe`, e nao
    `.venv/bin/python`. Sem `bin/`, o script tem de achar o de `Scripts/` — e
    NAO cair no `python3` do PATH, que pode ser outro interprete, sem o pacote."""
    shutil.rmtree(raiz_token / ".venv")
    log = raiz_token / "python.exe.log"
    python_dublado(raiz_token / ".venv" / "Scripts" / "python.exe", log)

    r = rodar(raiz_token, tmp_path)
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert log.exists(), "o script nao usou .venv/Scripts/python.exe"
    assert arquivo_passaporte(raiz_token).exists()


def test_win7b_sem_venv_e_sem_python3_o_python_serve(raiz_token, tmp_path):
    """WIN7b — o instalador do python.org para Windows cria `python`, nao
    `python3`. Sem venv e sem `python3` no PATH, `python` e o candidato."""
    shutil.rmtree(raiz_token / ".venv")
    log = raiz_token / "python.log"
    pasta = raiz_token / "dubles" / "python"
    python_dublado(pasta / "python", log)
    assert shutil.which("python3", path=path_minimo(tmp_path)) is None, "o PATH minimo trouxe python3"

    r = rodar(raiz_token, tmp_path, str(pasta))
    saida = r.stdout + r.stderr
    assert r.returncode == SAIDA_AGUARDANDO, saida
    assert log.exists(), "o script nao usou o `python` do PATH"


def test_win7c_sem_python_nenhum_a_falha_e_legivel_e_antes_de_tudo(raiz_token, tmp_path):
    """WIN7c — Invariante 6: sem interpretador nenhum, o script para no comeco
    dizendo o que procurou e o que fazer, em vez de morrer em
    `command not found` no primeiro passo que o usa."""
    shutil.rmtree(raiz_token / ".venv")
    r = rodar(raiz_token, tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "nao achei Python" in r.stderr
    assert ".venv/Scripts/python.exe" in r.stderr
    assert "1/7" not in r.stdout, "seguiu para o passo 1 sem Python"
