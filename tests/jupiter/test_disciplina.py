"""T26-T33: a ferramenta.

A pergunta do §5 do SPEC1: "essa disciplina tem quantos créditos e qual o
pré-requisito?". Os créditos são incondicionais; o pré-requisito NÃO é —
ele depende do curso (§5.2 do recon), e T30 existe para a ferramenta não
fingir o contrário.

O cliente nasce no corpo de cada teste: numa fixture, o NotImplementedError
viraria erro de setup em vez de falha.
"""
import pytest

from usp_mcp.jupiter import cliente, dwr, erros, ferramentas

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
    d = ferramentas.disciplina("PSI3323", cliente=c, secoes=("ementa", "programa"))
    cru = dwr.decodificar(psi3323)

    assert d["ementa"] == cru["pgmrsudis"]
    assert d["programa"] == cru["pgmdis"]
    assert d["ementa"] != d["programa"]


def test_t29_vazios_e_espanhol_omitidos_ingles_sob_pedido(gravador, psi3323):
    c = cliente.ClienteJupiter(gravador([psi3323]))
    d = ferramentas.disciplina("PSI3323", cliente=c)
    assert not [k for k in d if k.endswith(("_en", "_es"))]
    assert not [k for k, v in d.items() if v in ("", None)]

    c2 = cliente.ClienteJupiter(gravador([psi3323]))
    d_en = ferramentas.disciplina("PSI3323", cliente=c2, idiomas=("pt", "en"))
    assert d_en["nome_en"] == dwr.decodificar(psi3323)["nomdisigl"]
    assert not [k for k in d_en if k.endswith("_es")], (
        "os 4 campos de espanhol vêm vazios nas duas amostras; espanhol nunca sai"
    )


def test_t30_a_ferramenta_diz_onde_esta_o_pre_requisito_em_vez_de_calar(gravador, psi3323):
    g = gravador([psi3323])
    d = ferramentas.disciplina("PSI3323", cliente=cliente.ClienteJupiter(g))

    assert len(g.chamadas) == 1, "uma ficha é UMA chamada"
    assert "pre_requisito" not in d, "o pré-requisito é da ferramenta `requisitos` desde 14/09"

    avisos = " ".join(d["avisos"]).lower()
    assert "requisitos" in avisos, "Invariante 7: diz onde está, em vez de omitir calado"
    for mentira in ("sem pré-requisito", "não tem pré-requisito", "nenhum pré-requisito"):
        assert mentira not in avisos, f"afirmou {mentira!r} sem ter consultado"


def test_t32_erro_da_usp_em_portugues_sem_stacktrace(gravador, erro):
    c = cliente.ClienteJupiter(gravador([erro]))
    with pytest.raises(dwr.JupiterErro) as exc:
        ferramentas.disciplina("ZZZ9999", cliente=c)
    assert exc.value.mensagem == "Disciplina inválida ou ainda não ativada !"
    assert "br.usp" not in str(exc.value)


# --- T80: a ficha por seção (14/09/2026) -------------------------------------


def test_t80_por_padrao_vem_o_cabecalho_e_a_ementa_e_mais_nada(gravador, ptc3314):
    d = ferramentas.disciplina("PTC3314", cliente=cliente.ClienteJupiter(gravador([ptc3314])))

    assert d["creditos_aula"] == 4 and d["carga_horaria_total"] == 60
    assert "ementa" in d
    for fora in ("objetivos", "programa", "bibliografia",
                 "metodo_avaliacao", "criterio_avaliacao", "norma_recuperacao"):
        assert fora not in d, f"{fora} veio sem ser pedido"
    assert d["secoes"] == ["ementa"]
    assert d["secoes_omitidas"] == ["objetivos", "programa", "bibliografia", "avaliacao"]
    assert d["avisos"] == [ferramentas.AVISO_PRE_REQUISITO]


def test_t80b_avaliacao_junta_os_tres_campos(gravador, ptc3314):
    d = ferramentas.disciplina(
        "PTC3314", cliente=cliente.ClienteJupiter(gravador([ptc3314])), secoes=("avaliacao",)
    )
    assert {"metodo_avaliacao", "criterio_avaliacao", "norma_recuperacao"} <= set(d)
    assert "ementa" not in d
    assert d["secoes_omitidas"] == ["ementa", "objetivos", "programa", "bibliografia"]


def test_t80c_todas_traz_as_cinco_e_nao_omite_nada(gravador, ptc3314):
    d = ferramentas.disciplina(
        "PTC3314", cliente=cliente.ClienteJupiter(gravador([ptc3314])), secoes=ferramentas.SECOES
    )
    for dentro in ("ementa", "objetivos", "programa", "bibliografia", "metodo_avaliacao"):
        assert dentro in d
    assert d["secoes_omitidas"] == []


@pytest.mark.parametrize(
    "pedido,esperado",
    [
        (None, ("ementa",)),
        ([], ("ementa",)),
        (["programa", "ementa"], ("ementa", "programa")),  # ordem da ficha, não do pedido
        (["TODAS"], ferramentas.SECOES),
        (["todas", "ementa"], ferramentas.SECOES),
        (["Avaliacao", "avaliacao"], ("avaliacao",)),
    ],
)
def test_t80d_resolver_secoes(pedido, esperado):
    assert ferramentas.resolver_secoes(pedido) == esperado


def test_t80e_secao_desconhecida_e_erro_legivel_citando_as_validas():
    with pytest.raises(erros.ErroJupiter) as exc:
        ferramentas.resolver_secoes(["horario"])
    mensagem = str(exc.value)
    assert "horario" in mensagem and "ementa" in mensagem and "todas" in mensagem


def test_t80f_paragrafo_repetido_na_fonte_sai_uma_vez(gravador, ptc3314):
    d = ferramentas.disciplina(
        "PTC3314", cliente=cliente.ClienteJupiter(gravador([ptc3314])), secoes=("bibliografia",)
    )
    assert d["bibliografia"].count("Mariotto") == 1
    cru = dwr.decodificar(ptc3314)
    assert cru["dscbbgdis"].count("Mariotto") == 2, (
        "a fixture mudou e a dedupe perdeu o caso que a motivou; refaça a medição"
    )


def test_t80g_a_ferramenta_nao_aceita_curso():
    import inspect

    parametros = inspect.signature(ferramentas.disciplina).parameters
    assert "curso" not in parametros and "codcur" not in parametros
    assert "secoes" in parametros
