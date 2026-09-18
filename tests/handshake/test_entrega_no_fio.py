"""E14: com a flag desligada, as duas ferramentas de escrita NÃO EXISTEM no fio.

**Ferramenta que aparece e sempre recusa ensina o modelo a tentar.** Ele a vê na
lista, escolhe, gasta uma chamada, lê a negativa e procura o contorno. Com ela
fora do `tools/list` o padrão continua sendo negar e nada no que o modelo lê
sugere que existe um caminho de escrita para achar.

Pelo `tools/list` REAL, de um processo de verdade, e não por introspecção do
módulo: o que importa é o que CHEGA ao cliente. Já custou caro neste repositório
acreditar no declarado — o SDK deriva o schema da assinatura, e por isso nenhuma
descrição de parâmetro viajava enquanto a suíte inteira estava verde. E o
registro em `main()` é um segundo lugar onde a condição podia ter sido esquecida:
declarar as duas fora da lista e registrá-las mesmo assim daria um servidor que
anuncia onze e aceita treze.

**Os dois processos sobem com o ambiente escrito à mão**, um com a flag em "1" e
outro em "0". É o que torna estas duas asserções independentes de quem rodou a
suíte: elas afirmam a mesma coisa com a flag ligada no terminal e com ela
desligada, que é o critério de parada do spec.
"""
from __future__ import annotations

import pytest

from tests.handshake.conftest import (
    MOTIVO_SEM_SDK,
    ClienteStdio,
    _tem_sdk,
)

pytestmark = pytest.mark.handshake

SERVIDOR = "usp_mcp.moodle.server"
FLAG = "USP_MCP_ENTREGA"
AS_DUAS = {"salvar_rascunho", "entregar"}


def _anunciadas(valor_da_flag: str) -> list[dict]:
    """Sobe o servidor com a flag neste valor e devolve o `tools/list` dele."""
    if not _tem_sdk():
        pytest.skip(MOTIVO_SEM_SDK)
    with ClienteStdio(SERVIDOR, env={FLAG: valor_da_flag}) as cliente:
        cliente.apertar_mao()
        return cliente.pedir("tools/list")["tools"]


def test_e14_sem_a_flag_as_duas_de_escrita_nao_aparecem():
    ferramentas = _anunciadas("0")
    nomes = {f["name"] for f in ferramentas}

    assert not (nomes & AS_DUAS), (
        f"com {FLAG} desligada o servidor anuncia {sorted(nomes & AS_DUAS)}. "
        "Uma ferramenta de escrita visível e sempre recusada é pior do que "
        "nenhuma: ela ensina o modelo que o caminho existe e que falta achar o "
        "jeito de passar."
    )
    # Onze desde 17/09/2026 (`questionarios`); eram dez.
    assert len(nomes) == 11, (
        f"o servidor anuncia {len(nomes)} ferramentas sem a flag: {sorted(nomes)}"
    )

    # E o padrão do projeto continua inteiro: nenhuma das onze se diz de escrita.
    escrevem_no_moodle = [
        f["name"]
        for f in ferramentas
        if (f.get("annotations") or {}).get("destructiveHint") is True
    ]
    assert not escrevem_no_moodle, (
        f"sem a flag ainda há ferramenta destrutiva no fio: {escrevem_no_moodle}"
    )


def test_e14b_com_a_flag_as_duas_aparecem_e_sao_treze():
    """A outra metade, e sem ela E14 ficaria verde num servidor que nunca as
    expõe — o falso-verde de sempre, aqui na forma "a condição está sempre
    falsa"."""
    nomes = {f["name"] for f in _anunciadas("1")}

    assert AS_DUAS <= nomes, (
        f"com {FLAG}=1 o servidor não anunciou {sorted(AS_DUAS - nomes)}. A "
        "condição do `listar_ferramentas()` e o registro em `main()` são dois "
        "lugares diferentes, e os dois precisam concordar."
    )
    assert len(nomes) == 13, (
        f"o servidor anuncia {len(nomes)} ferramentas com a flag: {sorted(nomes)}"
    )
