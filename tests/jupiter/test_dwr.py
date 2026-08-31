"""T4-T12: decodificar o envelope DWR.

O Jupiter devolve HTTP 200 no erro (§4.5 do recon). Quem discriminar por
status code produz exatamente o silêncio que o Invariante 6 proíbe — daí T6.
"""
import pytest

from conftest import fonte_de
from usp_mcp.jupiter import dwr

pytestmark = pytest.mark.contrato


def test_t4_objeto_unico_vira_mapa_de_26_campos(psi3323, ptc3314):
    for bruto, sigla in ((psi3323, "PSI3323"), (ptc3314, "PTC3314")):
        o = dwr.decodificar(bruto)
        assert isinstance(o, dict), f"{sigla}: objeto único não virou mapa"
        assert len(o) == 26, f"{sigla}: pubObterDisciplina tem 26 campos, veio {len(o)}"
        assert o["coddis"] == sigla


def test_t5_array_de_um_elemento_nao_colapsa(requisito):
    # A armadilha: a fixture de pré-requisito tem EXATAMENTE 1 elemento. Um
    # decoder que "simplifique" lista de 1 quebra a ferramenta em silêncio.
    r = dwr.decodificar(requisito)
    assert isinstance(r, list), "array de 1 elemento virou objeto"
    assert len(r) == 1
    assert r[0]["coddisreq"] == "MAT2453"


def test_t6_erro_levanta_nunca_devolve_vazio(erro):
    # HTTP 200 nos dois casos. A discriminação é por conteúdo, nunca por status.
    with pytest.raises(dwr.JupiterErro):
        dwr.decodificar(erro)


def test_t7_erro_exposto_nao_carrega_stacktrace_nem_classe_java(erro):
    with pytest.raises(dwr.JupiterErro) as exc:
        dwr.decodificar(erro)
    despejo = "".join((repr(exc.value), str(exc.value), repr(vars(exc.value))))
    for vazamento in ("stackTrace", "javaClassName", "usp.erro.USPException", "br.usp"):
        assert vazamento not in despejo, (
            f"{vazamento!r} sobreviveu ao erro. São 46 frames: ~1.978 tokens "
            "contra ~17 da mensagem — 116x, e é a resposta errada."
        )


def test_t8_mensagem_do_erro_e_a_localized_message_em_portugues(erro):
    with pytest.raises(dwr.JupiterErro) as exc:
        dwr.decodificar(erro)
    assert exc.value.mensagem == "Disciplina inválida ou ainda não ativada !"


def test_t9_escapes_do_envelope(psi3323):
    o = dwr.decodificar(psi3323)
    assert o["nomdis"] == "Laboratório de Eletrônica I", "\\uXXXX não resolvido"
    assert o["dtaatvdis"] == "01/01/2025", "\\/ não desescapado"
    assert o["dtadtvdis"] is None, "null virou string"
    assert "\n" in o["objdis"], "quebra de linha perdida"


def test_t10_envelope_truncado_e_erro_explicito(psi3323):
    truncado = psi3323.replace("//#DWR-END#", "")
    with pytest.raises(dwr.RespostaInvalida):
        dwr.decodificar(truncado)


def test_t11_corpo_html_e_erro_explicito():
    # Rota desconhecida no host cai em 302 para /wsusuario/ (§9 do recon): o
    # corpo que chega é a tela de login, não um envelope DWR.
    html = "<html><head><title>Senha unica USP</title></head><body></body></html>"
    with pytest.raises(dwr.RespostaInvalida):
        dwr.decodificar(html)


def test_t12_decoder_le_sem_executar(psi3323, tmp_path):
    alvo = tmp_path / "efeito.txt"
    hostil = psi3323.replace(
        '{coddis:"PSI3323"',
        '{x:__import__("pathlib").Path(%r).write_text("executou"),coddis:"PSI3323"'
        % str(alvo),
        1,
    )
    try:
        dwr.decodificar(hostil)
    except (dwr.RespostaInvalida, dwr.JupiterErro):
        pass
    assert not alvo.exists(), "o decoder EXECUTOU código vindo do payload"

    fonte = fonte_de(dwr)
    for perigo in ("eval(", "exec(", "literal_eval"):
        assert perigo not in fonte, f"{perigo!r} em dwr.py: o decoder lê, não roda"
