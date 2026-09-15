"""A1-A8: a promessa de read-only chega ao cliente como CAMPO, não como prosa.

O Invariante 1 diz que este projeto é de leitura por padrão. Até aqui isso
estava escrito em português no `CLAUDE.md`, na descrição de cada ferramenta e na
cabeça de quem manteve o código — e um cliente MCP não lê nada disso. O
protocolo tem bloco próprio para a mesma frase (`readOnlyHint`,
`destructiveHint`, `idempotentHint`, `openWorldHint`), e é por ele que o cliente
decide o que chama sozinho e o que para para perguntar.

Três decisões de desenho, nenhuma é estilo:

**Pelo `tools/list` real, não por introspecção do módulo.** O que importa é o
que CHEGA ao cliente. Já custou caro neste repositório acreditar no declarado:
o SDK deriva o schema da assinatura e não do `inputSchema`, e por isso nenhuma
descrição de parâmetro viajava enquanto a suíte inteira estava verde. Anotação
registrada em `listar_ferramentas()` e esquecida no `servidor.tool()` de
`main()` teria exatamente essa cara. A6 é quem compara as duas fontes.

**Por descoberta, nunca por lista escrita à mão.** Os servidores saem do mesmo
glob de `tests/handshake/conftest.py`, e as ferramentas saem do que cada um
anuncia. Um quarto servidor, ou uma décima quarta ferramenta, entra coberto no
dia em que nascer — e entra REPROVANDO se nascer sem anotação, que é o ponto.

**A varredura é função pura, para A8 poder sabotá-la.** Sem isso, um extrator
quebrado deixaria A1-A5 verdes sem ter olhado ferramenta nenhuma: é o mesmo
falso-verde que o U3 e o F7 existem para impedir.

Offline e sem credencial: `initialize` e `tools/list` são respondidos sem passar
por `chamar_ferramenta`, como no resto da camada de handshake.
"""
from __future__ import annotations

import importlib

import pytest

from tests.handshake.conftest import (
    MOTIVO_SEM_SDK,
    ClienteStdio,
    _tem_sdk,
    descobrir_servidores,
)

pytestmark = pytest.mark.handshake


# --------------------------------------------------------------- a varredura
#
# Funções puras sobre a lista que o `tools/list` devolve. Separadas dos testes
# de propósito: é isto que A8 alimenta com um caso fabricado para provar que a
# varredura enxerga o defeito que ela existe para achar.


def _bloco(ferramenta: dict) -> dict:
    """As anotações desta ferramenta, ou dicionário vazio se não vieram.

    O SDK omite a chave inteira quando a ferramenta foi registrada sem
    anotação — não manda `{}` nem `null`. "Sem bloco" e "bloco vazio" são o
    mesmo defeito para quem lê, e aqui os dois caem no mesmo lugar.
    """
    return ferramenta.get("annotations") or {}


def sem_anotacao(ferramentas: list[dict]) -> list[str]:
    """Nomes das ferramentas que chegam ao cliente sem bloco de anotações."""
    return [f["name"] for f in ferramentas if not _bloco(f)]


def sem_read_only(ferramentas: list[dict]) -> list[str]:
    """Nomes das que não declaram `readOnlyHint` como booleano.

    Booleano, e não "tem a chave": `None` ou string no campo é ausência com
    outra cara, e o protocolo não tem terceiro valor para este campo.
    """
    return [
        f["name"]
        for f in ferramentas
        if not isinstance(_bloco(f).get("readOnlyHint"), bool)
    ]


def destrutivas(ferramentas: list[dict]) -> list[str]:
    """Nomes das que se declaram destrutivas."""
    return [f["name"] for f in ferramentas if _bloco(f).get("destructiveHint") is True]


def sem_mundo_aberto(ferramentas: list[dict]) -> list[str]:
    """Nomes das que não declaram `openWorldHint` como booleano."""
    return [
        f["name"]
        for f in ferramentas
        if not isinstance(_bloco(f).get("openWorldHint"), bool)
    ]


