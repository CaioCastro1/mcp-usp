"""T59-T66: o segundo transporte, a política de caminho e a ferramenta.

`listarCursosRequisitos` é GET de HTML — outra superfície que o DWR, e por isso
outra allowlist. O §2 do SPEC1 vale igual aqui: o default é negar, e um buscador
genérico de URL anularia qualquer filtro por nome de consulta.

**Asserção sobre o que FOI ENVIADO, não só sobre a saída** — a lição do T47: o
dublê devolve a fixture aconteça o que acontecer, então um teste que só olha o
resultado fica verde com a sigla trocada.
"""
import pytest

from usp_mcp.jupiter import cliente, erros, ferramentas, politica

pytestmark = pytest.mark.contrato


class GravadorGet:
    """Dublê do transporte GET: guarda a URL pedida e devolve a fixture."""

    def __init__(self, resposta, status=200):
        self.resposta = resposta
        self.status = status
        self.urls = []

    def __call__(self, url, cabecalhos):
        self.urls.append(url)
        return self.status, self.resposta


# --- política de caminho ---------------------------------------------------

def test_t59_caminho_fora_da_allowlist_e_negado():
    """`obterTurma` existe, é do mesmo host e traz nome de professor e sala.
    Não estar na fatia tem que bastar para ser negado."""
    decisao = politica.decidir_caminho("obterTurma")

    assert not decisao.permitida
    assert "obterTurma" in decisao.motivo


def test_t60_o_unico_caminho_permitido_e_o_da_fatia():
    assert politica.decidir_caminho("listarCursosRequisitos").permitida
    assert politica.CAMINHOS_PERMITIDOS == frozenset({"listarCursosRequisitos"})


# --- cliente ---------------------------------------------------------------

def test_t61_a_sigla_enviada_e_a_sigla_pedida(psi3323_html):
    """T47 de novo: sem esta asserção, trocar a sigla por uma constante deixa a
    suíte verde, porque o dublê devolve a mesma fixture de qualquer jeito."""
    transporte = GravadorGet(psi3323_html)
    c = cliente.ClienteJupiter(lambda *a: (200, ""), transporte_get=transporte)

    c.obter_requisitos("PTC3314")

    assert transporte.urls == [
        "https://uspdigital.usp.br/jupiterweb/listarCursosRequisitos?coddis=PTC3314"
    ]


def test_t62_o_cliente_devolve_bytes_nao_texto(psi3323_html):
    """Quem decide o charset é o recorte (ISO-8859-1). Se o cliente decodificar
    por conta, o acento chega corrompido e nenhum teste de contagem pega."""
    transporte = GravadorGet(psi3323_html)
    c = cliente.ClienteJupiter(lambda *a: (200, ""), transporte_get=transporte)

    assert isinstance(c.obter_requisitos("PSI3323"), bytes)


def test_t63_status_diferente_de_200_vira_erro_legivel(psi3323_html):
    transporte = GravadorGet(psi3323_html, status=500)
    c = cliente.ClienteJupiter(lambda *a: (200, ""), transporte_get=transporte)

    with pytest.raises(erros.RespostaInvalida, match="500"):
        c.obter_requisitos("PSI3323")


def test_t64_a_segunda_pergunta_igual_nao_vai_a_usp(psi3323_html):
    """Invariante 5. Requisito muda por currículo, não por pergunta."""
    transporte = GravadorGet(psi3323_html)
    c = cliente.ClienteJupiter(lambda *a: (200, ""), transporte_get=transporte)

    c.obter_requisitos("PSI3323")
    c.obter_requisitos("PSI3323")

    assert len(transporte.urls) == 1


# --- ferramenta ------------------------------------------------------------

