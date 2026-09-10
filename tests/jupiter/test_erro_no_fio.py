"""E1-E4: a mensagem de erro do Jupiter chega ao MODELO, não só ao stderr.

Medido em 10/09/2026 contra o `mcp 2.2.0` instalado: `disciplina{"sigla":
"XXX9999"}` devolvia ao modelo `Error executing tool disciplina` — 31 bytes — e
a mensagem que o Jupiter de fato deu ("Disciplina inválida ou ainda não ativada
!") ficava no stderr. Aqui a perda dói duas vezes: a `JupiterErro` existe
justamente para extrair essa frase dos 46 frames de stack trace do Tomcat que a
USP devolve com HTTP 200 (~1.978 tokens contra ~17), e o SDK descartava o que
sobrou desse trabalho.

A causa é do SDK. O `Tool.run` do 2.0.0 tinha um ramo só; o do 2.2.0 separa
`ToolError`/`ResourceError` (o texto viaja) de `except Exception` (crash, e "the
exception's own text stays on the server"). `ErroJupiter` herda de `Exception`,
então caía no ramo de crash — e `requirements.txt` declara `mcp>=2,<3`, então
toda instalação nova nascia muda.

**Por que `_handle_call_tool` e não `call_tool`.** A pública `call_tool()`
LEVANTA a exceção; quem a converte no `CallToolResult(is_error=True)` que viaja
no fio é `_handle_call_tool`, e é o texto DELE que o modelo lê. E4 é o único que
olha a exceção, porque é a corrente de causas que ele verifica.

Molde de T45-T48: `main()` roda em processo com só `run()` substituído, e o
transporte responde da fixture. Offline, sem credencial, sem rede.
"""
import asyncio

import pytest

from tests.jupiter.conftest import Gravador
from usp_mcp.jupiter import server
from usp_mcp.jupiter.erros import ErroJupiter


@pytest.fixture
def servidor_montado(monkeypatch):
    """Roda `main()` até a borda do stdio e devolve o `MCPServer` que ele montou."""
    mcp_server = pytest.importorskip("mcp.server")

    capturado = {}

    def _run_falso(self, transport="stdio", **kwargs):
        capturado["servidor"] = self
        capturado["transporte"] = transport

    monkeypatch.setattr(mcp_server.MCPServer, "run", _run_falso)
    server.main()

    assert "servidor" in capturado, "main() retornou sem chegar em run()"
    return capturado["servidor"]


def _no_fio(servidor, nome, argumentos):
    """O `CallToolResult` que o cliente MCP receberia — `is_error` e texto.

    `_handle_call_tool` é privada e é usada aqui por não haver outra: ela é o
    ponto do SDK em que a exceção vira o resultado que o modelo lê.
    """
    from mcp_types import CallToolRequestParams

    return asyncio.run(
        servidor._handle_call_tool(
            None, CallToolRequestParams(name=nome, arguments=argumentos)
        )
    )


@pytest.mark.contrato
def test_e1_erro_de_dominio_chega_com_a_mensagem(servidor_montado, monkeypatch, erro):
    gravador = Gravador([erro])
    monkeypatch.setattr(server, "transporte_http", gravador)

    resultado = _no_fio(servidor_montado, "disciplina", {"sigla": "XXX9999"})

    assert resultado.is_error, (
        "o Jupiter responde HTTP 200 no erro; se isto vier sem is_error, o "
        "silêncio voltou por outro caminho"
    )
    texto = resultado.content[0].text
    assert "Disciplina inválida" in texto, (
        f"o modelo recebeu {texto!r}. A frase que a USP mandou existe, foi "
        "extraída do stack trace e ficou no stderr — Invariante 6 quebrado na "
        "fronteira MCP."
    )


@pytest.mark.contrato
def test_e2_a_mensagem_nao_e_a_generica_do_sdk(servidor_montado, monkeypatch, erro):
    """A asserção que E1 sozinho não faz: o texto tem de DISTINGUIR, não só existir.

    A genérica do SDK (31 bytes) faz "essa sigla não existe" e "a USP caiu"
    parecerem o mesmo problema — que é exatamente o que a docstring de
    `erros.py` diz que estas classes existem para impedir.
    """
    monkeypatch.setattr(server, "transporte_http", Gravador([erro]))

    texto = _no_fio(servidor_montado, "disciplina", {"sigla": "XXX9999"}).content[0].text

    assert texto.strip() != "Error executing tool disciplina"
    assert len(texto) > 60, f"{len(texto)} caracteres: {texto!r}"
    # A metade que cura: a sigla pode existir e só não estar ativada, e o modelo
    # precisa saber disso para não afirmar que a disciplina não existe.
    assert "ainda não ativada" in texto


@pytest.mark.contrato
def test_e3_crash_de_verdade_continua_retido(servidor_montado, monkeypatch):
    """O outro lado da tradução, e a razão de ela não ser `except Exception`.

    Traduzir tudo devolveria ao modelo o traceback do Tomcat que a `JupiterErro`
    existe para descartar — 116x o custo, e a resposta errada. O SDK reter o
    texto de um crash é o comportamento certo; o defeito era só `ErroJupiter`
    contar como crash.
    """
    def _crash(nome, argumentos, **kwargs):
        raise RuntimeError("segredo")

    monkeypatch.setattr(server, "chamar_ferramenta", _crash)

    resultado = _no_fio(servidor_montado, "disciplina", {"sigla": "PSI3323"})

    assert resultado.is_error
    assert "segredo" not in resultado.content[0].text, (
        "o texto de uma exceção NÃO prevista vazou para o modelo"
    )


@pytest.mark.contrato
def test_e4_a_traducao_nao_engole_a_classe(servidor_montado, monkeypatch):
    """A tradução é envelope, não substituição: `ErroJupiter` continua a moeda interna.

    Sem o `from exc`, o log do servidor perde qual subclasse falhou — e é ela que
    separa "a USP recusou o pedido" de "veio HTML de login no lugar do envelope
    DWR", que têm curas diferentes para quem opera.
    """
    excecoes = pytest.importorskip("mcp.server.mcpserver.exceptions")
    ToolError, UnexpectedToolError = excecoes.ToolError, excecoes.UnexpectedToolError

    alvo = ErroJupiter("mensagem do domínio que o modelo precisa ler")

    def _recusa(nome, argumentos, **kwargs):
        raise alvo

    monkeypatch.setattr(server, "chamar_ferramenta", _recusa)

    with pytest.raises(ToolError) as capturado:
        asyncio.run(servidor_montado.call_tool("disciplina", {"sigla": "PSI3323"}))

    assert not isinstance(capturado.value, UnexpectedToolError), (
        "o SDK classificou como crash: a fronteira não traduziu o ErroJupiter"
    )
    # O SDK reembrulha o nosso `ToolError` com o prefixo do nome da ferramenta,
    # então o nosso é o `__cause__` do que sai — e o `ErroJupiter` original é o
    # `__cause__` do nosso.
    nosso = capturado.value.__cause__
    assert isinstance(nosso, ToolError), f"a causa foi {nosso!r}"
    assert str(nosso) == str(alvo)
    assert nosso.__cause__ is alvo, "a exceção do domínio não ficou na corrente"
