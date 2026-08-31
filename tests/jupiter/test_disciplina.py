"""T26-T33: a ferramenta.

A pergunta do §5 do SPEC1: "essa disciplina tem quantos créditos e qual o
pré-requisito?". Os créditos são incondicionais; o pré-requisito NÃO é —
ele depende do curso (§5.2 do recon), e T30 existe para a ferramenta não
fingir o contrário.

O cliente nasce no corpo de cada teste: numa fixture, o NotImplementedError
viraria erro de setup em vez de falha.
"""
import pytest

from usp_mcp.jupiter import cliente, dwr, ferramentas

pytestmark = pytest.mark.contrato


@pytest.mark.parametrize("entrada", ["PSI3323", "psi3323", "PSI 3323", "  psi 3323  "])
def test_t26_normalizacao_de_sigla(gravador, psi3323, entrada):
    c = cliente.ClienteJupiter(gravador([psi3323]))
    assert ferramentas.disciplina(entrada, cliente=c)["sigla"] == "PSI3323"


@pytest.mark.parametrize("qual,sigla,carga", [("psi", "PSI3323", 45), ("ptc", "PTC3314", 60)])
def test_t27_carga_horaria_e_calculada_nunca_lida(
    gravador, psi3323, ptc3314, qual, sigla, carga
):
    bruto = psi3323 if qual == "psi" else ptc3314
    c = cliente.ClienteJupiter(gravador([bruto]))
    d = ferramentas.disciplina(sigla, cliente=c)

    assert d["carga_horaria_total"] == carga

    cru = dwr.decodificar(bruto)
    assert cru["cgahoreto"] == "0", "a fixture mudou; refaça a medição antes de seguir"
    # Ler cgahoreto devolveria 0 h com cara de resposta certa: o silêncio do
    # Invariante 6 sem erro nenhum no caminho. A fórmula está no §4.3 do recon.
    assert d["carga_horaria_total"] == int(cru["creaul"]) * 15 + int(cru["cretrb"]) * 30


def test_t28_ementa_e_conteudo_programatico_nao_estao_trocados(gravador, psi3323):
    c = cliente.ClienteJupiter(gravador([psi3323]))
    d = ferramentas.disciplina("PSI3323", cliente=c)
    cru = dwr.decodificar(psi3323)

    assert d["ementa"] == cru["pgmrsudis"]
    assert d["programa"] == cru["pgmdis"]
    assert d["ementa"] != d["programa"]


def test_t29_vazios_e_espanhol_omitidos_ingles_sob_pedido(gravador, psi3323):
    c = cliente.ClienteJupiter(gravador([psi3323]))
    d = ferramentas.disciplina("PSI3323", cliente=c)
    assert not [k for k in d if k.endswith(("_en", "_es"))]
    assert not [k for k, v in d.items() if v in ("", None) and k != "pre_requisito"]

    c2 = cliente.ClienteJupiter(gravador([psi3323]))
    d_en = ferramentas.disciplina("PSI3323", cliente=c2, idiomas=("pt", "en"))
    assert d_en["nome_en"] == dwr.decodificar(psi3323)["nomdisigl"]
    assert not [k for k in d_en if k.endswith("_es")], (
        "os 4 campos de espanhol vêm vazios nas duas amostras; espanhol nunca sai"
    )


def test_t30_sem_curso_a_ferramenta_diz_o_que_nao_sabe(gravador, psi3323):
    g = gravador([psi3323])
    d = ferramentas.disciplina("PSI3323", cliente=cliente.ClienteJupiter(g))

    assert d["pre_requisito"] is None
    assert len(g.chamadas) == 1, "consultou o pré-requisito sem ter curso"

    avisos = " ".join(d["avisos"]).lower()
    assert "requisito" in avisos and "curso" in avisos, (
        "Invariante 7: o pré-requisito é condicional ao curso. Omitir calado "
        "é o que o invariante proíbe."
    )
    for mentira in ("sem pré-requisito", "não tem pré-requisito", "nenhum pré-requisito"):
        assert mentira not in avisos, f"afirmou {mentira!r} sem ter consultado"


def test_t31_com_curso_duas_chamadas_e_requisito_estruturado(gravador, psi3323, requisito):
    # As duas respostas são stubs: a Fase 1 nunca capturou disciplina e
    # pré-requisito da MESMA disciplina, então o que este teste cobre offline
    # é a COMPOSIÇÃO de duas chamadas, não o pareamento.
    # O pareamento foi verificado AO VIVO em 31/08 — MAT2454 no curso 3033-0
    # devolve MAT2453 — e está no §9. Trazer isso para cá exigiria capturar
    # as duas fixtures pareadas; enquanto não houver, este teste não o cobre.
    g = gravador([psi3323, requisito])
    d = ferramentas.disciplina("PSI3323", curso=("3033", "0"), cliente=cliente.ClienteJupiter(g))

    assert len(g.chamadas) == 2
    assert g.chamadas[1]["corpo"].count("c0-e") >= 3, "requisito exige coddis+codcur+codhab"

    req = d["pre_requisito"]
    assert isinstance(req, list) and len(req) == 1
    assert req[0]["sigla"] == "MAT2453"
    assert req[0]["tipo"] == "PR"
    assert req[0]["nome"] == "Cálculo Diferencial e Integral I"


def test_t32_erro_da_usp_em_portugues_sem_stacktrace(gravador, erro):
    c = cliente.ClienteJupiter(gravador([erro]))
    with pytest.raises(dwr.JupiterErro) as exc:
        ferramentas.disciplina("ZZZ9999", cliente=c)
    assert exc.value.mensagem == "Disciplina inválida ou ainda não ativada !"
    assert "br.usp" not in str(exc.value)


def test_t33_discrepancia_codcur_e_declarada_nao_resolvida(gravador, psi3323, requisito):
    # §5.1 do recon: o Ciclo Básico Elétrica é 3033 no DWR e 3032 no HTML de
    # listarCursosRequisitos. Não investigado, e não se inventa explicação.
    # Comportamento travado: usar o código recebido sem traduzir E avisar.
    c = cliente.ClienteJupiter(gravador([psi3323, requisito]))
    d = ferramentas.disciplina("PSI3323", curso=("3032", "0"), cliente=c)

    avisos = " ".join(d["avisos"])
    assert "3032" in avisos and "3033" in avisos
    assert "não verificad" in avisos.lower() or "não investigad" in avisos.lower()
