"""Fronteira MCP do Jupiter (§6 do SPEC1).

O pacote não tem servidor na raiz de propósito: o do Moodle é o entrypoint
LOCAL, porque carrega credencial pessoal que não pode sair da máquina do dono
(Invariante 4). **Este não carrega credencial nenhuma** — o `ControlePublicoDWR`
é público e stateless — e é justamente por isso que o §6 o coloca como candidato
a servidor hospedado, com cache compartilhado. Hoje ele fala stdio porque é a
mesma canalização do cliente; a opção de hospedar continua aberta, e continua
aberta *porque* não há segredo para vazar.

A camada é fina de propósito. O valor está na política (`politica.py`), no
envelope (`dwr.py`) e na ferramenta (`ferramentas.py`) — nada disso tem a ver
com protocolo MCP. `listar_ferramentas` e `chamar_ferramenta` são funções puras
que qualquer adaptador chama sem o SDK instalado; `main()` é a casca stdio, e
só ela importa o SDK — import de topo quebraria a suíte, que roda sem ele.

Uma coisa esta fronteira consegue e a do Moodle não: **ser testada ponta a ponta
offline.** Sem credencial, basta injetar o transporte e a fixture responde.
"""
from __future__ import annotations

from .cliente import ClienteJupiter, transporte_http
from .erros import ErroJupiter
from .ferramentas import disciplina

_NOME_FERRAMENTA = "disciplina"


def listar_ferramentas() -> list[dict]:
    """Descreve a ferramenta como o MODELO a vê.

    A descrição usa o vocabulário de quem pergunta — "créditos", "ementa",
    "pré-requisito", a sigla que o aluno já sabe — e nunca o nome da consulta
    DWR por trás. É isso que faz o modelo escolher a ferramenta certa diante de
    uma pergunta em português.
    """
    return [
        {
            "name": _NOME_FERRAMENTA,
            "description": (
                "Consulta o catálogo público do JupiterWeb (USP): créditos, "
                "carga horária, ementa, objetivos, programa, bibliografia e "
                "critério de avaliação de uma disciplina, pela sigla. Se você "
                "informar o curso, traz também o pré-requisito — que depende do "
                "curso, não só da disciplina. Use para 'quantos créditos tem "
                "PTC3314', 'qual a ementa de MAT2454', 'o que preciso ter feito "
                "antes dessa matéria'. NÃO traz horário de aula, sala nem vagas."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sigla": {
                        "type": "string",
                        "description": (
                            "Sigla da disciplina, como aparece no JupiterWeb — "
                            "por exemplo PTC3314 ou MAT2454. Espaço e caixa não "
                            "importam."
                        ),
                    },
                    "codcur": {
                        "type": "string",
                        "description": (
                            "Código do curso, para o pré-requisito. Opcional: "
                            "sem ele a resposta diz que não consultou, em vez "
                            "de afirmar que não há pré-requisito."
                        ),
                    },
                    "codhab": {
                        "type": "string",
                        "description": "Código da habilitação. Padrão '0'.",
                    },
                    "ingles": {
                        "type": "boolean",
                        "description": (
                            "Inclui as versões em inglês dos textos. Padrão "
                            "falso: elas quase dobram o tamanho da resposta."
                        ),
                        "default": False,
                    },
                },
                "required": ["sigla"],
                "additionalProperties": False,
            },
        }
    ]


_ROTULOS = (
    ("ementa", "Ementa"),
    ("objetivos", "Objetivos"),
    ("programa", "Conteúdo programático"),
    ("bibliografia", "Bibliografia"),
    ("metodo_avaliacao", "Método de avaliação"),
    ("criterio_avaliacao", "Critério de avaliação"),
    ("norma_recuperacao", "Norma de recuperação"),
    ("nome_en", "Nome (inglês)"),
    ("ementa_en", "Ementa (inglês)"),
    ("objetivos_en", "Objetivos (inglês)"),
    ("programa_en", "Conteúdo programático (inglês)"),
)


def formatar(ficha: dict) -> str:
    """Texto para o modelo ler. Curto no topo, prosa depois.

    A carga horária aparece com a conta à vista de propósito: ela é calculada,
    não lida, e deixar isso explícito é o que impede alguém de "corrigir" para
    o campo `cgahoreto` — que vale zero.
    """
    linhas = [
        f"{ficha['sigla']} — {ficha['nome']}",
        f"Créditos: {ficha['creditos_aula']} aula + {ficha['creditos_trabalho']} "
        f"trabalho · Carga horária: {ficha['carga_horaria_total']} h "
        f"({ficha['creditos_aula']}×15 + {ficha['creditos_trabalho']}×30)",
        f"Tipo: {ficha['tipo']} · Ativação: {ficha['ativacao']}",
    ]

    requisitos = ficha.get("pre_requisito")
    if requisitos:
        itens = ", ".join(
            f"{r['sigla']} ({r['nome']})" for r in requisitos
        )
        linhas.append(f"Pré-requisito: {itens}")

    for campo, rotulo in _ROTULOS:
        if ficha.get(campo):
            linhas.append(f"\n{rotulo}:\n{ficha[campo]}")

    # Invariante 7: o que a ferramenta NÃO sabe vai junto, nunca por omissão.
    for aviso in ficha.get("avisos") or ():
        linhas.append(f"\n⚠ {aviso}")

    return "\n".join(linhas)


