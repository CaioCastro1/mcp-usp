"""Fronteira MCP do RUCard (§6 do SPEC1).

O servidor mora dentro do subpacote, nunca na raiz: o §6 separa entrypoint local
com credencial pessoal (Moodle, stdio) de servidor público cacheável, e a
estrutura reflete isso em vez de deixar a separação só na prosa.

**Este é o mais hospedável dos três.** A hash do RUCard é compartilhada e
embutida no app oficial: ninguém manda credencial, o cache é compartilhável e o
dado é público. Hoje ele fala stdio porque é a mesma canalização dos outros
dois; a opção de hospedar continua aberta, e continua aberta *porque* não há
segredo para vazar (há teste de política que falha se isso mudar).

A camada é fina de propósito. O valor está na política, na projeção do catálogo
e na ferramenta. `listar_ferramentas` e `chamar_ferramenta` são funções puras que
qualquer adaptador chama sem o SDK instalado; `main()` é a casca stdio, e só ela
importa o SDK — import de topo quebraria a suíte, que roda sem ele.
"""
from __future__ import annotations

from .cliente import ClienteRucard, transporte_http
from .erros import ErroRucard
from .ferramentas import bandejao

_NOME_FERRAMENTA = "bandejao"

_ROTULO = {"cafe": "café da manhã", "almoco": "almoço", "jantar": "jantar"}


def listar_ferramentas() -> list[dict]:
    """Descreve a ferramenta como o MODELO a vê.

    A descrição usa o vocabulário de quem pergunta — "bandejão", "almoço",
    "hoje", "vegetariana" — e nunca o nome da rota por trás. É isso que faz o
    modelo escolher esta ferramenta diante de uma pergunta em português em vez
    de sair procurando na web.

    E ela diz o que NÃO faz (Invariante 7 aplicado à descrição): sem isso o
    modelo promete café da manhã, cardápio de semana passada e saldo do cartão,
    que são três coisas que esta API não dá.
    """
    return [
        {
            "name": _NOME_FERRAMENTA,
            "description": (
                "Cardápio dos bandejões da USP na Cidade Universitária — "
                "CENTRAL, PUSP-CB, FÍSICA e QUÍMICAS. Diz o que tem no almoço e "
                "no jantar de um dia, com calorias, preço de aluno, horário e a "
                "opção do dia (marcada como vegetariana quando o RU marca), nos "
                "quatro restaurantes de uma vez, para comparar onde vale a pena "
                "comer. Use para 'o que tem no bandejão hoje', 'vale a pena "
                "almoçar no Central?', 'que horas fecha o jantar', 'o das "
                "Químicas abre no sábado?'. LIMITES: só a semana corrente (não "
                "há cardápio de outra semana, nem passada nem futura); não há "
                "cardápio de café da manhã publicado, só o horário; e nada de "
                "saldo, extrato ou recarga do cartão."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dia": {
                        "type": "string",
                        "description": (
                            "'hoje', 'amanhã' ou uma data como 26/08/2026. "
                            "Somente a semana corrente tem cardápio."
                        ),
                        "default": "hoje",
                    },
                    "refeicao": {
                        "type": "string",
                        "enum": ["almoco", "jantar", "cafe", "todas"],
                        "description": (
                            "Qual refeição. 'todas' traz almoço e jantar. "
                            "'cafe' responde o horário e diz que o cardápio não "
                            "é publicado."
                        ),
                        "default": "todas",
                    },
                    "restaurantes": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["6", "7", "8", "9"]},
                        "description": (
                            "Ids dos restaurantes: 6 CENTRAL, 7 PUSP-CB, 8 "
                            "FÍSICA, 9 QUÍMICAS. Omita para comparar os quatro."
                        ),
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        }
    ]


def _linha_da_refeicao(nome_ru: str, qual: str, dados: dict) -> list[str]:
    rotulo = _ROTULO[qual]
    situacao = dados["situacao"]

    if situacao != "aberto":
        return [f"{nome_ru} · {rotulo}: {dados.get('detalhe') or situacao}"]

    cabecalho = [f"{nome_ru} · {rotulo}"]
    if dados.get("horario"):
        cabecalho.append(dados["horario"])
    if dados.get("preco_aluno"):
        cabecalho.append(f"R$ {dados['preco_aluno']} (aluno)")
    if dados.get("calorias"):
        cabecalho.append(f"{dados['calorias']} kcal")

    linhas = [" · ".join(cabecalho)]
    # Itens numa linha só, separados por ' · ': sete itens por refeição em
    # quatro RUs seriam 56 linhas, e o teto de custo (R37b) existe para impedir
    # que a formatação engorde sem ninguém ver.
    if dados.get("itens"):
        linhas.append("  " + " · ".join(dados["itens"]))
    if dados.get("opcao"):
        marca = " [marcada como vegetariana]" if dados.get("opcao_vegetariana_marcada") else ""
        linhas.append(f"  Opção: {dados['opcao']}{marca}")
    return linhas


def formatar(resposta: dict) -> str:
    """Texto para o modelo ler. Compacto, e com o que não se sabe no fim."""
    linhas = [f"Bandejão — {resposta['dia_semana']} {resposta['data']}"]

    for ru in resposta["restaurantes"]:
        for qual in resposta["refeicoes"]:
            dados = ru["refeicoes"].get(qual)
            if dados:
                linhas.extend(_linha_da_refeicao(ru["nome"], qual, dados))

    # Invariante 7: o que a ferramenta NÃO sabe vai junto, nunca por omissão.
    for aviso in resposta.get("avisos") or ():
        linhas.append(f"⚠ {aviso}")

    return "\n".join(linhas)