def escrevem(ferramentas: list[dict]) -> list[dict]:
    """As ferramentas que se declaram NÃO read-only, inteiras."""
    return [f for f in ferramentas if _bloco(f).get("readOnlyHint") is False]


def sem_justificar_a_escrita(ferramentas: list[dict]) -> list[str]:
    """Nomes das que escrevem e não dizem o quanto a escrita é inofensiva.

    Quem declara `readOnlyHint` falso passa a dever os dois campos que só têm
    significado nesse caso: `destructiveHint` (o default do protocolo é
    verdadeiro, então o silêncio aqui é a acusação mais pesada possível) e
    `idempotentHint` (que é o que separa "enche cache" de "faz de novo toda vez").
    """
    faltando = []
    for ferramenta in escrevem(ferramentas):
        bloco = _bloco(ferramenta)
        if not isinstance(bloco.get("destructiveHint"), bool) or not isinstance(
            bloco.get("idempotentHint"), bool
        ):
            faltando.append(ferramenta["name"])
    return faltando


# ----------------------------------------------------------------- a colheita


@pytest.fixture(scope="session")
def anunciadas():
    """`{modulo: [ferramenta, ...]}` do `tools/list` de CADA servidor descoberto.

    Um processo por servidor, uma vez para a sessão inteira, pelo mesmo motivo
    medido no `servidor_vivo`: subir interpretador com SDK custa segundos, e o
    que precisa ser real é o processo, não o número de subidas.

    A falha de subida é guardada e devolvida junto, nunca levantada aqui: uma
    fixture que levanta transforma `FAILED` em `ERROR` de setup, e "o servidor
    não sobe" é o caso que mais importa desta suíte.
    """
    if not _tem_sdk():
        pytest.skip(MOTIVO_SEM_SDK)

    colhido: dict[str, list[dict]] = {}
    falhas: dict[str, str] = {}
    for modulo in descobrir_servidores():
        with ClienteStdio(modulo) as cliente:
            try:
                cliente.apertar_mao()
                colhido[modulo] = cliente.pedir("tools/list")["tools"]
            except Exception as exc:  # noqa: BLE001 — o diagnóstico vai ao teste
                falhas[modulo] = f"{modulo} não respondeu ao tools/list: {exc}"
    return colhido, falhas


def _colheita(anunciadas) -> dict[str, list[dict]]:
    """O colhido — e falha AQUI, num teste, se algum servidor não subiu."""
    colhido, falhas = anunciadas
    assert not falhas, "\n".join(falhas.values())
    return colhido


# ------------------------------------------------------------------ A1 a A8


def test_a1_toda_ferramenta_anunciada_traz_bloco_de_anotacoes(anunciadas):
    mudas = {
        modulo: sem_anotacao(ferramentas)
        for modulo, ferramentas in _colheita(anunciadas).items()
        if sem_anotacao(ferramentas)
    }
    assert not mudas, (
        f"ferramenta sem anotação nenhuma no fio: {mudas}. Declare as anotações "
        "no descritor de `listar_ferramentas()` (use `SO_LEITURA` de "
        "`usp_mcp/anotacoes.py`, ou escreva um bloco novo lá com a razão ao "
        "lado) e passe `annotations=anotacoes.para_o_sdk(descritor)` no "
        "`servidor.tool()` correspondente em `main()`."
    )


def test_a2_toda_ferramenta_declara_read_only_hint(anunciadas):
    # O campo do item: é ele que diz ao cliente que chamar isto não muda nada.
    calados = {
        modulo: sem_read_only(ferramentas)
        for modulo, ferramentas in _colheita(anunciadas).items()
        if sem_read_only(ferramentas)
    }
    assert not calados, (
        f"ferramenta sem `readOnlyHint` booleano no fio: {calados}. Toda "
        "ferramenta deste projeto tem de responder essa pergunta por escrito: "
        "verdadeiro se ela não modifica nada, falso se ela modifica — inclusive "
        "se o que ela modifica é só o disco de quem chama. Omitir não é "
        "neutro: o cliente assume o pior."
    )


