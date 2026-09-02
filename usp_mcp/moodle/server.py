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
from .arquivo import baixar_arquivo
from .cliente import ClienteMoodle
from .erros import ErroMoodle
from .material import material
from .o_que_vence import o_que_vence

# URL default: mesma do §8 do SPEC1 e de scripts/ws.sh. MOODLE_URL sobrescreve
# para quem precisa apontar para outro ambiente (não há esse caso hoje, mas
# não custa não fixar o valor).
_URL_PADRAO = "https://edisciplinas.usp.br"

# Três ferramentas (§5: crescer é decisão de §9 — a segunda entrou em 31/08, a
# terceira em 01/09). Os nomes vêm das perguntas do dono, não das funções do
# Moodle por trás.
_NOME_FERRAMENTA = "o_que_vence"
_NOME_MATERIAL = "material"
_NOME_ARQUIVO = "baixar_arquivo"


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
        },
        {
            "name": _NOME_MATERIAL,
            "description": (
                "Lista os arquivos publicados no espaço de uma disciplina no "
                "e-Disciplinas (Moodle da USP): PDFs de regras e programação da "
                "matéria, listas de exercícios, roteiros, apostilas, provas de "
                "semestres anteriores, além dos links externos que o professor "
                "postou. Use para 'que arquivos tem em PSI3323', 'cadê as regras "
                "da disciplina', 'tem prova antiga em PTC3314', 'onde está a "
                "lista de exercícios'. NÃO devolve o link de download do arquivo "
                "interno, porque baixá-lo exigiria a credencial do usuário — "
                "diz o nome e onde está, e a pessoa abre pelo e-Disciplinas."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "disciplina": {
                        "type": "string",
                        "description": (
                            "Sigla da disciplina como no e-Disciplinas, por "
                            "exemplo PSI3323 ou PTC3314. Espaço e caixa não "
                            "importam. Casa também com pedaço do nome."
                        ),
                    },
                    "busca": {
                        "type": "string",
                        "description": (
                            "Filtra por pedaço do nome do arquivo — 'prova', "
                            "'lista', 'regras'. Opcional: sem ele vem tudo, e "
                            "a saída diz quantos itens ficaram de fora quando "
                            "o filtro é usado."
                        ),
                    },
                },
                "required": ["disciplina"],
                "additionalProperties": False,
            },
        },
        {
            "name": _NOME_ARQUIVO,
            "description": (
                "Baixa um arquivo publicado no espaço da disciplina no "
                "e-Disciplinas (Moodle da USP) e devolve o CAMINHO dele no disco "
                "desta máquina, para que você mesmo o abra com a sua ferramenta "
                "de leitura de arquivos. Use para 'me dá a lista 2 de PSI3323', "
                "'abre a apostila de amp op', 'pega a prova anterior'. Para saber "
                "que arquivos existem antes de escolher, use `material`."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "disciplina": {
                        "type": "string",
                        "description": (
                            "Sigla da disciplina como no e-Disciplinas, por "
                            "exemplo PSI3323. Espaço e caixa não importam. Casa "
                            "também com pedaço do nome."
                        ),
                    },
                    "nome": {
                        "type": "string",
                        "description": (
                            "Pedaço do nome do arquivo, como aparece em "
                            "`material` — 'lista 2', 'apostila', 'regras'. "
                            "Acento e caixa não importam. Se casar com mais de "
                            "um, a resposta lista os candidatos em vez de "
                            "escolher por você."
                        ),
                    },
                    "todos": {
                        "type": "boolean",
                        "description": (
                            "Baixa TODOS os arquivos que casarem, em vez de "
                            "recusar a ambiguidade. Padrão falso. Há teto por "
                            "chamada, e o que ficar de fora é nomeado na saída."
                        ),
                    },
                },
                "required": ["disciplina", "nome"],
                "additionalProperties": False,
            },
        },
    ]