def chamar_ferramenta(nome: str, argumentos: dict, *, cliente=None) -> str:
    """Despacha para a ferramenta pedida, ou levanta erro legível.

    Nome desconhecido levanta `ErroRucard` citando o nome pedido: "ferramenta
    não existe" e "ferramenta existe mas não achou nada" têm curas diferentes
    para quem lê, e devolver vazio confundiria os dois (Invariante 6).

    `cliente` é injetável — e, como no Jupiter e diferente do Moodle, a
    fronteira inteira roda offline contra fixture, porque não falta credencial
    nenhuma para isso.
    """
    if nome != _NOME_FERRAMENTA:
        raise ErroRucard(
            f"Ferramenta desconhecida: {nome!r}. A única ferramenta exposta por "
            f"este servidor é {_NOME_FERRAMENTA!r} — ela responde cardápio, "
            "horário e preço, e não mexe em cartão nem em saldo."
        )

    if cliente is None:
        # Nenhuma credencial pessoal é montada aqui: a hash é pública e sai do
        # ambiente (§1.2), e o cliente falha legível se ela não estiver lá.
        cliente = ClienteRucard(transporte_http)

    return formatar(
        bandejao(
            dia=argumentos.get("dia", "hoje"),
            refeicao=argumentos.get("refeicao", "todas"),
            restaurantes=argumentos.get("restaurantes"),
            cliente=cliente,
        )
    )


def main() -> None:  # pragma: no cover — casca stdio
    """Adaptador stdio real. O import do SDK fica aqui dentro, não no topo: a
    suíte importa este módulo sem o SDK instalado, e um import de topo quebraria
    a coleta por causa de uma dependência que as funções puras nem usam.

    Coberto por `tests/handshake/` desde 31/08/2026: aquele teste sobe este
    processo, aperta a mão e compara o que sai no fio com o que
    `listar_ferramentas()` declara."""
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise SystemExit(
            "O SDK do MCP (pacote `mcp`) não está instalado. Rode "
            "`.venv/bin/python -m pip install -r requirements.txt`. As funções "
            "`listar_ferramentas` e `chamar_ferramenta` funcionam sem ele."
        ) from exc

    from usp_mcp.env import carregar_env

    # A hash vive no `.env` (§8), como no Moodle — com a diferença de que esta
    # não é credencial pessoal. Sem isto, o servidor sobe e falha na primeira
    # pergunta por uma variável que o arquivo tinha.
    carregar_env()

    from typing import Literal

    from usp_mcp.adaptador import anotar

    descritor = listar_ferramentas()[0]
    servidor = MCPServer(name="usp-mcp-rucard", version="0.1.0")

    def _bandejao(dia="hoje", refeicao="todas", restaurantes=None) -> str:
        # Assinatura explícita em vez de **kwargs: o SDK deriva daqui o schema
        # que o modelo vê, e **kwargs produziria ferramenta sem parâmetro.
        return chamar_ferramenta(
            descritor["name"],
            {"dia": dia, "refeicao": refeicao, "restaurantes": restaurantes},
        )

    # O SDK lê a ASSINATURA, não o inputSchema declarado (§9, 31/08/2026). Sem
    # isto, o `enum` que ensina que só existem quatro RUs não chega ao modelo, e
    # ele inventa id para receber negativa da allowlist depois — erro certo pela
    # via mais cara. Os Literal ficam à vista aqui; H8 é quem os mantém iguais
    # aos do schema declarado.
    anotar(
        _bandejao,
        descritor["inputSchema"],
        {
            "dia": str,
            "refeicao": Literal["almoco", "jantar", "cafe", "todas"],
            "restaurantes": list[Literal["6", "7", "8", "9"]] | None,
        },
    )
    servidor.tool(name=descritor["name"], description=descritor["description"])(_bandejao)

    servidor.run(transport="stdio")


def _auto_verificar() -> int:  # pragma: no cover — utilitário de linha de comando
    """`python -m usp_mcp.rucard.server --auto-verificar`: o que dá para checar
    sem tocar a rede da USP."""
    import os

    from usp_mcp.env import carregar_env

    print("ferramentas expostas :", [f["name"] for f in listar_ferramentas()])
    print("credencial pessoal   : NENHUMA (hash pública e compartilhada, §1.2)")

    carregar_env()
    print("RUCARD_HASH          :",
          "presente" if os.environ.get("RUCARD_HASH") else "AUSENTE — copie .env.example")

    try:
        from mcp.server import MCPServer as _M
    except ImportError:
        print("SDK do MCP           : AUSENTE — pip install -r requirements.txt")
        return 1
    print("SDK do MCP           : presente")

    import inspect

    declarados = set(listar_ferramentas()[0]["inputSchema"]["properties"])
    servidor = _M(name="verificacao", version="0.0.0")

    @servidor.tool(name="bandejao", description="verificação")
    def _sonda(dia: str = "hoje", refeicao: str = "todas",
               restaurantes: list[str] | None = None) -> str:
        return ""

    reais = set(inspect.signature(_sonda).parameters)
    print("schema x assinatura  :",
          "OK" if declarados == reais else f"DIVERGEM {declarados ^ reais}")
    return 0 if declarados == reais else 1


if __name__ == "__main__":  # pragma: no cover
    import sys

    if "--auto-verificar" in sys.argv:
        raise SystemExit(_auto_verificar())
    main()
