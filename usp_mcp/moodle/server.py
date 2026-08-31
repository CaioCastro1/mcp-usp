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

from ..env import carregar_env
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

    # O `.env` é a única casa do token (§8, gitignorado) — decisão de
    # 31/08/2026. `carregar_env` usa `setdefault`, então o bloco `env` de um
    # cliente MCP, se existir, ganha do arquivo. Chamado aqui e não no import
    # do módulo para que importar `server` continue sendo livre de efeito
    # colateral (é o que os testes de contrato fazem).
    carregar_env()

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


def main() -> None:  # pragma: no cover — casca stdio; ver nota abaixo.
    """Adaptador stdio real. Import do SDK fica AQUI dentro, não no topo do
    módulo: os testes de contrato importam `usp_mcp.moodle.server` sem o SDK
    do MCP instalado, e um import de topo quebraria a coleta inteira da
    suíte por causa de uma dependência que as funções puras nem chegam a usar.

    Sem teste automático de propósito — exercitar isto exigiria subir um
    processo stdio e um cliente MCP falso, o que testaria o SDK e não este
    projeto. O que dá para verificar sem rede está em `--auto-verificar`, e a
    verificação que importa é plugar num cliente de verdade e perguntar.
    """
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise SystemExit(
            "O SDK do MCP (pacote `mcp`) não está instalado. Rode "
            "`.venv/bin/python -m pip install -r requirements.txt`. As funções "
            "`listar_ferramentas` e `chamar_ferramenta` funcionam sem ele."
        ) from exc

    descritor = listar_ferramentas()[0]
    servidor = MCPServer(name="usp-mcp-moodle", version="0.1.0")

    @servidor.tool(name=descritor["name"], description=descritor["description"])
    def _o_que_vence(dias: int = 14, limite: int | None = None) -> str:
        # Assinatura explícita em vez de `**kwargs`: o SDK deriva o schema que
        # o modelo vê a partir dela, e um `**kwargs` produziria uma ferramenta
        # sem parâmetro nenhum. Mantida em sincronia com o `inputSchema` de
        # `listar_ferramentas` — `_auto_verificar` compara os dois.
        return chamar_ferramenta(descritor["name"], {"dias": dias, "limite": limite})

    servidor.run(transport="stdio")


def _auto_verificar() -> int:  # pragma: no cover — utilitário de linha de comando
    """`python -m usp_mcp.moodle.server --auto-verificar`: o que dá para
    checar sem tocar a rede da USP nem gastar uma chamada da conta.

    Existe porque `main()` não tem teste: sem isto, a única forma de saber que
    o adaptador casa com o SDK instalado seria plugar num cliente e ver
    falhar. Não substitui essa verificação — reduz o que ela precisa descobrir.
    """
    from .. import env as _env

    print("ferramentas expostas :", [f["name"] for f in listar_ferramentas()])

    arquivo = _env.achar_env()
    print(".env encontrado      :", arquivo or "NÃO — copie .env.example (§8)")
    _env.carregar_env()
    # Forma, nunca valor (Invariante 3).
    token = os.environ.get("MOODLE_TOKEN") or ""
    print(
        "MOODLE_TOKEN         :",
        f"presente, {len(token)} chars" if token else "AUSENTE",
    )
    print("MOODLE_URL           :", os.environ.get("MOODLE_URL", _URL_PADRAO))

    try:
        from mcp.server import MCPServer  # noqa: F401
    except ImportError:
        print("SDK do MCP           : AUSENTE — pip install -r requirements.txt")
        return 1
    print("SDK do MCP           : presente")

    # O schema que o modelo vê tem de casar com a assinatura que o adaptador
    # registra; divergir aqui é o erro que só apareceria em uso real.
    declarados = set(listar_ferramentas()[0]["inputSchema"]["properties"])
    import inspect

    from mcp.server import MCPServer as _M

    servidor = _M(name="verificacao", version="0.0.0")

    @servidor.tool(name="o_que_vence", description="verificação")
    def _sonda(dias: int = 14, limite: int | None = None) -> str:
        return ""

    reais = set(inspect.signature(_sonda).parameters)
    print("schema x assinatura  :", "OK" if declarados == reais else f"DIVERGEM {declarados ^ reais}")
    if declarados != reais:
        return 1

    print()
    print("Nada acima tocou a rede da USP. O que falta é plugar num cliente")
    print("MCP e perguntar — só isso exercita chamar_ferramenta de verdade.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    if "--auto-verificar" in sys.argv:
        raise SystemExit(_auto_verificar())
    main()
