"""T88-T93: a resposta que chega QUEBRADA também vira erro legível.

O buraco que este arquivo fecha foi medido contra um servidor local em
`127.0.0.1` que responde mal de três jeitos, e vale para as duas superfícies do
Jupiter (o POST do DWR e o GET da página de requisitos):

| o que o servidor faz                    | o que o `http.client` levanta | é `OSError`? |
|-----------------------------------------|-------------------------------|--------------|
| `Content-Length` maior que o corpo       | `IncompleteRead`              | **não**      |
| primeira linha que não é status HTTP     | `BadStatusLine`               | **não**      |
| fecha sem escrever um byte               | `RemoteDisconnected`          | sim          |

O `except (URLError, TimeoutError)` dos dois transportes não pega nenhuma das
três: as duas primeiras não são `OSError` (e `URLError` é subclasse de `OSError`),
e `RemoteDisconnected` é `ConnectionResetError` — `OSError`, mas nem `URLError`
nem `TimeoutError`. Então a exceção subia crua até a fronteira MCP, onde o SDK a
classifica como crash e o modelo recebe os 32 bytes de `Error executing tool
disciplina`. É o mesmo defeito que o `test_erro_no_fio.py` fechou para o erro de
domínio, agora pelo lado do transporte.

**Por que servidor de socket e não dublê.** Um dublê que levante
`IncompleteRead` prova que o `except` pega a classe; não prova que a classe é
essa. Quem decide isso é a biblioteca padrão lendo bytes reais. O servidor vive
em `tests/servidor_ruim.py`, escuta só em `127.0.0.1` e guarda o que recebeu —
as asserções sobre o que FOI ENVIADO saem de lá.
"""
import asyncio

import pytest

from tests.servidor_ruim import ServidorRuim
from usp_mcp.jupiter import cliente, server
from usp_mcp.jupiter.erros import ErroJupiter, JupiterIndisponivel

pytestmark = pytest.mark.contrato

MODOS = ("incompleto", "linha_ruim", "desconecta")

CORPO_DWR = (
    "callCount=1\nwindowName=\nc0-scriptName=ControlePublicoDWR\n"
    "c0-methodName=obter\nc0-id=0\nc0-param0=string:pubObterDisciplina\n"
)


# --- o transporte do DWR (POST) ---------------------------------------------


@pytest.mark.parametrize("modo", MODOS)
def test_t88_resposta_quebrada_no_post_vira_erro_legivel(modo):
    """As três patologias, uma a uma, contra o transporte real.

    Sem marcar `modo` no id do teste isto seria um teste só que passa com duas
    das três consertadas — e `desconecta` é justamente a que o RUCard já pegava
    e o Jupiter não, ou seja, a que some primeiro de um teste agregado.
    """
    with ServidorRuim(modo) as servidor:
        with pytest.raises(ErroJupiter) as capturado:
            cliente.transporte_http(
                servidor.url("/dwr/call/plaincall/ControlePublicoDWR.obter.dwr"),
                CORPO_DWR,
                {"Content-Type": "text/plain", "User-Agent": cliente.AGENTE},
            )

    assert isinstance(capturado.value, JupiterIndisponivel), (
        f"{modo}: a exceção que subiu foi {type(capturado.value).__name__}. Crua, "
        "ela chega ao modelo como a genérica do SDK, de 32 bytes."
    )


@pytest.mark.parametrize("modo", MODOS)
def test_t89_o_corpo_dwr_saiu_inteiro_antes_de_o_fio_quebrar(modo):
    """Asserção sobre o que FOI ENVIADO, e não só sobre o que voltou.

    Sem ela este arquivo ficaria verde com um transporte que nem chegasse a
    montar o corpo: qualquer exceção antes do `send` daria o mesmo `raises`.
    """
    with ServidorRuim(modo) as servidor:
        with pytest.raises(ErroJupiter):
            cliente.transporte_http(
                servidor.url("/dwr/call/plaincall/ControlePublicoDWR.obter.dwr"),
                CORPO_DWR,
                {"Content-Type": "text/plain", "User-Agent": cliente.AGENTE},
            )

    recebido = servidor.pedido.decode("latin-1")
    assert recebido.startswith("POST /dwr/call/plaincall/"), recebido[:80]
    assert "c0-methodName=obter" in recebido
    assert "c0-param0=string:pubObterDisciplina" in recebido
    assert cliente.AGENTE in recebido, (
        "o User-Agent identificável não saiu: quem administra o JupiterWeb tem "
        "que conseguir saber quem está batendo"
    )


