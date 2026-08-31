"""Fronteira MCP do Moodle. Entrypoint local stdio (§6 do SPEC1).

Este pacote não tem servidor na raiz de propósito: o servidor público
(RUCard/Jupiter) é outro processo, sem credencial pessoal. Este módulo é o
entrypoint LOCAL — dado autenticado do dono nunca sai desta máquina
(Invariante 4). É por isso que ele fala stdio, não HTTP hospedado.

A suíte (`tests/moodle/test_server_mcp.py`) tem só 3 testes de propósito: o
valor real está na projeção (`projecao.py`) e na política (`politica.py`),
que não têm nada a ver com protocolo MCP. Esta camada expõe duas funções
puras — `listar_ferramentas` e `chamar_ferramenta` — que qualquer adaptador
de protocolo pode chamar sem precisar do SDK instalado; `main()` é a casca
stdio por cima, e só ela importa o SDK (import de topo quebraria a suíte,
que roda sem o SDK presente).
"""
from __future__ import annotations

import os

from .cliente import ClienteMoodle
from .erros import ErroMoodle
from .o_que_vence import o_que_vence

# URL default: mesma do §8 do SPEC1 e de scripts/ws.sh. MOODLE_URL sobrescreve
# para quem precisa apontar para outro ambiente (não há esse caso hoje, mas
# não custa não fixar o valor).
_URL_PADRAO = "https://edisciplinas.usp.br"

# Nome da única ferramenta exposta (§5: fatia vertical, crescer é decisão de
# §9). O nome vem da pergunta do dono, não da função do Moodle por trás dela.
_NOME_FERRAMENTA = "o_que_vence"


def listar_ferramentas() -> list[dict]:
    """Descreve a ferramenta como o MODELO a vê: nome, descrição, parâmetros.

    A descrição usa o vocabulário de quem pergunta ("entrega", "prazo",
    "vence"), não o nome da função do Moodle por trás (T43) — é isso que faz
    o modelo escolher a ferramenta certa diante de uma pergunta em português.
    """
    return [
        {
            "name": _NOME_FERRAMENTA,
            "description": (
                "Lista o que tem prazo de entrega em breve nas disciplinas do "
                "e-Disciplinas (Moodle da USP): tarefas e questionários que "
                "vencem dentro de uma janela de dias a partir de agora. Use "
                "para responder perguntas como 'o que eu tenho para entregar', "
                "'o que vence essa semana' ou 'tem alguma tarefa vencendo'."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dias": {
                        "type": "integer",
                        "description": (
                            "Tamanho da janela, em dias, a partir de agora. "
                            "Padrão 14."
                        ),
                        "default": 14,
                    },
                    "limite": {
                        "type": "integer",
                        "description": (
                            "Número máximo de vencimentos no texto de saída. "
                            "Sem padrão: se omitido, todos os vencimentos "
                            "encontrados na janela entram na resposta."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        }
    ]


def chamar_ferramenta(nome: str, argumentos: dict) -> str:
    """Despacha para a ferramenta pedida pelo nome, ou levanta erro legível.

    Nome desconhecido é a fronteira do Invariante 6 (T44): não devolve lista
    vazia nem `None` silencioso — levanta `ErroMoodle` citando o nome pedido,
    porque "ferramenta não existe" e "ferramenta existe mas não achou nada"
    têm curas diferentes para quem lê o erro.
    """
    if nome != _NOME_FERRAMENTA:
        raise ErroMoodle(
            f"Ferramenta desconhecida: {nome!r}. A única ferramenta exposta "
            f"por este servidor é {_NOME_FERRAMENTA!r}."
        )

    # Credencial só é lida aqui, na hora de montar o cliente — nunca logada
    # nem exposta (Invariante 3). Este caminho não é exercitado por teste
    # offline (T44 só cobre o nome desconhecido); ele fala com a rede da USP,
    # que o sandbox não alcança (§1.1).
    cliente = ClienteMoodle(
        token=os.environ.get("MOODLE_TOKEN", ""),
        url=os.environ.get("MOODLE_URL", _URL_PADRAO),
    )

    resposta = o_que_vence(
        cliente,
        dias=argumentos.get("dias", 14),
        limite=argumentos.get("limite"),
    )
    return resposta.texto


def main() -> None:  # pragma: no cover — casca stdio, sem teste offline.
    """Adaptador stdio real. Import do SDK fica AQUI dentro, não no topo do
    módulo: os testes de contrato importam `usp_mcp.moodle.server` sem o SDK
    do MCP instalado, e um import de topo quebraria a coleta inteira da
    suíte por causa de uma dependência que este entrypoint nem chegou a usar.
    """
    try:
        import mcp.server.stdio
        from mcp.server import Server
        from mcp.types import TextContent, Tool
    except ImportError as exc:
        raise SystemExit(
            "O SDK do MCP (pacote `mcp`) não está instalado. Instale-o para "
            "rodar este entrypoint stdio; as funções `listar_ferramentas` e "
            "`chamar_ferramenta` funcionam sem ele."
        ) from exc

    servidor = Server("usp-mcp-moodle")

    @servidor.list_tools()
    async def _listar() -> list[Tool]:
        return [Tool(**f) for f in listar_ferramentas()]

    @servidor.call_tool()
    async def _chamar(nome: str, argumentos: dict) -> list[TextContent]:
        texto = chamar_ferramenta(nome, argumentos or {})
        return [TextContent(type="text", text=texto)]

    async def _rodar() -> None:
        async with mcp.server.stdio.stdio_server() as (leitura, escrita):
            await servidor.run(leitura, escrita, servidor.create_initialization_options())

    import asyncio

    asyncio.run(_rodar())


if __name__ == "__main__":  # pragma: no cover
    main()