def chamar_ferramenta(nome: str, argumentos: dict, *, cliente=None) -> str:
    """Despacha para a ferramenta pedida, ou levanta erro legível.

    Nome desconhecido levanta `ErroJupiter` citando o nome pedido: "ferramenta
    não existe" e "ferramenta existe mas não achou nada" têm curas diferentes
    para quem lê o erro, e devolver vazio confundiria os dois (Invariante 6).

    `cliente` é injetável — sem credencial, a fronteira inteira roda offline
    contra fixture. É a diferença entre esta e a do Moodle.
    """
    if nome != _NOME_FERRAMENTA:
        raise ErroJupiter(
            f"Ferramenta desconhecida: {nome!r}. A única ferramenta exposta por "
            f"este servidor é {_NOME_FERRAMENTA!r}."
        )

    if cliente is None:
        # Nenhuma credencial é montada aqui, e não há env de segredo a ler:
        # o bean é público e stateless (§4.4 do recon, verificado).
        cliente = ClienteJupiter(transporte_http)

    codcur = argumentos.get("codcur")
    curso = (codcur, argumentos.get("codhab", "0")) if codcur else None
    idiomas = ("pt", "en") if argumentos.get("ingles") else ("pt",)

    return formatar(
        disciplina(argumentos["sigla"], curso, cliente=cliente, idiomas=idiomas)
    )


def main() -> None:
    """Adaptador stdio real. O import do SDK fica aqui dentro, não no topo: a
    suíte importa este módulo sem o SDK instalado, e um import de topo quebraria
    a coleta por causa de uma dependência que as funções puras nem usam.

    **Tem teste, por dois caminhos que não se substituem.** T45-T48
    (`tests/jupiter/test_server_stdio.py`) rodam isto em processo, substituindo
    só `run()`, e alcançam o que o processo esconde: o corpo enviado e a
    mensagem de SDK ausente. `tests/handshake/` sobe o processo de verdade e
    compara o que sai NO FIO com o que `listar_ferramentas()` declara — foi lá
    que apareceu o schema mais pobre que o declarado. Foi este buraco que, na
    trilha do Moodle, escondeu um `main()` falando a API antiga do SDK com a
    suíte inteira verde.
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

    descritor = listar_ferramentas()[0]
    servidor = MCPServer(name="usp-mcp-jupiter", version="0.1.0")

    def _disciplina(sigla, codcur=None, codhab="0", ingles=False) -> str:
        # Assinatura explícita em vez de **kwargs: o SDK deriva daqui o schema
        # que o modelo vê, e **kwargs produziria ferramenta sem parâmetro.
        return chamar_ferramenta(
            descritor["name"],
            {"sigla": sigla, "codcur": codcur, "codhab": codhab, "ingles": ingles},
        )

    # O SDK lê a ASSINATURA, não o inputSchema declarado (§9, 31/08/2026): sem
    # isto, o aviso de que sem `codcur` não há pré-requisito não chega ao modelo.
    anotar(
        _disciplina,
        descritor["inputSchema"],
        {"sigla": str, "codcur": str | None, "codhab": str, "ingles": bool},
    )
    servidor.tool(name=descritor["name"], description=descritor["description"])(_disciplina)

    servidor.run(transport="stdio")


def _auto_verificar() -> int:  # pragma: no cover — utilitário de linha de comando
    """`python -m usp_mcp.jupiter.server --auto-verificar`: o que dá para checar
    sem tocar a rede da USP."""
    print("ferramentas expostas :", [f["name"] for f in listar_ferramentas()])
    print("credencial exigida   : NENHUMA (bean público e stateless, §4.4 do recon)")

    try:
        from mcp.server import MCPServer as _M
    except ImportError:
        print("SDK do MCP           : AUSENTE — pip install -r requirements.txt")
        return 1
    print("SDK do MCP           : presente")

    import inspect

    declarados = set(listar_ferramentas()[0]["inputSchema"]["properties"])
    servidor = _M(name="verificacao", version="0.0.0")

    @servidor.tool(name="disciplina", description="verificação")
    def _sonda(sigla: str, codcur: str | None = None, codhab: str = "0",
               ingles: bool = False) -> str:
        return ""

    reais = set(inspect.signature(_sonda).parameters)
    print("schema x assinatura  :", "OK" if declarados == reais else f"DIVERGEM {declarados ^ reais}")
    return 0 if declarados == reais else 1


if __name__ == "__main__":  # pragma: no cover
    import sys

    if "--auto-verificar" in sys.argv:
        raise SystemExit(_auto_verificar())
    main()
