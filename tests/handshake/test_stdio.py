"""H1-H9: o adaptador stdio de cada servidor, exercitado de verdade.

Fecha o furo que o backlog registrou três vezes. O que cada teste protege:

- **H1-H3**: o processo sobe, aperta a mão e se identifica. É o que teria pegado
  o `main()` do Moodle escrito contra a API antiga do SDK, com a suíte 99/99 verde.
- **H4-H5**: o que o servidor anuncia é o que o código declara. Duas fontes que
  precisam concordar e que nada obrigava a concordar.
- **H6-H8**: o que o MODELO vê no fio carrega o que a declaração promete —
  descrição por parâmetro e `enum`. Este é o achado que motivou os testes existirem:
  o SDK deriva o schema da ASSINATURA da função, não do `inputSchema` declarado, e
  antes desta suíte nenhuma descrição de parâmetro e nenhum `enum` chegava ao modelo.
- **H9**: a suíte não pode passar verde sem ter encontrado servidor nenhum.

Nada aqui toca a rede da USP nem lê credencial: `initialize` e `tools/list` são
respondidos sem passar por `chamar_ferramenta`.
"""
from __future__ import annotations

import importlib

import pytest

from tests.handshake.conftest import (
    MOTIVO_SEM_SDK,
    _tem_sdk,
    descobrir_servidores,
    sistema_de,
)

pytestmark = pytest.mark.handshake


def _vivo(servidor_vivo):
    """`(modulo, cliente)` — e falha AQUI, num teste, se o servidor não subiu.

    A fixture guarda o diagnóstico em vez de levantar, para que "o servidor não
    sobe" apareça como `FAILED` legível e não como `ERROR` de setup (§4 do
    CONVENTIONS.md). É o caso que mais importa: foi assim que o `main()` do
    Moodle ficou quebrado com a suíte inteira verde.
    """
    modulo, cliente = servidor_vivo
    assert cliente.falha is None, cliente.falha
    return modulo, cliente


def _declarado(modulo: str) -> list[dict]:
    """O que o código declara, lido em processo — sem SDK, funções puras."""
    return importlib.import_module(modulo).listar_ferramentas()


def test_h1_o_servidor_sobe_e_responde_ao_initialize(servidor_vivo):
    servidor, cliente = _vivo(servidor_vivo)
    assert cliente.info.get("protocolVersion"), (
        "sem protocolVersion no initialize: o processo respondeu alguma coisa "
        "que não é um handshake MCP."
    )
    assert cliente.vivo(), f"{servidor} morreu depois do handshake"


def test_h2_o_nome_anunciado_segue_a_convencao_do_pacote(servidor_vivo):
    # Derivado do caminho do módulo, nunca de uma lista escrita à mão: um
    # servidor novo que se anuncie com outro nome é achado, não exceção.
    servidor, cliente = _vivo(servidor_vivo)
    esperado = f"usp-mcp-{sistema_de(servidor)}"
    info = cliente.info["serverInfo"]
    assert info["name"] == esperado, (
        f"{servidor} se anuncia como {info['name']!r}; a convenção dos três é "
        f"{esperado!r}, e é por esse nome que o cliente MCP o identifica."
    )
    assert info.get("version")


def test_h3_nada_de_ruido_no_stderr_durante_o_handshake(servidor_vivo):
    # stderr é o canal onde um servidor stdio quebra o cliente: qualquer coisa
    # impressa lá durante o handshake é sintoma (traceback, aviso de depreciação).
    servidor, cliente = _vivo(servidor_vivo)
    cliente.pedir("tools/list")
    barulho = cliente.stderr_disponivel()
    assert not barulho.strip(), f"{servidor} escreveu em stderr: {barulho!r}"


def test_h4_as_ferramentas_anunciadas_sao_as_declaradas(servidor_vivo):
    servidor, cliente = _vivo(servidor_vivo)
    declaradas = [f["name"] for f in _declarado(servidor)]
    anunciadas = [t["name"] for t in cliente.pedir("tools/list")["tools"]]

    assert sorted(anunciadas) == sorted(declaradas), (
        f"{servidor} anuncia {anunciadas} e declara {declaradas}. As duas listas "
        "são escritas em lugares diferentes e nada além deste teste as obriga a "
        "concordar."
    )


def test_h5_a_descricao_que_o_modelo_le_e_a_declarada(servidor_vivo):
    # A descrição é o que faz o modelo escolher a ferramenta certa. Se a
    # registrada no adaptador divergir da declarada, os testes de vocabulário
    # das três suítes passam a verificar um texto que ninguém lê.
    servidor, cliente = _vivo(servidor_vivo)
    declaradas = {f["name"]: f["description"] for f in _declarado(servidor)}
    for ferramenta in cliente.pedir("tools/list")["tools"]:
        assert ferramenta["description"] == declaradas[ferramenta["name"]], (
            f"{servidor}: a descrição de {ferramenta['name']!r} no fio não é a "
            "declarada em listar_ferramentas()."
        )