def test_a3_nenhuma_ferramenta_se_declara_destrutiva(anunciadas):
    # Nenhuma das treze escreve no e-Disciplinas: a allowlist tem cinco funções
    # de leitura e a lista de bloqueio permanente não é aberta por flag nenhuma.
    # Este teste é o alarme para o dia em que isso deixar de ser verdade.
    achadas = {
        modulo: destrutivas(ferramentas)
        for modulo, ferramentas in _colheita(anunciadas).items()
        if destrutivas(ferramentas)
    }
    assert not achadas, (
        f"ferramenta com `destructiveHint` verdadeiro: {achadas}. Nenhuma "
        "ferramenta daqui escreve no Moodle hoje. Se alguma passou a escrever, "
        "esta linha não é o lugar de resolver: a escrita só existe atrás de "
        "`USP_MCP_ALLOW_WRITES=1` e a decisão precisa estar registrada antes."
    )


def test_a4_toda_ferramenta_declara_open_world_hint(anunciadas):
    # As treze fazem requisição a um sistema que não é deste repositório, e o
    # que existe do outro lado (disciplina, arquivo, cardápio) não está
    # enumerado em lugar nenhum daqui. O default do protocolo já é verdadeiro;
    # declarar é o que separa "olhamos e é aberto" de "ninguém olhou".
    calados = {
        modulo: sem_mundo_aberto(ferramentas)
        for modulo, ferramentas in _colheita(anunciadas).items()
        if sem_mundo_aberto(ferramentas)
    }
    assert not calados, (
        f"ferramenta sem `openWorldHint` booleano no fio: {calados}. Se ela "
        "fala com a USP, o valor é verdadeiro. Se ela passou a responder de "
        "cache local sem tocar a rede, é falso — e aí o interessante é a "
        "mudança, que merece estar escrita ao lado do campo."
    )


def test_a5_quem_escreve_diz_o_quanto_a_escrita_e_inofensiva(anunciadas):
    devendo = {
        modulo: sem_justificar_a_escrita(ferramentas)
        for modulo, ferramentas in _colheita(anunciadas).items()
        if sem_justificar_a_escrita(ferramentas)
    }
    assert not devendo, (
        f"ferramenta com `readOnlyHint` falso e sem os campos que qualificam "
        f"essa escrita: {devendo}. Quem declara que modifica alguma coisa deve "
        "`destructiveHint` (o default do protocolo é verdadeiro — calar é se "
        "acusar do pior) e `idempotentHint` (é ele que separa encher um cache "
        "de repetir o efeito a cada chamada). Os dois booleanos, e a razão de "
        "cada um escrita ao lado em `usp_mcp/anotacoes.py`."
    )


def test_a6_as_anotacoes_no_fio_sao_as_declaradas(anunciadas):
    # Duas fontes escritas em lugares diferentes — o descritor de
    # `listar_ferramentas()` e a chamada de `servidor.tool()` em `main()` — e
    # nada além deste teste as obriga a concordar. É o mesmo furo do H5 e, com
    # um campo novo, o furo volta: registrar dez ferramentas e esquecer o
    # `annotations=` de uma delas passaria por todos os testes acima menos A1.
    for modulo, ferramentas in _colheita(anunciadas).items():
        declaradas = {
            f["name"]: f.get("annotations")
            for f in importlib.import_module(modulo).listar_ferramentas()
        }
        for ferramenta in ferramentas:
            nome = ferramenta["name"]
            assert _bloco(ferramenta) == (declaradas[nome] or {}), (
                f"{modulo}: as anotações de {nome!r} no fio são "
                f"{_bloco(ferramenta)} e as declaradas são {declaradas[nome]}. "
                "Quem registra em `main()` tem de passar o bloco do descritor, "
                "não um bloco próprio — senão a razão escrita ao lado do "
                "descritor passa a explicar um campo que ninguém recebe."
            )


