"""L1-L6: o lançador que faz os servidores subirem de QUALQUER cwd.

O `.mcp.json` versionado dizia `"command": ".venv/bin/python"`. Isso funciona no
Claude Code, que roda o servidor com o cwd na raiz do projeto, e falha em todo
cliente que não faça isso — o Claude Desktop entre eles, que é justamente o alvo
do empacotamento `.mcpb` do §6.1. Medido: `cd /tmp && .venv/bin/python -m
usp_mcp.rucard.server` sai com rc=127 e "no such file or directory".

As duas saídas óbvias estão as duas erradas. Caminho absoluto no `.mcp.json`
põe o caminho da máquina de alguém num arquivo versionado (é o Invariante 3
aplicado a caminho em vez de segredo). Caminho relativo transfere ao cliente uma
premissa que nem todo cliente cumpre — e falha CALADA, que é o pior modo.
A saída é um lançador que resolve o próprio diretório: o `.mcp.json` segue
relativo, e quem usa cliente sem `cd` aponta para o caminho absoluto do script,
no arquivo de config da máquina dele.

**Esta suíte é o teste do lançador, não do servidor.** Ela sobe o processo pelo
`scripts/servidor.sh` de um cwd que NÃO é a raiz — que é a única coisa que o
handshake de `tests/handshake/` não faz, porque lá o `ClienteStdio` sobe com
`cwd=RAIZ`. O cliente JSON-RPC é o mesmo, emprestado de lá: o que muda é o
comando e o diretório de onde ele parte.

Nada aqui toca a rede da USP nem lê credencial: `initialize` é respondido antes
de qualquer `chamar_ferramenta`, como no handshake. L1/L2 pulam sem o SDK
instalado; L3-L6 rodam sempre, porque olham config e shell, não o SDK.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

from tests.handshake.conftest import (
    RAIZ,
    TEMPO_LIMITE_S,
    ClienteStdio,
    com_sdk,
    descobrir_servidores,
    sistema_de,
)

LANCADOR = RAIZ / "scripts" / "servidor.sh"

# Descoberta, nunca lista escrita à mão — mesma razão do H9: um quarto sistema
# entra coberto no dia em que nascer, em vez de entrar com o mesmo furo.
SISTEMAS = [sistema_de(m) for m in descobrir_servidores()]


def _rodar(argumentos: list[str], cwd) -> subprocess.CompletedProcess:
    """Roda o lançador e devolve o processo terminado, sem levantar nada."""
    return subprocess.run(
        argumentos,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=TEMPO_LIMITE_S,
    )


# --------------------------------------------------------------- L1 e L2: sobe


@pytest.mark.handshake
@com_sdk
def test_l1_o_lancador_sobe_de_outro_cwd(tmp_path):
    assert LANCADOR.is_file(), (
        f"{LANCADOR} não existe. É ele que resolve a raiz do checkout para "
        "clientes que não fazem cd — sem ele o .mcp.json só serve ao Claude Code."
    )
    # O bit de execução é parte do contrato, não detalhe de arquivo: o cliente
    # MCP chama o caminho direto, sem `bash` na frente. Sem +x no git, todo
    # checkout novo falha com "permission denied" — outra falha calada.
    assert os.access(LANCADOR, os.X_OK), (
        f"{LANCADOR} não é executável. `chmod +x` e confira que o git guardou "
        "o modo 100755 (`git ls-files -s scripts/servidor.sh`)."
    )

    # `cwd=tmp_path` é a asserção de verdade deste teste: é o `cd /tmp` do
    # sintoma medido, escrito em teste para não depender de ninguém lembrar.
    with ClienteStdio(
        "usp_mcp.rucard.server", comando=[str(LANCADOR), "rucard"], cwd=tmp_path
    ) as cliente:
        info = cliente.apertar_mao()
        assert info["serverInfo"]["name"] == "usp-mcp-rucard", (
            f"o lançador subiu alguma coisa que se anuncia como "
            f"{info['serverInfo']['name']!r}, e não o servidor do RUCard."
        )
        assert cliente.vivo()


@pytest.mark.handshake
@com_sdk
@pytest.mark.parametrize("sistema", SISTEMAS)
def test_l2_os_tres_servidores_sobem_pelo_lancador(sistema, tmp_path):
    # Cada um tem de se identificar com o PRÓPRIO nome: um lançador que ignore
    # o argumento e suba sempre o mesmo servidor passaria em L1 e quebraria dois
    # dos três clientes, calado.
    with ClienteStdio(
        f"usp_mcp.{sistema}.server", comando=[str(LANCADOR), sistema], cwd=tmp_path
    ) as cliente:
        info = cliente.apertar_mao()
        assert info["serverInfo"]["name"] == f"usp-mcp-{sistema}", (
            f"`servidor.sh {sistema}` subiu {info['serverInfo']['name']!r}. "
            "O argumento do lançador tem de escolher o módulo."
        )


# ------------------------------------------------------------ L3 e L4: config


def test_l3_o_mcp_json_aponta_para_o_lancador():
    config = json.loads((RAIZ / ".mcp.json").read_text(encoding="utf-8"))
    servidores = config["mcpServers"]
    assert servidores, ".mcp.json sem servidor nenhum registrado"

    for nome, entrada in servidores.items():
        assert entrada["command"] == "scripts/servidor.sh", (
            f"{nome} chama {entrada['command']!r}. Chamar o interpretador direto "
            "é o bug: o caminho relativo assume que o cliente faz cd na raiz, e "
            "só o Claude Code faz."
        )
        argumentos = entrada.get("args", [])
        assert len(argumentos) == 1, (
            f"{nome} passa {argumentos} ao lançador; o contrato é um argumento "
            "só, o nome do sistema."
        )
        assert argumentos[0] in SISTEMAS, (
            f"{nome} pede o sistema {argumentos[0]!r}, que não existe em "
            f"usp_mcp/. Os que existem: {SISTEMAS}."
        )


def test_l4_nenhum_caminho_de_maquina_no_mcp_json():
    # A mesma asserção que R2/T2 já fazem nos conftests, agora no arquivo que
    # mais convida ao erro: a cura preguiçosa deste bug é colar o caminho
    # absoluto da própria máquina aqui, e ele quebra para todo mundo menos um.
    fonte = (RAIZ / ".mcp.json").read_text(encoding="utf-8")
    for agulha in ("/Users/", "/home/", "C:\\", "/private/tmp"):
        assert agulha not in fonte, (
            f"caminho absoluto de máquina no .mcp.json: {agulha!r}. O arquivo é "
            "versionado e compartilhado — o absoluto mora no config da máquina "
            "de quem usa (ver a seção do README), nunca aqui."
        )


# ---------------------------------------------------------- L5 e L6: recusas


def test_l5_sem_venv_a_falha_diz_a_cura(tmp_path):
    # Um checkout de mentira com tudo menos o venv: é o estado exato de quem
    # acabou de clonar, e o estado de todo worktree novo (§3 do CLAUDE.md).
    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    shutil.copy2(LANCADOR, checkout / "scripts" / "servidor.sh")
    for sistema in SISTEMAS:
        (checkout / "usp_mcp" / sistema).mkdir(parents=True)
        (checkout / "usp_mcp" / sistema / "server.py").write_text("", encoding="utf-8")

    processo = _rodar([str(checkout / "scripts" / "servidor.sh"), "rucard"], tmp_path)

    assert processo.returncode != 0, "sem venv, o lançador não pode sair com 0"
    saida = processo.stdout + processo.stderr
    assert "python3 -m venv .venv" in saida, (
        "a falha sem venv tem de dizer o comando que a cura — hoje o erro cru é "
        f"'no such file or directory', que não ensina nada (Invariante 6). "
        f"Saiu: {saida!r}"
    )


def test_l6_o_lancador_recusa_sistema_desconhecido(tmp_path):
    processo = _rodar([str(LANCADOR), "bandejao"], tmp_path)

    assert processo.returncode != 0, (
        "`servidor.sh bandejao` saiu com 0. Sistema que não existe é erro, e "
        "erro que sai com 0 é o modo mais caro de falhar num servidor stdio."
    )
    saida = processo.stdout + processo.stderr
    for sistema in SISTEMAS:
        assert sistema in saida, (
            f"a recusa não cita {sistema!r}. Quem errou o nome precisa ler quais "
            f"são os válidos na própria negativa (Invariante 6). Saiu: {saida!r}"
        )
    # A recusa vem ANTES do python: deixar o interpretador subir para descobrir
    # que o módulo não existe custa uma subida e devolve um traceback no lugar
    # de uma frase.
    for vestigio in ("No module named", "ModuleNotFoundError", "Traceback"):
        assert vestigio not in saida, (
            f"a recusa passou pelo interpretador ({vestigio!r} na saída). O "
            "nome do sistema é validado no shell, contra usp_mcp/*/server.py."
        )
