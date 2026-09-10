"""E1-E4: a mensagem de erro do RUCard chega ao MODELO, não só ao stderr.

Este arquivo nasceu de uma medição, não de simetria com os outros: contra o
`mcp 2.2.0` instalado, `bandejao{"dia":"blergh"}` devolvia ao modelo
`Error executing tool bandejao` — 29 bytes — enquanto a mensagem escrita para
esse caso ("não entendi o dia 'blergh'. Use 'hoje', 'amanhã' ou uma data como
26/08/2026…") ficava no stderr do servidor, onde nenhum modelo lê. É o
Invariante 6 quebrado exatamente na fronteira, e a suíte inteira ficava verde:
os testes das funções puras alcançam a exceção, e nenhum alcançava o fio.

A causa é do SDK, e vale registrá-la aqui porque ela decide a forma dos testes.
O `Tool.run` do 2.0.0 tinha um ramo só (`except Exception` repassando o texto);
o do 2.2.0 tem dois: `ToolError`/`ResourceError` viajam com a mensagem, e
qualquer outra exceção vira `UnexpectedToolError(f"Error executing tool {nome}")`
— "a crash: the exception's own text stays on the server". `ErroRucard` herda de
`Exception`, então caía no ramo de crash. Como `requirements.txt` declara
`mcp>=2,<3`, toda instalação nova nascia muda.

**Por que `_handle_call_tool` e não `call_tool`.** A pública `call_tool()`
LEVANTA a exceção; quem a converte no `CallToolResult(is_error=True)` que viaja
no fio é `_handle_call_tool`, e é o texto DELE que o modelo lê. Assertar sobre a
exceção seria parar uma etapa antes do lugar onde a mensagem se perdia — E4 faz
isso de propósito, para olhar a corrente de causas, e E1-E3 olham o fio.

Molde de T45-T48/T78-T81: `main()` roda em processo com só `run()` substituído.
Offline, sem credencial e sem tocar a rede da USP — o transporte injetado
levanta se alguém o chamar, o que também prova que a recusa acontece antes de
sair requisição.
"""
import asyncio

import pytest

from usp_mcp.rucard import server
from usp_mcp.rucard.erros import ErroRucard

# Forma, nunca o valor real — e a hash do RUCard nem é credencial de ninguém
# (§1.2). Fixa aqui para que o teste não dependa de o `.env` existir.
HASH_DE_TESTE = "0" * 32


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


@pytest.fixture
def sem_rede(monkeypatch):
    """Transporte que recusa ser chamado, e hash presente para o cliente montar.

    Duas coisas de uma vez: nenhuma requisição sai daqui (§1.1 — a rede da USP é
    alcançável desta máquina, e é justamente por isso que o dublê precisa gritar),
    e o erro que os testes exercitam é o do DOMÍNIO, não o de hash ausente.
    """
    def _levanta(url, corpo, cabecalhos):  # pragma: no cover — só se o teste falhar
        raise AssertionError(
            f"saiu requisição para {url!r}: o dia inválido deveria ser recusado "
            "antes de qualquer I/O"
        )

    monkeypatch.setenv("RUCARD_HASH", HASH_DE_TESTE)
    monkeypatch.setattr(server, "transporte_http", _levanta)


def _no_fio(servidor, nome, argumentos):
    """O `CallToolResult` que o cliente MCP receberia — `is_error` e texto.

    `_handle_call_tool` é privada e é usada aqui por não haver outra: ela é o
    ponto do SDK em que a exceção vira o resultado que o modelo lê, e a pública
    `call_tool()` levanta antes disso.
    """
    from mcp_types import CallToolRequestParams

    return asyncio.run(
        servidor._handle_call_tool(
            None, CallToolRequestParams(name=nome, arguments=argumentos)
        )
    )


