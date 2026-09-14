"""T49-T58: o recorte da página de requisitos por curso.

A pergunta do §5 do SPEC1 que a fatia de 31/08 deixou pela metade: "e qual o
pré-requisito?". A medição de 14/09 (§9) mostrou que ela não se responde pelo
curso — o único `codcur` descobrível pela API devolve zero linha para as
disciplinas de 6º semestre — e sim pela sigla.

Estes testes travam o recorte: 30 kB de HTML viram uma lista de currículos, e
**nenhuma das quatro formas de ausência** pode sair parecendo "não precisa de
nada".
"""
import pytest

from usp_mcp.jupiter import requisitos

pytestmark = pytest.mark.contrato


def test_t49_um_curriculo_vira_um_bloco(psi3323_html):
    """PSI3323 aparece sob um único currículo, o 3032 (medido em 14/09)."""
    blocos = requisitos.recortar(psi3323_html)

    assert len(blocos) == 1
    assert blocos[0].codcur == "3032"


def test_t50_o_bloco_carrega_habilitacao_periodo_e_ideal(psi3323_html):
    """Sem a habilitação, dois currículos do mesmo curso ficam indistinguíveis
    na saída — e o 3032 e o 3033 têm exatamente o mesmo nome de habilitação."""
    b = requisitos.recortar(psi3323_html)[0]

    assert b.nome_curso == "Engenharia"
    assert b.habilitacao == "Ciclo Básico - Engenharia Elétrica"
    assert b.periodo == "integral"
    assert b.periodo_ideal == 6


def test_t51_o_acento_sobrevive_ao_iso_8859_1(mat2455_html):
    """O JupiterWeb serve ISO-8859-1. Decodificar como UTF-8 estoura, e
    decodificar errado entrega 'CÃ¡lculo' — que passa despercebido em teste
    que só conta linhas."""
    exigencias = [e for b in requisitos.recortar(mat2455_html) for e in b.exigencias]

    assert any(e.nome == "Cálculo Diferencial e Integral II" for e in exigencias)


def test_t52_as_exigencias_vem_com_sigla_e_nome(psi3323_html):
    b = requisitos.recortar(psi3323_html)[0]

    assert [(e.sigla, e.nome) for e in b.exigencias] == [
        ("PSI3322", "Eletrônica II")
    ]


def test_t53_os_23_curriculos_de_mat2455_sao_recortados(mat2455_html):
    """A fixture tem 23 blocos: o recorte não pode parar no primeiro nem
    engolir os vazios (Invariante 7 — sem limite silencioso)."""
    blocos = requisitos.recortar(mat2455_html)

    assert len(blocos) == 23
    assert [b.codcur for b in blocos][:4] == ["3021", "3022", "3023", "3032"]


def test_t54_o_curriculo_piloto_exige_disciplina_de_codigo_numerico(mat2455_html):
    """3023 é o Civil novo, e ele exige `2000101` — código só de dígitos.

    Este teste existe porque a medição de 14/09 errou aqui: o parser de
    exploração pedia letras na sigla, não via `2000101`, e eu registrei sete
    currículos como "sem requisito cadastrado". Eles têm — em outro
    vocabulário. Uma sigla que não casa com o formato esperado não pode virar
    ausência silenciosa (Invariante 7); é o mesmo erro do limite silencioso de
    20 do calendário, agora num regex.
    """
    por_curso = {b.codcur: b for b in requisitos.recortar(mat2455_html)}

    assert [e.sigla for e in por_curso["3023"].exigencias] == ["2000101"]
    assert por_curso["3023"].exigencias[0].nome.startswith("Fundamentos Científicos")


def test_t55_a_adocao_do_piloto_e_parcial_entre_os_cursos_de_ingresso(mat2455_html):
    """Sete currículos de ingresso já pedem o piloto; Elétrica, Mecânica e
    Ambiental seguem no vocabulário antigo. Achatar isso numa regra por
    'curso vigente' daria a resposta errada para metade da Poli."""
    por_curso = {b.codcur: b for b in requisitos.recortar(mat2455_html)}
    piloto = {c for c in ("3023", "3073", "3084", "3093", "3123", "3201", "3251")
              if [e.sigla for e in por_curso[c].exigencias] == ["2000101"]}
    antigo = {c for c in ("3033", "3045", "3152")
              if "MAT2454" in [e.sigla for e in por_curso[c].exigencias]}

    assert len(piloto) == 7
    assert len(antigo) == 3


def test_t56_pagina_sem_curso_nenhum_recorta_zero(ptc3313_html):
    """PTC3313: 26.623 B e nenhum bloco. Não é erro — é ausência de registro,
    e quem chama precisa poder distinguir isso de 'a página não carregou'."""
    assert requisitos.recortar(ptc3313_html) == []


@pytest.mark.parametrize(
    "codcur,sigla,tipo,rotulo",
    [
        ("3250", "MAT2454", "requisito", "Requisito"),
        ("3032", "MAT2454", "requisito_fraco", "Requisito fraco"),
    ],
)
def test_t57_o_mesmo_par_e_duro_num_curriculo_e_fraco_noutro(
    mat2455_html, codcur, sigla, tipo, rotulo
):
    """O tipo é propriedade do CURRÍCULO, não da dupla de disciplinas (§9,
    14/09). Achatar os dois numa resposta só perde a informação que decide a
    matrícula: em 3032 dá para cursar devendo Cálculo II, em 3250 não."""
    por_curso = {b.codcur: b for b in requisitos.recortar(mat2455_html)}
    exigencia = next(
        e for e in por_curso[codcur].exigencias if e.sigla == sigla
    )

    assert exigencia.tipo == tipo
    assert exigencia.rotulo == rotulo


def test_t58_correquisito_nao_e_pre_requisito(psi3323_html):
    """PSI3322 é 'Indicação de Conjunto': cursa JUNTO. O `formatar` que está na
    main anuncia isso como exigência prévia — é resposta errada, não omissão."""
    exigencia = requisitos.recortar(psi3323_html)[0].exigencias[0]

    assert exigencia.tipo == "correquisito"
    assert exigencia.rotulo == "Indicação de Conjunto"