def test_h6_os_parametros_no_fio_sao_os_declarados(servidor_vivo):
    servidor, cliente = _vivo(servidor_vivo)
    declaradas = {f["name"]: f["inputSchema"] for f in _declarado(servidor)}
    ferramentas = cliente.pedir("tools/list")["tools"]

    for ferramenta in ferramentas:
        declarado = declaradas[ferramenta["name"]]
        no_fio = ferramenta["inputSchema"]

        assert set(no_fio.get("properties", {})) == set(declarado["properties"]), (
            f"{servidor}: os parâmetros de {ferramenta['name']!r} no fio são "
            f"{sorted(no_fio.get('properties', {}))} e os declarados são "
            f"{sorted(declarado['properties'])}. O SDK deriva o schema da "
            "ASSINATURA da função registrada em main(), não do inputSchema — "
            "então divergir aqui é o modelo vendo outra ferramenta."
        )

        esperado_obrigatorio = set(declarado.get("required", []))
        no_fio_obrigatorio = set(no_fio.get("required", []))
        assert no_fio_obrigatorio == esperado_obrigatorio, (
            f"{servidor}: {ferramenta['name']!r} exige {sorted(no_fio_obrigatorio)} "
            f"no fio e {sorted(esperado_obrigatorio)} na declaração. No SDK, o que "
            "define obrigatório é a ausência de default na assinatura."
        )


def test_h7_a_descricao_de_cada_parametro_chega_ao_modelo(servidor_vivo):
    servidor, cliente = _vivo(servidor_vivo)
    # Achado desta sessão: o SDK monta o schema a partir da assinatura, e a
    # descrição escrita no `inputSchema` declarado NÃO viajava. O modelo recebia
    # `{"title": "Dia", "type": "string"}` no lugar de "'hoje', 'amanhã' ou uma
    # data como 26/08/2026" — texto escrito com cuidado e entregue a ninguém.
    # A cura é `Annotated[..., Field(description=...)]` na assinatura de main().
    declaradas = {f["name"]: f["inputSchema"] for f in _declarado(servidor)}
    ferramentas = cliente.pedir("tools/list")["tools"]

    for ferramenta in ferramentas:
        declarado = declaradas[ferramenta["name"]]["properties"]
        no_fio = ferramenta["inputSchema"].get("properties", {})
        for parametro, forma in declarado.items():
            if not forma.get("description"):
                continue
            assert no_fio.get(parametro, {}).get("description"), (
                f"{servidor}: o parâmetro {parametro!r} de {ferramenta['name']!r} "
                "tem descrição declarada e nenhuma no fio. Quem lê o schema é o "
                "modelo, e ele está lendo um schema mais pobre do que o escrito."
            )


def test_h8_todo_enum_declarado_chega_ao_modelo(servidor_vivo):
    servidor, cliente = _vivo(servidor_vivo)
    # O `enum` é o que ensina o modelo que só existem quatro RUs. Sem ele no
    # fio, o modelo inventa um id e recebe negativa da allowlist — o erro certo
    # pela via mais cara, e depois de uma requisição inútil.
    declaradas = {f["name"]: f["inputSchema"] for f in _declarado(servidor)}
    ferramentas = cliente.pedir("tools/list")["tools"]

    for ferramenta in ferramentas:
        declarado = declaradas[ferramenta["name"]]["properties"]
        no_fio = ferramenta["inputSchema"].get("properties", {})
        for parametro, forma in declarado.items():
            esperados = forma.get("enum") or (forma.get("items") or {}).get("enum")
            if not esperados:
                continue
            texto = str(no_fio.get(parametro, {}))
            for valor in esperados:
                assert f"'{valor}'" in texto or f'"{valor}"' in texto, (
                    f"{servidor}: {parametro!r} declara o valor {valor!r} num "
                    f"enum que não chega ao fio. O modelo vê {texto[:200]}."
                )


def test_h9_a_descoberta_de_servidores_nao_pode_vir_vazia():
    # Sem isto, um glob que deixe de casar transforma a suíte inteira em zero
    # teste — verde, e verificando nada. É o mesmo raciocínio do R1/T1.
    servidores = descobrir_servidores()
    assert servidores, (
        "nenhum servidor encontrado em usp_mcp/*/server.py. Se a estrutura do "
        "pacote mudou, este teste é o único aviso de que a suíte de handshake "
        "parou de cobrir alguma coisa."
    )
    for esperado in ("usp_mcp.moodle.server", "usp_mcp.jupiter.server",
                     "usp_mcp.rucard.server"):
        assert esperado in servidores, f"{esperado} sumiu da descoberta"


def test_h10_o_skip_sem_sdk_diz_o_motivo_por_escrito():
    # Como o R44/T40 da camada live: "não rodou" e "não rodou, e aqui está por
    # quê" são coisas diferentes (Invariante 6 aplicado à própria suíte).
    assert "mcp" in MOTIVO_SEM_SDK and "requirements.txt" in MOTIVO_SEM_SDK
    assert len(MOTIVO_SEM_SDK) > 80
    if _tem_sdk():
        # E o caso normal é o SDK presente: se ele estiver aqui, os testes acima
        # rodaram de verdade em vez de terem sido pulados em silêncio.
        assert True