@pytest.mark.contrato
def test_e1_erro_de_dominio_chega_com_a_mensagem(servidor_montado, sem_rede):
    resultado = _no_fio(servidor_montado, "bandejao", {"dia": "blergh"})

    assert resultado.is_error, "dia que o domínio recusa tem de virar erro no fio"
    texto = resultado.content[0].text
    assert "não entendi o dia" in texto, (
        f"o modelo recebeu {texto!r}. A mensagem escrita para este caso existe e "
        "ficou no stderr do servidor — Invariante 6 quebrado na fronteira MCP."
    )


@pytest.mark.contrato
def test_e2_a_mensagem_nao_e_a_generica_do_sdk(servidor_montado, sem_rede):
    """A asserção que E1 sozinho não faz: o texto tem de CURAR, não só existir.

    Medido em 10/09/2026: a genérica do SDK tem 29 bytes e diz ao modelo apenas
    que algo falhou. Com ela, a próxima tentativa dele é adivinhar — outra data
    inventada, outra chamada. O que evita a segunda chamada é a cura escrita
    junto do fato.
    """
    resultado = _no_fio(servidor_montado, "bandejao", {"dia": "blergh"})
    texto = resultado.content[0].text

    assert texto.strip() != "Error executing tool bandejao"
    assert len(texto) > 60, f"{len(texto)} caracteres: {texto!r}"
    assert "26/08/2026" in texto and "hoje" in texto, (
        "a cura ('use hoje, amanhã ou uma data como 26/08/2026') não atravessou"
    )


@pytest.mark.contrato
def test_e3_crash_de_verdade_continua_retido(servidor_montado, monkeypatch):
    """O outro lado da tradução, e a razão de ela não ser `except Exception`.

    O SDK retém o texto de um crash de propósito, e está certo: um `KeyError` ou
    o traceback de 46 frames do Tomcat que a `JupiterErro` existe para descartar
    não são resposta para o modelo. Traduzir tudo devolveria o silêncio ao lugar
    errado — cala o previsto, fala o imprevisto.
    """
    def _crash(nome, argumentos, **kwargs):
        raise RuntimeError("segredo")

    monkeypatch.setattr(server, "chamar_ferramenta", _crash)

    resultado = _no_fio(servidor_montado, "bandejao", {"dia": "hoje"})

    assert resultado.is_error
    assert "segredo" not in resultado.content[0].text, (
        "o texto de uma exceção NÃO prevista vazou para o modelo"
    )


@pytest.mark.contrato
def test_e4_a_traducao_nao_engole_a_classe(servidor_montado, monkeypatch):
    """A tradução é envelope, não substituição: `ErroRucard` continua a moeda interna.

    Sem o `from exc`, o log do servidor perde qual das cinco subclasses de
    `ErroRucard` falhou — e é a subclasse que separa "hash ausente" de "a USP
    devolveu lixo", que têm curas diferentes para quem opera.
    """
    ToolError = pytest.importorskip("mcp.server.mcpserver.exceptions").ToolError
    UnexpectedToolError = pytest.importorskip(
        "mcp.server.mcpserver.exceptions"
    ).UnexpectedToolError

    alvo = ErroRucard("mensagem do domínio que o modelo precisa ler")

    def _recusa(nome, argumentos, **kwargs):
        raise alvo

    monkeypatch.setattr(server, "chamar_ferramenta", _recusa)

    with pytest.raises(ToolError) as capturado:
        asyncio.run(servidor_montado.call_tool("bandejao", {"dia": "hoje"}))

    assert not isinstance(capturado.value, UnexpectedToolError), (
        "o SDK classificou como crash: a fronteira não traduziu o ErroRucard"
    )
    # O SDK reembrulha o nosso `ToolError` com o prefixo do nome da ferramenta,
    # então o nosso é o `__cause__` do que sai — e o `ErroRucard` original é o
    # `__cause__` do nosso.
    nosso = capturado.value.__cause__
    assert isinstance(nosso, ToolError), f"a causa foi {nosso!r}"
    assert str(nosso) == str(alvo)
    assert nosso.__cause__ is alvo, "a exceção do domínio não ficou na corrente"