def chamar_ferramenta(nome: str, argumentos: dict, *, cliente=None) -> str:
    """Despacha para a ferramenta pedida pelo nome, ou levanta erro legível.

    Nome desconhecido é a fronteira do Invariante 6 (T44): não devolve lista
    vazia nem `None` silencioso — levanta `ErroMoodle` citando o nome pedido,
    porque "ferramenta não existe" e "ferramenta existe mas não achou nada"
    têm curas diferentes para quem lê o erro.
    """
    if nome not in (_NOME_FERRAMENTA, _NOME_MATERIAL, _NOME_ARQUIVO):
        raise ErroMoodle(
            f"Ferramenta desconhecida: {nome!r}. As ferramentas expostas por "
            f"este servidor são {_NOME_FERRAMENTA!r}, {_NOME_MATERIAL!r} e "
            f"{_NOME_ARQUIVO!r}."
        )

    if cliente is None:
        # O `.env` é a única casa do token (§8, gitignorado) — decisão de
        # 31/08/2026. `carregar_env` usa `setdefault`, então o bloco `env` de um
        # cliente MCP, se existir, ganha do arquivo. Chamado aqui e não no import
        # do módulo para que importar `server` continue sendo livre de efeito
        # colateral (é o que os testes de contrato fazem).
        carregar_env()

        # Credencial só é lida aqui, na hora de montar o cliente — nunca logada
        # nem exposta (Invariante 3).
        cliente = ClienteMoodle(
            token=os.environ.get("MOODLE_TOKEN", ""),
            url=os.environ.get("MOODLE_URL", _URL_PADRAO),
        )

    if nome == _NOME_MATERIAL:
        return material(
            cliente,
            argumentos["disciplina"],
            busca=argumentos.get("busca"),
        ).texto

    if nome == _NOME_ARQUIVO:
        return baixar_arquivo(
            cliente,
            argumentos["disciplina"],
            argumentos["nome"],
            todos=bool(argumentos.get("todos")),
            raiz=argumentos.get("raiz"),
        ).texto

    return o_que_vence(
        cliente,
        dias=argumentos.get("dias", 14),
        limite=argumentos.get("limite"),
    ).texto


def main() -> None:  # pragma: no cover — casca stdio; ver nota abaixo.
    """Adaptador stdio real. Import do SDK fica AQUI dentro, não no topo do
    módulo: os testes de contrato importam `usp_mcp.moodle.server` sem o SDK
    do MCP instalado, e um import de topo quebraria a coleta inteira da
    suíte por causa de uma dependência que as funções puras nem chegam a usar.

    **Tem teste, por dois caminhos que não se substituem.** T78-T81
    (`tests/moodle/test_server_stdio.py`) rodam isto em processo, substituindo só
    `run()`, e alcançam o que o processo esconde: o dicionário montado para
    `chamar_ferramenta` e a mensagem de SDK ausente. `tests/handshake/` sobe o
    processo de verdade e compara o que sai NO FIO com o declarado — foi lá que
    apareceu o schema mais pobre que o `inputSchema`. Antes de 31/08/2026 esta
    docstring dizia "sem teste automático de propósito", com a justificativa de
    que exercitá-lo testaria o SDK; as duas metades estavam erradas, e foi este
    buraco que escondeu um `main()` falando a API antiga com a suíte 99/99 verde.
    """
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise SystemExit(
            "O SDK do MCP (pacote `mcp`) não está instalado. Rode "
            "`.venv/bin/python -m pip install -r requirements.txt`. As funções "
            "`listar_ferramentas` e `chamar_ferramenta` funcionam sem ele."
        ) from exc

    from usp_mcp.adaptador import anotar

    porta_vence, porta_material, porta_arquivo = listar_ferramentas()
    descritor = porta_vence
    servidor = MCPServer(name="usp-mcp-moodle", version="0.1.0")

    def _o_que_vence(dias=14, limite=None) -> str:
        # Assinatura explícita em vez de `**kwargs`: o SDK deriva o schema que
        # o modelo vê a partir dela, e um `**kwargs` produziria uma ferramenta
        # sem parâmetro nenhum. Mantida em sincronia com o `inputSchema` de
        # `listar_ferramentas` — `_auto_verificar` compara os dois.
        return chamar_ferramenta(descritor["name"], {"dias": dias, "limite": limite})

    # O SDK lê a ASSINATURA, não o inputSchema declarado (§9, 31/08/2026). Sem
    # isto, "Padrão 14" e a explicação de `limite` não chegam ao modelo.
    anotar(_o_que_vence, descritor["inputSchema"], {"dias": int, "limite": int | None})
    servidor.tool(name=descritor["name"], description=descritor["description"])(_o_que_vence)

    def _material(disciplina, busca=None) -> str:
        # `disciplina` SEM default de propósito: no SDK é a ausência de default
        # que torna o parâmetro obrigatório no fio, e o `inputSchema` a declara
        # em `required`. Com `=None` os dois divergiam e o modelo via uma
        # ferramenta que aceita ser chamada sem disciplina — H6 pegou.
        return chamar_ferramenta(
            porta_material["name"], {"disciplina": disciplina, "busca": busca}
        )

    # Mesmo motivo: sem `anotar`, "Espaço e caixa não importam" e a explicação de
    # `busca` não chegam ao modelo — ele veria só {"title": "Disciplina"}.
    anotar(_material, porta_material["inputSchema"], {"disciplina": str, "busca": str | None})
    servidor.tool(name=porta_material["name"], description=porta_material["description"])(_material)

    def _baixar_arquivo(disciplina, nome, todos=False) -> str:
        # `disciplina` e `nome` SEM default: no SDK é a ausência de default que
        # torna o parâmetro obrigatório no fio, e o `inputSchema` os declara em
        # `required`. Com `=None` os dois divergiriam — foi assim que H6 pegou
        # `material` em 31/08.
        return chamar_ferramenta(
            porta_arquivo["name"],
            {"disciplina": disciplina, "nome": nome, "todos": todos},
        )

    anotar(
        _baixar_arquivo,
        porta_arquivo["inputSchema"],
        {"disciplina": str, "nome": str, "todos": bool},
    )
    servidor.tool(
        name=porta_arquivo["name"], description=porta_arquivo["description"]
    )(_baixar_arquivo)

    servidor.run(transport="stdio")


