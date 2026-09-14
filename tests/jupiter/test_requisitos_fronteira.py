"""T67-T73: a fronteira MCP da fatia de requisitos, e o bug que ela corrige.

O `formatar` que estava na `main` imprimia correquisito sob o rótulo
"Pré-requisito:". Não é omissão — é resposta errada: PSI3322 pode ser cursada
JUNTO com PSI3323, e o aluno que lesse a saída adiaria a matrícula por um ano.
"""
import pytest

from tests.jupiter.conftest import Gravador
from usp_mcp.jupiter import cliente, server
from tests.jupiter.test_requisitos_cliente import GravadorGet

pytestmark = pytest.mark.politica


def test_t67_o_servidor_expoe_duas_ferramentas():
    nomes = [f["name"] for f in server.listar_ferramentas()]

    assert nomes == ["disciplina", "requisitos"]


def test_t68_requisitos_pede_so_a_sigla():
    """Nenhum `codcur` na superfície: a medição de 14/09 mostrou que o código
    descobrível é justamente o que não responde."""
    (ferramenta,) = [f for f in server.listar_ferramentas() if f["name"] == "requisitos"]
    schema = ferramenta["inputSchema"]

    assert schema["required"] == ["sigla"]
    assert set(schema["properties"]) == {"sigla"}
    for vazamento in ("codcur", "codhab", "DWR", "listarCursosRequisitos"):
        assert vazamento not in ferramenta["description"]


def test_t69_a_descricao_diz_que_a_resposta_e_por_curriculo():
    (ferramenta,) = [f for f in server.listar_ferramentas() if f["name"] == "requisitos"]
    descricao = ferramenta["description"].lower()

    assert "currículo" in descricao or "curso" in descricao
    assert "correquisito" in descricao or "junto" in descricao


def test_t70_correquisito_nao_sai_como_pre_requisito(
    psi3323_html, ingresso_poli, colegiados
):
    """O bug de 31/08, agora travado: o rótulo tem que dizer que cursa junto."""
    c = cliente.ClienteJupiter(
        Gravador([colegiados, ingresso_poli]),
        transporte_get=GravadorGet(psi3323_html),
    )
    saida = server.chamar_ferramenta("requisitos", {"sigla": "PSI3323"}, cliente=c)

    assert "PSI3322" in saida
    assert "junto" in saida.lower()
    linha = next(l for l in saida.splitlines() if "PSI3322" in l)
    assert "pré-requisito" not in linha.lower()


def test_t71_requisito_fraco_e_duro_saem_diferentes(
    mat2455_html, ingresso_poli, colegiados
):
    """Em 3032 dá para matricular devendo Cálculo II; em 3250 não. Achatar os
    dois apaga a informação que decide a matrícula."""
    c = cliente.ClienteJupiter(
        Gravador([colegiados, ingresso_poli]),
        transporte_get=GravadorGet(mat2455_html),
    )
    saida = server.chamar_ferramenta("requisitos", {"sigla": "MAT2455"}, cliente=c)

    assert "devendo" in saida.lower()
    assert saida.count("3032") >= 1 and saida.count("3250") >= 1


def test_t72_o_silencio_do_ptc3313_chega_ao_modelo(
    ptc3313_html, ingresso_poli, colegiados
):
    """Invariante 6: se a saída não disser, o modelo conclui que não há
    exigência — que é exatamente a conclusão errada na fronteira da ênfase."""
    c = cliente.ClienteJupiter(
        Gravador([colegiados, ingresso_poli]),
        transporte_get=GravadorGet(ptc3313_html),
    )
    saida = server.chamar_ferramenta("requisitos", {"sigla": "PTC3313"}, cliente=c)

    assert "não conclua" in saida.lower()
    assert "ênfase" in saida.lower()


def test_t73_disciplina_sem_curso_aponta_para_requisitos(gravador, psi3323):
    """Antes, pedia um par (codcur, codhab) que ninguém sabe de cabeça — e que
    a medição mostrou ser o par errado quando alguém sabe."""
    c = cliente.ClienteJupiter(gravador([psi3323]))
    saida = server.chamar_ferramenta("disciplina", {"sigla": "PSI3323"}, cliente=c)

    assert "requisitos" in saida


@pytest.mark.parametrize(
    "marca,fraco,esperado",
    [('stamtrrcp:"S"', True, "devendo"), ('stamtrrcp:"N"', False, "pré-requisito")],
)
def test_t76_o_caminho_dwr_tambem_distingue_fraco_de_duro(
    psi3323, requisito, marca, fraco, esperado
):
    """`disciplina` com curso lê `pubListarRequisitoDisciplina`, e ali o
    discriminador é `stamtrrcp` — 'S' é o "Requisito fraco" da página.

    Sem isto, a mesma exigência sai como "Pré-requisito" por uma ferramenta e
    como "Requisito fraco" pela outra, para o mesmo par. Duas respostas
    diferentes para a mesma pergunta é pior do que uma incompleta.

    A fixture real de MAT2454 vem com `S` — MAT2453 é exigência FRACA dela. O
    caso duro nasce trocando só essa letra, para as duas metades virem da mesma
    forma de resposta e não de um envelope inventado.
    """
    from usp_mcp.jupiter import ferramentas

    c = cliente.ClienteJupiter(
        Gravador([psi3323, requisito.replace('stamtrrcp:"S"', marca)])
    )

    ficha = ferramentas.disciplina("PSI3323", ("3032", "0"), cliente=c)
    saida = server.formatar(ficha)

    assert ficha["pre_requisito"][0]["fraco"] is fraco
    assert esperado in saida.lower()


def test_t77_o_silencio_nao_escolhe_a_causa_que_nao_sabe(
    ptc3313_html, ingresso_poli, colegiados
):
    """Zero currículo tem DUAS causas possíveis e elas são indistinguíveis daqui.

    MAT2453 é Cálculo I, primeira do currículo: o silêncio dela é ausência real.
    PTC3313 é de ênfase: o silêncio é falta de registro. A página devolve a
    mesma coisa para as duas, e a saída dizia "da ênfase em diante esse endpoint
    costuma não ter registro" — explicação absurda para Cálculo I, e é o que
    uma pergunta de aceite pegou.

    O Invariante 7 não pede que a ferramenta saiba: pede que ela não invente
    qual das duas é.
    """
    c = cliente.ClienteJupiter(
        Gravador([colegiados, ingresso_poli]),
        transporte_get=GravadorGet(ptc3313_html),
    )
    saida = server.chamar_ferramenta("requisitos", {"sigla": "PTC3313"}, cliente=c)

    # As duas causas aparecem, e nenhuma é apresentada como a provável.
    assert "não conclua" in saida.lower()
    for causa in ("ênfase", "primeira"):
        assert causa in saida.lower(), f"a causa {causa!r} não é oferecida"
    for ranking in ("provavelmente", "costuma", "mais provável"):
        assert ranking not in saida.lower(), (
            f"{ranking!r} rankeia uma causa que a ferramenta não consegue medir"
        )
