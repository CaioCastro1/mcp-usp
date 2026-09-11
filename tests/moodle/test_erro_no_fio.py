"""E1-E4: a mensagem de erro do Moodle chega ao MODELO, não só ao stderr.

Medido em 10/09/2026 contra o `mcp 2.2.0` instalado: `o_que_vence{}` sem token
devolvia ao modelo `Error executing tool o_que_vence` — 32 bytes. A mensagem
escrita para esse caso ("MOODLE_TOKEN ausente ou vazio — configure-o no .env
(ver .env.example) antes de usar o cliente.") ficava no stderr do servidor. É o
pior dos três casos: o erro é de CONFIGURAÇÃO, tem cura de uma linha, e a cura
era entregue a ninguém — o modelo só podia repetir a chamada.

A causa é do SDK. O `Tool.run` do 2.0.0 tinha um ramo só; o do 2.2.0 separa
`ToolError`/`ResourceError` (o texto viaja) de `except Exception` (crash, e "the
exception's own text stays on the server"). `ErroMoodle` herda de `Exception`,
então caía no ramo de crash — e `requirements.txt` declara `mcp>=2,<3`, então
toda instalação nova nascia muda.

**Por que `_handle_call_tool` e não `call_tool`.** A pública `call_tool()`
LEVANTA a exceção; quem a converte no `CallToolResult(is_error=True)` que viaja
no fio é `_handle_call_tool`, e é o texto DELE que o modelo lê. E4 é o único que
olha a exceção, porque é a corrente de causas que ele verifica.

Molde de T78-T81: `main()` roda em processo com só `run()` substituído. Offline,
sem rede e **sem credencial** — E1 exercita justamente a ausência dela, e o
valor do token não é lido nem impresso em lugar nenhum (Invariante 3).
"""
import asyncio

import pytest

from usp_mcp.moodle import server
from usp_mcp.moodle.erros import ErroMoodle


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
def sem_token(monkeypatch):
    """`MOODLE_TOKEN` vazio no ambiente, e vazio ele fica.

    `carregar_env` usa `setdefault`, então a chave já presente aqui vence o
    `.env` da máquina — sem isto o teste passaria ou falharia conforme quem o
    roda tenha token configurado, que é a pior espécie de teste.
    """
    monkeypatch.setenv("MOODLE_TOKEN", "")


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
def test_e1_erro_de_dominio_chega_com_a_mensagem(servidor_montado, sem_token):
    resultado = _no_fio(servidor_montado, "o_que_vence", {})

    assert resultado.is_error, "sem token não há resposta possível — tem de ser erro"
    texto = resultado.content[0].text
    assert "MOODLE_TOKEN ausente ou vazio" in texto, (
        f"o modelo recebeu {texto!r}. A mensagem escrita para este caso existe e "
        "ficou no stderr do servidor — Invariante 6 quebrado na fronteira MCP."
    )


@pytest.mark.contrato
def test_e2_a_mensagem_nao_e_a_generica_do_sdk(servidor_montado, sem_token):
    """A asserção que E1 sozinho não faz: o texto tem de CURAR, não só existir.

    Um erro de configuração cuja cura não viaja transforma o modelo em laço:
    ele repete a chamada, recebe os mesmos 32 bytes e não tem por onde sair. É a
    diferença entre "falhou" e "falhou, e aqui está o arquivo que resolve".
    """
    texto = _no_fio(servidor_montado, "o_que_vence", {}).content[0].text

    assert texto.strip() != "Error executing tool o_que_vence"
    assert len(texto) > 60, f"{len(texto)} caracteres: {texto!r}"
    assert ".env.example" in texto, "a cura (copiar o .env.example) não atravessou"


@pytest.mark.contrato
def test_e3_crash_de_verdade_continua_retido(servidor_montado, monkeypatch):
    """O outro lado da tradução, e a razão de ela não ser `except Exception`.

    Aqui o motivo tem nome próprio: o Moodle é o entrypoint com credencial
    pessoal (Invariante 4), e o texto de uma exceção imprevista deste processo é
    a última coisa que deve viajar por engano. O SDK reter o crash é o
    comportamento certo; o defeito era só `ErroMoodle` contar como crash.
    """
    def _crash(nome, argumentos, **kwargs):
        raise RuntimeError("segredo")

    monkeypatch.setattr(server, "chamar_ferramenta", _crash)

    resultado = _no_fio(servidor_montado, "o_que_vence", {})

    assert resultado.is_error
    assert "segredo" not in resultado.content[0].text, (
        "o texto de uma exceção NÃO prevista vazou para o modelo"
    )


@pytest.mark.contrato
def test_e4_a_traducao_nao_engole_a_classe(servidor_montado, monkeypatch):
    """A tradução é envelope, não substituição: `ErroMoodle` continua a moeda interna.

    Sem o `from exc`, o log do servidor perde qual das quatro subclasses falhou —
    e é ela que separa "token venceu" de "a USP caiu", que a docstring de
    `erros.py` registra como o motivo de as classes existirem.
    """
    excecoes = pytest.importorskip("mcp.server.mcpserver.exceptions")
    ToolError, UnexpectedToolError = excecoes.ToolError, excecoes.UnexpectedToolError

    alvo = ErroMoodle("mensagem do domínio que o modelo precisa ler")

    def _recusa(nome, argumentos, **kwargs):
        raise alvo

    monkeypatch.setattr(server, "chamar_ferramenta", _recusa)

    with pytest.raises(ToolError) as capturado:
        asyncio.run(servidor_montado.call_tool("o_que_vence", {}))

    assert not isinstance(capturado.value, UnexpectedToolError), (
        "o SDK classificou como crash: a fronteira não traduziu o ErroMoodle"
    )
    # O SDK reembrulha o nosso `ToolError` com o prefixo do nome da ferramenta,
    # então o nosso é o `__cause__` do que sai — e o `ErroMoodle` original é o
    # `__cause__` do nosso.
    nosso = capturado.value.__cause__
    assert isinstance(nosso, ToolError), f"a causa foi {nosso!r}"
    assert str(nosso) == str(alvo)
    assert nosso.__cause__ is alvo, "a exceção do domínio não ficou na corrente"