def test_a7_a_varredura_nao_pode_vir_vazia(anunciadas):
    # Sem isto, um glob que deixe de casar ou um `tools/list` que volte vazio
    # transformam A1-A6 em seis testes verdes que não olharam ferramenta
    # nenhuma. Mesmo raciocínio do H9 e do U2.
    colhido = _colheita(anunciadas)
    assert colhido, (
        "nenhum servidor colhido. A descoberta vem do glob `usp_mcp/*/server.py`: "
        "se a estrutura do pacote mudou, esta suíte parou de cobrir alguma coisa."
    )

    for modulo, ferramentas in colhido.items():
        assert ferramentas, f"{modulo} anunciou zero ferramenta no tools/list"

    total_no_fio = sum(len(f) for f in colhido.values())
    total_declarado = sum(
        len(importlib.import_module(m).listar_ferramentas()) for m in colhido
    )
    assert total_no_fio == total_declarado, (
        f"{total_no_fio} ferramentas no fio e {total_declarado} declaradas. "
        "Ferramenta declarada e não anunciada é ferramenta que nenhum cliente "
        "vê — e este teste conta os dois lados justamente porque contar só um "
        "deixaria o número bater com a lista errada."
    )


def test_a8_a_varredura_acharia_uma_ferramenta_sem_anotacao():
    """A8 — sabotagem controlada da própria varredura.

    Cada função de varredura recebe um caso fabricado com UM defeito e tem de
    apontar exatamente a ferramenta defeituosa. Sem isto, um `_bloco` quebrado
    (um `.get` no nome errado, por exemplo) deixaria A1-A5 verdes exatamente no
    caso que eles foram escritos para pegar.
    """
    boa = {
        "name": "boa",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "openWorldHint": True,
        },
    }
    muda = {"name": "muda"}  # registrada sem `annotations` — o SDK omite a chave
    vazia = {"name": "vazia", "annotations": {}}
    sem_o_campo = {"name": "sem_o_campo", "annotations": {"openWorldHint": True}}
    destrutiva = {
        "name": "destrutiva",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    }
    escreve_e_cala = {
        "name": "escreve_e_cala",
        "annotations": {"readOnlyHint": False, "openWorldHint": True},
    }
    escreve_e_explica = {
        "name": "escreve_e_explica",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    }
    sem_mundo = {"name": "sem_mundo", "annotations": {"readOnlyHint": True}}

    amostra = [
        boa,
        muda,
        vazia,
        sem_o_campo,
        destrutiva,
        escreve_e_cala,
        escreve_e_explica,
        sem_mundo,
    ]

    assert sem_anotacao(amostra) == ["muda", "vazia"], (
        "a varredura não separou quem chega sem bloco de anotações — e bloco "
        "vazio é o mesmo defeito que bloco ausente."
    )
    assert sem_read_only(amostra) == ["muda", "vazia", "sem_o_campo"], (
        "a varredura não achou quem omite `readOnlyHint`"
    )
    assert destrutivas(amostra) == ["destrutiva"], (
        "a varredura não isolou quem se declara destrutiva — e não pode acusar "
        "quem declara `destructiveHint` falso"
    )
    assert sem_mundo_aberto(amostra) == ["muda", "vazia", "sem_mundo"], (
        "a varredura não achou quem omite `openWorldHint`"
    )
    assert [f["name"] for f in escrevem(amostra)] == [
        "destrutiva",
        "escreve_e_cala",
        "escreve_e_explica",
    ], "a varredura não separou quem declara que escreve"
    assert sem_justificar_a_escrita(amostra) == ["escreve_e_cala"], (
        "a varredura não achou quem escreve sem qualificar a escrita, ou "
        "acusou quem qualificou"
    )

    # E o contrário, que é a metade que costuma faltar: sobre uma lista sã,
    # toda varredura tem de ficar calada. Uma função que acusa sempre passaria
    # por todas as asserções acima e reprovaria A1-A5 para sempre.
    sa = [boa, escreve_e_explica]
    assert sem_anotacao(sa) == []
    assert sem_read_only(sa) == []
    assert destrutivas(sa) == []
    assert sem_mundo_aberto(sa) == []
    assert sem_justificar_a_escrita(sa) == []