# --- o transporte da página de requisitos (GET) ------------------------------


@pytest.mark.parametrize("modo", MODOS)
def test_t90_resposta_quebrada_no_get_vira_erro_legivel(modo):
    """A segunda superfície tem o mesmo `except` e o mesmo buraco."""
    with ServidorRuim(modo) as servidor:
        with pytest.raises(ErroJupiter) as capturado:
            cliente.transporte_get_http(
                servidor.url("/listarCursosRequisitos?coddis=PSI3323"),
                {"User-Agent": cliente.AGENTE},
            )

    assert isinstance(capturado.value, JupiterIndisponivel)
    recebido = servidor.pedido.decode("latin-1")
    assert recebido.startswith("GET /listarCursosRequisitos?coddis=PSI3323"), recebido[:80]


# --- a mensagem: legível, e honesta sobre qual dos dois casos é --------------


def test_t91_corpo_cortado_nao_e_descrito_como_ausencia_de_rede():
    """"Não respondeu" é a frase errada para um servidor que respondeu mal.

    A mensagem antiga dizia que num ambiente sem acesso à rede da USP a chamada
    não tem como sair — verdade para timeout, e diagnóstico errado aqui: o
    servidor respondeu, e o que veio é que não é HTTP íntegro. Quem lê decide
    coisas diferentes nos dois casos.
    """
    with ServidorRuim("incompleto") as servidor:
        with pytest.raises(JupiterIndisponivel) as capturado:
            cliente.transporte_get_http(servidor.url("/x"), {"User-Agent": cliente.AGENTE})

    texto = str(capturado.value)
    assert "IncompleteRead" in texto, (
        f"a mensagem não nomeia o que houve: {texto!r}"
    )
    assert "sandbox" not in texto.lower(), (
        "a mensagem de rede ausente vazou para um caso em que a rede funcionou"
    )


def test_t92_a_mensagem_nao_carrega_o_corpo_cru_do_servidor():
    """`BadStatusLine` carrega a linha que o servidor mandou, e ela pode ser
    grande. A mensagem é para ser lida, não para transportar o fio."""
    with ServidorRuim("linha_ruim") as servidor:
        with pytest.raises(JupiterIndisponivel) as capturado:
            cliente.transporte_get_http(servidor.url("/x"), {"User-Agent": cliente.AGENTE})

    texto = str(capturado.value)
    assert "BadStatusLine" in texto
    assert len(texto) < 600, f"{len(texto)} caracteres — a mensagem virou despejo"


# --- a ponta: o que o MODELO recebe -----------------------------------------


def test_t93_o_fio_mcp_recebe_a_mensagem_e_nao_a_generica_do_sdk(monkeypatch):
    """Fim a fim, com o transporte REAL apontado para o servidor local.

    É o teste que mediu o defeito: sem a correção, o que chega aqui são os 32
    bytes de `Error executing tool disciplina`, porque o SDK classifica qualquer
    exceção que não seja nossa como crash e retém o texto no servidor.
    """
    mcp_server = pytest.importorskip("mcp.server")
    from mcp_types import CallToolRequestParams

    capturado = {}

    def _run_falso(self, transport="stdio", **kwargs):
        capturado["servidor"] = self

    monkeypatch.setattr(mcp_server.MCPServer, "run", _run_falso)

    with ServidorRuim("incompleto") as ruim:
        def _transporte_local(url, corpo, cabecalhos):
            # O transporte REAL, só com o endereço trocado: é ele que tem o
            # `except`, e trocá-lo por um dublê aqui mediria outra coisa.
            return cliente.transporte_http(ruim.url("/dwr"), corpo, cabecalhos)

        monkeypatch.setattr(server, "transporte_http", _transporte_local)
        server.main()
        assert "servidor" in capturado, "main() retornou sem chegar em run()"

        resultado = asyncio.run(
            capturado["servidor"]._handle_call_tool(
                None, CallToolRequestParams(name="disciplina", arguments={"sigla": "PSI3323"})
            )
        )

    assert resultado.is_error
    texto = resultado.content[0].text
    assert texto.strip() != "Error executing tool disciplina", (
        "a exceção de transporte subiu crua e o modelo recebeu a genérica do SDK"
    )
    assert len(texto) > 60, f"{len(texto)} caracteres: {texto!r}"
    assert "JupiterWeb" in texto
