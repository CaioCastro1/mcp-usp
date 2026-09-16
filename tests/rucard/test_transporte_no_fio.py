"""R49-R53: a resposta que chega QUEBRADA também vira erro legível.

Medido contra um servidor local em `127.0.0.1` que responde mal de três jeitos:

| o que o servidor faz                    | o que o `http.client` levanta | é `OSError`? |
|-----------------------------------------|-------------------------------|--------------|
| `Content-Length` maior que o corpo       | `IncompleteRead`              | **não**      |
| primeira linha que não é status HTTP     | `BadStatusLine`               | **não**      |
| fecha sem escrever um byte               | `RemoteDisconnected`          | sim          |

O `except OSError` do cliente pega a terceira e **deixa passar as duas
primeiras**. A docstring do transporte diz que erro de rede sobe como `OSError`
"para o cliente traduzir", e o raciocínio está certo — o que estava errado é a
premissa: nem toda falha de transporte é `OSError`. Quando escapa, a exceção
sobe crua até a fronteira MCP, o SDK a classifica como crash e o modelo recebe
`Error executing tool bandejao`, de 29 bytes.

`desconecta` entra parametrizado junto mesmo já passando: é a que separa este
sistema do Jupiter, e um teste que só cobrisse as duas quebradas deixaria a
regressão dela sem guarda.

**Por que servidor de socket e não dublê.** Um dublê que levante
`IncompleteRead` prova que o `except` pega a classe; não prova que a classe é
essa. O servidor vive em `tests/servidor_ruim.py` e guarda o que recebeu — é de
lá que saem as asserções sobre o que FOI ENVIADO.
"""
import asyncio
import datetime

import pytest

from tests.rucard.conftest import HASH_DE_TESTE
from tests.servidor_ruim import ServidorRuim
from usp_mcp.rucard import cliente as mod_cliente, server
from usp_mcp.rucard.cliente import ClienteRucard
from usp_mcp.rucard.erros import ErroRucard, RucardIndisponivel

pytestmark = pytest.mark.contrato

MODOS = ("incompleto", "linha_ruim", "desconecta")
SEG_FASE1 = datetime.date(2026, 8, 24)


@pytest.mark.parametrize("modo", MODOS)
def test_r49_resposta_quebrada_vira_erro_legivel(modo, monkeypatch):
    with ServidorRuim(modo) as servidor:
        monkeypatch.setattr(mod_cliente, "URL_BASE", servidor.url(""))
        c = ClienteRucard(mod_cliente.transporte_http, hash_rucard=HASH_DE_TESTE)

        with pytest.raises(ErroRucard) as capturado:
            c.menu("6", SEG_FASE1)

    assert isinstance(capturado.value, RucardIndisponivel), (
        f"{modo}: a exceção que subiu foi {type(capturado.value).__name__}. Crua, "
        "ela chega ao modelo como a genérica do SDK, de 29 bytes."
    )


@pytest.mark.parametrize("modo", MODOS)
def test_r50_a_hash_saiu_no_corpo_antes_de_o_fio_quebrar(modo, monkeypatch):
    """Asserção sobre o que FOI ENVIADO, e não só sobre o que voltou.

    Sem ela, um transporte que falhasse antes de montar o corpo daria o mesmo
    `raises` — e o teste estaria medindo a própria desistência.
    """
    with ServidorRuim(modo) as servidor:
        monkeypatch.setattr(mod_cliente, "URL_BASE", servidor.url(""))
        c = ClienteRucard(mod_cliente.transporte_http, hash_rucard=HASH_DE_TESTE)
        with pytest.raises(ErroRucard):
            c.menu("6", SEG_FASE1)

    recebido = servidor.pedido.decode("latin-1")
    assert recebido.startswith("POST /menu/6"), recebido[:80]
    assert f"hash={HASH_DE_TESTE}" in recebido, (
        "o corpo form-urlencoded com a hash não saiu"
    )
    assert mod_cliente.AGENTE in recebido


def test_r51_corpo_cortado_nao_e_descrito_como_timeout(monkeypatch):
    """"Timeout ou conexão recusada" é o diagnóstico errado para um servidor
    que respondeu e respondeu mal. Quem lê decide coisas diferentes nos dois."""
    with ServidorRuim("incompleto") as servidor:
        monkeypatch.setattr(mod_cliente, "URL_BASE", servidor.url(""))
        c = ClienteRucard(mod_cliente.transporte_http, hash_rucard=HASH_DE_TESTE)
        with pytest.raises(RucardIndisponivel) as capturado:
            c.menu("6", SEG_FASE1)

    texto = str(capturado.value)
    assert "IncompleteRead" in texto, f"a mensagem não nomeia o que houve: {texto!r}"
    assert "timeout" not in texto.lower(), (
        "a mensagem de timeout vazou para um caso em que o servidor respondeu"
    )


def test_r52_a_mensagem_nao_carrega_o_corpo_cru_do_servidor(monkeypatch):
    """`BadStatusLine` carrega a linha que o servidor mandou, e ela pode ser
    grande. Mesmo raciocínio dos 3.240 B de HTML do Tomcat."""
    with ServidorRuim("linha_ruim") as servidor:
        monkeypatch.setattr(mod_cliente, "URL_BASE", servidor.url(""))
        c = ClienteRucard(mod_cliente.transporte_http, hash_rucard=HASH_DE_TESTE)
        with pytest.raises(RucardIndisponivel) as capturado:
            c.menu("6", SEG_FASE1)

    texto = str(capturado.value)
    assert "BadStatusLine" in texto
    assert len(texto) < 600, f"{len(texto)} caracteres — a mensagem virou despejo"


def test_r53_o_fio_mcp_recebe_a_mensagem_e_nao_a_generica_do_sdk(monkeypatch):
    """Fim a fim, com o transporte REAL apontado para o servidor local.

    Os quatro RUs falham do mesmo jeito, e `bandejao` levanta quando NENHUM
    responde — é o caminho em que a mensagem tem de atravessar.
    """
    mcp_server = pytest.importorskip("mcp.server")
    from mcp_types import CallToolRequestParams

    capturado = {}

    def _run_falso(self, transport="stdio", **kwargs):
        capturado["servidor"] = self

    monkeypatch.setattr(mcp_server.MCPServer, "run", _run_falso)
    monkeypatch.setenv("RUCARD_HASH", HASH_DE_TESTE)

    with ServidorRuim("incompleto") as ruim:
        monkeypatch.setattr(mod_cliente, "URL_BASE", ruim.url(""))
        server.main()
        assert "servidor" in capturado, "main() retornou sem chegar em run()"

        resultado = asyncio.run(
            capturado["servidor"]._handle_call_tool(
                None, CallToolRequestParams(name="bandejao", arguments={"dia": "hoje"})
            )
        )

    assert resultado.is_error
    texto = resultado.content[0].text
    assert texto.strip() != "Error executing tool bandejao", (
        "a exceção de transporte subiu crua e o modelo recebeu a genérica do SDK"
    )
    assert len(texto) > 60, f"{len(texto)} caracteres: {texto!r}"
    assert "RUCard" in texto