def _auto_verificar() -> int:  # pragma: no cover — utilitário de linha de comando
    """`python -m usp_mcp.moodle.server --auto-verificar`: o que dá para
    checar sem tocar a rede da USP nem gastar uma chamada da conta.

    Nasceu porque `main()` não tinha teste. Desde 31/08/2026 tem
    (`tests/handshake/`), e isto continua útil por outro motivo: roda em um
    comando, imprime o diagnóstico de configuração (`.env`, token, SDK) que um
    teste não imprime, e responde "por que o servidor não sobe aqui" mais rápido
    do que uma suíte.
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
    # registra. Isto checava a PRIMEIRA ferramenta e imprimia "OK" como se
    # falasse pelas duas — meia checagem com cara de checagem inteira, que é o
    # Invariante 7 quebrado dentro da própria ferramenta de verificação.
    # Corrigido em 31/08; a cobertura de verdade está em T79.
    import inspect

    from mcp.server import MCPServer as _M

    servidor = _M(name="verificacao", version="0.0.0")

    @servidor.tool(name="o_que_vence", description="verificação")
    def _sonda_vence(dias: int = 14, limite: int | None = None) -> str:
        return ""

    @servidor.tool(name="material", description="verificação")
    def _sonda_material(disciplina: str, busca: str | None = None) -> str:
        return ""

    @servidor.tool(name="baixar_arquivo", description="verificação")
    def _sonda_arquivo(disciplina: str, nome: str, todos: bool = False) -> str:
        return ""

    sondas = {
        "o_que_vence": _sonda_vence,
        "material": _sonda_material,
        "baixar_arquivo": _sonda_arquivo,
    }
    divergiu = False
    for ferramenta in listar_ferramentas():
        nome = ferramenta["name"]
        declarados = set(ferramenta["inputSchema"]["properties"])
        sonda = sondas.get(nome)
        if sonda is None:
            print(f"schema x assinatura  : {nome}: SEM SONDA — acrescente uma aqui")
            divergiu = True
            continue
        reais = set(inspect.signature(sonda).parameters)
        estado = "OK" if declarados == reais else f"DIVERGEM {declarados ^ reais}"
        print(f"schema x assinatura  : {nome}: {estado}")
        divergiu = divergiu or declarados != reais
    if divergiu:
        return 1

    print()
    print("Nada acima tocou a rede da USP. A suíte já cobre a fronteira MCP")
    print("offline (T78-T81); o que falta é a rede — plugar e perguntar.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    if "--auto-verificar" in sys.argv:
        raise SystemExit(_auto_verificar())
    main()