def test_t65_cada_curriculo_sai_marcado_por_pertencer_ao_ingresso(
    mat2455_html, ingresso_poli, colegiados, gravador
):
    """3033 consta na lista de ingresso; 3032 não. A marca não diz "extinto" —
    ênfase e módulo também ficam de fora da lista, e o JupiterWeb não distingue
    os três casos (§9, 14/09)."""
    c = cliente.ClienteJupiter(
        gravador([colegiados, ingresso_poli]),
        transporte_get=GravadorGet(mat2455_html),
    )
    ficha = ferramentas.requisitos("MAT2455", cliente=c)
    por_curso = {b["codcur"]: b for b in ficha["curriculos"]}

    assert por_curso["3033"]["ingresso"] is True
    assert por_curso["3032"]["ingresso"] is False


def test_t66_pagina_sem_curriculo_avisa_em_vez_de_devolver_lista_vazia(
    ptc3313_html, ingresso_poli, colegiados, gravador
):
    """Invariante 7. Lista vazia aqui seria lida como "não precisa de nada", e
    a fronteira de ênfase/módulo é justamente onde isso engana mais."""
    c = cliente.ClienteJupiter(
        gravador([colegiados, ingresso_poli]),
        transporte_get=GravadorGet(ptc3313_html),
    )
    ficha = ferramentas.requisitos("PTC3313", cliente=c)

    assert ficha["curriculos"] == []
    assert any("não conclua" in a.lower() for a in ficha["avisos"])


# --- T81: agrupar currículos com a mesma combinação de exigências (14/09) -----


def _mat2455(mat2455_html, ingresso_poli, colegiados):
    from usp_mcp.jupiter import cliente as _cliente, ferramentas
    from tests.jupiter.conftest import Gravador

    c = _cliente.ClienteJupiter(
        Gravador([colegiados, ingresso_poli]), transporte_get=GravadorGet(mat2455_html)
    )
    return ferramentas.requisitos("MAT2455", cliente=c)


def test_t81_mat2455_tem_23_curriculos_em_4_combinacoes(mat2455_html, ingresso_poli, colegiados):
    from usp_mcp.jupiter import ferramentas

    grupos = ferramentas.agrupar_curriculos(_mat2455(mat2455_html, ingresso_poli, colegiados)["curriculos"])

    assert len(grupos) == 4
    assert sum(len(membros) for _, membros in grupos) == 23
    assert [len(membros) for _, membros in grupos] == [13, 7, 2, 1], "maiores primeiro"


def test_t81b_o_tipo_separa_grupos_mesmo_com_as_mesmas_siglas(mat2455_html, ingresso_poli, colegiados):
    from usp_mcp.jupiter import ferramentas

    grupos = ferramentas.agrupar_curriculos(_mat2455(mat2455_html, ingresso_poli, colegiados)["curriculos"])
    por_codcur = {c["codcur"]: chave for chave, membros in grupos for c in membros}

    # 3250 exige MAT2454 + MAT3458 como requisito DURO; 3033 exige as mesmas como
    # FRACO. Mesmas siglas, grupos diferentes — é a informação que decide a matrícula.
    assert por_codcur["3250"] != por_codcur["3033"]
    assert {s for s, _, _, _ in por_codcur["3250"]} == {s for s, _, _, _ in por_codcur["3033"]}
    # 3033, 3032 e 3045 exigem a mesma coisa nos mesmos termos: um grupo só.
    assert por_codcur["3033"] == por_codcur["3032"] == por_codcur["3045"]
    # Os sete do projeto piloto (2000101) ficam juntos.
    piloto = {"3023", "3073", "3084", "3093", "3123", "3201", "3251"}
    assert len({por_codcur[c] for c in piloto}) == 1


def test_t81c_curriculo_sem_exigencia_forma_o_grupo_vazio_por_ultimo():
    from usp_mcp.jupiter import ferramentas

    a = {"codcur": "1", "exigencias": [{"sigla": "X", "nome": "x", "tipo": "requisito", "rotulo": "Requisito"}]}
    vazio = {"codcur": "2", "exigencias": []}
    grupos = ferramentas.agrupar_curriculos([vazio, a])
    assert grupos[-1][0] == () and grupos[-1][1] == [vazio]
