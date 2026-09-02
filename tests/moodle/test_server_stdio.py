"""T78-T81: o adaptador stdio do Moodle, contra o SDK realmente instalado.

Fecha o buraco que custou caro nesta trilha: o `main()` daqui foi escrito contra
a API antiga do SDK (`Server` + `@list_tools`) e **nunca funcionou**, com a suíte
99/99 verde, porque nenhum teste o alcançava. O Jupiter ganhou o teste
equivalente em 31/08; aqui ele estava registrado no backlog como impossível
"porque falta um token".

**A causa registrada estava errada, e medi antes de escrever isto:** três dos
quatro testes não tocam credencial nenhuma — registrar ferramenta no SDK, derivar
schema e falhar legível sem o SDK não dependem de token. O que faltava era
`chamar_ferramenta` aceitar cliente injetável, como a do Jupiter já aceitava.
Aceita desde 31/08, e por isso o T80 existe.

Só `run()` é substituído — a chamada que bloquearia no stdin. Tudo antes dela é
produção casando com o SDK real.
"""
import asyncio
import sys

import pytest

from tests.moodle.conftest import ClienteFalso
from usp_mcp.moodle import disciplinas as disc
from usp_mcp.moodle import server


@pytest.fixture(autouse=True)
def _cache_limpo():
    disc.limpar_cache()
    yield
    disc.limpar_cache()


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
    return capturado


@pytest.mark.contrato
def test_t78_main_registra_as_tres_ferramentas(servidor_montado):
    """O bug histórico em uma asserção: API errada do SDK e nada aqui roda."""
    ferramentas = asyncio.run(servidor_montado["servidor"].list_tools())

    assert sorted(f.name for f in ferramentas) == [
        "baixar_arquivo",
        "material",
        "o_que_vence",
    ]
    assert servidor_montado["transporte"] == "stdio", (
        "o adaptador deixou de escutar em stdio — o .mcp.json fala stdio"
    )
    # Se a descrição registrada divergir da declarada, T43 audita um texto que
    # o modelo nunca vê.
    declaradas = {f["name"]: f["description"] for f in server.listar_ferramentas()}
    for f in ferramentas:
        assert f.description == declaradas[f.name]


@pytest.mark.contrato
def test_t79_schema_derivado_casa_com_o_declarado(servidor_montado):
    """O SDK deriva o schema da ASSINATURA; `listar_ferramentas` declara à mão.

    Divergir é o erro que só aparece em uso real: o modelo lê um parâmetro que o
    adaptador não aceita, ou deixa de ver um que existe.
    """
    ferramentas = asyncio.run(servidor_montado["servidor"].list_tools())
    declaradas = {
        f["name"]: set(f["inputSchema"]["properties"])
        for f in server.listar_ferramentas()
    }
    for f in ferramentas:
        derivados = set(f.input_schema["properties"])
        assert derivados == declaradas[f.name], (
            f"{f.name}: divergem {derivados ^ declaradas[f.name]}"
        )


@pytest.mark.contrato
def test_t80_call_tool_de_material_atravessa_ate_a_fixture(
    servidor_montado, monkeypatch, disciplinas_brutas, conteudo_bruto
):
    """Ponta a ponta pelo SDK, offline e SEM credencial nenhuma.

    Era isto que o §9 dizia ser impossível na fronteira do Moodle. O que faltava
    não era token — era injeção.
    """
    falso = ClienteFalso({
        "core_webservice_get_site_info": {"userid": 999},
        "core_enrol_get_users_courses": disciplinas_brutas,
        "core_course_get_contents": conteudo_bruto,
    })
    monkeypatch.setattr(server, "ClienteMoodle", lambda **kw: falso)

    resultado = asyncio.run(
        servidor_montado["servidor"].call_tool("material", {"disciplina": "psi 3323"})
    )

    assert not resultado.is_error, resultado
    texto = resultado.content[0].text
    assert "PSI3323" in texto
    assert "programacao_e_regras" in texto, "o acervo não atravessou o SDK"

    # Asserção sobre o parâmetro ENVIADO: o dublê devolve a fixture aconteça o
    # que acontecer, então só isto pega uma resolução de sigla trocada.
    assert falso.params_de("core_course_get_contents")["courseid"] == 142033

    # Invariante 3 atravessando a fronteira inteira, não só a projeção.
    assert "pluginfile.php" not in texto


@pytest.mark.contrato
def test_t81_sem_o_sdk_a_falha_e_legivel_e_diz_a_cura(monkeypatch):
    monkeypatch.setitem(sys.modules, "mcp.server", None)

    with pytest.raises(SystemExit) as exc:
        server.main()

    mensagem = str(exc.value)
    assert "mcp" in mensagem
    assert "pip install -r requirements.txt" in mensagem
